"""
Unit Tests for SolarSense EMS High-Performance Feature Store & Data Repository
=============================================================================
Validates:
1. Canonical repository initialization & physical domain invariants.
2. 24-hour Optimization Horizon Slice with zero-copy NumPy vectors.
3. Multi-day state overrides (initial SoC & monthly MDI ratchet).
4. Dynamic NEPRA/LESCO B3 Tariff Strategy with seasonal peak windows.
5. Target-aware ML feature matrix splits with 24-hour purge gap.
6. Simulation Window DTO formatting for Next.js 60 FPS playback.
7. MDI penalty spike detection and Polars engine consistency.
"""

from datetime import datetime
from decimal import Decimal
import numpy as np
import polars as pl
import pytest

from src.data_engineering.feature_store import (
    EMSDataRepository,
    TariffPolicy,
    OptimizationHorizonSlice,
    SimulationWindowDTO,
    MLTaskSplits,
    PKT_TZ,
)


@pytest.fixture(scope="module")
def repo() -> EMSDataRepository:
    """Instantiates the repository once across all test cases."""
    return EMSDataRepository()


# =====================================================================
# 1. Repository Invariants & Physical Integrity
# =====================================================================

def test_repository_invariants(repo: EMSDataRepository):
    """Verifies row counts, date bounds, and timezone consistency."""
    meta = repo.get_metadata()
    assert meta["total_records"] == 11136, "Dataset must have exactly 11,136 hourly rows (464 days)"
    assert meta["total_days"] == 464, "Total unique days must equal 464"
    assert meta["sanctioned_load_kw"] == 500.0, "Sanctioned capacity ceiling must be 500 kW"
    assert meta["total_historical_mdi_violations"] > 0, "Must detect historical MDI violations"


def test_zero_solar_at_night(repo: EMSDataRepository):
    """Ensures physics invariant: solar generation must be 0.0 W when GHI == 0."""
    night_records = repo._df.filter(pl.col("ghi_wm2") == 0.0)
    assert night_records.height > 0
    max_night_solar = night_records["effective_solar_kw"].max()
    assert max_night_solar == 0.0, f"Solar power at night must be 0.0, got {max_night_solar}"


def test_timezone_normalization(repo: EMSDataRepository):
    """Validates that all timestamps are localized to Asia/Karachi (UTC+05:00)."""
    ts_sample = repo._df["timestamp"][0]
    assert ts_sample.tzinfo is not None, "Timestamp must be timezone-aware"
    assert str(ts_sample.tzinfo) == "Asia/Karachi", "Timezone must be Asia/Karachi"


# =====================================================================
# 2. Optimization Horizon Slice & State Overrides (Tweak 1)
# =====================================================================

def test_optimization_slice_shapes_and_types(repo: EMSDataRepository):
    """Tests 24-hour vector shapes and dtypes required by HiGHS/CVXPY."""
    slice_data = repo.get_optimization_slice("2026-09-23")
    assert isinstance(slice_data, OptimizationHorizonSlice)
    assert slice_data.horizon_hours == 24
    assert len(slice_data.timestamps_iso) == 24

    # 1D C-contiguous NumPy vectors of length 24
    assert slice_data.solar_kw.shape == (24,)
    assert slice_data.solar_kw.dtype == np.float64
    assert slice_data.factory_load_kw.shape == (24,)
    assert slice_data.factory_load_kw.dtype == np.float64
    assert slice_data.grid_tariff_pkr.shape == (24,)
    assert slice_data.grid_tariff_pkr.dtype == np.float64
    assert slice_data.outage_prob.shape == (24,)
    assert slice_data.actual_outage_mask.shape == (24,)
    assert slice_data.actual_outage_mask.dtype == np.int8


