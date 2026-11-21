"""
The signed-in user's own data: profile, site (onboarding), settings and report preferences.

Nothing here takes a user or site id from the client. Every query is scoped by the authenticated
user's id, so one account can never read or change another's rows.
"""

from __future__ import annotations

from datetime import time
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from src.api.account_schemas import (
    NOTIFICATION_DEFAULTS,
    BlackoutWindowOut,
    DeleteAccountRequest,
    NotificationPrefOut,
    OnboardingRequest,
    ProfileOut,
    ProfileUpdate,
    ReportPrefs,
    SettingsOut,
    SettingsUpdate,
    SiteOut,
    TariffOut,
    UserOut,
)
from src.api.core.config import AppSettings
from src.api.core.rate_limit import RateLimiter, RateRule
from src.api.core.security import verify_password
from src.api.db.models import BlackoutWindow, NotificationPref, ReportPref, Site, User
from src.api.db.session import get_db, get_read_db
from src.api.deps import (
    CurrentUser,
    TokenVersionCache,
    enforce_limit,
    get_current_user,
    get_rate_limiter,
    get_settings,
    get_token_versions,
)
from src.api.routers.auth import user_out
from src.api.user_site import station_code_for

router = APIRouter(prefix="/api", tags=["Account"])

DELETE_PER_USER = RateRule(limit=5, window_seconds=15 * 60)

DbSession = Annotated[Session, Depends(get_db)]
ReadSession = Annotated[Session, Depends(get_read_db)]
Me = Annotated[CurrentUser, Depends(get_current_user)]


