"""
SolarSense EMS — 24-Hour MILP Battery Dispatch Optimizer (CVXPY + HiGHS)
========================================================================
Minimises LESCO B3 energy cost + monthly MDI exceedance penalty + diesel backup fuel +
battery wear for a 24-hour horizon, returning an immutable `DispatchResultDTO` whose terminal
state (SoC, MDI high-water mark) feeds Day d+1 of a rolling multi-day backtest.

Design guarantees
-----------------
1. Parameterised, vectorised CVXPY problem (DPP): built ONCE per horizon length; each solve only
   assigns Parameter values, so Python canonicalisation overhead is minimal.
2. Always feasible by construction:
   - `p_curtail >= 0` absorbs sunny-blackout surplus (anti-islanding slack),
   - `p_diesel` is unconstrained in blackout hours, `p_grid` in live-grid hours,
   - the outage reserve floor is SOFT (`s_reserve >= 0`, penalised) - never a hard constraint.
3. Physics: blackout hours force `p_grid == 0`; live-grid hours force `p_diesel == 0`;
   MDI is billed only on grid-connected hours (outage MDI immunity) and only on the marginal
   exceedance above the monthly high-water mark (ratchet).
4. Charge/discharge mutual exclusivity enforced with binary variables (HiGHS MILP).
5. HiGHS status is verified before any `.value` is read; on any failure a deterministic
   rule-based dispatch is returned (`status == "FALLBACK"`).
6. Financials are quantised to 0.01 PKR with `Decimal` / `ROUND_HALF_EVEN`.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Dict, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cvxpy as cp
import numpy as np
import numpy.typing as npt

from src.data_engineering.feature_store import OptimizationHorizonSlice, TariffPolicy

FloatVec = npt.NDArray[np.float64]

_CENT = Decimal("0.01")


def _pkr(value: float) -> Decimal:
    """Quantises a float PKR amount to 0.01 using banker's rounding."""
    return Decimal(repr(round(float(value), 6))).quantize(_CENT, rounding=ROUND_HALF_EVEN)


# =====================================================================
# 1. Domain Contracts
# =====================================================================

@dataclass(frozen=True, slots=True)
class BESSConfig:
    """Immutable battery hardware parameters.
    Default: LESCO B3 Industrial microgrid benchmark (600 kWh / 250 kW).
    Use BESSConfig.station_residential() for Station LHR-RES-01.
    """
    capacity_kwh: float = 600.0
    max_charge_kw: float = 250.0
    max_discharge_kw: float = 250.0
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95
    min_soc_pct: float = 0.10   # 60 kWh hard physical floor
    max_soc_pct: float = 1.00   # 600 kWh ceiling
    degradation_cost_pkr_per_kwh: float = 2.0

    @classmethod
    def industrial_600kwh(cls) -> BESSConfig:
        """Factory for 600 kWh / 250 kW LESCO B3 Industrial microgrid battery."""
        return cls()

    @classmethod
    def station_residential(cls) -> BESSConfig:
        """Factory for Station LHR-RES-01 5.12 kWh LiFePO4 residential battery."""
        return cls(
            capacity_kwh=5.12,
            max_charge_kw=5.0,
            max_discharge_kw=5.0,
            charge_efficiency=0.95,
            discharge_efficiency=0.95,
            min_soc_pct=0.15,
            max_soc_pct=1.00,
            degradation_cost_pkr_per_kwh=2.0,
        )

    @property
    def min_soc_kwh(self) -> float:
        return self.capacity_kwh * self.min_soc_pct

    @property
    def max_soc_kwh(self) -> float:
        return self.capacity_kwh * self.max_soc_pct


