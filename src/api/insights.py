"""
Recorded history behind the Outage, Savings, Reports and Panels screens, read from the processed datasets.

The API serves the recorded rows as they are; the frontend turns them into charts and labels with the
same builders it uses for its sample data, so both show identical figures. Each file is read once per
process and cached (the datasets only change when the data pipeline is re-run, which restarts the API).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import polars as pl
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = PROJECT_ROOT / "data" / "processed"
OUTAGES_CSV = PROCESSED / "grid_outages" / "lesco_johar_town_outages.csv"
MASTER_CSV = PROCESSED / "master_ems_timeseries.csv"
MONTHLY_METER_CSV = PROCESSED / "residential_load" / "lahore_residential_monthly_metered_ground_truth.csv"
DAILY_GENERATION_CSV = PROCESSED / "solar_timeseries" / "goodwe_lahore_daily.csv"
ALARMS_CSV = PROJECT_ROOT / "data" / "raw" / "goodwe_inverter_reports" / "goodwe_sems_agent_alarm_events_oct2026.csv"

# Shorter events are inverter blips (mostly 5-minute peak-hour discharges), not grid outages.
MIN_OUTAGE_MINUTES = 15
METER_MONTHS = 12
# The Energy screen compares each month with the same month a year earlier.
METER_HISTORY_MONTHS = 24


class DatasetUnavailable(Exception):
    """A processed dataset the endpoint needs is missing on this server."""


# ---------- response contracts ----------


class OutageEventOut(BaseModel):
    date: str
    start: str
    end: str
    minutes: float
    energy_kwh: float
    soc_end_pct: float | None


class OutageHistoryOut(BaseModel):
    # None while the site has neither recorded nor logged data.
    period_start: str | None
    period_end: str | None
    events: list[OutageEventOut]
    # Last day of the recorded station dataset (station site only) and of the site's own log.
    recorded_through: str | None = None
    logged_through: str | None = None
    logged_days: int = 0


class DailyEnergyOut(BaseModel):
    date: str
    solar_kwh: float
    load_kwh: float
    import_kwh: float
    export_kwh: float
    # None on days the battery was not measured (most of the recorded dataset before 2025-11-20).
    battery_charged_kwh: float | None = None
    battery_discharged_kwh: float | None = None


class MonthlyMeterOut(BaseModel):
    month: str
    pv_kwh: float
    load_kwh: float
    purchased_kwh: float
    sold_kwh: float


class EnergyRatesOut(BaseModel):
    """The site's tariff rates from the tariff engine, PKR per kWh as decimal strings (src/api/site_tariff.py)."""

    # A kWh of solar used at home: the all-in import it avoids (Off-Peak, or the site's slab rate).
    self_consumed_pkr_per_kwh: str
    # A kWh sent to the grid: the regime's export credit (0 under zero-export).
    export_pkr_per_kwh: str


class MonthCostOut(BaseModel):
    """The latest month's LESCO bill estimate from the tariff engine (fixed charges and taxes included)."""

    month: str
    cost_pkr: str
    without_solar_pkr: str


class EnergyHistoryOut(BaseModel):
    daily: list[DailyEnergyOut]
    monthly: list[MonthlyMeterOut]
    # Up to the last 24 months, oldest first (same rows as `monthly`, further back).
    monthly_history: list[MonthlyMeterOut] = []
    # Last day the monthly totals cover (the latest month is partial up to here); None with no data yet.
    metered_through: str | None
    recorded_through: str | None = None
    logged_through: str | None = None
    # Complete days in the site's own log.
    logged_days: int = 0
    # Last day of the recorded hourly data the station's daily rows come from (station site only).
    hourly_through: str | None = None
    # The site's tariff, set by the endpoint (None with no data yet).
    rates: EnergyRatesOut | None = None
    current_month: MonthCostOut | None = None


class SoilingHistoryOut(BaseModel):
    wash_date: str
    as_of: str
    # Soiling-model performance ratio for each day from the wash to as_of.
    model_pr: list[float]
    daily_loss_kwh: float


class SiteSoilingOut(SoilingHistoryOut):
    """One site's dust model (src/api/site_soiling.py). wash_date is the latest clean event."""

    # live: fitted to the site's own logged output; recorded: the station's recorded model.
    source: Literal["live", "recorded"]
    clean_event: Literal["wash", "rain"]
    # Complete logged days after the clean event that the live model could use (it needs 3).
    logged_days_since_clean: int
    # Fraction of output lost per day, compounding: PR(t) = PR(0) * exp(-rate * t).
    loss_rate_per_day: float
    # What one lost kWh is worth at the site's tariff (avoided Off-Peak import and lost export, blended).
    tariff_pkr_per_kwh: float
    # Typical price of one wash (backend configuration); the user can change it on the Panels screen.
    wash_cost_pkr: float


# ---------- loaders ----------


def _read(path: Path, **kwargs: object) -> pl.DataFrame:
    if not path.exists():
        raise DatasetUnavailable(path.name)
    return pl.read_csv(path, **kwargs)  # type: ignore[arg-type]


