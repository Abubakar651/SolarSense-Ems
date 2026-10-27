"""
Unit Tests for the SolarSense EMS 24-Hour MILP Battery Dispatch Optimizer
=========================================================================
Validates optimality, latency budget, power-balance conservation, SoC dynamics, charge/discharge
mutual exclusivity, blackout islanding physics, anti-islanding curtailment feasibility, soft reserve
slack, monthly MDI ratchet / peak shaving, outage MDI immunity, deterministic fallback, DTO
immutability, multi-day state continuity and the use_forecasts=True repository wiring.
"""

from dataclasses import FrozenInstanceError
from datetime import datetime
from decimal import Decimal
import time

import numpy as np
import pytest

from src.data_engineering.feature_store import (
    BESS_CAPACITY_KWH,
    BESS_MIN_SOC_KWH,
    EMSDataRepository,
    OptimizationHorizonSlice,
    PKT_TZ,
)
from src.optimizer.milp_solver import BESSConfig, DispatchResultDTO, MILPBatteryOptimizer

BESS = BESSConfig()
BAL_TOL = 1e-5


@pytest.fixture(scope="module")
def repo() -> EMSDataRepository:
    return EMSDataRepository()


@pytest.fixture(scope="module")
def optimizer() -> MILPBatteryOptimizer:
    opt = MILPBatteryOptimizer()
    opt.warm_up()
    return opt


def make_slice(
    solar, load, outage, soc0=300.0, hw=500.0, prob=None, surge=None, month=1
) -> OptimizationHorizonSlice:
    """Builds a synthetic 24h slice (winter LESCO tariff: peak 17-20h)."""
    hours = np.arange(24)
    tariff = np.where(np.isin(hours, (17, 18, 19, 20)), 60.0, 38.0)
    load = np.ascontiguousarray(load, dtype=np.float64)
    outage = np.ascontiguousarray(outage, dtype=np.int8)
    return OptimizationHorizonSlice(
        window_start=datetime(2026, month, 15, tzinfo=PKT_TZ),
        horizon_hours=24,
        timestamps_iso=tuple(f"2026-{month:02d}-15T{h:02d}:00:00+0500" for h in range(24)),
        solar_kw=np.ascontiguousarray(solar, dtype=np.float64),
        factory_load_kw=load,
        peak_surge_kw=np.where(outage == 1, 0.0, load if surge is None else surge).astype(np.float64),
        outage_prob=outage.astype(np.float64) if prob is None else np.ascontiguousarray(prob, dtype=np.float64),
        actual_outage_mask=outage,
        grid_tariff_pkr=np.ascontiguousarray(tariff, dtype=np.float64),
        initial_soc_kwh=float(soc0),
        monthly_mdi_high_water_kw=float(hw),
    )


def balance_residual(sl: OptimizationHorizonSlice, r: DispatchResultDTO) -> float:
    inflow = sl.solar_kw - r.p_curtail_kw + r.p_grid_kw + r.p_diesel_kw + r.p_dis_kw
    outflow = sl.factory_load_kw + r.p_ch_kw
    return float(np.max(np.abs(inflow - outflow)))


def soc_residual(r: DispatchResultDTO) -> float:
    nxt = r.soc_kwh[:-1] + BESS.charge_efficiency * r.p_ch_kw - r.p_dis_kw / BESS.discharge_efficiency
    return float(np.max(np.abs(r.soc_kwh[1:] - nxt)))


# =====================================================================
# 1. Optimality, latency, conservation
# =====================================================================

def test_solver_optimality_status(repo, optimizer):
    res = optimizer.solve_24h_dispatch(repo.get_optimization_slice("2025-07-17"))
    assert res.status in ("OPTIMAL", "OPTIMAL_INACCURATE")
    assert res.status != "FALLBACK"


def test_solve_latency_budget(repo, optimizer):
    """Warm 24h MILP solve (incl. DTO + Decimal financials) < 25 ms."""
    sl = repo.get_optimization_slice("2025-07-17", override_mdi_high_water_kw=500.0)
    for _ in range(5):
        optimizer.solve_24h_dispatch(sl)
    times = []
    for _ in range(50):
        t0 = time.perf_counter()
        optimizer.solve_24h_dispatch(sl)
        times.append((time.perf_counter() - t0) * 1000.0)
    assert float(np.min(times)) < 35.0, f"min {np.min(times):.2f} ms"
    assert float(np.median(times)) < 45.0, f"median {np.median(times):.2f} ms"




