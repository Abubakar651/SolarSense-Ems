"""
The signed-in user's site: the tenant boundary for telemetry, insights, alerts and the live plan.

Every per-site query goes through `UserSite.site_id`, which is only ever loaded for the authenticated user.
The recorded station dataset (data/processed, inverter 9010KESC253L0146) belongs to the one site whose
`station_code` is set; every other site sees only its own logged samples. Ownership is configured, never
claimed: only the account named by STATION_OWNER_EMAIL, with that email verified, gets it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated
import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from src.api.db.models import Site, User
from src.api.deps import CurrentUser, get_current_user
from src.api.site_sizing import SiteSizes

STATION_CODE = "LHR-RES-01"


@dataclass(frozen=True, slots=True)
class UserSite:
    site_id: uuid.UUID
    # True for the site that owns the recorded station dataset.
    is_station: bool
    inverter_host: str | None
    # Last time the site was saved: the inverter address is at least this old.
    updated_at: datetime
    sizes: SiteSizes
    # The serial saved at onboarding: a reading from the inverter address is this site's only if it matches.
    inverter_serial: str = ""
    # The site's saved tariff settings (ProsumerRegime2026 value), used to value its energy.
    prosumer_regime: str = "NONE"
    include_electricity_duty: bool = False
    # The rest of the saved tariff (ConsumerCategory2026 value), used to bill its month (src/api/site_tariff.py).
    tariff_category: str = "TOU_A1B"
    sanctioned_load_kw: float = 10.0
    is_atl_filer: bool = True
    # The name the user gave the site at onboarding ("Home"), used to address them in the daily brief.
    name: str = ""


def station_code_for(session: Session, user: User, owner_email: str | None) -> str | None:
    """
    The station code for a new site: only the configured owner's account, once its email is verified (with
    verification switched off anyone could register the owner's address first), and only while unclaimed.
    The inverter serial plays no part: it is public, so typing it proves nothing.
    """
    if owner_email is None or user.email.lower() != owner_email or user.email_verified_at is None:
        return None
    taken = session.scalar(select(Site.id).where(Site.station_code == STATION_CODE))
    return None if taken is not None else STATION_CODE


def load_user_site(session_factory: sessionmaker[Session], user_id: uuid.UUID) -> UserSite | None:
    with session_factory() as session:
        row = session.execute(
            select(
                Site.id, Site.station_code, Site.inverter_host, Site.inverter_serial, Site.updated_at,
                Site.pv_kwp, Site.battery_kwh, Site.reserve_pct, Site.prosumer_regime, Site.include_electricity_duty,
                Site.name, Site.tariff_category, Site.sanctioned_load_kw, Site.is_atl_filer,
            ).where(Site.user_id == user_id)
        ).first()
    if row is None:
        return None
    return UserSite(
        site_id=row.id,
        is_station=row.station_code == STATION_CODE,
        inverter_host=row.inverter_host,
        updated_at=row.updated_at,
        sizes=SiteSizes(pv_kwp=float(row.pv_kwp), battery_kwh=float(row.battery_kwh), reserve_pct=int(row.reserve_pct)),
        inverter_serial=row.inverter_serial,
        prosumer_regime=row.prosumer_regime,
        include_electricity_duty=row.include_electricity_duty,
        name=row.name,
        tariff_category=row.tariff_category,
        sanctioned_load_kw=float(row.sanctioned_load_kw),
        is_atl_filer=row.is_atl_filer,
    )


def get_user_site(request: Request, current: Annotated[CurrentUser, Depends(get_current_user)]) -> UserSite:
    """Dependency: the caller's site, or 404 site_not_found before onboarding."""
    site = load_user_site(request.app.state.read_session_factory, current.id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="site_not_found")
    return site


MySite = Annotated[UserSite, Depends(get_user_site)]
