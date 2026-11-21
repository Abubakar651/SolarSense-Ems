"""
Live 24-hour forecast for the current day at Station LHR-RES-01.

The forecasters were trained on the recorded dataset, whose lag features (24 h, 48 h, 168 h and a
7-day rolling mean lagged 24 h) need the 192 hours before the forecast day. For days after the
dataset ends, that history comes from the logged inverter samples (inverter_samples table); any hour
with too few samples falls back to the same position in the dataset's final 192 hours, which ends
at 23:00 and so lines up hour-of-day for hour-of-day. Features are built by the same
build_task_frame used in training, from the Open-Meteo forecast for the day.

Everything here is pure: the database read, the weather fetch and the clock live at the edges
(src/api/live_plan.py).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal, Optional, Protocol

import numpy as np
import numpy.typing as npt
import polars as pl

from src.data_engineering.feature_store import PKT_TZ, build_task_frame

FloatVec = npt.NDArray[np.float64]
IntVec = npt.NDArray[np.int8]

HORIZON_HOURS = 24
# lag_168h plus the 168-hour rolling mean of the 24 h lag reach back 24 + 168 = 192 hours.
HISTORY_HOURS = 192
# An hour counts as logged once half of its 5-minute polls arrived.
MIN_SAMPLES_PER_HOUR = 6
# Matches the dataset's outage definition (outages of 15 minutes or more): a quarter of the hour.
OUTAGE_FRACTION = 0.25
# AGENTS.md law 1: astronomical night 20:00-04:00 PKT has zero solar whatever the model says.
NIGHT_HOURS = frozenset({20, 21, 22, 23, 0, 1, 2, 3})
# With nothing logged in the day's first hour, a level logged this shortly before midnight still stands for it
# (a home's night load moves the battery a few percent an hour at most).
SOC_LOOKBACK = timedelta(hours=3)

WEATHER_VARIABLES: Mapping[str, str] = {
    "shortwave_radiation": "ghi_wm2",
    "direct_normal_irradiance": "dni_wm2",
    "diffuse_radiation": "dhi_wm2",
    "temperature_2m": "temp_c",
    "relative_humidity_2m": "humidity_pct",
    "wind_speed_10m": "wind_ms",
    "precipitation": "rain_mm",
}


class WeatherUnavailable(RuntimeError):
    """The weather forecast is missing hours or values the forecasters need."""


class HistoryNotLogged(RuntimeError):
    """The site has logged no usable hour of the recent history the forecasters need."""


def _locked(values: npt.ArrayLike, dtype: Any = np.float64) -> np.ndarray:
    arr = np.ascontiguousarray(values, dtype=dtype)
    arr.setflags(write=False)
    return arr


@dataclass(frozen=True, slots=True)
class TelemetrySample:
    """One logged inverter poll (an inverter_samples row)."""

    recorded_at: datetime
    pv_power_w: float
    load_power_w: float
    battery_soc_pct: float
    is_blackout: bool
    # + is export / charging (the live reader's signs). Not used by the forecast.
    grid_power_w: float = 0.0
    battery_power_w: float = 0.0


@dataclass(frozen=True, slots=True)
class HourlyHistory:
    """The 192 hours before the forecast day, oldest first (kW averages; outage flag 0/1)."""

    solar_kw: FloatVec
    load_kw: FloatVec
    outage_flag: FloatVec
    logged_hours: int


@dataclass(frozen=True, slots=True)
class WeatherHours:
    """Hourly weather for the 24 hours of the forecast day, in the training dataset's units."""

    ghi_wm2: FloatVec
    dni_wm2: FloatVec
    dhi_wm2: FloatVec
    temp_c: FloatVec
    humidity_pct: FloatVec
    wind_ms: FloatVec
    rain_mm: FloatVec


@dataclass(frozen=True, slots=True)
class LiveForecast:
    day_start: datetime
    timestamps_iso: tuple[str, ...]
    solar_kw: FloatVec
    load_kw: FloatVec
    load_p90_kw: FloatVec
    outage_prob: FloatVec
    history_logged_hours: int


class _SolarModel(Protocol):
    feature_names: Sequence[str]

    def predict_24h(self, X_24: np.ndarray) -> np.ndarray: ...