@lru_cache(maxsize=4)
def outage_history(path: Path = OUTAGES_CSV) -> OutageHistoryOut:
    df = _read(path, infer_schema_length=0)
    dates = df["date"]
    events = (
        df.with_columns(
            pl.col("duration_minutes").cast(pl.Float64),
            pl.col("energy_kwh").cast(pl.Float64),
            pl.col("soc_end_pct").cast(pl.Float64, strict=False),
        )
        .filter(pl.col("duration_minutes") >= MIN_OUTAGE_MINUTES)
        .sort(["date", "start_time"])
    )
    return OutageHistoryOut(
        period_start=str(dates.min()),
        period_end=str(dates.max()),
        events=[
            OutageEventOut(
                date=row["date"],
                start=row["start_time"][:5],
                end=row["end_time"][:5],
                minutes=row["duration_minutes"],
                energy_kwh=row["energy_kwh"],
                soc_end_pct=row["soc_end_pct"],
            )
            for row in events.iter_rows(named=True)
        ],
    )


@lru_cache(maxsize=4)
def energy_history(
    master: Path = MASTER_CSV, meter: Path = MONTHLY_METER_CSV, daily_generation: Path = DAILY_GENERATION_CSV
) -> EnergyHistoryOut:
    hourly = _read(
        master,
        columns=[
            "date", "solar_energy_kwh", "residential_load_kw", "grid_import_kw", "grid_export_kw",
            "bat_charged_kwh", "bat_discharged_kwh",
        ],
        infer_schema_length=10000,
    )

    def battery_day(column: str) -> pl.Expr:
        # A day's battery total only when every hour of it was measured.
        measured = pl.col(column).is_not_null().all()
        return pl.when(measured).then(pl.col(column).sum().round(2)).otherwise(None)

    # Hourly kW averages are kWh for that hour, so a day's energy is the sum of its hours.
    daily = (
        hourly.group_by("date")
        .agg(
            pl.col("solar_energy_kwh").sum().round(2).alias("solar_kwh"),
            pl.col("residential_load_kw").sum().round(2).alias("load_kwh"),
            pl.col("grid_import_kw").sum().round(2).alias("import_kwh"),
            pl.col("grid_export_kw").sum().round(2).alias("export_kwh"),
            battery_day("bat_charged_kwh").alias("battery_charged_kwh"),
            battery_day("bat_discharged_kwh").alias("battery_discharged_kwh"),
        )
        .sort("date")
    )
    meters = _read(meter, infer_schema_length=10000).sort("month")
    metered_through = _read(daily_generation, columns=["date"])["date"].max()
    months = [
        MonthlyMeterOut(
            month=str(row["month"])[:7],
            pv_kwh=row["pv_generation_kwh"],
            load_kwh=row["load_consumption_kwh"],
            purchased_kwh=row["purchased_from_grid_kwh"],
            sold_kwh=row["sold_to_grid_kwh"],
        )
        for row in meters.iter_rows(named=True)
    ]
    return EnergyHistoryOut(
        daily=[DailyEnergyOut(**row) for row in daily.iter_rows(named=True)],
        monthly=months[-METER_MONTHS:],
        monthly_history=months[-METER_HISTORY_MONTHS:],
        metered_through=str(metered_through),
    )


@lru_cache(maxsize=4)
def recorded_hourly_flows(master: Path = MASTER_CSV) -> pl.DataFrame:
    """The recorded hours: date, hour, residential_load_kw and grid_import_kw (hourly kW means = kWh)."""
    return _read(
        master, columns=["date", "hour", "residential_load_kw", "grid_import_kw"], infer_schema_length=10000
    )


@lru_cache(maxsize=4)
def soiling_history(master: Path = MASTER_CSV) -> SoilingHistoryOut:
    days = (
        _read(
            master,
            columns=["date", "event_type", "soiling_model_pr", "soiling_loss_kwh"],
            infer_schema_length=10000,
        )
        .unique(subset=["date"], keep="first")
        .with_columns(pl.col("soiling_model_pr").cast(pl.Float64, strict=False))
        .sort("date")
    )
    washes = days.filter(pl.col("event_type") == "manual_wash_confirmed")["date"]
    if washes.is_empty():
        raise DatasetUnavailable("no confirmed panel wash in the dataset")
    wash_date = str(washes.max())
    since_wash = days.filter((pl.col("date") >= wash_date) & pl.col("soiling_model_pr").is_not_null())
    latest = since_wash.tail(1).row(0, named=True)
    return SoilingHistoryOut(
        wash_date=wash_date,
        as_of=str(latest["date"]),
        model_pr=[round(v, 6) for v in since_wash["soiling_model_pr"].to_list()],
        daily_loss_kwh=round(float(latest["soiling_loss_kwh"]), 3),
    )


@lru_cache(maxsize=4)
def inverter_alarms(path: Path = ALARMS_CSV) -> list[dict[str, object]]:
    """Inverter alarm log rows (alarm_name, start_time, end_time, status, severity, duration_minutes)."""
    return _read(path, infer_schema_length=0).to_dicts()
