"""
One site's dust (soiling) model for the Panels screen and the panels_dirty alert.

Live for every site: src/soiling/live_model.py over the site's own complete logged days since its latest
clean event (a wash the user recorded, or a day of washing rain). Until that has enough days:
- the station site keeps the recorded model (insights.soiling_history), as long as no clean event came
  after the recorded data ends (after one, the recorded curve no longer describes the panels);
- every other site is "collecting" (SoilingCollectingError).
A lost kWh is valued at the site's own tariff through the tariff engine, never at a fixed rate.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import math
import uuid

import numpy as np
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool

from src.api import insights
from src.api.db.models import PanelWash
from src.api.insights import DailyEnergyOut, SiteSoilingOut
from src.api.recent_weather import RecentWeather, RecentWeatherService
from src.api.telemetry_history import daily_energy
from src.api.user_site import UserSite
from src.data_engineering.feature_store import PKT_TZ
from src.forecast.live_forecast import TelemetrySample, WeatherUnavailable
from src.optimizer.lesco_2026_tariff_and_dispatch import LescoCY2026TariffEngine, ProsumerRegime2026
from src.soiling.live_model import (
    SoilingCollecting,
    SoilingFit,
    daily_loss_kwh,
    fit_soiling,
    latest_clean_event,
)

# Days the wash advice adds dust up over at most; the Panels screen's wash calculator uses the same window.
WASH_HORIZON_DAYS = 14
# The site's recent export share decides how much of a lost kWh was lost export rather than bought back.
EXPORT_SHARE_DAYS = 30
RECENT_WASHES = 20

SamplesSince = Callable[[datetime], Sequence[TelemetrySample]]


class SoilingCollectingError(Exception):
    """The live model needs more logged days after the clean event (and no recorded model applies)."""

    def __init__(self, collecting: SoilingCollecting) -> None:
        super().__init__("soiling_collecting")
        self.collecting = collecting


@dataclass(frozen=True, slots=True)
class Valuation:
    engine: LescoCY2026TariffEngine
    wash_cost_pkr: float
    # The station owner's contract export rate (station_profile); None for every other site.
    station_export_override_pkr_per_kwh: float | None


# ---------- washes ----------


def load_washes(session_factory: sessionmaker[Session], site_id: uuid.UUID, limit: int = RECENT_WASHES) -> list[date]:
    """The site's latest recorded washes, newest first."""
    with session_factory() as session:
        return list(
            session.scalars(
                select(PanelWash.washed_on)
                .where(PanelWash.site_id == site_id)
                .order_by(PanelWash.washed_on.desc())
                .limit(limit)
            )
        )


def record_wash(session: Session, site_id: uuid.UUID, now: datetime) -> date:
    """Records a wash today (local day of `now`); recording the same day again changes nothing."""
    day = now.astimezone(PKT_TZ).date()
    insert = pg_insert if session.get_bind().dialect.name == "postgresql" else sqlite_insert
    session.execute(
        insert(PanelWash)
        .values(site_id=site_id, washed_on=day, created_at=now)
        .on_conflict_do_nothing(index_elements=["site_id", "washed_on"])
    )
    session.commit()
    return day


# ---------- valuation ----------


def export_share(daily: Sequence[DailyEnergyOut]) -> float:
    """Fraction of the solar energy that was exported over these days (0 without solar)."""
    solar = sum(d.solar_kwh for d in daily)
    exported = sum(d.export_kwh for d in daily)
    return min(1.0, exported / solar) if solar > 0.0 else 0.0


def lost_kwh_value_pkr(site: UserSite, share: float, valuation: Valuation) -> float:
    """
    What one kWh lost to dust costs this site: the share it would have used itself is bought back at the
    all-in Off-Peak rate (solar hours are Off-Peak hours), the share it would have exported is lost at its
    regime's export value. Same blend as the station's soiling status (src/api/main.py).
    """
    engine = valuation.engine
    _, off_peak_all_in = engine.get_all_in_tou_marginal_rates_pkr(
        include_electricity_duty=site.include_electricity_duty, include_fpa_marginal=True
    )
    export_value = engine.marginal_value_of_exported_kwh(
        ProsumerRegime2026(site.prosumer_regime),
        export_rate_override_pkr_per_kwh=valuation.station_export_override_pkr_per_kwh if site.is_station else None,
        include_electricity_duty=site.include_electricity_duty,
    )
    return round((1.0 - share) * float(off_peak_all_in) + share * float(export_value), 2)


# ---------- the model for one site ----------


