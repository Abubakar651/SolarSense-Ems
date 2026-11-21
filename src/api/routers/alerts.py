"""
The signed-in user's alerts: list and mark as read.

Alerts are created from the user's own site data when the list is read (see src/api/alert_rules.py).
Their ids are deterministic, so re-reading inserts nothing new and keeps read state. An alert id that
belongs to another user answers 404, exactly like one that doesn't exist, so ids can't be probed.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import logging
import threading
from typing import Annotated, Any
import uuid

import anyio
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from src.api import alert_rules, insights
from src.api.insights import OutageEventOut
from src.api.site_samples import SiteSampleCache
from src.api.site_soiling import WASH_HORIZON_DAYS, SiteSoilingService, SoilingCollectingError
from src.api.telemetry_history import outage_events
from src.api.user_site import UserSite, load_user_site
from src.api.account_schemas import NOTIFICATION_DEFAULTS, AlertOut
from src.api.db.models import Alert, NotificationPref
from src.api.db.session import get_db, get_read_db
from src.api.deps import CurrentUser, get_current_user, get_now
from src.data_engineering.feature_store import PKT_TZ
from src.forecast.live_forecast import WeatherUnavailable

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])

DbSession = Annotated[Session, Depends(get_db)]
ReadSession = Annotated[Session, Depends(get_read_db)]
Me = Annotated[CurrentUser, Depends(get_current_user)]
Now = Annotated[datetime, Depends(get_now)]


def _enabled_in_app(session: Session, user_id: uuid.UUID) -> set[str]:
    saved = dict(
        session.execute(
            select(NotificationPref.alert_key, NotificationPref.in_app).where(NotificationPref.user_id == user_id)
        ).all()
    )
    return {key for key, (in_app, _email) in NOTIFICATION_DEFAULTS.items() if saved.get(key, in_app)}


# Outages and inverter silences older than this don't raise new alerts.
ALERT_LOOKBACK = timedelta(days=14)
# Longer than any expected outage, so one that started before the lookback edge is seen whole.
OUTAGE_EDGE_MARGIN = timedelta(days=1)


def _event_start(event: OutageEventOut) -> datetime:
    return datetime.combine(date.fromisoformat(event.date), time.fromisoformat(event.start), PKT_TZ)


def _station_candidates(app_state: Any, user_id: uuid.UUID, enabled: set[str]) -> list[alert_rules.AlertCandidate]:
    """Alerts from the recorded station dataset, for the site that owns it. A missing file skips that type."""
    out: list[alert_rules.AlertCandidate] = []
    if "grid_outage" in enabled:
        try:
            out += alert_rules.grid_outage_alerts(user_id, insights.inverter_alarms())
        except insights.DatasetUnavailable:
            logger.warning("Inverter alarm log missing; no recorded grid outage alerts")
    return out


def _panels_dirty_candidates(
    app_state: Any, user_id: uuid.UUID, site: UserSite, now: datetime
) -> list[alert_rules.AlertCandidate]:
    """
    From the site's dust model: the live one, valued at the site's tariff over the days until the next
    washing rain (at most WASH_HORIZON_DAYS, as on the Panels screen). The station's recorded model keeps
    its original rule, and only applies while the station has no live model.
    """
    service: SiteSoilingService | None = getattr(app_state, "site_soiling", None)
    calculator = getattr(app_state, "loss_calculator", None)
    if service is None or calculator is None:
        return []
    try:
        # This route runs in a worker thread; the model's weather fetch runs on the app's event loop.
        soiling, weather = anyio.from_thread.run(service.soiling, site, now)
    except (SoilingCollectingError, WeatherUnavailable):
        return []
    except insights.DatasetUnavailable:
        logger.warning("Soiling history missing; no panel alerts")
        return []
    if soiling.source == "recorded":
        decision = calculator.evaluate_daily_cleaning_decision(daily_kwh_lost=soiling.daily_loss_kwh)
        return alert_rules.panels_dirty_alert(user_id, soiling.as_of, soiling.daily_loss_kwh, decision)
    rain_in = weather.days_until_rain if weather is not None else None
    decision = calculator.evaluate_daily_cleaning_decision(
        daily_kwh_lost=soiling.daily_loss_kwh,
        days_until_rain=min(WASH_HORIZON_DAYS if rain_in is None else rain_in, WASH_HORIZON_DAYS),
        tariff_rate_override_pkr_per_kwh=soiling.tariff_pkr_per_kwh,
    )
    return alert_rules.panels_dirty_alert(
        user_id, soiling.as_of, soiling.daily_loss_kwh, decision, event_key=f"live:{soiling.wash_date}"
    )


def _candidates(
    app_state: Any, user_id: uuid.UUID, site: UserSite | None, enabled: set[str], now: datetime
) -> list[alert_rules.AlertCandidate]:
    """Alerts the user's own data supports; none from any other site."""
    if site is None:
        return []
    out: list[alert_rules.AlertCandidate] = []
    if site.is_station:
        out += _station_candidates(app_state, user_id, enabled)
    if "panels_dirty" in enabled:
        out += _panels_dirty_candidates(app_state, user_id, site, now)

    if enabled & {"grid_outage", "inverter_offline"}:
        cache: SiteSampleCache = app_state.site_samples
        since = now - ALERT_LOOKBACK
        if "grid_outage" in enabled:
            # Read from before the lookback edge so an outage the edge cuts through keeps its real start;
            # it is then left out, instead of reappearing with a later start on every read.
            samples = cache.samples(site.site_id, since - OUTAGE_EDGE_MARGIN, now)
            events = [e for e in outage_events(samples) if _event_start(e) >= since]
            out += alert_rules.logged_outage_alerts(user_id, events)
        if "inverter_offline" in enabled and site.inverter_host is not None:
            # The last sample ever, not just in the lookback: a long silence is the same silence.
            latest = cache.samples(site.site_id, datetime.min.replace(tzinfo=timezone.utc), now)[-1:]
            last = latest[0].recorded_at if latest else None
            out += alert_rules.inverter_offline_alert(user_id, last, site.updated_at, now)

    engine = getattr(app_state, "lesco_engine", None)
    if "peak_soon" in enabled and engine is not None:
        today = now.astimezone(PKT_TZ).date()
        window = engine.get_seasonal_window(today.month)
        out += alert_rules.peak_soon_alert(
            user_id, today.isoformat(), window.peak_start_hour, window.peak_end_hour, now=now
        )
    return out


