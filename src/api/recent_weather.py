"""
Lahore's daily sunlight and rain around today, from the Open-Meteo forecast API with past_days.

Feeds the live dust model (src/api/site_soiling.py): each past day's modelled GHI is the expected-output
baseline of that logged day, a past day with washing rain is a clean event, today's GHI prices today's
dust loss, and the first washing rain ahead says how long dust keeps costing. Every site is in Lahore, so
one request serves them all. Cached for `ttl`; after a failed request the service answers "unavailable"
for `retry_after` without asking again, so a weather outage doesn't slow every page.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import httpx
import numpy as np
import numpy.typing as npt
import polars as pl

from src.api.rain_forecast import RainUnavailable, days_until_rain
from src.forecast.live_forecast import WeatherUnavailable

# Open-Meteo's limit for past_days.
PAST_DAYS = 92
FORECAST_DAYS = 16

FetchRecentWeather = Callable[[], Awaitable[Mapping[str, Any]]]


@dataclass(frozen=True, slots=True)
class RecentWeather:
    """Local days, oldest first, with their GHI (kWh/m2, NaN if any hour is missing) and rain (mm, NaN if missing)."""

    days: tuple[date, ...]
    ghi_kwh_m2: npt.NDArray[np.float64]
    rain_mm: npt.NDArray[np.float64]
    # Days from the day the weather was fetched for to the first washing rain; None when none is forecast.
    days_until_rain: int | None

    def ghi_on(self, day: date) -> float | None:
        try:
            value = float(self.ghi_kwh_m2[self.days.index(day)])
        except ValueError:
            return None
        return value if np.isfinite(value) else None


def parse_recent_weather(payload: Mapping[str, Any], today: date) -> RecentWeather:
    hourly, daily = payload.get("hourly"), payload.get("daily")
    if not isinstance(hourly, Mapping) or not isinstance(daily, Mapping):
        raise WeatherUnavailable("weather has no hourly or daily block")
    times, ghi = hourly.get("time"), hourly.get("shortwave_radiation")
    days, rain = daily.get("time"), daily.get("precipitation_sum")
    if not (isinstance(times, list) and isinstance(ghi, list) and len(times) == len(ghi) and times):
        raise WeatherUnavailable("hourly irradiance is malformed")
    if not (isinstance(days, list) and isinstance(rain, list) and len(days) == len(rain) and days):
        raise WeatherUnavailable("daily precipitation is malformed")

    per_day = (
        pl.DataFrame({"time": times, "ghi": ghi}, schema={"time": pl.Utf8, "ghi": pl.Float64}, strict=False)
        .group_by(pl.col("time").str.slice(0, 10).alias("day"))
        # Open-Meteo's hourly value is the mean W/m2 over the hour, so the day's sum / 1000 is kWh/m2.
        .agg((pl.col("ghi").sum() / 1000.0).alias("ghi_kwh_m2"), pl.col("ghi").count().alias("hours"))
        .with_columns(pl.when(pl.col("hours") == 24).then(pl.col("ghi_kwh_m2")).alias("ghi_kwh_m2"))
    )
    frame = (
        pl.DataFrame(
            {"day": [str(d) for d in days], "rain_mm": rain},
            schema={"day": pl.Utf8, "rain_mm": pl.Float64},
            strict=False,
        )
        .join(per_day.select("day", "ghi_kwh_m2"), on="day", how="left")
        .sort("day")
    )
    try:
        rain_ahead = days_until_rain(payload, today)
    except RainUnavailable as exc:
        raise WeatherUnavailable(str(exc)) from exc
    return RecentWeather(
        days=tuple(date.fromisoformat(d) for d in frame["day"]),
        ghi_kwh_m2=_locked(frame["ghi_kwh_m2"].fill_null(np.nan).to_numpy()),
        rain_mm=_locked(frame["rain_mm"].fill_null(np.nan).to_numpy()),
        days_until_rain=rain_ahead,
    )


def _locked(values: npt.NDArray[Any]) -> npt.NDArray[np.float64]:
    vec = np.ascontiguousarray(values, dtype=np.float64)
    vec.setflags(write=False)
    return vec


class RecentWeatherService:
    def __init__(
        self,
        fetch: FetchRecentWeather,
        clock: Callable[[], datetime],
        ttl: timedelta = timedelta(hours=1),
        retry_after: timedelta = timedelta(minutes=5),
    ) -> None:
        self._fetch = fetch
        self._clock = clock
        self._ttl = ttl
        self._retry_after = retry_after
        self._cached: tuple[RecentWeather, datetime, date] | None = None
        self._failed_at: datetime | None = None

    async def get(self, today: date) -> RecentWeather:
        """The weather around `today`. Raises WeatherUnavailable when it can't be fetched or parsed."""
        now = self._clock()
        if self._cached is not None:
            weather, made_at, made_for = self._cached
            if made_for == today and now - made_at < self._ttl:
                return weather
        if self._failed_at is not None and now - self._failed_at < self._retry_after:
            raise WeatherUnavailable("recent weather failed recently; not retried yet")
        try:
            weather = parse_recent_weather(await self._fetch(), today)
        except (httpx.HTTPError, WeatherUnavailable) as exc:
            self._failed_at = now
            raise WeatherUnavailable(f"recent weather unavailable: {exc}") from exc
        self._failed_at = None
        self._cached = (weather, now, today)
        return weather