class _LoadModel(Protocol):
    feature_names: Sequence[str]

    def predict_24h(self, X_24: np.ndarray) -> tuple[np.ndarray, np.ndarray]: ...


class _OutageModel(Protocol):
    feature_names: Sequence[str]

    def predict_proba_24h(self, X_24: np.ndarray) -> np.ndarray: ...


def day_start_of(now: datetime) -> datetime:
    """Local midnight (PKT) of the day `now` falls on."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    local = now.astimezone(PKT_TZ)
    return local.replace(hour=0, minute=0, second=0, microsecond=0)


def _hour_buckets(samples: Sequence[TelemetrySample], start: datetime, hours: int) -> tuple[np.ndarray, ...]:
    """Per-hour sample count, summed pv/load power (W) and blackout count over [start, start + hours)."""
    count = np.zeros(hours, dtype=np.int64)
    pv_sum = np.zeros(hours, dtype=np.float64)
    load_sum = np.zeros(hours, dtype=np.float64)
    blackout = np.zeros(hours, dtype=np.int64)
    if not samples:
        return count, pv_sum, load_sum, blackout

    offsets = np.array([(s.recorded_at - start).total_seconds() for s in samples], dtype=np.float64)
    idx = np.floor(offsets / 3600.0).astype(np.int64)
    inside = (idx >= 0) & (idx < hours)
    idx = idx[inside]
    pv = np.array([s.pv_power_w for s in samples], dtype=np.float64)[inside]
    load = np.array([s.load_power_w for s in samples], dtype=np.float64)[inside]
    out = np.array([s.is_blackout for s in samples], dtype=np.int64)[inside]

    np.add.at(count, idx, 1)
    np.add.at(pv_sum, idx, pv)
    np.add.at(load_sum, idx, load)
    np.add.at(blackout, idx, out)
    return count, pv_sum, load_sum, blackout


def hourly_history(
    samples: Sequence[TelemetrySample],
    day_start: datetime,
    fallback: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> HourlyHistory:
    """
    Hourly averages of the logged samples for the 192 hours before `day_start`. Hours with fewer
    than MIN_SAMPLES_PER_HOUR samples take the fallback (dataset) value at the same position.
    """
    fb_solar, fb_load, fb_outage = (np.asarray(a, dtype=np.float64) for a in fallback)
    if not (fb_solar.size == fb_load.size == fb_outage.size == HISTORY_HOURS):
        raise ValueError(f"fallback history must have {HISTORY_HOURS} hours")

    start = day_start - timedelta(hours=HISTORY_HOURS)
    count, pv_sum, load_sum, blackout = _hour_buckets(samples, start, HISTORY_HOURS)
    logged = count >= MIN_SAMPLES_PER_HOUR
    safe = np.maximum(count, 1)

    solar_kw = np.where(logged, pv_sum / safe / 1000.0, fb_solar)
    load_kw = np.where(logged, load_sum / safe / 1000.0, fb_load)
    outage = np.where(logged, (blackout / safe >= OUTAGE_FRACTION).astype(np.float64), fb_outage)
    return HourlyHistory(
        solar_kw=_locked(solar_kw),
        load_kw=_locked(load_kw),
        outage_flag=_locked(outage),
        logged_hours=int(logged.sum()),
    )


def own_log_fallback(
    samples: Sequence[TelemetrySample], day_start: datetime
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    A gap filler for hourly_history built only from the site's own logged hours in the 192 before `day_start`:
    each hour takes the mean of the logged hours at the same hour of day (no outage). An hour of day the log
    never covered takes the mean of all logged hours (solar: of the logged daylight hours, 0 at night).
    Raises HistoryNotLogged when no hour is logged at all.
    """
    start = day_start - timedelta(hours=HISTORY_HOURS)
    count, pv_sum, load_sum, _ = _hour_buckets(samples, start, HISTORY_HOURS)
    logged = count >= MIN_SAMPLES_PER_HOUR
    if not logged.any():
        raise HistoryNotLogged("no logged hour in the recent history")
    safe = np.maximum(count, 1)
    solar = pv_sum / safe / 1000.0
    load = load_sum / safe / 1000.0
    # HISTORY_HOURS is whole days, so position i falls at hour of day (start.hour + i) % 24.
    hour_of_day = (np.arange(HISTORY_HOURS) + start.astimezone(PKT_TZ).hour) % 24
    night = np.isin(hour_of_day, list(NIGHT_HOURS))
    day_logged = logged & ~night

    profile_solar = np.zeros(24)
    profile_load = np.full(24, load[logged].mean())
    if day_logged.any():
        profile_solar[[h for h in range(24) if h not in NIGHT_HOURS]] = solar[day_logged].mean()
    for_hour = np.zeros((24, HISTORY_HOURS), dtype=bool)
    for_hour[hour_of_day, np.arange(HISTORY_HOURS)] = True
    per_hour = (for_hour & logged).sum(axis=1)
    has = per_hour > 0
    profile_solar[has] = (for_hour & logged)[has] @ solar / per_hour[has]
    profile_load[has] = (for_hour & logged)[has] @ load / per_hour[has]
    return (
        _locked(profile_solar[hour_of_day]),
        _locked(profile_load[hour_of_day]),
        _locked(np.zeros(HISTORY_HOURS)),
    )


