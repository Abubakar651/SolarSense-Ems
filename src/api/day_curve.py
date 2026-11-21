"""
One day's power curve for the Energy screen: PV, home load, battery, grid and battery level through the day.

A site's own logged polls (about every 5 minutes) win for any day they cover. The station site also gets its
recorded data for the days the log does not cover: the 5-minute telemetry file, then the hourly dataset (one point
per hour). Every other site gets only its own log, so no tenant sees another site's data. Pure apart from the two
cached dataset reads: samples and dates come from the caller.

Signs follow the live reader: battery_kw is + while charging, grid_kw is + while exporting. The recorded 5-minute file
stores the battery the other way round (+ discharging), so it is flipped here.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from functools import lru_cache
from pathlib import Path

import polars as pl
from pydantic import BaseModel

from src.api import insights
from src.api.user_site import UserSite
from src.data_engineering.feature_store import PKT_TZ
from src.forecast.live_forecast import TelemetrySample

FIVE_MIN_CSV = insights.PROCESSED / "solar_timeseries" / "goodwe_station_5min_telemetry.csv"


class DayNotFound(Exception):
    """The requested day has no data for this site."""


class CurvePointOut(BaseModel):
    time: str  # local HH:MM
    pv_kw: float
    load_kw: float
    # None where the source did not measure the battery or the grid.
    battery_kw: float | None
    grid_kw: float | None
    soc_pct: float | None


class DayPeaksOut(BaseModel):
    """The day's highest readings, each None when the day never measured it."""

    pv_kw: float | None
    load_kw: float | None
    charge_kw: float | None
    discharge_kw: float | None
    import_kw: float | None
    export_kw: float | None


class DayCurveOut(BaseModel):
    # None with no data at all yet.
    date: str | None
    # Minutes between points: 5 for logged and recorded 5-minute data, 60 for the recorded hourly dataset.
    interval_minutes: int | None
    points: list[CurvePointOut]
    peaks: DayPeaksOut
    # Every day this site has a curve for, oldest first.
    dates: list[str]


def _point(
    time: str, pv: float, load: float, battery: float | None, grid: float | None, soc: float | None
) -> CurvePointOut:
    def clean(value: float | None) -> float | None:
        # "+ 0.0" turns -0.0 into 0.0 so a flipped idle battery does not show as -0.
        return None if value is None else round(value, 3) + 0.0

    return CurvePointOut(
        time=time, pv_kw=clean(pv) or 0.0, load_kw=clean(load) or 0.0,
        battery_kw=clean(battery), grid_kw=clean(grid), soc_pct=None if soc is None else round(soc, 1),
    )


def _peak(values: list[float]) -> float | None:
    return max(values) if values else None


def peaks(points: Sequence[CurvePointOut]) -> DayPeaksOut:
    battery = [p.battery_kw for p in points if p.battery_kw is not None]
    grid = [p.grid_kw for p in points if p.grid_kw is not None]
    return DayPeaksOut(
        pv_kw=_peak([p.pv_kw for p in points]),
        load_kw=_peak([p.load_kw for p in points]),
        charge_kw=_peak([b for b in battery if b > 0]) if battery else None,
        discharge_kw=_peak([-b for b in battery if b < 0]) if battery else None,
        import_kw=_peak([-g for g in grid if g < 0]) if grid else None,
        export_kw=_peak([g for g in grid if g > 0]) if grid else None,
    )


# ---------- sources ----------


def logged_days(samples: Sequence[TelemetrySample]) -> set[str]:
    return {s.recorded_at.astimezone(PKT_TZ).date().isoformat() for s in samples}


def logged_points(samples: Sequence[TelemetrySample], day: str) -> list[CurvePointOut]:
    local = [(s.recorded_at.astimezone(PKT_TZ), s) for s in samples]
    return [
        _point(at.strftime("%H:%M"), s.pv_power_w / 1000, s.load_power_w / 1000, s.battery_power_w / 1000,
               s.grid_power_w / 1000, s.battery_soc_pct)
        for at, s in sorted((pair for pair in local if pair[0].date().isoformat() == day), key=lambda p: p[0])
    ]


@lru_cache(maxsize=2)
def _five_minute(path: Path = FIVE_MIN_CSV) -> pl.DataFrame:
    frame = insights._read(path, infer_schema_length=10000)
    # The file's own `date` column is the day each row was recorded on (the timestamp is local, naive).
    return frame.with_columns(pl.col("timestamp").cast(pl.String).str.slice(11, 5).alias("time"))


@lru_cache(maxsize=2)
def _hourly(master: Path = insights.MASTER_CSV) -> pl.DataFrame:
    return insights._read(
        master,
        columns=[
            "date", "hour", "solar_energy_kwh", "residential_load_kw", "grid_import_kw", "grid_export_kw",
            "bat_charged_kwh", "bat_discharged_kwh", "battery_soc_mean",
        ],
        infer_schema_length=10000,
    )


def _recorded_five_minute(day: str) -> list[CurvePointOut]:
    rows = _five_minute().filter(pl.col("date") == day).sort("timestamp")
    return [
        _point(r["time"], r["pv_power_kw"], r["load_power_kw"], -r["battery_power_kw"], r["grid_power_kw"],
               r["battery_soc_pct"])
        for r in rows.iter_rows(named=True)
    ]


def _recorded_hourly(day: str) -> list[CurvePointOut]:
    rows = _hourly().filter(pl.col("date") == day).sort("hour")
    points = []
    for r in rows.iter_rows(named=True):
        charged, discharged = r["bat_charged_kwh"], r["bat_discharged_kwh"]
        measured = charged is not None and discharged is not None
        points.append(
            _point(f"{r['hour']:02d}:00", r["solar_energy_kwh"], r["residential_load_kw"],
                   charged - discharged if measured else None,  # an hour's kWh is its mean kW
                   r["grid_export_kw"] - r["grid_import_kw"], r["battery_soc_mean"])
        )
    return points


def _recorded_days(source: pl.DataFrame) -> set[str]:
    return set(source["date"].cast(pl.String).unique().to_list())


# ---------- the answer ----------


def day_curve_for_site(site: UserSite, samples: Sequence[TelemetrySample], day: date | None) -> DayCurveOut:
    """The site's curve for `day` (default: its latest day). Raises DayNotFound for a day it has none for."""
    own = logged_days(samples)
    five_min = _recorded_days(_five_minute()) if site.is_station else set()
    hourly = _recorded_days(_hourly()) if site.is_station else set()
    dates = sorted(own | five_min | hourly)
    if not dates and day is None:
        return DayCurveOut(date=None, interval_minutes=None, points=[], peaks=peaks([]), dates=[])

    chosen = day.isoformat() if day else dates[-1]
    if chosen in own:
        points, interval = logged_points(samples, chosen), 5
    elif chosen in five_min:
        points, interval = _recorded_five_minute(chosen), 5
    elif chosen in hourly:
        points, interval = _recorded_hourly(chosen), 60
    else:
        raise DayNotFound(chosen)
    return DayCurveOut(date=chosen, interval_minutes=interval, points=points, peaks=peaks(points), dates=dates)
