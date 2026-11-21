"""
Inputs for one site's live plan today: the forecast for the day plus what the site's own logged telemetry
says about it so far.

Per site: the lag history, today's blackout hours, starting battery level and this month's grid flows come
only from that site's samples. Hours its log doesn't cover yet are filled from its own logged hours (the
station site alone fills them from its recorded last week); a site with no logged hour at all has no
forecast yet (HistoryNotLogged). The forecasters learned the station's 7.02 kWp array, so the site's logged
solar is brought to that scale on the way in (and the caller scales the forecast back to the site's array).

The weather is shared (every site is in Lahore) and each site's forecast is cached for `forecast_ttl`, so
the weather API and the long history query are not hit per request.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Optional
import uuid

import httpx
from starlette.concurrency import run_in_threadpool

from src.api.site_sizing import to_station_scale
from src.api.telemetry_history import month_to_date_flows
from src.api.user_site import UserSite
from src.data_engineering.feature_store import EMSDataRepository
from src.data_engineering.month_to_date import MonthToDateFlowsDTO
from src.forecast.live_forecast import (
    HISTORY_HOURS,
    SOC_LOOKBACK,
    IntVec,
    LiveForecast,
    StartingSoc,
    TelemetrySample,
    WeatherHours,
    WeatherUnavailable,
    day_outage_mask,
    day_start_of,
    forecast_day,
    hourly_history,
    own_log_fallback,
    parse_open_meteo_hourly,
    starting_soc,
)
from src.optimizer.lesco_2026_tariff_and_dispatch import LescoCY2026TariffEngine

FetchWeather = Callable[[date], Awaitable[Mapping[str, Any]]]
LoadSamples = Callable[[uuid.UUID, datetime, datetime], list[TelemetrySample]]


@dataclass(frozen=True, slots=True)
class LiveDayInputs:
    forecast: LiveForecast
    outage_mask: IntVec
    # A level, not an amount: the plan applies it to the site's own battery. None: nothing logged near midnight.
    initial_soc: Optional[StartingSoc]
    # This month's grid flows before today from the site's log; None when no hour of the month is logged.
    month_flows: Optional[MonthToDateFlowsDTO]


class LivePlanService:
    def __init__(
        self,
        repo: EMSDataRepository,
        load_samples: LoadSamples,
        fetch_weather: FetchWeather,
        clock: Callable[[], datetime],
        forecast_ttl: timedelta = timedelta(minutes=30),
        max_sites: int = 256,
        tariff_engine: Optional[LescoCY2026TariffEngine] = None,
    ) -> None:
        # Only its seasonal peak windows are used, to split the month's imports.
        self._engine = tariff_engine or LescoCY2026TariffEngine()
        self._repo = repo
        self._load_samples = load_samples
        self._fetch_weather = fetch_weather
        self._clock = clock
        self._ttl = forecast_ttl
        self._max_sites = max_sites
        self._weather: Optional[tuple[WeatherHours, datetime, datetime]] = None
        # Per site: today's forecast, this month's flows before today (both fixed for the day) and when made.
        self._forecasts: OrderedDict[
            uuid.UUID, tuple[LiveForecast, Optional[MonthToDateFlowsDTO], datetime]
        ] = OrderedDict()

    def _fresh(self, made_at: datetime, now: datetime) -> bool:
        return now - made_at < self._ttl

    async def _weather_for(self, day: datetime, now: datetime) -> WeatherHours:
        if self._weather is not None:
            weather, made_at, made_for = self._weather
            if made_for == day and self._fresh(made_at, now):
                return weather
        try:
            payload = await self._fetch_weather(day.date())
        except httpx.HTTPError as exc:
            raise WeatherUnavailable(f"weather forecast request failed: {exc}") from exc
        weather = parse_open_meteo_hourly(payload, day)
        self._weather = (weather, now, day)
        return weather

    def _cached_forecast(
        self, site_id: uuid.UUID, day: datetime, now: datetime
    ) -> Optional[tuple[LiveForecast, Optional[MonthToDateFlowsDTO]]]:
        entry = self._forecasts.get(site_id)
        if entry is None:
            return None
        forecast, flows, made_at = entry
        if forecast.day_start != day or not self._fresh(made_at, now):
            return None
        return forecast, flows

    def _remember(
        self, site_id: uuid.UUID, forecast: LiveForecast, flows: Optional[MonthToDateFlowsDTO], now: datetime
    ) -> None:
        self._forecasts.pop(site_id, None)
        self._forecasts[site_id] = (forecast, flows, now)
        if len(self._forecasts) > self._max_sites:
            self._forecasts.popitem(last=False)

    def _gap_fallback(
        self, site: UserSite, scaled: list[TelemetrySample], day: datetime
    ) -> tuple[Any, Any, Any]:
        """The station's recorded last week for the station site; every other site's own logged hours."""
        if site.is_station:
            return self._repo.recent_history(HISTORY_HOURS)
        return own_log_fallback(scaled, day)

    async def inputs(self, site: UserSite) -> LiveDayInputs:
        """
        Raises WeatherUnavailable when there is no usable weather forecast for today, and HistoryNotLogged when
        a site other than the station has logged none of the recent history yet.
        """
        now = self._clock()
        day = day_start_of(now)
        cached = self._cached_forecast(site.site_id, day, now)

        if cached is None:
            weather = await self._weather_for(day, now)
            samples = await run_in_threadpool(
                self._load_samples, site.site_id, min(day.replace(day=1), day - timedelta(hours=HISTORY_HOURS)), now
            )
            scaled = to_station_scale(samples, site.sizes.pv_kwp)
            history = hourly_history(scaled, day, self._gap_fallback(site, scaled, day))
            forecast = await run_in_threadpool(forecast_day, self._repo.forecasters(), day, history, weather)
            flows = await run_in_threadpool(month_to_date_flows, samples, day.date(), self._engine)
            self._remember(site.site_id, forecast, flows, now)
            near_today = [s for s in samples if s.recorded_at >= day - SOC_LOOKBACK]
        else:
            forecast, flows = cached
            near_today = await run_in_threadpool(self._load_samples, site.site_id, day - SOC_LOOKBACK, now)

        return LiveDayInputs(
            forecast=forecast,
            outage_mask=day_outage_mask(near_today, day, now),
            initial_soc=starting_soc(near_today, day),
            month_flows=flows,
        )