def day_outage_mask(samples: Sequence[TelemetrySample], day_start: datetime, now: datetime) -> IntVec:
    """
    Blackout hours of the forecast day so far, from the logged samples (same quarter-hour rule as
    the history). Hours after `now` are 0: a future outage is a probability, not a constraint.
    """
    count, _, _, blackout = _hour_buckets(samples, day_start, HORIZON_HOURS)
    flagged = (count > 0) & (blackout / np.maximum(count, 1) >= OUTAGE_FRACTION)
    current_hour = int((now - day_start).total_seconds() // 3600)
    flagged[np.arange(HORIZON_HOURS) > current_hour] = False
    return _locked(flagged, dtype=np.int8)


@dataclass(frozen=True, slots=True)
class StartingSoc:
    pct: float
    # logged_midnight: the day's first logged level; logged_before_midnight: the last one within SOC_LOOKBACK before.
    source: Literal["logged_midnight", "logged_before_midnight"]


def starting_soc(samples: Sequence[TelemetrySample], day_start: datetime) -> Optional[StartingSoc]:
    """
    Battery level (%) at the start of the day: the first sample in its first hour, else the latest sample in
    the SOC_LOOKBACK before midnight, else None (nothing logged near midnight).
    """
    first_hour = [s for s in samples if day_start <= s.recorded_at < day_start + timedelta(hours=1)]
    if first_hour:
        earliest = min(first_hour, key=lambda s: s.recorded_at)
        return StartingSoc(float(np.clip(earliest.battery_soc_pct, 0.0, 100.0)), "logged_midnight")
    before = [s for s in samples if day_start - SOC_LOOKBACK <= s.recorded_at < day_start]
    if before:
        latest = max(before, key=lambda s: s.recorded_at)
        return StartingSoc(float(np.clip(latest.battery_soc_pct, 0.0, 100.0)), "logged_before_midnight")
    return None


def parse_open_meteo_hourly(payload: Mapping[str, Any], day_start: datetime) -> WeatherHours:
    """
    The `hourly` block of an Open-Meteo forecast for one day (timezone Asia/Karachi, wind in m/s),
    mapped to the dataset's columns. Gaps are filled the way the dataset's ingestion fills them.
    """
    hourly = payload.get("hourly")
    if not isinstance(hourly, Mapping):
        raise WeatherUnavailable("weather payload has no hourly block")
    expected = [(day_start + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(HORIZON_HOURS)]
    if list(hourly.get("time", [])) != expected:
        raise WeatherUnavailable("weather forecast does not cover the 24 hours of the day")

    columns: dict[str, np.ndarray] = {}
    for api_key, column in WEATHER_VARIABLES.items():
        raw = hourly.get(api_key)
        if not isinstance(raw, list) or len(raw) != HORIZON_HOURS:
            raise WeatherUnavailable(f"weather forecast is missing {api_key}")
        columns[column] = np.array([np.nan if v is None else float(v) for v in raw], dtype=np.float64)

    temp = pl.Series(columns["temp_c"], nan_to_null=True).fill_null(strategy="backward").fill_null(25.0)
    return WeatherHours(
        ghi_wm2=_locked(np.nan_to_num(columns["ghi_wm2"], nan=0.0)),
        dni_wm2=_locked(np.nan_to_num(columns["dni_wm2"], nan=0.0)),
        dhi_wm2=_locked(np.nan_to_num(columns["dhi_wm2"], nan=0.0)),
        temp_c=_locked(temp.to_numpy()),
        humidity_pct=_locked(np.nan_to_num(columns["humidity_pct"], nan=50.0)),
        wind_ms=_locked(np.nan_to_num(columns["wind_ms"], nan=0.0)),
        rain_mm=_locked(np.nan_to_num(columns["rain_mm"], nan=0.0)),
    )


def live_feature_frame(day_start: datetime, history: HourlyHistory, weather: WeatherHours) -> pl.DataFrame:
    """
    The 192 history hours followed by the 24 forecast hours, in the dataset's column layout.
    History rows carry targets (for the lags) and no weather; forecast rows carry weather and no targets.
    """
    if day_start.tzinfo is None:
        raise ValueError("day_start must be timezone-aware")
    start = day_start.astimezone(PKT_TZ) - timedelta(hours=HISTORY_HOURS)
    timestamps = pl.datetime_range(
        start,
        start + timedelta(hours=HISTORY_HOURS + HORIZON_HOURS - 1),
        interval="1h",
        time_zone="Asia/Karachi",
        eager=True,
    ).alias("timestamp")

    no_history = np.full(HISTORY_HOURS, np.nan)
    no_targets = np.full(HORIZON_HOURS, np.nan)

    def weather_col(name: str, values: FloatVec) -> pl.Series:
        return pl.Series(name, np.concatenate([no_history, values]), nan_to_null=True)

    def target_col(name: str, values: FloatVec) -> pl.Series:
        return pl.Series(name, np.concatenate([values, no_targets]), nan_to_null=True)

    return pl.DataFrame([
        timestamps,
        weather_col("ghi_wm2", weather.ghi_wm2),
        weather_col("dni_wm2", weather.dni_wm2),
        weather_col("dhi_wm2", weather.dhi_wm2),
        weather_col("temp_c", weather.temp_c),
        weather_col("humidity_pct", weather.humidity_pct),
        weather_col("wind_ms", weather.wind_ms),
        weather_col("rain_mm", weather.rain_mm),
        target_col("effective_solar_kw", history.solar_kw),
        target_col("factory_load_kw", history.load_kw),
        target_col("outage_flag", history.outage_flag),
    ])


def _horizon_matrix(frame: pl.DataFrame, task: str, feature_names: Sequence[str]) -> np.ndarray:
    task_frame, _, _ = build_task_frame(frame, task)
    return np.ascontiguousarray(
        task_frame.select(list(feature_names)).tail(HORIZON_HOURS).to_numpy(), dtype=np.float64
    )


def forecast_day(
    forecasters: tuple[_SolarModel, _LoadModel, _OutageModel],
    day_start: datetime,
    history: HourlyHistory,
    weather: WeatherHours,
) -> LiveForecast:
    """Solar, load (with p90) and outage probability for the 24 hours from `day_start`."""
    solar_model, load_model, outage_model = forecasters
    frame = live_feature_frame(day_start, history, weather)

    solar = solar_model.predict_24h(_horizon_matrix(frame, "solar", solar_model.feature_names))
    load, load_p90 = load_model.predict_24h(_horizon_matrix(frame, "load", load_model.feature_names))
    outage_prob = outage_model.predict_proba_24h(_horizon_matrix(frame, "outage", outage_model.feature_names))

    local_start = day_start.astimezone(PKT_TZ)
    hours = [local_start + timedelta(hours=h) for h in range(HORIZON_HOURS)]
    night = np.array([t.hour in NIGHT_HOURS for t in hours])
    solar = np.where(night | (weather.ghi_wm2 <= 0.0), 0.0, solar)

    return LiveForecast(
        day_start=local_start,
        timestamps_iso=tuple(t.strftime("%Y-%m-%dT%H:%M:%S%z") for t in hours),
        solar_kw=_locked(solar),
        # A regression tree can dip just below zero near idle hours; a home never draws negative power.
        load_kw=_locked(np.maximum(load, 0.0)),
        load_p90_kw=_locked(np.maximum(load_p90, 0.0)),
        outage_prob=_locked(np.clip(outage_prob, 0.0, 1.0)),
        history_logged_hours=history.logged_hours,
    )