def test_multi_day_state_overrides(repo: EMSDataRepository):
    """
    Tweak 1: Validates that sequential multi-day simulation overrides
    override_initial_soc_kwh and override_mdi_high_water_kw correctly.
    """
    # 1. Ground truth default
    default_slice = repo.get_optimization_slice("2026-09-23")
    assert default_slice.is_counterfactual is False

    # 2. Overridden state from previous day's solver output
    custom_soc = 345.5
    custom_high_water = 528.0
    overridden_slice = repo.get_optimization_slice(
        "2026-09-23",
        override_initial_soc_kwh=custom_soc,
        override_mdi_high_water_kw=custom_high_water,
    )
    assert overridden_slice.is_counterfactual is True
    assert overridden_slice.initial_soc_kwh == custom_soc
    assert overridden_slice.monthly_mdi_high_water_kw == custom_high_water


def test_monthly_mdi_ratchet_tracking(repo: EMSDataRepository):
    """Verifies that the monthly high-water mark is at least the sanctioned 500 kW ceiling."""
    slice_data = repo.get_optimization_slice("2026-09-23")
    assert slice_data.monthly_mdi_high_water_kw >= 500.0


# =====================================================================
# 3. Dynamic Tariff Policy Strategy Pattern
# =====================================================================

def test_tariff_policy_seasonal_windows():
    """Verifies official LESCO 4-hour seasonal peak window shifts."""
    policy = TariffPolicy()

    # Winter (Jan): 17:00 – 21:00
    assert policy.get_peak_hours_for_month(1) == (17, 18, 19, 20)
    assert policy.is_peak_hour(datetime(2026, 1, 15, 17, 30, tzinfo=PKT_TZ)) is True
    assert policy.is_peak_hour(datetime(2026, 1, 15, 15, 0, tzinfo=PKT_TZ)) is False

    # Summer (Jul): 19:00 – 23:00
    assert policy.get_peak_hours_for_month(7) == (19, 20, 21, 22)
    assert policy.is_peak_hour(datetime(2026, 7, 15, 19, 30, tzinfo=PKT_TZ)) is True
    assert policy.is_peak_hour(datetime(2026, 7, 15, 17, 30, tzinfo=PKT_TZ)) is False

    # Autumn (Oct): 18:00 – 22:00
    assert policy.get_peak_hours_for_month(10) == (18, 19, 20, 21)


def test_marginal_mdi_penalty_calculation():
    """Verifies that MDI penalty is only assessed on marginal increases above the ratchet."""
    policy = TariffPolicy(mdi_penalty_per_kw_pkr=Decimal("1200.00"), sanctioned_load_kw=500.0)

    # 1. Peak 530 kW against default 500 kW ceiling -> 30 kW exceedance * 1200 PKR = 36,000 PKR
    pen1 = policy.calculate_marginal_mdi_penalty(peak_kw=530.0, current_high_water_mark_kw=500.0)
    assert pen1 == Decimal("36000.00")

    # 2. Subsequent peak of 525 kW in the same month -> no new penalty
    pen2 = policy.calculate_marginal_mdi_penalty(peak_kw=525.0, current_high_water_mark_kw=530.0)
    assert pen2 == Decimal("0.00")

    # 3. New record peak of 540 kW in the same month -> 10 kW marginal increase * 1200 PKR = 12,000 PKR
    pen3 = policy.calculate_marginal_mdi_penalty(peak_kw=540.0, current_high_water_mark_kw=530.0)
    assert pen3 == Decimal("12000.00")


# =====================================================================
# 4. Target-Aware Purged ML Splitting (Tweak 2)
# =====================================================================

def test_ml_target_aware_splits_solar(repo: EMSDataRepository):
    """Tweak 2: Validates solar forecasting split has correct features and no cross-target leaks."""
    splits = repo.get_ml_feature_matrix("solar")
    assert isinstance(splits, MLTaskSplits)
    assert splits.task == "solar"

    # Strict isolation: solar model must not see factory load or future outages
    assert "factory_load_kw" not in splits.feature_names
    assert "outage_flag" not in splits.feature_names
    assert "tariff_rate_pkr" not in splits.feature_names
    assert "ghi_wm2" in splits.feature_names
    assert "hour_sin" in splits.feature_names

    # Check non-empty partitions
    assert splits.train_target.shape[0] > 0
    assert splits.val_target.shape[0] > 0
    assert splits.test_target.shape[0] > 0