def _load_user(session: Session, current: CurrentUser) -> User:
    user = session.get(User, current.id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    return user


def _load_user_and_site(session: Session, current: CurrentUser) -> tuple[User, Site]:
    """User, site and blackout windows in one query: 401 without the user, 404 without a site."""
    row = (
        session.execute(
            select(User, Site)
            .outerjoin(Site, Site.user_id == User.id)
            .options(joinedload(Site.blackouts))
            .where(User.id == current.id)
        )
        .unique()
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    user, site = row
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="site_not_found")
    return user, site


def _saved_prefs(session: Session, user_id: object) -> dict[str, tuple[bool, bool]]:
    rows = session.execute(
        select(NotificationPref.alert_key, NotificationPref.in_app, NotificationPref.email).where(
            NotificationPref.user_id == user_id
        )
    )
    return {key: (in_app, email) for key, in_app, email in rows}


def _hhmm(value: time) -> str:
    return value.strftime("%H:%M")


def _parse_hhmm(value: str) -> time:
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


def _settings_out(user: User, site: Site, saved_prefs: dict[str, tuple[bool, bool]]) -> SettingsOut:
    """Builds the response from rows already in memory; alert types never saved use their defaults."""
    notifications = [
        NotificationPrefOut(key=key, in_app=in_app, email=email)
        for key, (in_app, email) in ({**NOTIFICATION_DEFAULTS, **saved_prefs}).items()
    ]
    return SettingsOut(
        profile=ProfileOut(name=user.name, phone=user.phone, email=user.email),
        site=SiteOut(
            name=site.name,
            city=site.city,
            address=site.address,
            timezone=site.timezone,
            pv_kwp=float(site.pv_kwp),
            battery_kwh=float(site.battery_kwh),
            inverter_make=site.inverter_make,
            inverter_serial=site.inverter_serial,
            inverter_host=site.inverter_host,
            station_code=site.station_code,
        ),
        reserve_pct=site.reserve_pct,
        blackouts=[BlackoutWindowOut(start=_hhmm(w.start_time), end=_hhmm(w.end_time)) for w in site.blackouts],
        tariff=TariffOut(
            category=site.tariff_category,
            regime=site.prosumer_regime,
            sanctioned_load_kw=float(site.sanctioned_load_kw),
            is_atl_filer=site.is_atl_filer,
            include_electricity_duty=site.include_electricity_duty,
            is_protected_consumer=site.is_protected_consumer,
        ),
        notifications=notifications,
    )


def _decimal(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


# ---------- profile ----------


@router.get("/me", response_model=UserOut)
def get_me(session: ReadSession, current: Me) -> UserOut:
    row = session.execute(
        select(User, exists().where(Site.user_id == User.id)).where(User.id == current.id)
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    user, onboarded = row
    return UserOut(id=user.id, name=user.name, email=user.email, phone=user.phone, onboarded=bool(onboarded))


@router.patch("/me", response_model=UserOut)
def update_me(body: ProfileUpdate, session: DbSession, current: Me) -> UserOut:
    user = _load_user(session, current)
    user.name = body.name
    user.phone = body.phone
    session.commit()
    return user_out(session, user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    body: DeleteAccountRequest,
    session: DbSession,
    current: Me,
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    versions: Annotated[TokenVersionCache, Depends(get_token_versions)],
) -> None:
    """Permanently deletes the account and, through ON DELETE CASCADE, every row it owns."""
    enforce_limit(limiter, f"delete:user:{current.id}", DELETE_PER_USER)
    user = _load_user(session, current)
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_password")
    session.execute(delete(User).where(User.id == user.id))
    session.commit()
    versions.invalidate(current.id)


# ---------- site (onboarding) ----------


@router.post("/site", status_code=status.HTTP_201_CREATED, response_model=SettingsOut)
def create_site(
    body: OnboardingRequest,
    session: DbSession,
    current: Me,
    settings: Annotated[AppSettings, Depends(get_settings)],
) -> SettingsOut:
    user = _load_user(session, current)
    if session.scalar(select(Site.id).where(Site.user_id == user.id)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="site_exists")
    site = Site(
        user_id=user.id,
        name=body.name,
        address=body.address,
        city=body.city,
        pv_kwp=_decimal(body.pv_kwp),
        battery_kwh=_decimal(body.battery_kwh),
        inverter_make=body.inverter_make,
        inverter_serial=body.inverter_serial,
        station_code=station_code_for(session, user, settings.station_owner_email),
        tariff_category=body.tariff_category,
        prosumer_regime=body.prosumer_regime,
        sanctioned_load_kw=_decimal(body.sanctioned_load_kw),
        is_protected_consumer=body.tariff_category == "PROTECTED",
    )
    session.add(site)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="site_exists") from None
    return _settings_out(user, site, {})


# ---------- settings ----------


@router.get("/settings", response_model=SettingsOut)
def get_account_settings(session: ReadSession, current: Me) -> SettingsOut:
    user, site = _load_user_and_site(session, current)
    return _settings_out(user, site, _saved_prefs(session, user.id))


@router.put("/settings", response_model=SettingsOut)
def replace_account_settings(body: SettingsUpdate, session: DbSession, current: Me) -> SettingsOut:
    """Saves the whole settings page at once (the UI has a single Save button)."""
    user, site = _load_user_and_site(session, current)

    user.name = body.profile.name
    user.phone = body.profile.phone

    site.name = body.site.name
    site.city = body.site.city
    site.address = body.site.address
    site.pv_kwp = _decimal(body.site.pv_kwp)
    site.battery_kwh = _decimal(body.site.battery_kwh)
    site.inverter_make = body.site.inverter_make
    if "inverter_host" in body.site.model_fields_set:
        site.inverter_host = body.site.inverter_host
    site.reserve_pct = body.reserve_pct
    site.tariff_category = body.tariff.category
    site.prosumer_regime = body.tariff.regime
    site.sanctioned_load_kw = _decimal(body.tariff.sanctioned_load_kw)
    site.is_atl_filer = body.tariff.is_atl_filer
    site.include_electricity_duty = body.tariff.include_electricity_duty
    site.is_protected_consumer = body.tariff.is_protected_consumer

    site.blackouts = [
        BlackoutWindow(position=i, start_time=_parse_hhmm(w.start), end_time=_parse_hhmm(w.end))
        for i, w in enumerate(body.blackouts)
    ]

    session.execute(delete(NotificationPref).where(NotificationPref.user_id == user.id))
    session.add_all(
        NotificationPref(user_id=user.id, alert_key=n.key, in_app=n.in_app, email=n.email)
        for n in body.notifications
    )
    session.commit()
    # Prefs were just replaced by the body, so the response is built from it instead of re-read.
    return _settings_out(user, site, {n.key: (n.in_app, n.email) for n in body.notifications})


# ---------- report emails ----------


@router.get("/report-preferences", response_model=ReportPrefs)
def get_report_prefs(session: ReadSession, current: Me) -> ReportPrefs:
    row = session.execute(
        select(User.email, ReportPref)
        .outerjoin(ReportPref, ReportPref.user_id == User.id)
        .where(User.id == current.id)
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    email, prefs = row
    if prefs is None:
        return ReportPrefs(monthly=True, weekly=False, send_to=email)
    return ReportPrefs(monthly=prefs.monthly, weekly=prefs.weekly, send_to=prefs.send_to)


@router.put("/report-preferences", response_model=ReportPrefs)
def put_report_prefs(body: ReportPrefs, session: DbSession, current: Me) -> ReportPrefs:
    prefs = session.get(ReportPref, current.id)
    if prefs is None:
        prefs = ReportPref(user_id=current.id, monthly=body.monthly, weekly=body.weekly, send_to=body.send_to)
        session.add(prefs)
    else:
        prefs.monthly, prefs.weekly, prefs.send_to = body.monthly, body.weekly, body.send_to
    session.commit()
    return body
