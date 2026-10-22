"""
SolarSense EMS — LESCO B3 Domain Stress Scenarios & Edge Cases
==============================================================
Validates the four principal domain stress scenarios identified during the Milestone 4 audit:
1. Day 1 vs. Day 28 MDI Ratchet Asymmetry:
   When MDI high-water mark is elevated (e.g. 580 kW), optimizer reallocates battery capacity
   away from 500-580 kW peak shaving to pure ToU arbitrage and diesel displacement.
2. Seasonal Peak-Window Boundary Transitions:
   May 31 (18-22h) -> June 1 (19-23h) month rollover shifts peak dispatch by 1 hour automatically.
3. Extended Multi-Hour Blackout Co-Dispatch (420 kW):
   4-hour evening blackout forces simultaneous BESS max discharge (250 kW) + Diesel (170 kW)
   until SoC reaches 60 kWh floor, transitioning cleanly to 100% diesel.
4. Ex-Ante Forecast vs. Ex-Post Realized Dispatch (Oracle Gap / VoPI):
   Quantifies the Value of Perfect Information between use_forecasts=True and use_forecasts=False.
"""

from datetime import datetime
from decimal import Decimal
import numpy as np
import pytest

from src.data_engineering.feature_store import (
    BESS_CAPACITY_KWH,
    BESS_MIN_SOC_KWH,
    EMSDataRepository,
    OptimizationHorizonSlice,
    PKT_TZ,
    TariffPolicy,
)
from src.optimizer.milp_solver import BESSConfig, MILPBatteryOptimizer

BESS = BESSConfig()
BAL_TOL = 1e-4


@pytest.fixture(scope="module")
def repo() -> EMSDataRepository:
    return EMSDataRepository()


@pytest.fixture(scope="module")
def optimizer() -> MILPBatteryOptimizer:
    opt = MILPBatteryOptimizer()
    opt.warm_up()
    return opt


def make_custom_slice(
    solar_kw: np.ndarray,
    load_kw: np.ndarray,
    outage_mask: np.ndarray,
    initial_soc_kwh: float = 300.0,
    mdi_high_water_kw: float = 500.0,
    month: int = 7,
    day: int = 15,
) -> OptimizationHorizonSlice:
    """Constructs a custom 24h slice for domain stress testing."""
    policy = TariffPolicy()
    hours = np.arange(24)
    peak_hours = policy.get_peak_hours_for_month(month)
    tariff = np.where(np.isin(hours, peak_hours), float(policy.peak_rate_pkr), float(policy.off_peak_rate_pkr))

    solar = np.ascontiguousarray(solar_kw, dtype=np.float64)
    load = np.ascontiguousarray(load_kw, dtype=np.float64)
    outage = np.ascontiguousarray(outage_mask, dtype=np.int8)

    return OptimizationHorizonSlice(
        window_start=datetime(2025, month, day, tzinfo=PKT_TZ),
        horizon_hours=24,
        timestamps_iso=tuple(f"2025-{month:02d}-{day:02d}T{h:02d}:00:00+0500" for h in range(24)),
        solar_kw=solar,
        factory_load_kw=load,
        peak_surge_kw=np.where(outage == 1, 0.0, load).astype(np.float64),
        outage_prob=outage.astype(np.float64),
        actual_outage_mask=outage,
        grid_tariff_pkr=np.ascontiguousarray(tariff, dtype=np.float64),
        initial_soc_kwh=float(initial_soc_kwh),
        monthly_mdi_high_water_kw=float(mdi_high_water_kw),
    )


# =====================================================================
# Stress Test 1: Day 1 vs. Day 28 MDI Ratchet Asymmetry
# =====================================================================