def test_ml_target_aware_splits_load(repo: EMSDataRepository):
    """Tweak 2: Validates load demand split has shift features and no solar leaks."""
    splits = repo.get_ml_feature_matrix("load")
    assert splits.task == "load"
    assert "effective_solar_kw" not in splits.feature_names
    assert "factory_shift_id" in splits.feature_names
    assert splits.train_target.shape[0] > 0


def test_ml_purge_gap_leakage_isolation(repo: EMSDataRepository):
    """Verifies that a 24-hour purge gap prevents lookahead boundary overlap."""
    train_df, val_df, test_df = repo.get_raw_splits(
        train_end="2026-06-30 23:00:00",
        val_end="2026-08-31 23:00:00",
        purge_hours=24,
    )
    t_train_last = train_df["timestamp"].max()
    t_val_first = val_df["timestamp"].min()
    gap_hours = (t_val_first - t_train_last).total_seconds() / 3600.0

    # Gap between last train hour and first val hour must be at least purge_hours (24.0h)
    assert gap_hours >= 24.0, f"Purge gap between train and val must be >= 24h, got {gap_hours}h"


# =====================================================================
# 5. Simulation Window DTO (Next.js / FastAPI Ready)
# =====================================================================

def test_simulation_window_dto(repo: EMSDataRepository):
    """Tests 24-hour JSON-ready DTO generation for web UI rendering."""
    sim = repo.get_simulation_window("2026-09-23")
    assert isinstance(sim, SimulationWindowDTO)
    assert sim.date_str == "2026-09-23"
    assert sim.horizon_hours == 24
    assert len(sim.hours) == 24
    assert len(sim.solar_generation_kw) == 24
    assert len(sim.factory_load_kw) == 24
    assert sim.baseline_electricity_cost_pkr > 0.0

    # Serialization test
    d = sim.to_dict()
    assert isinstance(d, dict)
    assert "solar_generation_kw" in d
    assert "baseline_mdi_penalty_pkr" in d


# =====================================================================
# 6. MDI Spikes Query (Tweak 3: Engine Consistency)
# =====================================================================

def test_mdi_spikes_polars_consistency(repo: EMSDataRepository):
    """Tweak 3: Validates that get_mdi_spikes returns a Polars DataFrame with correct spikes."""
    spikes = repo.get_mdi_spikes(threshold_kw=500.0)
    assert isinstance(spikes, pl.DataFrame), "Must return Polars DataFrame for engine consistency"
    assert spikes.height == 169, f"Expected exactly 169 grid-connected spikes > 500kW, got {spikes.height}"

    # All returned rows must exceed 500 kW net grid draw
    min_spike = spikes["grid_import_kw"].min()
    assert min_spike > 500.0, f"Expected grid_import_kw > 500, got {min_spike}"
    assert "exceedance_kw" in spikes.columns
    assert "instantaneous_penalty_pkr" in spikes.columns

    # Detail 1: Zero MDI violations allowed during blackouts
    blackout_violations = spikes.filter(pl.col("outage_flag") == 1).height
    assert blackout_violations == 0, "MDI violations must only occur when grid is connected"


# =====================================================================
# 7. Tightened Domain Details (MDI Physics, Diesel Cost, Read-Only, Lags)
# =====================================================================

def test_mdi_outage_physics_reconciliation(repo: EMSDataRepository):
    """
    Point 2: Reconciles historical 2.36 Million PKR MDI penalty.
    Asserts MDI fines only count during grid-connected hours (outage_flag == 0)
    and reflect net grid draw (grid_import_kw > 500).
    Also asserts that get_optimization_slice() monthly ratchet ignores blackout peaks.
    """
    spikes = repo.get_mdi_spikes(threshold_kw=500.0)
    total_penalty = ((spikes["grid_import_kw"] - 500.0) * float(repo.policy.mdi_penalty_per_kw_pkr)).sum()
    
    # Historical baseline loss. Was 2,360,353.20 PKR before the solar series was repaired/reconstructed
    # (repair_master_dataset.py); net grid draw = load - solar, so the baseline re-pins to the new solar.
    assert abs(total_penalty - 2334661.20) < 1.0, f"MDI penalty must equal 2.33M PKR, got {total_penalty:,.2f}"

    # Verify that monthly ratchet in get_optimization_slice ignores blackout hours
    # and tracks net grid peak import, staying >= 500.0 kW
    slice_data = repo.get_optimization_slice("2026-01-14")
    assert slice_data.monthly_mdi_high_water_kw >= 500.0
    assert (slice_data.peak_surge_kw[slice_data.actual_outage_mask == 1] == 0.0).all(), (
        "During blackouts, net grid peak surge must strictly equal 0.0 kW (outage MDI immunity)"
    )