def _store(session: Session, user_id: uuid.UUID, candidates: list[alert_rules.AlertCandidate]) -> None:
    if not candidates:
        return
    insert = pg_insert if session.get_bind().dialect.name == "postgresql" else sqlite_insert
    stmt = (
        insert(Alert)
        .values(
            [
                {
                    "id": c.id,
                    "user_id": user_id,
                    "severity": c.severity,
                    "title": c.title,
                    "detail": c.detail,
                    "created_at": c.created_at,
                }
                for c in candidates
            ]
        )
    )
    # An outage still running when first seen is stored with its duration so far; later reads refresh the
    # text. created_at and read state are left as they are.
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={"severity": stmt.excluded.severity, "title": stmt.excluded.title, "detail": stmt.excluded.detail},
        )
    )
    session.commit()


class _StoredAlertIds:
    """
    Alerts this process has already written, per user, so a list read only opens a write transaction
    when the data produced something new or changed (every app page reads the list). Losing it is
    harmless: the upsert is idempotent, it just costs one extra write.
    """

    def __init__(self, max_users: int = 10_000) -> None:
        self._ids: dict[uuid.UUID, set[alert_rules.AlertCandidate]] = {}
        self._max_users = max_users
        self._lock = threading.Lock()

    def unseen(self, user_id: uuid.UUID, candidates: list[alert_rules.AlertCandidate]) -> list[alert_rules.AlertCandidate]:
        with self._lock:
            known = self._ids.get(user_id, set())
            return [c for c in candidates if c not in known]

    def remember(self, user_id: uuid.UUID, stored: list[alert_rules.AlertCandidate]) -> None:
        with self._lock:
            if len(self._ids) >= self._max_users and user_id not in self._ids:
                self._ids.clear()
            self._ids.setdefault(user_id, set()).update(stored)


_stored = _StoredAlertIds()


@router.get("", response_model=list[AlertOut])
def list_alerts(
    request: Request,
    session: ReadSession,
    current: Me,
    now: Now,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[AlertOut]:
    """Newest first."""
    site = load_user_site(request.app.state.read_session_factory, current.id)
    candidates = _candidates(request.app.state, current.id, site, _enabled_in_app(session, current.id), now)
    new = _stored.unseen(current.id, candidates)
    if new:
        with request.app.state.session_factory() as write_session:
            _store(write_session, current.id, new)
        _stored.remember(current.id, new)
    rows = session.scalars(
        select(Alert).where(Alert.user_id == current.id).order_by(Alert.created_at.desc()).limit(limit)
    )
    return [
        AlertOut(id=a.id, severity=a.severity, title=a.title, detail=a.detail, created_at=a.created_at, read=a.read_at is not None)  # type: ignore[arg-type]
        for a in rows
    ]


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(session: DbSession, current: Me, now: Now) -> None:
    session.execute(
        update(Alert).where(Alert.user_id == current.id, Alert.read_at.is_(None)).values(read_at=now)
    )
    session.commit()


@router.post("/{alert_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(alert_id: uuid.UUID, session: DbSession, current: Me, now: Now) -> None:
    alert = session.scalar(select(Alert).where(Alert.id == alert_id, Alert.user_id == current.id))
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="alert_not_found")
    if alert.read_at is None:
        alert.read_at = now
        session.commit()
