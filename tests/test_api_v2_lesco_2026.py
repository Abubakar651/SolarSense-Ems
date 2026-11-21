"""API integration tests for the CY 2026 LESCO v2 endpoints (default regime: grandfathered)."""

from dataclasses import replace
from decimal import Decimal
import time
import uuid

import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.api.db.models import Base, Site, User
from src.api.deps import CurrentUser, get_current_user
from src.api.main import app
from src.api.user_site import STATION_CODE
from src.api.telemetry_logger import ReaderPool
from src.data_engineering.goodwe_live_reader import GoodWeLiveTelemetryDTO


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _sign_in_with_hardware(station_code=None):
    """A new user whose site has the station's hardware, owning the recorded dataset when `station_code` is set."""
    user_id = uuid.uuid4()
    with app.state.session_factory() as session:
        session.add(User(id=user_id, email=f"{user_id}@example.com", password_hash="x", name="Owner"))
        session.add(Site(
            user_id=user_id, name="Home", address="904-A Johar Town", city="Lahore", pv_kwp=Decimal("7.02"),
            battery_kwh=Decimal("5.12"), inverter_make="GoodWe", inverter_serial="9010KESC253L0146",
            tariff_category="TOU_A1B", prosumer_regime="GRANDFATHERED_NET_METERING",
            sanctioned_load_kw=Decimal("10"), station_code=station_code,
        ))
        session.commit()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id=user_id, token_version=0)


@pytest.fixture
def station(client):
    """Signed in as the site that owns the recorded station dataset (the only one /api/v2/optimize serves)."""
    Base.metadata.drop_all(app.state.engine)
    Base.metadata.create_all(app.state.engine)
    _sign_in_with_hardware(STATION_CODE)
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_v2_bill_estimate_matches_pdf_examples(client):
    r = client.post("/api/v2/bill/estimate", json={
        "category": "UNPROTECTED", "sanctioned_load_kw": 2.0, "current_kwh": 350,
        "fpa_reference_2m_prior_kwh": 400, "is_atl_filer": False,
    })
    assert r.status_code == 200
    assert r.json()["total_payable_pkr"] == "18073.74"
    assert r.json()["line_items"]["gst_on_current_bill_pkr"] == "2677.19"

    r = client.post("/api/v2/bill/estimate", json={
        "category": "TOU_A1B", "sanctioned_load_kw": 5.0, "peak_kwh": 120, "off_peak_kwh": 380,
        "fpa_reference_2m_prior_kwh": 600, "include_electricity_duty": True, "is_atl_filer": False,
    })
    assert r.json()["total_payable_pkr"] == "31653.26"

    assert client.post("/api/v2/bill/estimate", json={
        "category": "BOGUS", "sanctioned_load_kw": 2.0}).status_code == 422


def test_v2_peak_window_all_seasons(client):
    expected = {1: (17, 21), 4: (18, 22), 7: (19, 23), 10: (18, 22)}
    for m, (a, b) in expected.items():
        d = client.get(f"/api/v2/tariff/peak-window?month={m}").json()
        assert (d["peak_start_hour"], d["peak_end_hour"]) == (a, b)
        assert d["peak_hours"] == list(range(a, b))
    assert client.get("/api/v2/tariff/peak-window?month=13").status_code == 422


def test_v2_prosumer_compare_grandfathered_wins(client):
    d = client.post("/api/v2/prosumer/compare", json={
        "gross_peak_import_kwh": 100, "gross_off_peak_import_kwh": 300, "gross_export_kwh": 450,
    }).json()
    assert d["grandfathered"]["net_billed_off_peak_import_kwh"] in ("0", "0.00")
    assert d["grandfathered"]["export_credit_pkr"] == "3798.00"
    assert d["net_billing_2026"]["export_credit_pkr"] == "3658.50"
    assert float(d["grandfathered_advantage_pkr"]) > 0.0


