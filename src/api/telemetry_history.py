"""
A site's own history from its logged inverter samples: daily and monthly energy, and grid outages.

Pure functions over samples; the database read and the clock stay with the caller. Energy follows the
recorded dataset's convention: an hour's mean power in kW is that hour's energy in kWh.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timedelta

import numpy as np
import polars as pl

from src.api.insights import MIN_OUTAGE_MINUTES, DailyEnergyOut, MonthlyMeterOut, OutageEventOut
from src.data_engineering.feature_store import PKT_TZ
from src.data_engineering.month_to_date import MonthToDateFlowsDTO, compute_month_to_date_flows
from src.forecast.live_forecast import MIN_SAMPLES_PER_HOUR, TelemetrySample
from src.optimizer.lesco_2026_tariff_and_dispatch import LescoCY2026TariffEngine

# A day counts once 22 of its 24 hours are logged; the missing hours are filled pro rata.
MIN_HOURS_PER_DAY = 22
# Polls normally arrive every 5 minutes. A longer silence means logging stopped, so an outage run ends
# at its last sample instead of being stretched over time nobody observed.
MAX_POLL_GAP = timedelta(minutes=15)


def _frame(samples: Sequence[TelemetrySample]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "at": [s.recorded_at.astimezone(PKT_TZ).replace(tzinfo=None) for s in samples],
            "pv_kw": [s.pv_power_w / 1000.0 for s in samples],
            "load_kw": [s.load_power_w / 1000.0 for s in samples],
            "import_kw": [max(0.0, -s.grid_power_w) / 1000.0 for s in samples],
            "export_kw": [max(0.0, s.grid_power_w) / 1000.0 for s in samples],
        },
        schema={"at": pl.Datetime("us"), "pv_kw": pl.Float64, "load_kw": pl.Float64,
                "import_kw": pl.Float64, "export_kw": pl.Float64},
    )


def hourly_energy(samples: Sequence[TelemetrySample]) -> pl.DataFrame:
    """
    The logged hours (at least MIN_SAMPLES_PER_HOUR polls), oldest first: `hour` (local start, naive), `date`,
    and the hour's mean pv_kw, load_kw, import_kw and export_kw (= its kWh).
    """
    return (
        _frame(samples)
        .with_columns(pl.col("at").dt.truncate("1h").alias("hour"))
        .group_by("hour")
        .agg(pl.len().alias("n"), pl.col("pv_kw", "load_kw", "import_kw", "export_kw").mean())
        .filter(pl.col("n") >= MIN_SAMPLES_PER_HOUR)
        .with_columns(pl.col("hour").dt.date().alias("date"))
        .sort("hour")
    )


def _battery_hours(samples: Sequence[TelemetrySample]) -> pl.DataFrame:
    """The same logged hours as hourly_energy(): `hour`, mean charge_kw and discharge_kw (battery power + is charging)."""
    return (
        pl.DataFrame(
            {
                "at": [s.recorded_at.astimezone(PKT_TZ).replace(tzinfo=None) for s in samples],
                "charge_kw": [max(0.0, s.battery_power_w) / 1000.0 for s in samples],
                "discharge_kw": [max(0.0, -s.battery_power_w) / 1000.0 for s in samples],
            },
            schema={"at": pl.Datetime("us"), "charge_kw": pl.Float64, "discharge_kw": pl.Float64},
        )
        .with_columns(pl.col("at").dt.truncate("1h").alias("hour"))
        .group_by("hour")
        .agg(pl.len().alias("n"), pl.col("charge_kw", "discharge_kw").mean())
        .filter(pl.col("n") >= MIN_SAMPLES_PER_HOUR)
        .select("hour", "charge_kw", "discharge_kw")
    )


def month_to_date_flows(
    samples: Sequence[TelemetrySample], today: date, engine: LescoCY2026TariffEngine
) -> MonthToDateFlowsDTO | None:
    """
    This month's logged grid flows before `today`, split at the tariff's seasonal peak window, or None when
    no hour of the month is logged. Hours the log missed are not in it, so the figures are a lower bound.
    """
    hourly = hourly_energy(samples).filter(
        (pl.col("date") >= today.replace(day=1)) & (pl.col("date") < today)
    ).select(
        pl.col("hour").dt.replace_time_zone("Asia/Karachi").alias("timestamp"),
        pl.col("hour").dt.hour().alias("hour"),
        pl.col("import_kw").alias("grid_import_kw"),
        pl.col("export_kw").alias("grid_export_kw"),
    )
    if hourly.is_empty():
        return None
    return compute_month_to_date_flows(hourly, today.isoformat(), engine)


def daily_energy(samples: Sequence[TelemetrySample], before: date) -> list[DailyEnergyOut]:
    """Complete local days before `before` (normally today), oldest first."""
    if not samples:
        return []
    hourly = (
        hourly_energy(samples)
        .filter(pl.col("date") < before)
        .join(_battery_hours(samples), on="hour", how="left")
    )
    days = (
        hourly.group_by("date")
        .agg(
            pl.len().alias("hours"),
            pl.col("pv_kw", "load_kw", "import_kw", "export_kw", "charge_kw", "discharge_kw").sum(),
        )
        .filter(pl.col("hours") >= MIN_HOURS_PER_DAY)
        .with_columns((24.0 / pl.col("hours")).alias("scale"))
        .sort("date")
    )
    return [
        DailyEnergyOut(
            date=row["date"].isoformat(),
            solar_kwh=round(row["pv_kw"] * row["scale"], 2),
            load_kwh=round(row["load_kw"] * row["scale"], 2),
            import_kwh=round(row["import_kw"] * row["scale"], 2),
            export_kwh=round(row["export_kw"] * row["scale"], 2),
            battery_charged_kwh=round(row["charge_kw"] * row["scale"], 2),
            battery_discharged_kwh=round(row["discharge_kw"] * row["scale"], 2),
        )
        for row in days.iter_rows(named=True)
    ]


def monthly_energy(daily: Sequence[DailyEnergyOut]) -> list[MonthlyMeterOut]:
    """Calendar-month totals of the complete days (the latest month is partial)."""
    months: dict[str, list[float]] = {}
    for d in daily:
        totals = months.setdefault(d.date[:7], [0.0, 0.0, 0.0, 0.0])
        totals[0] += d.solar_kwh
        totals[1] += d.load_kwh
        totals[2] += d.import_kwh
        totals[3] += d.export_kwh
    return [
        MonthlyMeterOut(month=m, pv_kwh=round(t[0], 2), load_kwh=round(t[1], 2),
                        purchased_kwh=round(t[2], 2), sold_kwh=round(t[3], 2))
        for m, t in sorted(months.items())
    ]


def outage_events(samples: Sequence[TelemetrySample]) -> list[OutageEventOut]:
    """
    Runs of blackout samples lasting MIN_OUTAGE_MINUTES or more, oldest first. A run ends at the first
    sample with the grid back, or at its last sample when logging went quiet for longer than MAX_POLL_GAP.
    """
    if not samples:
        return []
    ordered = sorted(samples, key=lambda s: s.recorded_at)
    at = np.array([s.recorded_at.timestamp() for s in ordered], dtype=np.float64)
    down = np.array([s.is_blackout for s in ordered], dtype=bool)
    gap_after = np.append(np.diff(at) > MAX_POLL_GAP.total_seconds(), True)

    events: list[OutageEventOut] = []
    i = 0
    n = len(ordered)
    while i < n:
        if not down[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and down[j + 1] and not gap_after[j]:
            j += 1
        grid_back = j + 1 < n and not gap_after[j]
        end_ts = at[j + 1] if grid_back else at[j]
        minutes = (end_ts - at[i]) / 60.0
        if minutes >= MIN_OUTAGE_MINUTES:
            run = ordered[i : j + 1]
            mean_load_kw = float(np.mean([s.load_power_w for s in run])) / 1000.0
            start = ordered[i].recorded_at.astimezone(PKT_TZ)
            end = datetime.fromtimestamp(end_ts, PKT_TZ)
            events.append(
                OutageEventOut(
                    date=start.date().isoformat(),
                    start=start.strftime("%H:%M"),
                    end=end.strftime("%H:%M"),
                    minutes=round(minutes, 1),
                    energy_kwh=round(mean_load_kw * minutes / 60.0, 3),
                    soc_end_pct=round(run[-1].battery_soc_pct, 1),
                )
            )
        i = j + 1
    return events