@dataclass(frozen=True, slots=True)
class DispatchResultDTO:
    """Read-only optimiser output; terminal state feeds Day d+1 of a rolling backtest."""
    window_start: str
    status: str                      # "OPTIMAL", "OPTIMAL_INACCURATE" or "FALLBACK"
    solve_time_ms: float
    # Dispatch vectors (kW) / state trajectory (kWh) - write-locked, C-contiguous float64
    p_grid_kw: FloatVec
    p_diesel_kw: FloatVec
    p_ch_kw: FloatVec
    p_dis_kw: FloatVec
    p_curtail_kw: FloatVec
    soc_kwh: FloatVec                # length horizon + 1 (soc[0] is the initial state)
    # State continuity
    initial_soc_kwh: float
    terminal_soc_kwh: float
    prior_mdi_high_water_kw: float
    updated_mdi_high_water_kw: float
    # Financial breakdown (PKR, quantised to 0.01, ROUND_HALF_EVEN)
    baseline_energy_pkr: Decimal
    baseline_diesel_pkr: Decimal
    baseline_mdi_penalty_pkr: Decimal
    baseline_total_pkr: Decimal
    optimized_energy_pkr: Decimal
    optimized_diesel_pkr: Decimal
    optimized_mdi_penalty_pkr: Decimal
    degradation_cost_pkr: Decimal
    optimized_total_pkr: Decimal
    net_savings_pkr: Decimal
    mdi_penalty_saved_pkr: Decimal
    diesel_cost_saved_pkr: Decimal

    def __post_init__(self) -> None:
        for vec in (
            self.p_grid_kw, self.p_diesel_kw, self.p_ch_kw,
            self.p_dis_kw, self.p_curtail_kw, self.soc_kwh,
        ):
            vec.setflags(write=False)


class _ProblemBundle:
    """A built parameterised CVXPY problem plus handles to its variables/parameters."""
    __slots__ = ("prob", "vars", "params")

    def __init__(self, prob: cp.Problem, variables: Dict[str, cp.Variable], params: Dict[str, cp.Parameter]):
        self.prob = prob
        self.vars = variables
        self.params = params


# =====================================================================
# 2. Optimizer
# =====================================================================