def _live(
    site: UserSite,
    fit: SoilingFit,
    weather: RecentWeather,
    daily: Sequence[DailyEnergyOut],
    today: date,
    valuation: Valuation,
) -> SiteSoilingOut:
    return SiteSoilingOut(
        wash_date=fit.clean.day.isoformat(),
        as_of=fit.as_of.isoformat(),
        model_pr=[round(float(v), 6) for v in fit.model_pr],
        daily_loss_kwh=round(daily_loss_kwh(fit, today, weather.ghi_on(today), site.sizes.pv_kwp), 3),
        source="live",
        clean_event=fit.clean.kind,
        logged_days_since_clean=fit.fit_days,
        loss_rate_per_day=round(fit.loss_rate_per_day, 6),
        tariff_pkr_per_kwh=lost_kwh_value_pkr(site, export_share(daily[-EXPORT_SHARE_DAYS:]), valuation),
        wash_cost_pkr=valuation.wash_cost_pkr,
    )


def _recorded(
    site: UserSite, logged_days: int, daily: Sequence[DailyEnergyOut], valuation: Valuation
) -> SiteSoilingOut:
    recorded = insights.soiling_history()
    pr = recorded.model_pr
    rate = -math.log(pr[-1] / pr[-2]) if len(pr) >= 2 and pr[-2] > 0 and pr[-1] > 0 else 0.0
    recent = list(daily[-EXPORT_SHARE_DAYS:]) or insights.energy_history().daily[-EXPORT_SHARE_DAYS:]
    return SiteSoilingOut(
        **recorded.model_dump(),
        source="recorded",
        clean_event="wash",
        logged_days_since_clean=logged_days,
        loss_rate_per_day=round(rate, 6),
        tariff_pkr_per_kwh=lost_kwh_value_pkr(site, export_share(recent), valuation),
        wash_cost_pkr=valuation.wash_cost_pkr,
    )


def soiling_for_site(
    site: UserSite,
    weather: RecentWeather | None,
    washes: Sequence[date],
    samples_since: SamplesSince,
    today: date,
    valuation: Valuation,
) -> SiteSoilingOut:
    """
    The site's dust model. `weather` None means it could not be fetched. Raises SoilingCollectingError,
    WeatherUnavailable (non-station site without weather) or insights.DatasetUnavailable (recorded model).
    """
    if weather is None:
        if site.is_station:
            return _recorded(site, 0, [], valuation)
        raise WeatherUnavailable("no recent weather for the dust model")

    clean = latest_clean_event(washes, weather.days, weather.rain_mm, today)
    daily: list[DailyEnergyOut] = []
    if clean is None:
        result: SoilingFit | SoilingCollecting = SoilingCollecting(None, 0)
    else:
        # Days before the weather window have no sunlight to compare with, so they are not read at all.
        start = datetime.combine(max(clean.day + timedelta(days=1), weather.days[0]), time(), PKT_TZ)
        daily = daily_energy(samples_since(start), before=today)
        days = [date.fromisoformat(d.date) for d in daily]
        ghi = [weather.ghi_on(d) for d in days]
        result = fit_soiling(
            clean,
            days,
            [d.solar_kwh for d in daily],
            [np.nan if g is None else g for g in ghi],
            site.sizes.pv_kwp,
        )
    if isinstance(result, SoilingFit):
        return _live(site, result, weather, daily, today, valuation)

    if site.is_station:
        recorded_end = date.fromisoformat(insights.soiling_history().as_of)
        if result.clean is None or result.clean.day <= recorded_end:
            return _recorded(site, result.fit_days, daily, valuation)
    raise SoilingCollectingError(result)


class SiteSoilingService:
    """Wires soiling_for_site to the weather service, the database and the site's logged samples."""

    def __init__(
        self,
        weather: RecentWeatherService,
        session_factory: sessionmaker[Session],
        load_samples: Callable[[uuid.UUID, datetime, datetime], list[TelemetrySample]],
        valuation: Valuation,
    ) -> None:
        self._weather = weather
        self._session_factory = session_factory
        self._load_samples = load_samples
        self.valuation = valuation

    async def soiling(self, site: UserSite, now: datetime) -> tuple[SiteSoilingOut, RecentWeather | None]:
        """The site's model and the weather it used (None when unavailable). Raises as soiling_for_site."""
        today = now.astimezone(PKT_TZ).date()
        try:
            weather: RecentWeather | None = await self._weather.get(today)
        except WeatherUnavailable:
            weather = None

        def compute() -> SiteSoilingOut:
            return soiling_for_site(
                site,
                weather,
                load_washes(self._session_factory, site.site_id),
                lambda start: self._load_samples(site.site_id, start, now),
                today,
                self.valuation,
            )

        # Reads the database and the site's samples: off the event loop.
        return await run_in_threadpool(compute), weather