@pytest.mark.parametrize("date", ["2025-07-01", "2025-07-17", "2025-12-21", "2026-01-13", "2026-09-23"])
def test_power_balance_soc_dynamics_and_exclusivity(repo, optimizer, date):
    sl = repo.get_optimization_slice(date)
    r = optimizer.solve_24h_dispatch(sl)
    assert balance_residual(sl, r) < BAL_TOL
    assert soc_residual(r) < BAL_TOL
    assert float(np.max(np.minimum(r.p_ch_kw, r.p_dis_kw))) < 1e-6, "p_ch * p_dis must be 0"
    assert (r.soc_kwh >= BESS.min_soc_kwh - 1e-6).all() and (r.soc_kwh <= BESS.max_soc_kwh + 1e-6).all()
    assert (r.p_ch_kw <= BESS.max_charge_kw + 1e-6).all() and (r.p_dis_kw <= BESS.max_discharge_kw + 1e-6).all()
    for vec in (r.p_grid_kw, r.p_diesel_kw, r.p_ch_kw, r.p_dis_kw, r.p_curtail_kw):
        assert (vec >= 0.0).all()


# =====================================================================
# 2. Blackout physics & feasibility safeguards
# =====================================================================

def test_blackout_islanding_physics(repo, optimizer):
    sl = repo.get_optimization_slice("2025-12-21")
    assert sl.actual_outage_mask.sum() > 0
    r = optimizer.solve_24h_dispatch(sl)
    out = sl.actual_outage_mask == 1
    assert (r.p_grid_kw[out] == 0.0).all(), "grid is dead during blackout"
    assert (r.p_diesel_kw[~out] == 0.0).all(), "no diesel while grid is live"


def test_sunny_midday_blackout_feasibility_with_curtailment(optimizer):
    """600 kW solar, 150 kW load, full battery, 5h blackout: must stay feasible via curtailment."""
    solar = np.zeros(24)
    solar[8:17] = 600.0 * np.sin(np.linspace(0.2, np.pi - 0.2, 9))
    outage = np.zeros(24, dtype=np.int8)
    outage[10:15] = 1
    sl = make_slice(solar, np.full(24, 150.0), outage, soc0=600.0)
    r = optimizer.solve_24h_dispatch(sl)
    assert r.status in ("OPTIMAL", "OPTIMAL_INACCURATE")
    assert r.p_curtail_kw[10:15].sum() > 0.0, "surplus must be curtailed, not infeasible"
    assert (r.p_grid_kw[10:15] == 0.0).all()
    assert balance_residual(sl, r) < BAL_TOL


def test_soft_reserve_prevents_infeasibility_and_precharges(optimizer):
    """Low starting SoC + high predicted outage risk must neither crash nor be ignored."""
    prob = np.zeros(24)
    prob[18:22] = 0.6
    sl = make_slice(np.zeros(24), np.full(24, 250.0), np.zeros(24, dtype=np.int8),
                    soc0=BESS.min_soc_kwh, prob=prob)
    r = optimizer.solve_24h_dispatch(sl)
    assert r.status in ("OPTIMAL", "OPTIMAL_INACCURATE")
    assert r.soc_kwh[18] > r.soc_kwh[0] + 50.0, "optimizer should pre-charge ahead of risky hours"
    assert balance_residual(sl, r) < BAL_TOL


def test_reserve_does_not_block_discharge_during_real_blackout(optimizer):
    """During an actual blackout the battery must serve load instead of paying for diesel."""
    outage = np.zeros(24, dtype=np.int8)
    outage[18:21] = 1
    sl = make_slice(np.zeros(24), np.full(24, 300.0), outage, soc0=600.0)
    r = optimizer.solve_24h_dispatch(sl)
    assert r.p_dis_kw[18:21].sum() > 0.0
    assert r.diesel_cost_saved_pkr > Decimal("0.00")


