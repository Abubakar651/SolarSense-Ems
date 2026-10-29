"""API integration tests for the CY 2026 LESCO v2 endpoints (default regime: grandfathered)."""

import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


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


def test_v2_optimize_default_regime_physics_and_latency(client):
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


def test_v2_optimize_single_phase_zero_export_and_errors(client):
    r = client.post("/api/v2/optimize", json={
        "date_str": "2026-07-01", "regime": "SINGLE_PHASE_SLAB_ZERO_EXPORT",
        "prior_month_to_date_import_kwh": 150.0,
    })
    assert r.status_code == 200
    assert max(r.json()["p_grid_export_kw"]) == 0.0
    assert client.post("/api/v2/optimize", json={"date_str": "2026-07-01", "regime": "X"}).status_code == 422
    assert client.post("/api/v2/optimize", json={"date_str": "1999-01-01"}).status_code == 404


def test_v2_optimize_auto_month_to_date_tracking(client):
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

