"""
Request/response contracts for accounts, sites, settings, alerts and report preferences.

Every request model forbids unknown fields (a typo or an attempt to set `token_version` is a 422,
never silently ignored) and bounds every string and number it accepts.
"""

from __future__ import annotations

from datetime import datetime
import ipaddress
from typing import Annotated, Literal
import uuid

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, StringConstraints, model_validator

from src.api.core.security import MAX_PASSWORD_BYTES, MIN_PASSWORD_BYTES

TariffCategory = Literal["LIFELINE", "PROTECTED", "UNPROTECTED", "TOU_A1B", "PREPAID_A1C"]
ProsumerRegime = Literal["GRANDFATHERED_NET_METERING", "NET_BILLING_2026", "SINGLE_PHASE_SLAB_ZERO_EXPORT"]
InverterMake = Literal["GoodWe", "Other"]
AlertSeverity = Literal["crit", "warn", "info", "ok"]
NotificationKey = Literal[
    "grid_outage", "outage_risk", "peak_soon", "panels_dirty", "inverter_offline", "weekly_digest"
]

# Defaults for a new account, in display order (in_app, email).
NOTIFICATION_DEFAULTS: dict[str, tuple[bool, bool]] = {
    "grid_outage": (True, True),
    "outage_risk": (True, True),
    "peak_soon": (True, False),
    "panels_dirty": (True, True),
    "inverter_offline": (True, True),
    "weekly_digest": (False, True),
}

MIN_RESERVE_PCT = 15
MAX_BLACKOUT_WINDOWS = 12


def _check_password(value: str) -> str:
    size = len(value.encode("utf-8"))
    if size < MIN_PASSWORD_BYTES:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_BYTES} characters.")
    if size > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes.")
    return value


def _lower(value: str) -> str:
    return value.lower()


# Home LAN ranges (RFC 1918). The API sends UDP to this address, so anything else (public hosts, loopback,
# link-local cloud metadata, hostnames that could resolve anywhere) is refused.
_HOME_NETWORKS = tuple(ipaddress.IPv4Network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))


def _check_inverter_host(value: str | None) -> str | None:
    """Blank clears the address; otherwise a private IPv4 address on the home network."""
    if value is None or not value.strip():
        return None
    try:
        address = ipaddress.IPv4Address(value.strip())
    except ValueError:
        raise ValueError("Enter the inverter's IPv4 address, e.g. 192.168.1.50.") from None
    if not any(address in network for network in _HOME_NETWORKS):
        raise ValueError("The inverter address must be on your home network (10.x.x.x, 172.16-31.x.x or 192.168.x.x).")
    return str(address)