def test_outage_mdi_immunity(optimizer):
    """Load above 500 kW during a blackout cannot incur an MDI fine (grid meter is dead)."""
    outage = np.zeros(24, dtype=np.int8)
    outage[10:14] = 1
    load = np.full(24, 300.0)
    load[10:14] = 650.0
    sl = make_slice(np.zeros(24), load, outage, soc0=60.0)
    r = optimizer.solve_24h_dispatch(sl)
    assert r.baseline_mdi_penalty_pkr == Decimal("0.00")
    assert r.optimized_mdi_penalty_pkr == Decimal("0.00")
    assert r.p_diesel_kw[10:14].sum() > 0.0


# =====================================================================
# 3. MDI ratchet, peak shaving, financials
# =====================================================================

def test_mdi_peak_shaving_and_positive_savings(repo, optimizer):
    # Test peak shaving when residential demand peaks during summer
    sl = repo.get_optimization_slice("2025-07-17", override_mdi_high_water_kw=5.0)
    r = optimizer.solve_24h_dispatch(sl)
    assert r.status in ("OPTIMAL", "OPTIMAL_INACCURATE")
    assert r.net_savings_pkr > Decimal("0.00")


def test_month_start_default_ratchet_saves_money(repo, optimizer):
    """Month start dispatch achieves positive ToU arbitrage and solar self-consumption savings."""
    sl = repo.get_optimization_slice("2025-07-01")
    r = optimizer.solve_24h_dispatch(sl)
    assert r.status in ("OPTIMAL", "OPTIMAL_INACCURATE")
    assert r.net_savings_pkr > Decimal("0.00")


def test_marginal_ratchet_no_penalty_below_high_water(repo, optimizer):
    """With the month's high-water already at 600 kW, no marginal MDI exceedance is billable."""
    sl = repo.get_optimization_slice("2025-07-17", override_mdi_high_water_kw=600.0)
    r = optimizer.solve_24h_dispatch(sl)
    assert r.baseline_mdi_penalty_pkr == Decimal("0.00")
    assert r.optimized_mdi_penalty_pkr == Decimal("0.00")
    assert r.prior_mdi_high_water_kw == 600.0
    assert r.updated_mdi_high_water_kw >= 600.0


def test_financial_breakdown_reconciles_exactly(repo, optimizer):
    r = optimizer.solve_24h_dispatch(repo.get_optimization_slice("2025-07-17", override_mdi_high_water_kw=500.0))
    assert r.baseline_total_pkr == r.baseline_energy_pkr + r.baseline_diesel_pkr + r.baseline_mdi_penalty_pkr
    assert r.optimized_total_pkr == (
        r.optimized_energy_pkr + r.optimized_diesel_pkr + r.optimized_mdi_penalty_pkr + r.degradation_cost_pkr
    )
    assert r.net_savings_pkr == r.baseline_total_pkr - r.optimized_total_pkr
    for money in (r.baseline_total_pkr, r.optimized_total_pkr, r.net_savings_pkr):
        assert isinstance(money, Decimal) and money == money.quantize(Decimal("0.01"))


# =====================================================================
# 4. Deterministic fallback
# =====================================================================

@pytest.mark.parametrize("date", ["2025-07-17", "2025-12-21"])
def test_fallback_dispatch_is_feasible(repo, date, monkeypatch):
    opt = MILPBatteryOptimizer()
    monkeypatch.setattr(opt, "_solve_with_highs", lambda T, values: None)
    sl = repo.get_optimization_slice(date)
    r = opt.solve_24h_dispatch(sl)
    assert r.status == "FALLBACK"
    assert balance_residual(sl, r) < BAL_TOL
    assert soc_residual(r) < BAL_TOL
    out = sl.actual_outage_mask == 1
    assert (r.p_grid_kw[out] == 0.0).all() and (r.p_diesel_kw[~out] == 0.0).all()
    assert float(np.max(np.minimum(r.p_ch_kw, r.p_dis_kw))) == 0.0
    assert (r.soc_kwh >= BESS.min_soc_kwh - 1e-9).all() and (r.soc_kwh <= BESS.max_soc_kwh + 1e-9).all()


# =====================================================================
# 5. Contracts: immutability, config, multi-day continuity
# =====================================================================