class MILPBatteryOptimizer:
    """Parameterised HiGHS MILP battery dispatch with deterministic fallback."""

    def __init__(
        self,
        bess: Optional[BESSConfig] = None,
        policy: Optional[TariffPolicy] = None,
        outage_reserve_threshold: float = 0.05,
        reserve_target_fraction: float = 0.50,
        enforce_exclusivity: bool = True,
        time_limit_s: float = 0.5,
    ) -> None:
        self.bess = bess or BESSConfig()
        self.policy = policy or TariffPolicy()
        self.outage_reserve_threshold = float(outage_reserve_threshold)
        self.reserve_target_fraction = float(reserve_target_fraction)
        self.enforce_exclusivity = bool(enforce_exclusivity)
        self.time_limit_s = float(time_limit_s)
        self._bundles: Dict[int, _ProblemBundle] = {}

    # -----------------------------------------------------------------
    # Problem construction (once per horizon length)
    # -----------------------------------------------------------------

    def _build_problem(self, T: int) -> _ProblemBundle:
        b = self.bess
        diesel_rate = float(self.policy.diesel_cost_pkr)
        mdi_rate = float(self.policy.mdi_penalty_per_kw_pkr)

        # Parameters (DPP: only ever multiplied by variables, never by each other)
        solar = cp.Parameter(T, nonneg=True, name="solar")
        load = cp.Parameter(T, nonneg=True, name="load")
        tariff = cp.Parameter(T, nonneg=True, name="tariff")
        outage = cp.Parameter(T, nonneg=True, name="outage")          # 1 = grid dead
        live = cp.Parameter(T, nonneg=True, name="live")              # 1 = grid live
        live_surge = cp.Parameter(T, nonneg=True, name="live_surge")  # live * surge_delta
        reserve_target = cp.Parameter(T, nonneg=True, name="reserve_target")
        reserve_pen = cp.Parameter(T, nonneg=True, name="reserve_pen")
        hw = cp.Parameter(nonneg=True, name="mdi_high_water")
        soc0 = cp.Parameter(nonneg=True, name="soc0")
        peak_grid_cap = cp.Parameter(T, nonneg=True, name="peak_grid_cap")

        # Decision variables
        p_grid = cp.Variable(T, nonneg=True, name="p_grid")
        p_diesel = cp.Variable(T, nonneg=True, name="p_diesel")
        p_ch = cp.Variable(T, nonneg=True, name="p_ch")
        p_dis = cp.Variable(T, nonneg=True, name="p_dis")
        p_curtail = cp.Variable(T, nonneg=True, name="p_curtail")
        s_reserve = cp.Variable(T, nonneg=True, name="s_reserve")
        soc = cp.Variable(T + 1, name="soc")
        mdi_excess = cp.Variable(nonneg=True, name="new_mdi_exceedance_kw")

        constraints = [
            # Power balance with anti-islanding curtailment slack
            solar - p_curtail + p_grid + p_diesel + p_dis == load + p_ch,
            p_curtail <= solar,
            # Blackout islanding vs grid mode
            cp.multiply(outage, p_grid) == 0,
            cp.multiply(live, p_diesel) == 0,
            # Post-blackout peak-window recharge suppression:
            # Prevents grid import from charging battery during expensive Peak ToU hours (46.85 PKR/kWh).
            # Battery charging during peak can ONLY be powered by surplus solar.
            p_grid <= peak_grid_cap,
            # Battery dynamics and limits
            soc[0] == soc0,
            soc[1:] == soc[:-1] + b.charge_efficiency * p_ch - p_dis / b.discharge_efficiency,
            soc >= b.min_soc_kwh,
            soc <= b.max_soc_kwh,
            p_ch <= b.max_charge_kw,
            p_dis <= b.max_discharge_kw,
            # Monthly MDI ratchet: grid-connected hours only, incl. intra-hour surge delta
            cp.multiply(live, p_grid) + live_surge - hw <= mdi_excess,
            # Soft pre-emptive outage reserve (start-of-hour SoC)
            soc[:-1] + s_reserve >= reserve_target,
        ]

        variables: Dict[str, cp.Variable] = {
            "p_grid": p_grid, "p_diesel": p_diesel, "p_ch": p_ch, "p_dis": p_dis,
            "p_curtail": p_curtail, "s_reserve": s_reserve, "soc": soc, "mdi_excess": mdi_excess,
        }

        if self.enforce_exclusivity:
            u_ch = cp.Variable(T, boolean=True, name="u_ch")
            constraints += [
                p_ch <= b.max_charge_kw * u_ch,
                p_dis <= b.max_discharge_kw * (1 - u_ch),
            ]
            variables["u_ch"] = u_ch

        objective = cp.Minimize(
            tariff @ p_grid
            + diesel_rate * cp.sum(p_diesel)
            + b.degradation_cost_pkr_per_kwh * (cp.sum(p_ch) + cp.sum(p_dis))
            + reserve_pen @ s_reserve
            + mdi_rate * mdi_excess
        )
        params = {
            "solar": solar, "load": load, "tariff": tariff, "outage": outage, "live": live,
            "live_surge": live_surge, "reserve_target": reserve_target,
            "reserve_pen": reserve_pen, "hw": hw, "soc0": soc0,
            "peak_grid_cap": peak_grid_cap,
        }
        return _ProblemBundle(cp.Problem(objective, constraints), variables, params)

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    def warm_up(self, horizon_hours: int = 24) -> None:
        """
        Builds and canonicalises the parameterised problem and performs one dummy solve.
        Call once at application startup (FastAPI lifespan) so no request pays the ~30 ms
        one-time CVXPY build cost.
        """
        T = int(horizon_hours)
        b = self.bess
        values = {
            "solar": np.zeros(T), "load": np.full(T, 200.0), "tariff": np.full(T, 38.0),
            "outage": np.zeros(T), "live": np.ones(T), "live_surge": np.zeros(T),
            "reserve_target": np.full(T, b.min_soc_kwh), "reserve_pen": np.zeros(T),
            "hw": float(self.policy.sanctioned_load_kw), "soc0": 0.5 * b.capacity_kwh,
            "peak_grid_cap": np.full(T, 1e6, dtype=np.float64),
        }
        self._solve_with_highs(T, values)

    def solve_24h_dispatch(self, slice_data: OptimizationHorizonSlice) -> DispatchResultDTO:
        """Solves one horizon and returns the immutable dispatch + financial breakdown."""
        t_start = time.perf_counter()
        b = self.bess
        T = int(slice_data.horizon_hours)

        solar = np.maximum(np.asarray(slice_data.solar_kw, dtype=np.float64), 0.0)
        load = np.maximum(np.asarray(slice_data.factory_load_kw, dtype=np.float64), 0.0)
        tariff = np.asarray(slice_data.grid_tariff_pkr, dtype=np.float64)
        outage = (np.asarray(slice_data.actual_outage_mask) == 1).astype(np.float64)
        live = 1.0 - outage
        prob = np.clip(np.asarray(slice_data.outage_prob, dtype=np.float64), 0.0, 1.0)
        surge_delta = np.maximum(
            np.asarray(slice_data.peak_surge_kw, dtype=np.float64) - load, 0.0
        )
        live_surge = live * surge_delta
        hw = float(max(slice_data.monthly_mdi_high_water_kw, self.policy.sanctioned_load_kw))
        soc0 = float(min(max(slice_data.initial_soc_kwh, b.min_soc_kwh), b.max_soc_kwh))

        # Soft reserve: only on live-grid hours (during a real blackout the battery SHOULD discharge)
        risky = (prob >= self.outage_reserve_threshold) & (live > 0.5)
        reserve_target = np.where(
            risky, self.reserve_target_fraction * b.capacity_kwh, b.min_soc_kwh
        )
        reserve_pen = np.where(risky, float(self.policy.diesel_cost_pkr) * prob, 0.0)

        # Post-blackout peak recharge suppression (Argon Recommendation 1):
        # Prevents grid import from charging battery during expensive Peak ToU hours.
        # Capping grid import at load (p_grid <= load) ensures any battery charging during peak is powered purely by solar.
        peak_rate = float(self.policy.peak_rate_pkr)
        is_peak_window = tariff >= (peak_rate - 1e-3)
        peak_grid_cap = np.full(T, 1e6, dtype=np.float64)
        for t in range(T):
            if is_peak_window[t] and soc0 >= b.min_soc_kwh:
                peak_grid_cap[t] = load[t]

        values = {
            "solar": solar, "load": load, "tariff": tariff, "outage": outage, "live": live,
            "live_surge": live_surge, "reserve_target": reserve_target,
            "reserve_pen": reserve_pen, "hw": hw, "soc0": soc0,
            "peak_grid_cap": peak_grid_cap,
        }

        solved = self._solve_with_highs(T, values)
        status = "FALLBACK"
        if solved is not None:
            status, vecs = solved
        else:
            vecs = self._fallback_dispatch(values)

        p_grid, p_diesel, p_ch, p_dis, p_curtail, soc = vecs
        solve_time_ms = (time.perf_counter() - t_start) * 1000.0

        return self._assemble_result(
            slice_data, status, solve_time_ms, values,
            p_grid, p_diesel, p_ch, p_dis, p_curtail, soc,
        )

    # -----------------------------------------------------------------
    # HiGHS solve with status verification
    # -----------------------------------------------------------------

    def _solve_with_highs(
        self, T: int, values: Dict[str, object]
    ) -> Optional[Tuple[str, Tuple[FloatVec, ...]]]:
        try:
            bundle = self._bundles.get(T)
            if bundle is None:
                bundle = self._build_problem(T)
                self._bundles[T] = bundle
            for name, param in bundle.params.items():
                param.value = values[name]

            bundle.prob.solve(
                solver=cp.HIGHS,
                time_limit=self.time_limit_s,
                mip_rel_gap=1e-4,
            )
            if bundle.prob.status not in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
                return None
            if bundle.prob.value is None:
                return None

            v = bundle.vars
            raw = [v[k].value for k in ("p_grid", "p_diesel", "p_ch", "p_dis", "p_curtail", "soc")]
            if any(x is None or not np.all(np.isfinite(x)) for x in raw):
                return None
            return str(bundle.prob.status).upper(), self._clean(raw, values)
        except Exception:  # noqa: BLE001 - any solver/numerical failure -> deterministic fallback
            return None

    def _clean(self, raw, values) -> Tuple[FloatVec, ...]:
        """Snaps solver round-off (|x| < 1e-7) to 0 and re-clamps SoC into its physical envelope."""
        b = self.bess
        out = []
        for i, arr in enumerate(raw):
            a = np.ascontiguousarray(arr, dtype=np.float64).copy()
            if i < 5:
                a[np.abs(a) < 1e-7] = 0.0
                np.maximum(a, 0.0, out=a)
            else:
                np.clip(a, b.min_soc_kwh, b.max_soc_kwh, out=a)
            out.append(a)
        return tuple(out)  # type: ignore[return-value]

    # -----------------------------------------------------------------
    # Deterministic rule-based fallback (feasible by construction)
    # -----------------------------------------------------------------

    def _fallback_dispatch(self, values: Dict[str, object]) -> Tuple[FloatVec, ...]:
        """
        Greedy hour-by-hour dispatch used only if HiGHS fails. Stateful in SoC, so a sequential
        pass over the 24-hour horizon is required (permitted by the engineering standards).
        Rules: solar surplus charges the battery (excess curtailed); blackout deficit is served by
        the battery then diesel; live-grid peak-tariff hours and MDI breaches are shaved by
        discharge; cheapest-tariff hours top up the battery when headroom below the MDI mark exists.
        """
        b = self.bess
        solar, load, tariff = values["solar"], values["load"], values["tariff"]
        outage, live_surge = values["outage"], values["live_surge"]
        hw, soc_now = float(values["hw"]), float(values["soc0"])
        T = len(load)
        low_tariff = float(np.min(tariff))
        high_tariff = float(np.max(tariff))

        p_grid = np.zeros(T)
        p_diesel = np.zeros(T)
        p_ch = np.zeros(T)
        p_dis = np.zeros(T)
        p_curtail = np.zeros(T)
        soc = np.empty(T + 1)
        soc[0] = soc_now

        for t in range(T):
            net = load[t] - solar[t]
            avail_dis = max(0.0, (soc_now - b.min_soc_kwh) * b.discharge_efficiency)
            room_ch = max(0.0, (b.max_soc_kwh - soc_now) / b.charge_efficiency)

            if net < 0.0:  # solar surplus
                surplus = -net
                ch = min(surplus, b.max_charge_kw, room_ch)
                p_ch[t] = ch
                p_curtail[t] = surplus - ch
            elif outage[t] > 0.5:  # islanded deficit
                dis = min(net, b.max_discharge_kw, avail_dis)
                p_dis[t] = dis
                p_diesel[t] = net - dis
            else:  # live grid
                shave = max(0.0, net + live_surge[t] - hw)
                want = net if tariff[t] >= high_tariff and high_tariff > low_tariff else shave
                dis = min(max(want, shave), net, b.max_discharge_kw, avail_dis)
                p_dis[t] = dis
                ch = 0.0
                if dis == 0.0 and tariff[t] <= low_tariff:
                    headroom = max(0.0, hw - live_surge[t] - net)
                    ch = min(b.max_charge_kw, room_ch, headroom)
                p_ch[t] = ch
                p_grid[t] = net - dis + ch

            soc_now = soc_now + b.charge_efficiency * p_ch[t] - p_dis[t] / b.discharge_efficiency
            soc_now = min(max(soc_now, b.min_soc_kwh), b.max_soc_kwh)
            soc[t + 1] = soc_now

        return p_grid, p_diesel, p_ch, p_dis, p_curtail, soc

    # -----------------------------------------------------------------
    # Result assembly & financial reconciliation
    # -----------------------------------------------------------------

    def _assemble_result(
        self,
        slice_data: OptimizationHorizonSlice,
        status: str,
        solve_time_ms: float,
        values: Dict[str, object],
        p_grid: FloatVec, p_diesel: FloatVec, p_ch: FloatVec,
        p_dis: FloatVec, p_curtail: FloatVec, soc: FloatVec,
    ) -> DispatchResultDTO:
        b, policy = self.bess, self.policy
        solar, load, tariff = values["solar"], values["load"], values["tariff"]
        live, live_surge, hw = values["live"], values["live_surge"], float(values["hw"])
        diesel_rate = float(policy.diesel_cost_pkr)

        # Baseline (no battery): net demand after solar; diesel on blackout hours, ToU otherwise
        net = np.maximum(load - solar, 0.0)
        base_energy = _pkr(float(tariff @ (net * live)))
        base_diesel = _pkr(diesel_rate * float(np.sum(net * (1.0 - live))))
        grid_net = net * live
        base_peak = float(np.max(grid_net)) if np.any(live > 0.5) else 0.0
        base_mdi = policy.calculate_marginal_mdi_penalty(base_peak, hw)
        base_total = base_energy + base_diesel + base_mdi

        # Optimised
        opt_energy = _pkr(float(tariff @ p_grid))
        opt_diesel = _pkr(diesel_rate * float(np.sum(p_diesel)))
        opt_peak = float(np.max(live * p_grid + live_surge)) if np.any(live > 0.5) else 0.0
        opt_mdi = policy.calculate_marginal_mdi_penalty(opt_peak, hw)
        degradation = _pkr(
            b.degradation_cost_pkr_per_kwh * float(np.sum(p_ch) + np.sum(p_dis))
        )
        opt_total = opt_energy + opt_diesel + opt_mdi + degradation

        return DispatchResultDTO(
            window_start=slice_data.window_start.isoformat(),
            status=status,
            solve_time_ms=round(solve_time_ms, 4),
            p_grid_kw=np.ascontiguousarray(p_grid, dtype=np.float64),
            p_diesel_kw=np.ascontiguousarray(p_diesel, dtype=np.float64),
            p_ch_kw=np.ascontiguousarray(p_ch, dtype=np.float64),
            p_dis_kw=np.ascontiguousarray(p_dis, dtype=np.float64),
            p_curtail_kw=np.ascontiguousarray(p_curtail, dtype=np.float64),
            soc_kwh=np.ascontiguousarray(soc, dtype=np.float64),
            initial_soc_kwh=float(soc[0]),
            terminal_soc_kwh=float(soc[-1]),
            prior_mdi_high_water_kw=hw,
            updated_mdi_high_water_kw=float(max(hw, opt_peak)),
            baseline_energy_pkr=base_energy,
            baseline_diesel_pkr=base_diesel,
            baseline_mdi_penalty_pkr=base_mdi,
            baseline_total_pkr=base_total,
            optimized_energy_pkr=opt_energy,
            optimized_diesel_pkr=opt_diesel,
            optimized_mdi_penalty_pkr=opt_mdi,
            degradation_cost_pkr=degradation,
            optimized_total_pkr=opt_total,
            net_savings_pkr=base_total - opt_total,
            mdi_penalty_saved_pkr=base_mdi - opt_mdi,
            diesel_cost_saved_pkr=base_diesel - opt_diesel,
        )


if __name__ == "__main__":
    from src.data_engineering.feature_store import EMSDataRepository

    repo = EMSDataRepository()
    opt = MILPBatteryOptimizer()
    sl = repo.get_optimization_slice("2025-07-17", override_mdi_high_water_kw=500.0)
    res = opt.solve_24h_dispatch(sl)
    print(f"status={res.status} solve={res.solve_time_ms:.2f} ms savings={res.net_savings_pkr} PKR")