def test_v2_optimize_default_regime_physics_and_latency(client, station):
    payload = {"date_str": "2026-07-01"}  # known 4-hour blackout date
    client.post("/api/v2/optimize", json=payload)  # warm
    t0 = time.perf_counter()
    r = client.post("/api/v2/optimize", json=payload)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert r.status_code == 200
    d = r.json()
    assert d["regime"] == "GRANDFATHERED_NET_METERING"
    assert d["season"] == "Summer"
    assert d["is_peak"][19:23] == [1, 1, 1, 1] and sum(d["is_peak"]) == 4
    assert d["status"] in ("optimal", "optimal_inaccurate", "OPTIMAL", "OPTIMAL_INACCURATE")
    out = np.array(d["outage_flags"]) == 1
    assert out.any()
    assert np.all(np.array(d["p_grid_import_kw"])[out] == 0.0)
    assert np.all(np.array(d["p_grid_export_kw"])[out] == 0.0)
    ch, dis = np.array(d["p_ch_kw"]), np.array(d["p_dis_kw"])
    assert np.all(ch * dis < 1e-6)
    soc = np.array(d["soc_kwh"])
    assert soc.min() >= 0.768 - 1e-6 and soc.max() <= 5.12 + 1e-6
    assert elapsed_ms < 50.0


def test_v2_optimize_single_phase_zero_export_and_errors(client, station):
    r = client.post("/api/v2/optimize", json={
        "date_str": "2026-07-01", "regime": "SINGLE_PHASE_SLAB_ZERO_EXPORT",
        "prior_month_to_date_import_kwh": 150.0,
    })
    assert r.status_code == 200
    assert max(r.json()["p_grid_export_kw"]) == 0.0
    assert client.post("/api/v2/optimize", json={"date_str": "2026-07-01", "regime": "X"}).status_code == 422
    assert client.post("/api/v2/optimize", json={"date_str": "1999-01-01"}).status_code == 404


def test_v2_optimize_replays_the_station_dataset_for_its_owner_only(client, station):
    assert client.post("/api/v2/optimize", json={"date_str": "2026-07-01"}).status_code == 200
    _sign_in_with_hardware()
    r = client.post("/api/v2/optimize", json={"date_str": "2026-07-01"})
    assert r.status_code == 403
    assert r.json()["detail"] == "station_only"


def test_v2_optimize_auto_month_to_date_tracking(client, station):
    # On 2026-07-15, MTD import from days 1..14 is automatically computed as 569.313 kWh
    r = client.post("/api/v2/optimize", json={"date_str": "2026-07-15"})
    assert r.status_code == 200
    d = r.json()
    assert d["projected_month_to_date_import_kwh"] > 569.0
    assert float(d["baseline_no_battery_cost_pkr"]) > 0.0
    assert float(d["net_savings_pkr"]) > 0.0
    assert float(d["export_rate_used_pkr_per_kwh"]) > 0.0


def test_agent_advisory_dynamic_seasonal_peak_windows(client):
    # Summer (July) -> 19:00–23:00
    r_jul = client.post("/api/agent/advisory", json={"date_str": "2026-07-01"})
    assert r_jul.status_code == 200
    d_jul = r_jul.json()
    assert "19:00–23:00" in d_jul["dispatch_arbitrage_brief"]
    assert any("19:00–23:00" in act for act in d_jul["recommended_actions"])

    # Winter (January) -> 17:00–21:00
    r_jan = client.post("/api/agent/advisory", json={"date_str": "2026-01-13"})
    assert r_jan.status_code == 200
    d_jan = r_jan.json()
    assert "17:00–21:00" in d_jan["dispatch_arbitrage_brief"]
    assert any("17:00–21:00" in act for act in d_jan["recommended_actions"])


def test_soiling_endpoint_dynamic_valuation(client):
    # On 2026-07-15, trailing 30-day export share dynamically blends import savings with export buyback
    r = client.get("/api/soiling/status?date=2026-07-15&days_until_rain=7")
    assert r.status_code == 200
    d = r.json()
    assert d["date"] == "2026-07-15"
    assert d["daily_kwh_lost"] > 0.0
    assert d["daily_revenue_lost_pkr"] > 0.0
    assert d["decision"] in ("TRIGGER CLEANING CREW", "HOLD (WAIT FOR NATURAL RAIN)")


