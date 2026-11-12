"""
Month-to-date grid flow tracking (vectorised Polars, binary-searched slices; no row loops).

Feeds the CY 2026 tariff logic with what only metering can know:
  - cumulative imported kWh (slab / 200-unit Protected guardrails),
  - Off-Peak imported kWh vs exported kWh (remaining 1:1 netting headroom for grandfathered prosumers),
  - trailing share of PV generation that actually went to the grid (valuation of lost soiling kWh).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import polars as pl

from src.optimizer.lesco_2026_tariff_and_dispatch import LescoCY2026TariffEngine

_TZ = ZoneInfo("Asia/Karachi")


@dataclass(frozen=True, slots=True)
class MonthToDateFlowsDTO:
    month_start: str
    through_exclusive: str
    days_elapsed: int
    import_kwh: float
    export_kwh: float
    peak_import_kwh: float
    off_peak_import_kwh: float
    netting_headroom_kwh: float  # max(0, off-peak import - export): units still cancellable 1:1


def _slice_between(df: pl.DataFrame, start: datetime, end: datetime) -> pl.DataFrame:
    ts = df["timestamp"]
    lo = ts.search_sorted(start)
    hi = ts.search_sorted(end)
    return df.slice(lo, max(0, hi - lo))


def compute_month_to_date_flows(
    df: pl.DataFrame, date_str: str, engine: LescoCY2026TariffEngine
) -> MonthToDateFlowsDTO:
    """Sums grid flows from day 1 of the month up to (excluding) `date_str` (causal: no future leakage)."""
    day = datetime.fromisoformat(date_str[:10]).replace(tzinfo=_TZ)
    start = day.replace(day=1)
    window = engine.get_seasonal_window(day.month)
    sl = _slice_between(df, start, day)
    if sl.height == 0:
        return MonthToDateFlowsDTO(str(start), str(day), 0, 0.0, 0.0, 0.0, 0.0, 0.0)
    is_peak = (pl.col("hour") >= window.peak_start_hour) & (pl.col("hour") < window.peak_end_hour)
    agg = sl.select(
        pl.col("grid_import_kw").sum().alias("imp"),
        pl.col("grid_export_kw").sum().alias("exp"),
        pl.col("grid_import_kw").filter(is_peak).sum().alias("peak"),
    ).row(0)
    imp, exp, peak = float(agg[0]), float(agg[1]), float(agg[2])
    off = imp - peak
    return MonthToDateFlowsDTO(
        month_start=str(start),
        through_exclusive=str(day),
        days_elapsed=sl.height // 24,
        import_kwh=round(imp, 4),
        export_kwh=round(exp, 4),
        peak_import_kwh=round(peak, 4),
        off_peak_import_kwh=round(off, 4),
        netting_headroom_kwh=round(max(0.0, off - exp), 4),
    )


def trailing_export_share(df: pl.DataFrame, date_str: str, days: int = 30) -> float:
    """Fraction of PV generation exported over the `days` before `date_str` (0.0 if no PV recorded)."""
    day = datetime.fromisoformat(date_str[:10]).replace(tzinfo=_TZ)
    sl = _slice_between(df, day - timedelta(days=days), day)
    if sl.height == 0:
        return 0.0
    solar = float(sl["effective_solar_kw"].sum())
    exp = float(sl["grid_export_kw"].sum())
    return min(1.0, exp / solar) if solar > 0.0 else 0.0
