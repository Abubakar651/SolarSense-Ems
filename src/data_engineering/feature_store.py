"""
SolarSense EMS — High-Performance Data Access & Feature Store Layer
===================================================================
Production-grade immutable Columnar Repository, typed Domain DTOs,
dynamic LESCO B3 Tariff Strategy, and target-aware ML splitters.

Key Architectural Guarantees:
1. Zero Mutable DataFrames: Emits frozen, slotted dataclass DTOs with contiguous
   1D NumPy vectors (float64, shape=(24,)) for direct matrix ingest by HiGHS/CVXPY.
2. Dynamic Tariff Strategy: Decouples NEPRA/LESCO B3 seasonal peak windows and rates
   from static dataset columns to support interactive "what-if" counterfactuals.
3. Multi-Day State Continuity: Supports `override_initial_soc_kwh` and
   `override_mdi_high_water_kw` for sequential rolling simulations and backtests.
4. Target-Aware Purged ML Splitting: Dedicated feature matrix generators for
   "solar", "load", and "outage" tasks with mandatory 24-hour purge gaps.
5. Strict Timezone Normalization: All timestamps anchored to Asia/Karachi (UTC+05:00).
6. 100% Engine Consistency: Unified on Apache Arrow / Polars + NumPy.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import zoneinfo

import numpy as np
import numpy.typing as npt
import polars as pl

# Type aliases for 24-hour horizon vectors
FloatVec24 = npt.NDArray[np.float64]
IntVec24 = npt.NDArray[np.int8]

# Pakistan Standard Time (UTC+05:00, No Daylight Saving Time)
PKT_TZ = zoneinfo.ZoneInfo("Asia/Karachi")

DEFAULT_CSV_PATH = Path("data/processed/master_ems_timeseries.csv")
DEFAULT_PARQUET_PATH = Path("data/processed/master_ems_timeseries.parquet")

# Battery physical envelope used to normalise/clamp the initial state of charge (kWh)
BESS_CAPACITY_KWH = 600.0
BESS_MIN_SOC_KWH = 60.0  # 10% hard physical floor


# =====================================================================
# 1. Dynamic Tariff Strategy Pattern (NEPRA / LESCO B3 Industrial)
# =====================================================================

@dataclass(frozen=True, slots=True)
class TariffPolicy:
    """
    Immutable NEPRA / LESCO B3 Industrial Time-of-Use (ToU) Billing Configuration.
    Supports counterfactual simulations (e.g. rate hikes, diesel price inflation).
    """
    off_peak_rate_pkr: Decimal = Decimal("38.00")
    peak_rate_pkr: Decimal = Decimal("60.00")
    diesel_cost_pkr: Decimal = Decimal("95.00")
    mdi_penalty_per_kw_pkr: Decimal = Decimal("1200.00")
    sanctioned_load_kw: float = 500.0
    step_duration_hours: float = 1.0

    def get_peak_hours_for_month(self, month: int) -> tuple[int, ...]:
        """
        Official LESCO 4-hour seasonal peak window (hour-beginning in PKT):
          - Dec to Feb (Winter): 17:00 – 21:00 (hours 17, 18, 19, 20)
          - Jun to Aug (Summer): 19:00 – 23:00 (hours 19, 20, 21, 22)
          - Mar to May / Sep to Nov: 18:00 – 22:00 (hours 18, 19, 20, 21)
        """
        if month in (12, 1, 2):
            return (17, 18, 19, 20)
        elif month in (6, 7, 8):
            return (19, 20, 21, 22)
        else:
            return (18, 19, 20, 21)

    def is_peak_hour(self, dt: datetime) -> bool:
        """Evaluates if a given datetime falls in the official seasonal peak window."""
        return dt.hour in self.get_peak_hours_for_month(dt.month)

    def get_rate_pkr(self, dt: datetime) -> float:
        """Returns the base energy rate in PKR/kWh as a float for solver vectorization."""
        return float(self.peak_rate_pkr if self.is_peak_hour(dt) else self.off_peak_rate_pkr)

    def calculate_marginal_mdi_penalty(
        self, peak_kw: float, current_high_water_mark_kw: float
    ) -> Decimal:
        """
        Calculates marginal MDI penalty on demand exceeding the monthly ratchet.
        Penalty = 1,200 PKR * max(0, peak_kw - max(current_high_water_mark_kw, sanctioned_load_kw))
        """
        threshold = max(current_high_water_mark_kw, self.sanctioned_load_kw)
        exceedance = max(0.0, peak_kw - threshold)
        if exceedance <= 0.0:
            return Decimal("0.00")
        penalty = Decimal(str(round(exceedance, 4))) * self.mdi_penalty_per_kw_pkr
        return penalty.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


# =====================================================================
# 2. Immutable Domain DTOs
# =====================================================================

@dataclass(frozen=True, slots=True)
class OptimizationHorizonSlice:
    """
    Zero-copy, C-contiguous NumPy vectors ready for direct matrix assembly in HiGHS/CVXPY.
    """
    window_start: datetime
    horizon_hours: int
    timestamps_iso: tuple[str, ...]
    solar_kw: FloatVec24
    factory_load_kw: FloatVec24
    peak_surge_kw: FloatVec24
    outage_prob: FloatVec24
    actual_outage_mask: IntVec24
    grid_tariff_pkr: FloatVec24
    initial_soc_kwh: float
    monthly_mdi_high_water_kw: float
    is_counterfactual: bool = False

    def __post_init__(self) -> None:
        """Enforces true immutability on underlying NumPy buffer pointers."""
        for vec in (
            self.solar_kw,
            self.factory_load_kw,
            self.peak_surge_kw,
            self.outage_prob,
            self.actual_outage_mask,
            self.grid_tariff_pkr,
        ):
            vec.setflags(write=False)


@dataclass(frozen=True, slots=True)
class SimulationWindowDTO:
    """
    Lightweight JSON-ready container designed for direct transmission over FastAPI
    to the Next.js frontend (TanStack Query / Zustand 60 FPS playback).
    """
    date_str: str
    horizon_hours: int
    timestamps: tuple[str, ...]
    hours: tuple[int, ...]
    solar_generation_kw: tuple[float, ...]
    factory_load_kw: tuple[float, ...]
    net_power_kw: tuple[float, ...]
    tariff_rates_pkr: tuple[float, ...]
    tariff_windows: tuple[str, ...]
    outage_flags: tuple[int, ...]
    baseline_electricity_cost_pkr: float
    baseline_mdi_penalty_pkr: float
    total_baseline_cost_pkr: float
    ghi_wm2: tuple[float, ...]
    temp_c: tuple[float, ...]

    def to_dict(self) -> Dict[str, Any]:
        """Serializes DTO to a JSON-compatible Python dictionary."""
        return {
            "date": self.date_str,
            "horizon_hours": self.horizon_hours,
            "timestamps": list(self.timestamps),
            "hours": list(self.hours),
            "solar_generation_kw": list(self.solar_generation_kw),
            "factory_load_kw": list(self.factory_load_kw),
            "net_power_kw": list(self.net_power_kw),
            "tariff_rates_pkr": list(self.tariff_rates_pkr),
            "tariff_windows": list(self.tariff_windows),
            "outage_flags": list(self.outage_flags),
            "baseline_electricity_cost_pkr": self.baseline_electricity_cost_pkr,
            "baseline_mdi_penalty_pkr": self.baseline_mdi_penalty_pkr,
            "total_baseline_cost_pkr": self.total_baseline_cost_pkr,
            "ghi_wm2": list(self.ghi_wm2),
            "temp_c": list(self.temp_c),
        }


@dataclass(frozen=True, slots=True)
class MLTaskSplits:
    """
    Target-aware, strictly causal train/val/test matrices with zero lookahead leakage.
    """
    task: str
    feature_names: tuple[str, ...]
    train_features: pl.DataFrame
    train_target: np.ndarray
    val_features: pl.DataFrame
    val_target: np.ndarray
    test_features: pl.DataFrame
    test_target: np.ndarray
    purge_hours: int
    metadata: Dict[str, Any]


# =====================================================================
# 3. Canonical EMS Data Repository
# =====================================================================

class EMSDataRepository:
    """
    High-Performance, In-Memory Columnar Data Access Layer for SolarSense EMS.
    Maintains a single-source-of-truth resident Arrow table with nanosecond-resolution
    slicing and strict Asia/Karachi timezone semantics.
    """

    def __init__(
        self,
        csv_path: Union[str, Path] = DEFAULT_CSV_PATH,
        parquet_path: Union[str, Path] = DEFAULT_PARQUET_PATH,
        policy: Optional[TariffPolicy] = None,
        force_reload_csv: bool = False,
    ) -> None:
        self.csv_path = Path(csv_path)
        self.parquet_path = Path(parquet_path)
        self.policy = policy or TariffPolicy()
        # Lazily populated once by _ensure_forecast_cache() (models + resident feature matrices)
        self._forecast_cache: Optional[Dict[str, Any]] = None

        self._df: pl.DataFrame = self._load_or_compile_canonical(force_reload_csv)
        self._validate_invariants()
        self._build_contiguous_cache()

    def _build_contiguous_cache(self) -> None:
        """
        Pre-computes contiguous Arrow and NumPy memory buffers and timestamp indices
        for sub-millisecond O(log N) / O(1) repository queries adhering to Section 2 latency budgets.
        """
        # Timestamp index mapping for O(1) lookup
        self._ts_to_idx: Dict[datetime, int] = {
            ts: i for i, ts in enumerate(self._df["timestamp"])
        }
        self._timestamps_iso: tuple[str, ...] = tuple(
            self._df["timestamp"].dt.to_string("%Y-%m-%dT%H:%M:%S%z").to_list()
        )
        self._solar_arr: np.ndarray = self._df["effective_solar_kw"].to_numpy().astype(np.float64)
        self._load_arr: np.ndarray = self._df["factory_load_kw"].to_numpy().astype(np.float64)
        self._grid_import_arr: np.ndarray = self._df["grid_import_kw"].to_numpy().astype(np.float64)
        self._diesel_import_arr: np.ndarray = self._df["diesel_import_kw"].to_numpy().astype(np.float64)
        self._outage_arr: np.ndarray = self._df["outage_flag"].to_numpy().astype(np.int8)
        self._battery_soc_arr: np.ndarray = self._df["battery_soc_mean"].to_numpy().astype(np.float64)
        self._ghi_arr: np.ndarray = self._df["ghi_wm2"].to_numpy().astype(np.float64)
        self._temp_arr: np.ndarray = self._df["temp_c"].to_numpy().astype(np.float64)
        self._hours_arr: np.ndarray = self._df["timestamp"].dt.hour().to_numpy()
        self._months_arr: np.ndarray = self._df["timestamp"].dt.month().to_numpy()

        # Net grid peak draw when connected (zeroed during blackouts for outage MDI immunity)
        self._grid_connected_kw: np.ndarray = np.where(
            self._outage_arr == 0,
            self._grid_import_arr,
            0.0,
        ).astype(np.float64)

    # -----------------------------------------------------------------
    # Ingestion & Canonical Parquet Compilation
    # -----------------------------------------------------------------

    def _load_or_compile_canonical(self, force_reload: bool) -> pl.DataFrame:
        """
        Loads cached Parquet if present; otherwise ingests CSV, sanitizes dtypes,
        normalizes timezones, and writes an optimized ZSTD Parquet file for instant cold starts.
        """
        if self.parquet_path.exists() and not force_reload:
            df = pl.read_parquet(self.parquet_path)
        else:
            if not self.csv_path.exists():
                raise FileNotFoundError(
                    f"Master EMS dataset not found at '{self.csv_path}'. "
                    f"Run 'src/data_engineering/build_master_feature_store.py' first."
                )
            df = self._ingest_and_clean_csv(self.csv_path)
            self.parquet_path.parent.mkdir(parents=True, exist_ok=True)
            df.write_parquet(self.parquet_path, compression="zstd")

        # Guarantee contiguous memory layout for zero-copy numpy conversions
        return df.sort("timestamp").rechunk()

    def _ingest_and_clean_csv(self, path: Path) -> pl.DataFrame:
        """Reads raw CSV, fixes casting quirks, and enforces Asia/Karachi timezone."""
        raw = pl.read_csv(path)

        # Parse timestamp and localize to Asia/Karachi
        df = raw.with_columns(
            pl.col("timestamp")
            .str.to_datetime("%Y-%m-%d %H:%M:%S")
            .dt.replace_time_zone("Asia/Karachi")
            .alias("timestamp")
        )

        # Ensure correct numeric types across all core telemetry columns
        numeric_casts = [
            pl.col("ghi_wm2").cast(pl.Float64).fill_null(0.0),
            pl.col("dni_wm2").cast(pl.Float64).fill_null(0.0),
            pl.col("dhi_wm2").cast(pl.Float64).fill_null(0.0),
            pl.col("temp_c").cast(pl.Float64).fill_null(strategy="backward").fill_null(25.0),
            pl.col("rain_mm").cast(pl.Float64).fill_null(0.0),
            pl.col("wind_ms").cast(pl.Float64).fill_null(0.0),
            pl.col("humidity_pct").cast(pl.Float64).fill_null(50.0),
            pl.col("factory_load_kw").cast(pl.Float64).fill_null(200.0),
            pl.col("grid_import_kw").cast(pl.Float64).fill_null(0.0),
            pl.col("diesel_import_kw").cast(pl.Float64).fill_null(0.0),
            pl.col("outage_flag").cast(pl.Int8).fill_null(0),
            pl.col("solar_energy_kwh").cast(pl.Float64, strict=False),
            pl.col("solar_peak_kw").cast(pl.Float64, strict=False),
            pl.col("battery_soc_mean").cast(pl.Float64, strict=False),
            pl.col("generation_kwh_daily").cast(pl.Float64, strict=False).fill_null(0.0),
        ]
        df = df.with_columns(numeric_casts)

        # Add physical daylight constraint and estimated solar profile if missing
        # Night hours (GHI = 0) have strictly 0.0 solar kWh
        df = df.with_columns(
            pl.when(pl.col("ghi_wm2") <= 0.0)
            .then(pl.lit(0.0))
            .otherwise(
                pl.col("solar_energy_kwh").fill_null(
                    # If high-res 5-min telemetry missing, distribute daily generation by GHI proportion
                    pl.col("generation_kwh_daily") * (pl.col("ghi_wm2") / pl.max("ghi_wm2").over("date"))
                ).fill_null(0.0)
            )
            .alias("effective_solar_kw")
        )

        return df

    def _validate_invariants(self) -> None:
        """Physical integrity check to detect timestamp shifts or corrupted data."""
        if self._df.height != 11136:
            raise ValueError(
                f"Data integrity violation: Expected 11,136 hourly rows (464 days), got {self._df.height}"
            )

        # Verify zero solar generation at night
        night_solar = (
            self._df.filter((pl.col("ghi_wm2") == 0.0) & (pl.col("effective_solar_kw") > 0.0))
            .height
        )
        if night_solar > 0:
            raise ValueError(f"Physics invariant broken: {night_solar} hours have solar > 0 at GHI == 0")

    # -----------------------------------------------------------------
    # Core Accessor: Optimization Horizon Slice (Solver Ready)
    # -----------------------------------------------------------------

    def get_optimization_slice(
        self,
        origin_ts: Union[str, datetime, date],
        policy: Optional[TariffPolicy] = None,
        horizon_hours: int = 24,
        use_forecasts: bool = False,
        override_initial_soc_kwh: Optional[float] = None,
        override_mdi_high_water_kw: Optional[float] = None,
    ) -> OptimizationHorizonSlice:
        """
        Extracts a strictly typed, contiguous 24-hour horizon slice for the MILP solver.
        
        Args:
            origin_ts: Start timestamp (e.g. "2026-09-23" or "2026-09-23 00:00:00").
            policy: Dynamic tariff rules (defaults to repository policy).
            horizon_hours: Horizon length (default 24).
            use_forecasts: If True, returns forecasted vectors; if False, returns ground truth.
            override_initial_soc_kwh: Optional state override for sequential multi-day runs.
            override_mdi_high_water_kw: Optional monthly ratchet override for multi-day runs.
        """
        active_policy = policy or self.policy
        ts_start = self._normalize_datetime(origin_ts)

        # 1. Fast O(1) indexed lookup on pre-cached resident buffers
        idx = self._ts_to_idx.get(ts_start)
        if idx is None:
            raise ValueError(
                f"Timestamp '{ts_start}' not found in master dataset "
                f"(range: {self._df['timestamp'].min()} to {self._df['timestamp'].max()})"
            )
        if idx + horizon_hours > self._df.height:
            raise ValueError(
                f"Requested {horizon_hours} hours from {ts_start}, but dataset ends at {self._df['timestamp'].max()}"
            )

        # 2. Monthly MDI High-Water Mark (Billing Ratchet)
        if override_mdi_high_water_kw is not None:
            effective_mdi_high_water = float(override_mdi_high_water_kw)
        else:
            # Slices strictly from the start of the current month up to ts_start, excluding blackouts
            month_start = ts_start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            idx_month_start = self._ts_to_idx.get(month_start, 0)
            if idx > idx_month_start:
                # Net grid peak draw when grid connected (outage_flag == 0)
                historical_peak = float(self._grid_connected_kw[idx_month_start:idx].max())
            else:
                historical_peak = 0.0
            effective_mdi_high_water = max(historical_peak, active_policy.sanctioned_load_kw)

        # 3. Initial Battery SoC (kWh): normalise units, then clamp to the physical envelope
        if override_initial_soc_kwh is not None:
            effective_initial_soc = float(override_initial_soc_kwh)
        else:
            soc_val = float(self._battery_soc_arr[idx])
            if np.isnan(soc_val):
                soc_frac = 0.90  # telemetry gap default
            elif soc_val <= 1.0:
                soc_frac = soc_val  # already a [0, 1] fraction
            else:
                soc_frac = soc_val / 100.0  # percentage (dataset stores 50-100)
            effective_initial_soc = soc_frac * BESS_CAPACITY_KWH
        effective_initial_soc = float(
            min(max(effective_initial_soc, BESS_MIN_SOC_KWH), BESS_CAPACITY_KWH)
        )

        # 4. Dynamic Tariff Vector via Policy Strategy
        h_slice = self._hours_arr[idx : idx + horizon_hours]
        m_slice = self._months_arr[idx : idx + horizon_hours]
        peak_pkr = float(active_policy.peak_rate_pkr)
        off_peak_pkr = float(active_policy.off_peak_rate_pkr)
        tariff_vec = np.array(
            [
                peak_pkr if int(h) in active_policy.get_peak_hours_for_month(int(m)) else off_peak_pkr
                for h, m in zip(h_slice, m_slice)
            ],
            dtype=np.float64,
        )

        # 5. Zero-copy / Contiguous NumPy Vectors with read-only protection
        timestamps_iso = self._timestamps_iso[idx : idx + horizon_hours]
        outage_mask = self._outage_arr[idx : idx + horizon_hours].copy()

        if use_forecasts:
            # O(1) slices of resident feature matrices + in-memory inference (no disk I/O)
            cache = self._ensure_forecast_cache()
            window = slice(idx, idx + horizon_hours)
            solar_vec = cache["solar_model"].predict_24h(cache["X_solar"][window])
            load_vec, load_p90 = cache["load_model"].predict_24h(cache["X_load"][window])
            outage_prob = cache["outage_model"].predict_proba_24h(cache["X_outage"][window])
            # p90 already encodes the upper-bound demand envelope: no extra inflation factor
            surge_vec = np.where(outage_mask == 1, 0.0, load_p90).astype(np.float64)
        else:
            solar_vec = self._solar_arr[idx : idx + horizon_hours].copy()
            load_vec = self._load_arr[idx : idx + horizon_hours].copy()
            outage_prob = outage_mask.astype(np.float64)
            # Ground truth: surge envelope == load (surge delta 0), zeroed during blackouts
            surge_vec = np.where(outage_mask == 1, 0.0, load_vec).astype(np.float64)

        return OptimizationHorizonSlice(
            window_start=ts_start,
            horizon_hours=horizon_hours,
            timestamps_iso=timestamps_iso,
            solar_kw=solar_vec,
            factory_load_kw=load_vec,
            peak_surge_kw=surge_vec,
            outage_prob=outage_prob,
            actual_outage_mask=outage_mask,
            grid_tariff_pkr=tariff_vec,
            initial_soc_kwh=effective_initial_soc,
            monthly_mdi_high_water_kw=effective_mdi_high_water,
            is_counterfactual=(override_mdi_high_water_kw is not None or override_initial_soc_kwh is not None),
        )

    # -----------------------------------------------------------------
    # Core Accessor: Simulation Window DTO (FastAPI / Next.js Ready)
    # -----------------------------------------------------------------

    def get_simulation_window(
        self,
        date_str: str,
        policy: Optional[TariffPolicy] = None,
    ) -> SimulationWindowDTO:
        """
        Returns a complete 24-hour JSON-ready payload formatted for Next.js 60 FPS playback.
        Calculates baseline electricity cost and MDI penalties for performance comparison.
        """
        active_policy = policy or self.policy
        ts_start = self._normalize_datetime(f"{date_str} 00:00:00")
        
        idx = self._ts_to_idx.get(ts_start)
        if idx is None:
            raise ValueError(f"Date '{date_str}' not found in dataset")
        if idx + 24 > self._df.height:
            raise ValueError(f"Insufficient hours for date '{date_str}'")

        h_slice = self._hours_arr[idx : idx + 24]
        m_slice = self._months_arr[idx : idx + 24]
        sol_slice = self._solar_arr[idx : idx + 24]
        load_slice = self._load_arr[idx : idx + 24]
        outage_slice = self._outage_arr[idx : idx + 24]
        grid_slice = self._grid_import_arr[idx : idx + 24]
        diesel_slice = self._diesel_import_arr[idx : idx + 24]
        ghi_slice = self._ghi_arr[idx : idx + 24]
        temp_slice = self._temp_arr[idx : idx + 24]

        solar_gen = tuple(float(x) for x in sol_slice)
        factory_load = tuple(float(x) for x in load_slice)
        net_power = tuple(round(s - l, 3) for s, l in zip(solar_gen, factory_load))
        outages = tuple(int(x) for x in outage_slice)

        peak_pkr = float(active_policy.peak_rate_pkr)
        off_peak_pkr = float(active_policy.off_peak_rate_pkr)
        diesel_rate = float(active_policy.diesel_cost_pkr)

        tariff_rates = []
        tariff_windows = []
        hourly_energy_costs = []

        for h, m, out, g_imp, d_imp, fl, sol in zip(
            h_slice, m_slice, outages, grid_slice, diesel_slice, factory_load, solar_gen
        ):
            is_peak = int(h) in active_policy.get_peak_hours_for_month(int(m))
            rate = peak_pkr if is_peak else off_peak_pkr
            tariff_rates.append(rate)
            tariff_windows.append("peak" if is_peak else "off_peak")

            if out == 1:
                # Blackout: Islanded diesel generator backup at 95 PKR/kWh
                deficit = float(d_imp) if d_imp > 0 else max(0.0, fl - sol)
                hourly_energy_costs.append(deficit * diesel_rate)
            else:
                # Grid-connected: LESCO Time-of-Use rates on net grid import
                deficit = float(g_imp) if g_imp > 0 else max(0.0, fl - sol)
                hourly_energy_costs.append(deficit * rate)

        base_energy_cost = sum(hourly_energy_costs)

        # Monthly MDI high-water mark up to origin_ts (resets on 1st of month)
        month_start = ts_start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        idx_month_start = self._ts_to_idx.get(month_start, 0)
        if idx > idx_month_start:
            prior_high_water = float(self._grid_connected_kw[idx_month_start:idx].max())
        else:
            prior_high_water = 0.0
        current_monthly_high_water = max(prior_high_water, active_policy.sanctioned_load_kw)

        # Baseline MDI penalty strictly on net grid peak draw when connected (outage_flag == 0)
        connected_grid_draws = [float(g_imp) for g_imp, out in zip(grid_slice, outages) if out == 0]
        max_grid_peak = max(connected_grid_draws) if connected_grid_draws else 0.0
        marginal_mdi = active_policy.calculate_marginal_mdi_penalty(
            max_grid_peak, current_monthly_high_water
        )
        total_baseline = round(base_energy_cost + float(marginal_mdi), 2)

        return SimulationWindowDTO(
            date_str=date_str,
            horizon_hours=24,
            timestamps=self._timestamps_iso[idx : idx + 24],
            hours=tuple(int(x) for x in h_slice),
            solar_generation_kw=solar_gen,
            factory_load_kw=factory_load,
            net_power_kw=net_power,
            tariff_rates_pkr=tuple(tariff_rates),
            tariff_windows=tuple(tariff_windows),
            outage_flags=outages,
            baseline_electricity_cost_pkr=round(base_energy_cost, 2),
            baseline_mdi_penalty_pkr=float(marginal_mdi),
            total_baseline_cost_pkr=total_baseline,
            ghi_wm2=tuple(float(x) for x in ghi_slice),
            temp_c=tuple(float(x) for x in temp_slice),
        )

    def get_day_slice(self, date_str: str) -> SimulationWindowDTO:
        """Convenience accessor alias for get_simulation_window."""
        return self.get_simulation_window(date_str)

    def get_tariff_window(self, date_str: str) -> Tuple[float, ...]:
        """Convenience accessor alias returning 24-hour hourly tariff rates in PKR."""
        return self.get_simulation_window(date_str).tariff_rates_pkr

    # -----------------------------------------------------------------
    # Core Accessor: Target-Aware ML Splitting with 24h Purge Gap
    # -----------------------------------------------------------------

    def get_raw_splits(
        self,
        train_end: Union[str, datetime] = "2026-06-30 23:00:00",
        val_end: Union[str, datetime] = "2026-08-31 23:00:00",
        purge_hours: int = 24,
    ) -> Tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
        """
        Splits dataset chronologically into Train, Validation, and Test partitions
        with an embargo/purge gap to eliminate rolling-lag target overlap.
        """
        t_train_end = self._normalize_datetime(train_end)
        t_val_start = t_train_end + pl.duration(hours=purge_hours)
        t_val_end = self._normalize_datetime(val_end)
        t_test_start = t_val_end + pl.duration(hours=purge_hours)

        train_df = self._df.filter(pl.col("timestamp") <= t_train_end)
        val_df = self._df.filter(
            (pl.col("timestamp") >= t_val_start) & (pl.col("timestamp") <= t_val_end)
        )
        test_df = self._df.filter(pl.col("timestamp") >= t_test_start)

        return train_df, val_df, test_df

    def get_ml_feature_matrix(
        self,
        task: str,
        train_end: Union[str, datetime] = "2026-06-30 23:00:00",
        val_end: Union[str, datetime] = "2026-08-31 23:00:00",
        purge_hours: int = 24,
    ) -> MLTaskSplits:
        """
        Generates clean, target-aware (X, y) matrices for the specific ML model,
        strictly preventing cross-model target leakage.

        Args:
            task: One of "solar" (LightGBM PV), "load" (Demand forecast), or "outage" (Classifier).
            train_end: Chronological training cutoff.
            val_end: Chronological validation cutoff.
            purge_hours: Buffer gap to isolate 24-hour forecast horizon lags.
        """
        # Shared builder guarantees train-time and inference-time features are identical
        augmented, feature_cols, target_col = self._build_task_frame(task)

        t_train_end = self._normalize_datetime(train_end)
        t_val_start = t_train_end + pl.duration(hours=purge_hours)
        t_val_end = self._normalize_datetime(val_end)
        t_test_start = t_val_end + pl.duration(hours=purge_hours)

        train_part = augmented.filter(pl.col("timestamp") <= t_train_end)
        val_part = augmented.filter(
            (pl.col("timestamp") >= t_val_start) & (pl.col("timestamp") <= t_val_end)
        )
        test_part = augmented.filter(pl.col("timestamp") >= t_test_start)

        return MLTaskSplits(
            task=task,
            feature_names=tuple(feature_cols),
            train_features=train_part.select(feature_cols),
            train_target=train_part[target_col].to_numpy(),
            val_features=val_part.select(feature_cols),
            val_target=val_part[target_col].to_numpy(),
            test_features=test_part.select(feature_cols),
            test_target=test_part[target_col].to_numpy(),
            purge_hours=purge_hours,
            metadata={
                "train_rows": train_part.height,
                "val_rows": val_part.height,
                "test_rows": test_part.height,
                "target_col": target_col,
            },
        )

    # -----------------------------------------------------------------
    # MDI Penalty Auditing & Helper Queries
    # -----------------------------------------------------------------

    def get_mdi_spikes(self, threshold_kw: float = 500.0) -> pl.DataFrame:
        """
        Returns all timestamps where net grid draw breached the sanctioned ceiling (500 kW)
        during grid-connected operation (outage_flag == 0), along with marginal penalties.
        During blackouts (outage_flag == 1), LESCO smart meters are de-energized, so no MDI fines apply.
        """
        spikes = (
            self._df.filter(
                (pl.col("outage_flag") == 0) & (pl.col("grid_import_kw") > threshold_kw)
            )
            .select([
                "timestamp", "date", "hour", "factory_load_kw", "effective_solar_kw",
                "grid_import_kw", "outage_flag", "tariff_window", "tariff_rate_pkr",
            ])
            .with_columns([
                (pl.col("grid_import_kw") - threshold_kw).alias("exceedance_kw"),
                ((pl.col("grid_import_kw") - threshold_kw) * float(self.policy.mdi_penalty_per_kw_pkr))
                .round(2)
                .alias("instantaneous_penalty_pkr"),
            ])
            .sort("grid_import_kw", descending=True)
        )
        return spikes

    def get_metadata(self) -> Dict[str, Any]:
        """Provides an executive overview of the dataset for logging and sanity testing."""
        return {
            "total_records": self._df.height,
            "total_days": self._df["date"].n_unique(),
            "start_timestamp": str(self._df["timestamp"].min()),
            "end_timestamp": str(self._df["timestamp"].max()),
            "sanctioned_load_kw": self.policy.sanctioned_load_kw,
            "total_historical_mdi_violations": self.get_mdi_spikes().height,
            "total_outage_hours": int(self._df["outage_flag"].sum()),
        }

    # -----------------------------------------------------------------
    # Shared ML Feature Frame & Lazy Forecaster Cache
    # -----------------------------------------------------------------

    def _build_task_frame(self, task: str) -> Tuple[pl.DataFrame, List[str], str]:
        """
        Builds the full-dataset (11,136 rows) augmented feature frame for an ML task.
        Shared by get_ml_feature_matrix() (splits) and the forecast cache (resident arrays)
        so training-time and inference-time features are identical by construction.
        """
        valid_tasks = {"solar", "load", "outage"}
        if task not in valid_tasks:
            raise ValueError(f"Invalid ML task '{task}'. Expected one of {valid_tasks}")

        # Augment dataframe with tree-friendly Fourier and calendar features
        augmented = self._df.with_columns([
            pl.col("timestamp").dt.hour().alias("hour"),
            pl.col("timestamp").dt.weekday().alias("weekday"),
            pl.col("timestamp").dt.month().alias("month"),
            pl.col("timestamp").dt.day().alias("day_of_month"),
            # Fourier cyclical pairs for hours and months
            (2.0 * np.pi * pl.col("timestamp").dt.hour() / 24.0).sin().alias("hour_sin"),
            (2.0 * np.pi * pl.col("timestamp").dt.hour() / 24.0).cos().alias("hour_cos"),
            (2.0 * np.pi * pl.col("timestamp").dt.month() / 12.0).sin().alias("month_sin"),
            (2.0 * np.pi * pl.col("timestamp").dt.month() / 12.0).cos().alias("month_cos"),
            # Shift phases
            pl.when(pl.col("timestamp").dt.hour().is_between(8, 16))
            .then(pl.lit(1))
            .when(pl.col("timestamp").dt.hour().is_between(16, 23))
            .then(pl.lit(2))
            .otherwise(pl.lit(0))
            .alias("factory_shift_id"),
        ])

        # Task-specific feature and target selection
        if task == "solar":
            target_col = "effective_solar_kw"
            base_features = [
                "ghi_wm2", "dni_wm2", "dhi_wm2", "temp_c", "humidity_pct",
                "wind_ms", "rain_mm", "hour", "month", "weekday",
                "hour_sin", "hour_cos", "month_sin", "month_cos",
            ]
        elif task == "load":
            target_col = "factory_load_kw"
            base_features = [
                "hour", "weekday", "month", "hour_sin", "hour_cos",
                "temp_c", "factory_shift_id", "humidity_pct",
            ]
        else:  # "outage"
            target_col = "outage_flag"
            base_features = [
                "hour", "weekday", "month", "hour_sin", "hour_cos",
                "temp_c", "rain_mm", "wind_ms", "humidity_pct",
            ]

        # Causal historical lag features for the target variable (strictly >= 24h lag for 24h lookahead)
        lag_24 = f"{target_col}_lag_24h"
        lag_48 = f"{target_col}_lag_48h"
        lag_168 = f"{target_col}_lag_168h"
        roll_7d = f"{target_col}_rolling_mean_7d_lag24"

        augmented = augmented.with_columns([
            pl.col(target_col).shift(24).fill_null(strategy="backward").fill_null(0.0).alias(lag_24),
            pl.col(target_col).shift(48).fill_null(strategy="backward").fill_null(0.0).alias(lag_48),
            pl.col(target_col).shift(168).fill_null(strategy="backward").fill_null(0.0).alias(lag_168),
            pl.col(target_col).shift(24).rolling_mean(window_size=168, min_samples=1).fill_null(strategy="backward").fill_null(0.0).alias(roll_7d),
            pl.col(target_col).shift(24).fill_null(strategy="backward").fill_null(0.0).alias("lag_24h"),
            pl.col(target_col).shift(48).fill_null(strategy="backward").fill_null(0.0).alias("lag_48h"),
            pl.col(target_col).shift(168).fill_null(strategy="backward").fill_null(0.0).alias("lag_168h"),
            pl.col(target_col).shift(24).rolling_mean(window_size=168, min_samples=1).fill_null(strategy="backward").fill_null(0.0).alias("rolling_mean_7d_lag24"),
        ])

        feature_cols = base_features + [
            lag_24, lag_48, lag_168, roll_7d,
            "lag_24h", "lag_48h", "lag_168h", "rolling_mean_7d_lag24",
        ]
        return augmented, feature_cols, target_col

    def _ensure_forecast_cache(self) -> Dict[str, Any]:
        """
        Lazily loads the 3 trained forecasters from disk and materialises the full-dataset
        feature matrices as resident, read-only, C-contiguous float64 NumPy arrays - exactly once.
        Subsequent use_forecasts=True slices are O(1) array slices + in-memory inference
        (no joblib I/O, no rolling-feature recomputation).
        """
        if self._forecast_cache is not None:
            return self._forecast_cache

        # Local imports: forecaster modules import this module at top level (avoid circular import)
        from src.forecast.train_solar_pv import SolarPVForecaster
        from src.forecast.train_factory_load import FactoryLoadForecaster
        from src.grid_outage.predict_outage import OutageRiskPredictor

        solar_model = SolarPVForecaster.load()
        load_model = FactoryLoadForecaster.load()
        outage_model = OutageRiskPredictor.load()

        def _resident_matrix(task: str, feature_names: List[str]) -> np.ndarray:
            frame, _, _ = self._build_task_frame(task)
            mat = np.ascontiguousarray(frame.select(feature_names).to_numpy(), dtype=np.float64)
            mat.setflags(write=False)
            return mat

        self._forecast_cache = {
            "solar_model": solar_model,
            "load_model": load_model,
            "outage_model": outage_model,
            "X_solar": _resident_matrix("solar", list(solar_model.feature_names)),
            "X_load": _resident_matrix("load", list(load_model.feature_names)),
            "X_outage": _resident_matrix("outage", list(outage_model.feature_names)),
        }
        return self._forecast_cache

    def warm_forecasters(self) -> None:
        """Eagerly builds the forecast cache (call once from the FastAPI lifespan startup hook)."""
        self._ensure_forecast_cache()

    # -----------------------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _normalize_datetime(val: Union[str, datetime, date]) -> datetime:
        """Coerces any valid date/string/datetime into a timezone-aware Asia/Karachi datetime."""
        if isinstance(val, str):
            # Parse ISO or standard date formats
            val_clean = val.replace("T", " ")
            if len(val_clean) == 10:  # YYYY-MM-DD
                dt = datetime.strptime(val_clean, "%Y-%m-%d")
            else:
                dt = datetime.fromisoformat(val_clean)
        elif isinstance(val, date) and not isinstance(val, datetime):
            dt = datetime(val.year, val.month, val.day)
        else:
            dt = val

        if dt.tzinfo is None:
            return dt.replace(tzinfo=PKT_TZ)
        return dt.astimezone(PKT_TZ)