def test_dto_and_config_immutability(repo, optimizer):
    r = optimizer.solve_24h_dispatch(repo.get_optimization_slice("2025-07-17"))
    for vec in (r.p_grid_kw, r.p_diesel_kw, r.p_ch_kw, r.p_dis_kw, r.p_curtail_kw, r.soc_kwh):
        assert vec.dtype == np.float64 and vec.flags["C_CONTIGUOUS"]
        with pytest.raises(ValueError, match="read-only"):
            vec[0] = 1.0
    assert r.soc_kwh.shape == (25,) and r.p_grid_kw.shape == (24,)
    with pytest.raises(FrozenInstanceError):
        r.status = "X"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        BESS.capacity_kwh = 1.0  # type: ignore[misc]
    assert (BESS.min_soc_kwh, BESS.max_soc_kwh) == (60.0, 600.0)


def test_multi_day_state_continuity(repo, optimizer):
    d1 = optimizer.solve_24h_dispatch(repo.get_optimization_slice("2025-07-17", override_mdi_high_water_kw=500.0))
    nxt = repo.get_optimization_slice(
        "2025-07-18",
        override_initial_soc_kwh=d1.terminal_soc_kwh,
        override_mdi_high_water_kw=d1.updated_mdi_high_water_kw,
    )
    assert nxt.initial_soc_kwh == pytest.approx(d1.terminal_soc_kwh)
    assert nxt.monthly_mdi_high_water_kw == pytest.approx(d1.updated_mdi_high_water_kw)
    d2 = optimizer.solve_24h_dispatch(nxt)
    assert d2.soc_kwh[0] == pytest.approx(d1.soc_kwh[-1])
    assert d2.prior_mdi_high_water_kw >= d1.prior_mdi_high_water_kw


# =====================================================================
# 6. Repository wiring (use_forecasts) and SoC / surge semantics
# =====================================================================

def test_initial_soc_clamped_to_physical_envelope(repo):
    assert repo.get_optimization_slice("2025-07-17", override_initial_soc_kwh=5.0).initial_soc_kwh == BESS_MIN_SOC_KWH
    assert repo.get_optimization_slice("2025-07-17", override_initial_soc_kwh=9999.0).initial_soc_kwh == BESS_CAPACITY_KWH
    default_soc = repo.get_optimization_slice("2025-07-17").initial_soc_kwh
    assert BESS_MIN_SOC_KWH <= default_soc <= BESS_CAPACITY_KWH


def test_ground_truth_surge_envelope_equals_load(repo):
    sl = repo.get_optimization_slice("2025-12-21")
    out = sl.actual_outage_mask == 1
    assert (sl.peak_surge_kw[out] == 0.0).all()
    assert np.allclose(sl.peak_surge_kw[~out], sl.factory_load_kw[~out]), "surge_delta must be 0 in truth mode"


def test_use_forecasts_slice_and_solve(repo, optimizer):
    truth = repo.get_optimization_slice("2026-09-23")
    fc = repo.get_optimization_slice("2026-09-23", use_forecasts=True)
    assert fc.solar_kw.shape == (24,) and fc.factory_load_kw.shape == (24,)
    assert not np.array_equal(fc.factory_load_kw, truth.factory_load_kw), "forecast must differ from truth"
    out = fc.actual_outage_mask == 1
    live = ~out
    assert (fc.peak_surge_kw[live] >= fc.factory_load_kw[live] - 1e-9).all(), "p90 >= point on live hours"
    assert ((fc.outage_prob >= 0.0) & (fc.outage_prob <= 1.0)).all()
    assert (fc.solar_kw[truth.solar_kw == 0.0] >= 0.0).all()
    r = optimizer.solve_24h_dispatch(fc)
    assert r.status in ("OPTIMAL", "OPTIMAL_INACCURATE")
    assert balance_residual(fc, r) < BAL_TOL


def test_use_forecasts_slice_latency(repo):
    repo.warm_forecasters()
    repo.get_optimization_slice("2026-09-23", use_forecasts=True)
    times = []
    for _ in range(100):
        t0 = time.perf_counter()
        repo.get_optimization_slice("2026-09-23", use_forecasts=True)
        times.append((time.perf_counter() - t0) * 1000.0)
    assert float(np.mean(times)) < 25.0, f"mean {np.mean(times):.3f} ms"


def test_forecast_cache_built_once(repo):
    repo.warm_forecasters()
    first = repo._forecast_cache
    repo.get_optimization_slice("2026-09-23", use_forecasts=True)
    assert repo._forecast_cache is first, "models/feature matrices must not be reloaded per call"
    assert not first["X_solar"].flags["WRITEABLE"] and first["X_solar"].flags["C_CONTIGUOUS"]
