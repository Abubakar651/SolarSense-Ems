"""
Tests for src/data_engineering/repair_master_dataset.py
=======================================================
Pure-kernel unit tests (synthetic arrays) + integration audit of the rebuilt master dataset.
"""

from pathlib import Path

import numpy as np
import polars as pl
import pytest

from src.data_engineering.repair_master_dataset import (
    ARRAY_KWP,
    anchor_to_daily_totals,
    block_ids,
    compute_pv_true_kw,
    days_since_clean_event,
    verify_master,
)

MASTER = Path("data/processed/master_ems_timeseries.csv")
RECON = Path("data/processed/solar_timeseries/goodwe_lahore_hourly_reconstructed.csv")
FIVE_MIN = Path("data/processed/solar_timeseries/goodwe_lahore_5min.csv")
DAILY = Path("data/raw/solar_timeseries/goodwe_lahore/goodwe_lahore_daily_raw.csv")


# ── STEP 1 kernel ──────────────────────────────────────────────────────────
def test_night_battery_discharge_is_not_solar():
    """Blackout: inverter AC output is 100% battery discharge, GHI == 0 -> PV must be 0."""
    active = np.array([2.0, 2.0, 0.14])
    battery = np.array([2.1, 1.5, 0.18])
    ghi = np.zeros(3)
    assert (compute_pv_true_kw(active, battery, ghi) == 0.0).all()


def test_pv_power_conservation_day():
    """Daytime: PV = AC out - discharge (+ charge)."""
    ghi = np.full(3, 500.0)
    active = np.array([4.0, 3.0, 5.0])
    battery = np.array([0.0, -1.0, 1.0])  # idle / charging 1 kW / discharging 1 kW
    np.testing.assert_allclose(compute_pv_true_kw(active, battery, ghi), [4.0, 4.0, 4.0])


def test_pv_clipped_to_array_rating_and_never_negative():
    ghi = np.full(3, 900.0)
    pv = compute_pv_true_kw(np.array([9.5, -0.02, 0.0]), np.array([0.0, 0.0, 3.0]), ghi)
    assert pv[0] == pytest.approx(ARRAY_KWP)
    assert pv[1] == 0.0 and pv[2] == 0.0
    assert ARRAY_KWP == pytest.approx(7.02)


# ── STEP 3 kernel ──────────────────────────────────────────────────────────
def _bell(peak: float) -> np.ndarray:
    h = np.arange(24)
    return np.clip(np.sin((h - 6) / 12 * np.pi), 0, None) * peak


def test_anchor_matches_daily_totals_exactly():
    base = np.stack([_bell(3.0), _bell(5.0), _bell(1.0)])
    target = np.array([20.0, 31.5, 4.2])
    out, scale = anchor_to_daily_totals(base, target)
    np.testing.assert_allclose(out.sum(axis=1), target, atol=1e-9)
    assert (out[:, :6] == 0).all() and (out[:, 19:] == 0).all()   # night stays zero
    np.testing.assert_allclose(scale, target / base.sum(axis=1))


def test_anchor_zero_target_day_is_all_zero():
    out, _ = anchor_to_daily_totals(np.stack([_bell(4.0)]), np.array([0.0]))
    assert (out == 0.0).all()


def test_anchor_respects_hourly_cap_and_still_conserves_energy():
    base = np.stack([_bell(6.0)])
    target = np.array([base.sum() * 1.6])               # forces the noon hours past 7.02 kW
    out, _ = anchor_to_daily_totals(base, target, cap_kw=ARRAY_KWP)
    assert out.max() <= ARRAY_KWP + 1e-9
    assert out.sum() == pytest.approx(target[0], abs=1e-8)


