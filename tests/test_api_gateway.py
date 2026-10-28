"""
SolarSense EMS — FastAPI Gateway Integration Tests
===================================================
Tests API routes, health metrics, 24h simulation window queries,
MILP optimization endpoint, and multi-day Server-Sent Events (SSE) backtest stream.
"""

import json
from fastapi.testclient import TestClient
import pytest

from src.api.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "SolarSense EMS Compute API"
    assert "docs_url" in data


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["dataset_rows"] == 11136
    assert data["solver_warmed_up"] is True


def test_get_simulation_window_ground_truth(client):
    response = client.get("/api/window?date=2025-07-17&use_forecasts=false")
    assert response.status_code == 200
    data = response.json()
    assert data["date"] == "2025-07-17"
    assert data["horizon_hours"] == 24
    assert len(data["solar_generation_kw"]) == 24
    assert len(data["factory_load_kw"]) == 24
    assert len(data["tariff_rates_pkr"]) == 24
    assert data["total_baseline_cost_pkr"] > 0.0


def test_get_simulation_window_with_forecasts(client):
    response = client.get("/api/window?date=2025-07-17&use_forecasts=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data["solar_generation_kw"]) == 24
    assert len(data["factory_load_kw"]) == 24


def test_get_simulation_window_not_found(client):
    response = client.get("/api/window?date=2099-01-01")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_optimize_dispatch_endpoint(client):
    payload = {
        "date_str": "2025-07-17",
        "use_forecasts": False,
        "initial_soc_kwh": 300.0,
        "mdi_high_water_kw": 500.0,
    }
    response = client.post("/api/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] in ("OPTIMAL", "OPTIMAL_INACCURATE")
    assert len(data["p_grid_kw"]) == 24
    assert len(data["p_ch_kw"]) == 24
    assert len(data["p_dis_kw"]) == 24
    assert len(data["soc_kwh"]) == 25  # T + 1
    assert data["solve_time_ms"] < 100.0  # Well within latency budget under test load



def test_optimize_dispatch_with_tariff_overrides(client):
    payload = {
        "date_str": "2025-07-17",
        "use_forecasts": False,
        "off_peak_rate_pkr": 42.0,
        "peak_rate_pkr": 68.0,
        "diesel_cost_pkr": 110.0,
    }
    response = client.post("/api/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OPTIMAL"


def test_stream_backtest_sse(client):
    # Test a 3-day streaming simulation
    response = client.get("/api/backtest/stream?start_date=2025-07-01&days=3&use_forecasts=false")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    frames = []
    for line in response.text.split("\n"):
        if line.startswith("data: "):
            frame_data = json.loads(line[len("data: "):])
            frames.append(frame_data)

    # 3 daily frames + 1 completion frame
    assert len(frames) == 4
    assert frames[0]["day"] == 1
    assert frames[0]["date"] == "2025-07-01"
    assert frames[0]["status"] == "OPTIMAL"
    assert frames[0]["updated_mdi_high_water_kw"] == pytest.approx(10.0, abs=5.0)
    assert frames[1]["day"] == 2
    assert frames[2]["day"] == 3
    assert frames[3]["status"] == "finished"


def test_residential_station_904a_envelope_and_soiling_defaults(client):
    """Verifies FastAPI residential 5.12 kWh BESS envelope, export vector, and 7.02 kWp soiling calculator."""
    from src.soiling.loss_calculator import SolarPlantLossCalculator
    from datetime import datetime

    payload = {
        "date_str": "2026-09-23",
        "use_forecasts": False,
        "initial_soc_kwh": 3.5,
    }
    response = client.post("/api/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("OPTIMAL", "OPTIMAL_INACCURATE")
    assert len(data["p_export_kw"]) == 24
    assert max(data["soc_kwh"]) <= 5.12 + 1e-6
    assert min(data["soc_kwh"]) >= 0.768 - 1e-6

    calc = SolarPlantLossCalculator()
    assert calc.plant_capacity_kw == pytest.approx(7.02)
    assert calc.panel_rating_w == pytest.approx(585.0)
    assert calc.num_panels == 12
    assert calc.wash_cost_pkr == pytest.approx(1500.0)
    assert calc.tariff_category == "A1_ToU"
    loss_res = calc.calculate_instantaneous_loss(
        poa_irradiance_wm2=850.0,
        ambient_temp_c=32.0,
        actual_power_kw=3.85,
        dt=datetime(2026, 10, 7, 12, 30),
    )
    assert loss_res["soiling_derate_percentage"] > 0.0
    assert loss_res["current_tariff_pkr_per_kwh"] == pytest.approx(34.53)


def test_get_available_dates_endpoint(client):
    response = client.get("/api/dates")
    assert response.status_code == 200
    data = response.json()
    assert data["min_date"] == "2025-07-01"
    assert data["max_date"] == "2026-10-07"
    assert data["total_days"] == 464
    assert data["total_hours"] == 11136
    assert len(data["preset_dates"]) >= 5


def test_get_soiling_status_endpoint(client):
    # Confirmed wash date
    res_wash = client.get("/api/soiling/status?date=2026-09-23&days_until_rain=7")
    assert res_wash.status_code == 200
    wash_data = res_wash.json()
    assert wash_data["date"] == "2026-09-23"
    assert wash_data["plant_capacity_kw"] == pytest.approx(7.02)
    assert wash_data["total_panels"] == 12
    assert wash_data["wash_cost_pkr"] == pytest.approx(1500.0)
    assert wash_data["event_type"] == "manual_wash_confirmed"

    # 14-day post-wash soiling date
    res_post = client.get("/api/soiling/status?date=2026-10-07&days_until_rain=7")
    assert res_post.status_code == 200
    post_data = res_post.json()
    assert post_data["days_since_last_wash"] == 14
    assert post_data["decision"] in ("TRIGGER CLEANING CREW", "HOLD (WAIT FOR NATURAL RAIN)")

    # Invalid date -> 404
    res_404 = client.get("/api/soiling/status?date=2099-01-01")
    assert res_404.status_code == 404


def test_vision_samples_and_inspect_endpoints(client):
    samples_res = client.get("/api/vision/samples")
    assert samples_res.status_code == 200
    samples_data = samples_res.json()
    assert len(samples_data["classes"]) == 5
    assert samples_data["total_samples"] > 0

    first_sample_path = samples_data["samples"][0]["sample_path"]
    inspect_res = client.post(
        "/api/vision/inspect",
        json={"sample_path": first_sample_path, "use_tta": False, "days_until_rain": 7},
    )
    assert inspect_res.status_code == 200
    diag = inspect_res.json()
    assert diag["condition"] in ("clean", "dusty", "bird_drop", "electrical_damage", "physical_damage")
    assert 0.0 <= diag["confidence"] <= 1.0
    assert len(diag["all_probabilities"]) == 5
    assert diag["wash_cost_pkr"] == pytest.approx(1500.0)

    # Path traversal protection check
    bad_res = client.post(
        "/api/vision/inspect",
        json={"sample_path": "../../etc/passwd", "use_tta": False},
    )
    assert bad_res.status_code == 400


def test_agent_advisory_endpoint(client):
    res = client.post(
        "/api/agent/advisory",
        json={
            "date_str": "2026-07-01",
            "use_forecasts": False,
            "days_until_rain": 7,
            "defect_condition": "dusty",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["date"] == "2026-07-01"
    assert data["station_id"] == "LHR-RES-01 / 904-A JT"
    assert "46.85" in data["dispatch_arbitrage_brief"]
    assert len(data["recommended_actions"]) >= 3
    assert data["key_metrics"]["outage_hours"] == pytest.approx(4.0)
    assert data["latency_ms"] < 100.0
