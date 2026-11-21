"""
Days until rain heavy enough to wash the panels, from the Open-Meteo daily forecast (Lahore).

Feeds the Panels screen's "clean now or wait for rain" advice. The threshold is the one the soiling
pipeline assumes washes the array (RAIN_CLEAN_MM). Cached for an hour; the forecast changes slowly.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from datetime import date, datetime, timedelta
from typing import Any

import httpx
from pydantic import BaseModel

from src.data_engineering.repair_master_dataset import RAIN_CLEAN_MM

FORECAST_DAYS = 16

FetchDailyRain = Callable[[], Awaitable[Mapping[str, Any]]]


class RainUnavailable(RuntimeError):
    """No usable daily precipitation forecast."""


class RainForecastOut(BaseModel):
    # None: no washing rain within the forecast horizon.
    days_until_rain: int | None
    threshold_mm: float
    horizon_days: int


def days_until_rain(payload: Mapping[str, Any], today: date, threshold_mm: float = RAIN_CLEAN_MM) -> int | None:
    """Days from `today` to the first forecast day with at least `threshold_mm` of rain (0 = today)."""
    daily = payload.get("daily")
    if not isinstance(daily, Mapping):
        raise RainUnavailable("forecast has no daily block")
    days, amounts = daily.get("time"), daily.get("precipitation_sum")
    if not isinstance(days, list) or not isinstance(amounts, list) or len(days) != len(amounts) or not days:
        raise RainUnavailable("forecast daily precipitation is malformed")
    for day, mm in zip(days, amounts):
        offset = (date.fromisoformat(str(day)) - today).days
        if offset >= 0 and mm is not None and float(mm) >= threshold_mm:
            return offset
    return None


class RainForecastService:
    def __init__(self, fetch: FetchDailyRain, clock: Callable[[], datetime], ttl: timedelta = timedelta(hours=1)) -> None:
        self._fetch = fetch
        self._clock = clock
        self._ttl = ttl
        self._cached: tuple[RainForecastOut, datetime, date] | None = None

    async def forecast(self, today: date) -> RainForecastOut:
        now = self._clock()
        if self._cached is not None:
            result, made_at, made_for = self._cached
            if made_for == today and now - made_at < self._ttl:
                return result
        try:
            payload = await self._fetch()
        except httpx.HTTPError as exc:
            raise RainUnavailable(f"rain forecast request failed: {exc}") from exc
        result = RainForecastOut(
            days_until_rain=days_until_rain(payload, today),
            threshold_mm=RAIN_CLEAN_MM,
            horizon_days=FORECAST_DAYS,
        )
        self._cached = (result, now, today)
        return result