LIVE_DTO = GoodWeLiveTelemetryDTO(
    timestamp_iso="2026-11-10T20:00:00+05:00",
    model_name="GW6000ES20",
    serial_number="9010KESC253L0146",
    battery_soc_pct=88.0,
    battery_soh_pct=100.0,
    battery_voltage_v=52.2,
    battery_current_a=38.5,
    battery_power_w=-2000.0,
    battery_mode="Discharge",
    battery_temp_c=26.5,
    pv1_voltage_v=0.0,
    pv1_power_w=0.0,
    pv2_voltage_v=0.0,
    pv2_power_w=0.0,
    total_pv_power_w=0.0,
    grid_voltage_v=0.0,
    grid_frequency_hz=0.0,
    grid_active_power_w=0.0,
    grid_mode="Not connected",
    is_grid_connected=False,
    is_blackout=True,
    house_consumption_w=2000.0,
    backup_voltage_v=228.3,
    backup_power_w=430.0,
    work_mode="Normal (Off-Grid)",
    today_pv_kwh=13.2,
    today_export_kwh=12.6,
    today_import_kwh=0.2,
    today_load_kwh=16.1,
    today_battery_charge_kwh=0.0,
    today_battery_discharge_kwh=0.5,
    inverter_temp_air_c=38.0,
    inverter_temp_radiator_c=37.0,
)


class _FakeReader:
    """Answers for one inverter address; the pool records which addresses were read."""

    def __init__(self, host: str, reads: list[str]) -> None:
        self.host = host
        self._reads = reads

    async def fetch_telemetry(self) -> GoodWeLiveTelemetryDTO:
        self._reads.append(self.host)
        return replace(LIVE_DTO, serial_number=f"SN-{self.host}")


@pytest.fixture
def inverter_reads(client):
    """Fresh tables and a reader pool of fakes; yields the list of inverter addresses that were read."""
    Base.metadata.drop_all(app.state.engine)
    Base.metadata.create_all(app.state.engine)
    reads: list[str] = []
    real_pool = app.state.inverter_readers
    app.state.inverter_readers = ReaderPool(make_reader=lambda host: _FakeReader(host, reads))
    yield reads
    app.state.inverter_readers = real_pool
    app.dependency_overrides.pop(get_current_user, None)


def _sign_in_with_site(inverter_host, inverter_serial=None):
    """
    A new user with a site at `inverter_host` (None: not connected), signed in for the next requests. The
    site's serial defaults to the one the fake inverter at that address reports.
    """
    user_id = uuid.uuid4()
    with app.state.session_factory() as session:
        session.add(User(id=user_id, email=f"{user_id}@example.com", password_hash="x", name="Owner"))
        session.add(Site(
            user_id=user_id, name="Home", address="Johar Town", city="Lahore", pv_kwp=Decimal("7.02"),
            battery_kwh=Decimal("5.12"), inverter_make="GoodWe", inverter_serial=inverter_serial or f"SN-{inverter_host}",
            inverter_host=inverter_host, tariff_category="TOU_A1B",
            prosumer_regime="GRANDFATHERED_NET_METERING", sanctioned_load_kw=Decimal("10"),
        ))
        session.commit()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id=user_id, token_version=0)


def test_v2_inverter_live_endpoint(client, inverter_reads):
    _sign_in_with_site("192.168.1.50")
    r = client.get("/api/v2/inverter/live")
    assert r.status_code == 200
    data = r.json()
    assert data["model_name"] == "GW6000ES20"
    assert data["serial_number"] == "SN-192.168.1.50"
    assert data["battery_soc_pct"] == 88.0
    assert data["is_blackout"] is True
    assert data["is_grid_connected"] is False
    assert inverter_reads == ["192.168.1.50"]


def test_v2_inverter_live_reads_only_the_callers_own_inverter(client, inverter_reads):
    _sign_in_with_site("192.168.1.50")
    _sign_in_with_site("10.0.0.7")
    assert client.get("/api/v2/inverter/live").json()["serial_number"] == "SN-10.0.0.7"
    assert inverter_reads == ["10.0.0.7"]


def test_v2_inverter_live_refuses_an_inverter_with_another_serial(client, inverter_reads):
    _sign_in_with_site("192.168.1.50", inverter_serial="SOMEONE-ELSE")
    r = client.get("/api/v2/inverter/live")
    assert r.status_code == 409 and r.json()["detail"] == "inverter_serial_mismatch"


def test_v2_inverter_live_without_an_address_is_not_configured(client, inverter_reads):
    _sign_in_with_site("192.168.1.50")
    _sign_in_with_site(None)
    r = client.get("/api/v2/inverter/live")
    assert r.status_code == 404 and r.json()["detail"] == "inverter_not_configured"
    assert inverter_reads == []