def test_anchor_uses_fallback_shape_when_model_curve_is_empty():
    ghi_shape = np.stack([_bell(2.0)])
    out, _ = anchor_to_daily_totals(np.zeros((1, 24)), np.array([10.0]), fallback_shape=ghi_shape)
    assert out.sum() == pytest.approx(10.0)
    assert (out[:, :6] == 0).all() and (out[:, 19:] == 0).all()
    # without a fallback, an empty curve cannot be scaled: stays zero and scale is undefined
    out0, scale0 = anchor_to_daily_totals(np.zeros((1, 24)), np.array([10.0]))
    assert (out0 == 0).all() and np.isnan(scale0[0])


# ── Soiling clock / CV blocks ──────────────────────────────────────────────
def test_days_since_clean_resets_on_rain_and_known_wash():
    rain = np.array([0, 0, 0, 3.0, 0, 0, 0, 0.0])
    wash = np.array([0, 0, 0, 0, 0, 0, 1, 0], dtype=bool)
    got = days_since_clean_event(rain, wash)
    # before the first reset the clock counts from record start; rain on idx 3; wash on idx 6
    np.testing.assert_array_equal(got, [1, 2, 3, 0, 1, 2, 0, 1])


def test_days_since_clean_is_capped():
    assert days_since_clean_event(np.zeros(200), np.zeros(200, dtype=bool)).max() == 90


def test_block_ids_split_on_gaps():
    days = np.array(["2025-11-20", "2025-11-21", "2025-11-21", "2025-12-20", "2025-12-21"], dtype="datetime64[D]")
    np.testing.assert_array_equal(block_ids(days), [0, 0, 0, 1, 1])


# ── Integration: repaired data on disk ─────────────────────────────────────
@pytest.mark.skipif(not FIVE_MIN.exists(), reason="5-min telemetry not built")
def test_5min_telemetry_has_no_phantom_solar():
    f5 = pl.read_csv(FIVE_MIN, try_parse_dates=True)
    assert "solar_power_kw_legacy" in f5.columns                     # original preserved for audit
    assert (f5["solar_power_kw"] == f5["pv_true_kw"]).all()
    assert f5["pv_true_kw"].max() <= ARRAY_KWP + 1e-9
    assert f5["pv_true_kw"].min() >= 0.0
    # every 5-min row whose battery was discharging >0.5 kW overnight now carries 0 kW PV
    night = f5.filter((pl.col("timestamp").dt.hour() <= 4) | (pl.col("timestamp").dt.hour() >= 21))
    assert night.filter(pl.col("battery_power_kw") > 0.5)["pv_true_kw"].max() == 0.0


@pytest.mark.skipif(not (RECON.exists() and DAILY.exists()), reason="reconstruction not built")
def test_reconstruction_matches_portal_daily_log_and_physics():
    r = pl.read_csv(RECON, try_parse_dates=True)
    d = pl.read_csv(DAILY, try_parse_dates=True)
    assert r.height == 11_136 and r["solar_energy_kwh"].null_count() == 0
    by_day = r.group_by("date").agg(pl.col("solar_energy_kwh").sum().alias("s")).join(d, on="date")
    assert (by_day["s"] - by_day["generation_kwh"]).abs().max() < 1e-6
    assert r["solar_energy_kwh"].max() <= ARRAY_KWP + 1e-9
    assert r["solar_energy_kwh"].min() >= 0.0
    assert set(r["solar_source"].unique().to_list()) == {"measured_5min", "reconstructed"}
    assert r.filter(pl.col("solar_source") == "measured_5min")["date"].n_unique() >= 39


@pytest.mark.skipif(not MASTER.exists(), reason="master dataset not built")
def test_master_dataset_night_solar_is_exactly_zero_and_complete():
    a = verify_master(MASTER)
    assert a["rows"] == 11_136
    assert a["solar_nulls"] == 0
    assert a["night_rows_with_solar"] == 0                           # GHI == 0  =>  solar == 0.0
    assert a["max_hourly_kw"] <= ARRAY_KWP + 1e-9
    assert a["max_abs_daily_err_kwh"] < 1e-6
