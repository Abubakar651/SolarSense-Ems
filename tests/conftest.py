"""
Shared test setup.

The environment is forced (not defaulted) before the API is imported, so a developer's .env with a
real Supabase URL or Resend key can never be used by the test suite.
"""

from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-only-jwt-secret-0123456789-abcdefghijklmnop"
os.environ["RESEND_API_KEY"] = "re_test_not_a_real_key"
os.environ["EMAIL_FROM"] = "SolarSense <no-reply@example.com>"
os.environ["FRONTEND_URL"] = "http://localhost:3000"
os.environ["CORS_ORIGINS"] = ""
os.environ["TRUSTED_PROXIES"] = ""
os.environ["EMAIL_DELIVERY"] = "resend"
os.environ["REQUIRE_EMAIL_VERIFICATION"] = "true"
# Never poll a real inverter from the test suite.
os.environ["INVERTER_POLL_SECONDS"] = "0"
# The default test account owns the recorded station dataset; other accounts never do.
os.environ["STATION_OWNER_EMAIL"] = "owner@example.com"
for _optional in ("ACCESS_TOKEN_TTL_HOURS", "REMEMBER_TOKEN_TTL_DAYS", "JWT_ISSUER", "JWT_AUDIENCE"):
    os.environ.pop(_optional, None)

from collections.abc import Callable, Iterator, Mapping  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from datetime import date, timedelta  # noqa: E402
import re  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
import pytest  # noqa: E402

from src.api.core import security  # noqa: E402
from src.api.db.models import Base, utc_now  # noqa: E402
from src.api.deps import authenticate_request, get_email_sender  # noqa: E402
from src.api.mail.sender import FakeEmailSender  # noqa: E402
from src.api.main import app, init_account_state  # noqa: E402
from src.api.recent_weather import FORECAST_DAYS, PAST_DAYS, RecentWeatherService  # noqa: E402
from src.api.site_soiling import SiteSoilingService, Valuation  # noqa: E402
from src.optimizer.lesco_2026_tariff_and_dispatch import LescoCY2026TariffEngine  # noqa: E402

# Cost 4 instead of 12 keeps the suite fast; the hashing code path is identical.
security.BCRYPT_ROUNDS = 4

DEFAULT_PASSWORD = "correct horse battery"


@pytest.fixture(autouse=True)
def _signed_in_unless_real_auth(request: pytest.FixtureRequest) -> Iterator[None]:
    """
    The compute-route tests predate auth; they run with authentication bypassed. Tests that
    exercise auth itself are marked `real_auth` and get the real dependency.
    """
    if request.node.get_closest_marker("real_auth"):
        yield
        return
    app.dependency_overrides[authenticate_request] = lambda: None
    yield
    app.dependency_overrides.pop(authenticate_request, None)


@pytest.fixture(scope="module")
def api() -> Iterator[TestClient]:
    """
    Client for the auth/account API. It starts only the account layer, not the full lifespan,
    so these tests don't depend on the telemetry datasets or the HiGHS solver being available.
    """
    init_account_state(app)
    Base.metadata.create_all(app.state.engine)
    yield TestClient(app)
    app.state.engine.dispose()


@pytest.fixture
def mailer(api: TestClient) -> Iterator[FakeEmailSender]:
    """Fresh tables, limits, caches and outbox for every test."""
    engine = app.state.engine
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    app.state.rate_limiter.reset()
    app.state.token_versions.clear()
    outbox = FakeEmailSender()
    app.dependency_overrides[get_email_sender] = lambda: outbox
    yield outbox
    app.dependency_overrides.pop(get_email_sender, None)


def token_from_email(outbox: FakeEmailSender, path: str) -> str:
    """The one-time token in the newest email linking to `path` (/verify or /reset)."""
    for message in reversed(outbox.sent):
        match = re.search(rf"{path}\?token=([A-Za-z0-9_\-]+)", message.text)
        if match:
            return match.group(1)
    raise AssertionError(f"No email with a {path} link")


@dataclass(frozen=True)
class Account:
    email: str
    password: str
    token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


def create_account(
    client: TestClient,
    outbox: FakeEmailSender,
    email: str = "owner@example.com",
    password: str = DEFAULT_PASSWORD,
    name: str = "Owner",
) -> Account:
    """Signs up, verifies the email and logs in."""
    assert client.post("/api/auth/signup", json={"name": name, "email": email, "password": password}).status_code == 201
    assert client.post("/api/auth/verify-email", json={"token": token_from_email(outbox, "/verify")}).status_code == 204
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return Account(email=email, password=password, token=response.json()["access_token"])


ONBOARDING = {
    "name": "Home",
    "address": "904-A Johar Town",
    "city": "Lahore",
    "pv_kwp": 7.02,
    "battery_kwh": 5.12,
    "inverter_make": "GoodWe",
    "inverter_serial": "9010KESC253L0146",
    "tariff_category": "TOU_A1B",
    "prosumer_regime": "GRANDFATHERED_NET_METERING",
    "sanctioned_load_kw": 10,
}


# ---------- the live dust model's weather, without the network ----------

# Station-style test wash price; the backend's real default comes from SolarPlantLossCalculator.
TEST_WASH_COST_PKR = 1500.0


def open_meteo_recent(
    today: date,
    ghi_kwh_m2: float = 4.5,
    rain_mm: Mapping[date, float] | None = None,
    ghi_overrides: Mapping[date, float | None] | None = None,
) -> dict[str, object]:
    """
    An Open-Meteo past_days answer around `today`: every day gets `ghi_kwh_m2` spread evenly over 06:00-17:00
    (a None override leaves that day's hours empty) and the rain in `rain_mm` (0 elsewhere).
    """
    rain_mm = rain_mm or {}
    ghi_overrides = ghi_overrides or {}
    days = [today + timedelta(days=offset) for offset in range(-PAST_DAYS, FORECAST_DAYS)]
    times: list[str] = []
    ghi: list[float | None] = []
    for day in days:
        total = ghi_overrides.get(day, ghi_kwh_m2)
        for hour in range(24):
            times.append(f"{day.isoformat()}T{hour:02d}:00")
            ghi.append(None if total is None else (total * 1000.0 / 12.0 if 6 <= hour < 18 else 0.0))
    return {
        "hourly": {"time": times, "shortwave_radiation": ghi},
        "daily": {"time": [d.isoformat() for d in days], "precipitation_sum": [rain_mm.get(d, 0.0) for d in days]},
    }


def site_soiling_service(payload: Callable[[], Mapping[str, object]]) -> SiteSoilingService:
    """The lifespan's SiteSoilingService on the test database and app.state.site_samples, weather from `payload`."""

    async def fetch() -> Mapping[str, object]:
        return payload()

    return SiteSoilingService(
        weather=RecentWeatherService(fetch, utc_now),
        session_factory=app.state.read_session_factory,
        load_samples=app.state.site_samples.samples,
        valuation=Valuation(
            engine=LescoCY2026TariffEngine(), wash_cost_pkr=TEST_WASH_COST_PKR, station_export_override_pkr_per_kwh=None
        ),
    )