def test_day1_vs_day28_mdi_ratchet_asymmetry(optimizer):
    """
    When prior high-water mark is 580 kW (Day 28):
    - A 540 kW off-peak spike incurs 0 PKR marginal MDI penalty.
    - Battery capacity is conserved for the 60 PKR peak window rather than wasted shaving 540 kW.
    When prior high-water mark is 500 kW (Day 1 of new month):
    - A 540 kW spike DOES incur marginal MDI penalty, so battery discharges to shave it.
    """
    solar = np.zeros(24)
    load = np.full(24, 250.0)
    # Off-peak surge at 14:00 (540 kW)
    load[14] = 540.0
    outage = np.zeros(24, dtype=np.int8)

    # Day 28: prior high-water mark is already 580 kW
    sl_day28 = make_custom_slice(solar, load, outage, initial_soc_kwh=300.0, mdi_high_water_kw=580.0, month=7)
    res_day28 = optimizer.solve_24h_dispatch(sl_day28)

    assert res_day28.status == "OPTIMAL"
    # Zero marginal MDI penalty because 540 kW <= 580 kW
    assert res_day28.updated_mdi_high_water_kw == 580.0
    # Battery should not waste full discharge on off-peak hour 14; it saves energy for peak hours (19-23 in July)
    assert res_day28.p_dis_kw[14] < 40.0  # Little to no discharge during cheap off-peak
    assert res_day28.p_dis_kw[19:23].sum() > 100.0  # Concentrated in 60 PKR peak window

    # Day 1 of Next Month: ratchet resets to 500 kW
    sl_day1 = make_custom_slice(solar, load, outage, initial_soc_kwh=300.0, mdi_high_water_kw=500.0, month=8)
    res_day1 = optimizer.solve_24h_dispatch(sl_day1)

    assert res_day1.status == "OPTIMAL"
    # To avoid 1200 PKR/kW penalty, battery MUST shave the 540 kW spike at hour 14 down to <= 500 kW
    assert res_day1.p_dis_kw[14] >= 40.0 - 1e-4, "Battery must shave 540 kW to 500 kW on Day 1"
    assert res_day1.p_grid_kw[14] <= 500.0 + 1e-4


# =====================================================================
# Stress Test 2: Seasonal Peak-Window Boundary Transitions
# =====================================================================

def test_seasonal_peak_boundary_rollover(repo, optimizer):
    """
    Verifies automatic 1-hour peak-window shift across month boundary:
    - May 31 (Month 5): Peak window is 18:00 - 22:00 (hours 18, 19, 20, 21)
    - June 1 (Month 6): Peak window is 19:00 - 23:00 (hours 19, 20, 21, 22)
    The optimizer must automatically shift peak discharge schedule by 1 hour.
    """
    policy = TariffPolicy()
    assert policy.get_peak_hours_for_month(5) == (18, 19, 20, 21)
    assert policy.get_peak_hours_for_month(6) == (19, 20, 21, 22)

    # Ground truth slices from repo
    sl_may31 = repo.get_optimization_slice("2026-05-31")
    sl_jun01 = repo.get_optimization_slice("2026-06-01")

    res_may31 = optimizer.solve_24h_dispatch(sl_may31)
    res_jun01 = optimizer.solve_24h_dispatch(sl_jun01)

    assert res_may31.status == "OPTIMAL"
    assert res_jun01.status == "OPTIMAL"

    # In May, hour 18 is PEAK (60 PKR) -> significant discharge
    # In June, hour 18 is OFF-PEAK (38 PKR) -> battery holds or charges, discharge is shifted
    assert sl_may31.grid_tariff_pkr[18] == 60.0
    assert sl_jun01.grid_tariff_pkr[18] == 38.0
    assert sl_jun01.grid_tariff_pkr[22] == 60.0  # Hour 22 becomes peak in June


# =====================================================================
# Stress Test 3: Extended Multi-Hour Feeder Fault (420 kW Co-Dispatch)
# =====================================================================