NewPassword = Annotated[str, AfterValidator(_check_password)]
# Login/delete accept any stored password but still cap size so bcrypt never sees > 72 bytes.
AnyPassword = Annotated[str, Field(min_length=1, max_length=MAX_PASSWORD_BYTES)]
Email = Annotated[EmailStr, Field(max_length=254), AfterValidator(_lower)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Text200 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, max_length=32, pattern=r"^[0-9+()\- ]*$")]
Serial = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
OneTimeToken = Annotated[str, StringConstraints(min_length=16, max_length=128)]
ClockTime = Annotated[str, StringConstraints(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]
Kwp = Annotated[float, Field(ge=0.5, le=2000)]
Kwh = Annotated[float, Field(ge=1, le=5000)]
LoadKw = Annotated[float, Field(ge=0.1, le=1000)]
InverterHost = Annotated[str | None, Field(max_length=45), AfterValidator(_check_inverter_host)]


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------- auth ----------


class SignupRequest(RequestModel):
    name: Name
    email: Email
    password: NewPassword


class LoginRequest(RequestModel):
    email: Email
    password: AnyPassword
    remember: bool = False


class EmailRequest(RequestModel):
    email: Email


class TokenRequest(RequestModel):
    token: OneTimeToken


class ResetPasswordRequest(RequestModel):
    token: OneTimeToken
    new_password: NewPassword


class ChangePasswordRequest(RequestModel):
    current_password: AnyPassword
    new_password: NewPassword


class UserOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    phone: str
    onboarded: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserOut


# ---------- account ----------


class ProfileUpdate(RequestModel):
    name: Name
    phone: Phone = ""


class DeleteAccountRequest(RequestModel):
    confirm: Literal["DELETE"]
    password: AnyPassword


# ---------- site & settings ----------


class OnboardingRequest(RequestModel):
    name: Name
    address: Text200
    city: Name
    pv_kwp: Kwp
    battery_kwh: Kwh
    inverter_make: InverterMake
    inverter_serial: Serial
    tariff_category: TariffCategory
    prosumer_regime: ProsumerRegime
    sanctioned_load_kw: LoadKw


class BlackoutWindowIn(RequestModel):
    start: ClockTime
    end: ClockTime


class NotificationPrefIn(RequestModel):
    key: NotificationKey
    in_app: bool
    email: bool


class SiteUpdate(RequestModel):
    name: Name
    city: Name
    address: Text200
    pv_kwp: Kwp
    battery_kwh: Kwh
    inverter_make: InverterMake
    # Left out: the saved address is kept. Blank or null: disconnects the inverter.
    inverter_host: InverterHost = None


class TariffUpdate(RequestModel):
    category: TariffCategory
    regime: ProsumerRegime
    sanctioned_load_kw: LoadKw
    is_atl_filer: bool
    include_electricity_duty: bool
    is_protected_consumer: bool


class SettingsUpdate(RequestModel):
    profile: ProfileUpdate
    site: SiteUpdate
    reserve_pct: Annotated[int, Field(ge=MIN_RESERVE_PCT, le=100)]
    blackouts: Annotated[list[BlackoutWindowIn], Field(max_length=MAX_BLACKOUT_WINDOWS)]
    tariff: TariffUpdate
    notifications: Annotated[list[NotificationPrefIn], Field(max_length=len(NOTIFICATION_DEFAULTS))]

    @model_validator(mode="after")
    def _check_lists(self) -> SettingsUpdate:
        windows = [(w.start, w.end) for w in self.blackouts]
        if any(start == end for start, end in windows):
            raise ValueError("A blackout window's start and end must differ.")
        if len(set(windows)) != len(windows):
            raise ValueError("Blackout windows must be unique.")
        keys = [n.key for n in self.notifications]
        if len(set(keys)) != len(keys):
            raise ValueError("Each notification key may appear once.")
        return self


class ProfileOut(BaseModel):
    name: str
    phone: str
    email: str


class SiteOut(BaseModel):
    name: str
    city: str
    address: str
    timezone: str
    pv_kwp: float
    battery_kwh: float
    inverter_make: str
    inverter_serial: str
    inverter_host: str | None
    # Set only on the site that owns the recorded station dataset.
    station_code: str | None


class TariffOut(BaseModel):
    category: str
    regime: str
    sanctioned_load_kw: float
    is_atl_filer: bool
    include_electricity_duty: bool
    is_protected_consumer: bool


class BlackoutWindowOut(BaseModel):
    start: str
    end: str


class NotificationPrefOut(BaseModel):
    key: str
    in_app: bool
    email: bool


class SettingsOut(BaseModel):
    profile: ProfileOut
    site: SiteOut
    reserve_pct: int
    blackouts: list[BlackoutWindowOut]
    tariff: TariffOut
    notifications: list[NotificationPrefOut]


# ---------- alerts & reports ----------


class AlertOut(BaseModel):
    id: uuid.UUID
    severity: AlertSeverity
    title: str
    detail: str
    created_at: datetime
    read: bool


class ReportPrefs(RequestModel):
    monthly: bool
    weekly: bool
    send_to: Email