def test_simulation_window_diesel_outage_cost(repo: EMSDataRepository):
    """
    Point 3: Verifies that get_simulation_window() charges 95.00 PKR/kWh (diesel cost)
    during outages (outage_flag == 1) and LESCO ToU rates only during grid-connected hours,
    plus the marginal monthly MDI penalty.
    """
    # 2026-01-13 has verified historical blackouts
    sim = repo.get_simulation_window("2026-01-13")
    assert any(flag == 1 for flag in sim.outage_flags), "Date 2026-01-13 must contain outage hours"
    assert sim.baseline_electricity_cost_pkr > 300000.0, "Baseline cost must include diesel generation cost"
    assert sim.total_baseline_cost_pkr == round(
        sim.baseline_electricity_cost_pkr + sim.baseline_mdi_penalty_pkr, 2
    ), "Total baseline must equal electricity cost + marginal MDI penalty"


def test_readonly_buffer_immutability(repo: EMSDataRepository):
    """
    Point 1: Validates that OptimizationHorizonSlice NumPy vectors are read-only
    via vec.setflags(write=False) and raise ValueError upon any mutation attempt.
    """
    slice_data = repo.get_optimization_slice("2026-09-23")

    # Asserting slice.solar_kw[0] = 999.0 raises ValueError
    with pytest.raises(ValueError, match="assignment destination is read-only"):
        slice_data.solar_kw[0] = 999.0

    with pytest.raises(ValueError, match="assignment destination is read-only"):
        slice_data.factory_load_kw[0] = 999.0

    with pytest.raises(ValueError, match="assignment destination is read-only"):
        slice_data.peak_surge_kw[0] = 999.0

    with pytest.raises(ValueError, match="assignment destination is read-only"):
        slice_data.grid_tariff_pkr[0] = 999.0

    with pytest.raises(ValueError, match="assignment destination is read-only"):
        slice_data.outage_prob[0] = 1.0

    with pytest.raises(ValueError, match="assignment destination is read-only"):
        slice_data.actual_outage_mask[0] = 1


def test_ml_causal_lag_features(repo: EMSDataRepository):
    """
    Point 4: Validates that get_ml_feature_matrix() adds causal historical lag features
    (lag_24h, lag_48h, lag_168h, rolling_mean_7d_lag24) with zero lookahead leakage.
    """
    solar_splits = repo.get_ml_feature_matrix("solar")
    expected_lags = [
        "lag_24h",
        "lag_48h",
        "lag_168h",
        "rolling_mean_7d_lag24",
        "effective_solar_kw_lag_24h",
        "effective_solar_kw_lag_48h",
        "effective_solar_kw_lag_168h",
        "effective_solar_kw_rolling_mean_7d_lag24",
    ]
    for lag in expected_lags:
        assert lag in solar_splits.feature_names, f"Expected {lag} in solar features"
        assert solar_splits.train_features[lag].null_count() == 0, f"No NaNs allowed in {lag}"

    load_splits = repo.get_ml_feature_matrix("load")
    assert "lag_24h" in load_splits.feature_names
    assert "lag_168h" in load_splits.feature_names
    assert "rolling_mean_7d_lag24" in load_splits.feature_names
    assert "factory_load_kw_lag_24h" in load_splits.feature_names
    assert load_splits.train_features["lag_24h"].null_count() == 0