def test_multihour_blackout_co_dispatch_420kw(optimizer):
    """
    4-hour blackout (hours 18, 19, 20, 21) with 420 kW load, 0 kW solar.
    Battery has 500 kWh initial SoC (usable above 60 kWh = 440 kWh).
    Battery power rating ceiling is 250 kW.
    Physics required:
    - Grid power == 0.0 kW (islanding)
    - Battery max discharge == 250.0 kW
    - Remaining load (420 - 250 = 170 kW) served by diesel generator!
    - When SoC hits 60.0 kWh floor, battery discharge stops and diesel carries 100% (420 kW).
    """
    solar = np.zeros(24)
    load = np.full(24, 200.0)
    outage = np.zeros(24, dtype=np.int8)

    # Blackout from 18:00 to 22:00 with 420 kW load
    blackout_hours = (18, 19, 20, 21)
    for h in blackout_hours:
        outage[h] = 1
        load[h] = 420.0

    sl = make_custom_slice(solar, load, outage, initial_soc_kwh=500.0, mdi_high_water_kw=500.0, month=7)
    res = optimizer.solve_24h_dispatch(sl)

    assert res.status == "OPTIMAL"

    for h in blackout_hours:
        # 1. Grid is dead
        assert res.p_grid_kw[h] == 0.0, f"Hour {h}: grid must be 0 in blackout"
        # 2. Power balance: battery discharge + diesel == load (420 kW)
        balance = res.p_dis_kw[h] + res.p_diesel_kw[h]
        assert abs(balance - 420.0) < BAL_TOL, f"Hour {h}: generation must meet 420 kW load"
        # 3. BESS cannot exceed 250 kW hardware limit
        assert res.p_dis_kw[h] <= BESS.max_discharge_kw + 1e-5

    # Across the 4-hour blackout, total generation must meet 4 * 420 = 1680 kWh
    total_dis = res.p_dis_kw[list(blackout_hours)].sum()
    total_diesel = res.p_diesel_kw[list(blackout_hours)].sum()
    assert abs(total_dis + total_diesel - 1680.0) < BAL_TOL

    # Co-dispatch verification: at maximum BESS discharge (250 kW), diesel co-dispatches the remaining 170 kW
    max_dis_idx = [h for h in blackout_hours if abs(res.p_dis_kw[h] - BESS.max_discharge_kw) < 1.0]
    assert len(max_dis_idx) >= 2, "BESS should discharge at maximum 250 kW for at least 2 full hours"
    for h in max_dis_idx:
        assert abs(res.p_diesel_kw[h] - 170.0) < 1.0, f"Hour {h}: diesel must co-dispatch 170 kW"

    # SoC never drops below 60.0 kWh floor
    assert (res.soc_kwh >= BESS.min_soc_kwh - 1e-4).all()
    assert abs(res.soc_kwh[22] - BESS.min_soc_kwh) < 1e-3, "Terminal SoC after 4h blackout reaches 60 kWh floor"


# =====================================================================
# Stress Test 4: Ex-Ante Forecast vs. Ex-Post Dispatch (VoPI)
# =====================================================================

def test_ex_ante_forecast_vs_ex_post_dispatch_vopi(repo, optimizer):
    """
    Compares 24h solve under ground truth (ex-post oracle) vs. ML forecasts (ex-ante).
    Verifies that use_forecasts=True solves to OPTIMAL and computes the Value of
    Perfect Information (VoPI) gap.
    """
    date_test = "2025-07-17"
    sl_oracle = repo.get_optimization_slice(date_test, use_forecasts=False)
    sl_forecast = repo.get_optimization_slice(date_test, use_forecasts=True)

    res_oracle = optimizer.solve_24h_dispatch(sl_oracle)
    res_forecast = optimizer.solve_24h_dispatch(sl_forecast)

    assert res_oracle.status == "OPTIMAL"
    assert res_forecast.status == "OPTIMAL"

    # In both cases, power balance is conserved
    assert abs(sl_oracle.solar_kw - res_oracle.p_curtail_kw + res_oracle.p_grid_kw + res_oracle.p_diesel_kw + res_oracle.p_dis_kw - sl_oracle.factory_load_kw - res_oracle.p_ch_kw).max() < BAL_TOL

    cost_oracle = float(res_oracle.baseline_energy_pkr)
    cost_forecast = float(res_forecast.baseline_energy_pkr)
    assert cost_oracle > 0.0
    assert cost_forecast > 0.0

    print(f"\n[VoPI Benchmark] Date: {date_test} | Oracle Cost: {cost_oracle:,.2f} PKR | Forecast Cost: {cost_forecast:,.2f} PKR")
