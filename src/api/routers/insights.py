"""
History for the Outage, Savings, Reports and Panels screens, scoped to the signed-in user's site.

Each answer comes from that site's own logged telemetry; only the site that owns the recorded station
dataset also gets that dataset (src/api/site_insights.py, src/api/site_soiling.py). The rain forecast is
for Lahore.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Annotated, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from src.api.db.models import utc_now
from src.api.day_curve import DayCurveOut, DayNotFound, day_curve_for_site
from src.api.deps import get_now
from src.api.insights import DatasetUnavailable, EnergyHistoryOut, OutageHistoryOut, SiteSoilingOut
from src.api.rain_forecast import RainForecastOut, RainForecastService, RainUnavailable
from src.api.site_insights import energy_for_site, outages_for_site, with_tariff
from src.api.site_samples import SiteSampleCache
from src.api.site_soiling import SiteSoilingService, SoilingCollectingError
from src.api.user_site import MySite
from src.data_engineering.feature_store import PKT_TZ
from src.forecast.live_forecast import TelemetrySample, WeatherUnavailable
from src.soiling.live_model import MIN_FIT_DAYS

router = APIRouter(prefix="/api/insights", tags=["Insights"])

HISTORY_WINDOW = timedelta(days=400)

_T = TypeVar("_T")

Now = Annotated[datetime, Depends(get_now)]


async def _load(loader: Callable[[], _T]) -> _T:
    # The first call reads CSVs and the site's samples (cached afterwards), so keep it off the event loop.
    try:
        return await run_in_threadpool(loader)
    except DatasetUnavailable:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="data_unavailable") from None


def _site_samples(request: Request, site: MySite) -> list[TelemetrySample]:
    cache: SiteSampleCache = request.app.state.site_samples
    now = utc_now()
    return cache.samples(site.site_id, now - HISTORY_WINDOW, now)


@router.get("/outages", response_model=OutageHistoryOut)
async def get_outage_history(request: Request, site: MySite) -> OutageHistoryOut:
    """Grid outages of 15 minutes or more at the user's site, oldest first."""
    return await _load(lambda: outages_for_site(site, _site_samples(request, site)))


@router.get("/day-curve", response_model=DayCurveOut)
async def get_day_curve(
    request: Request, site: MySite, day: Annotated[date | None, Query(alias="date")] = None
) -> DayCurveOut:
    """
    One day's PV, load, battery (+ charging), grid (+ exporting) and battery level at the user's site, with the
    day's peaks and every day available. Defaults to the latest day; 404 day_not_found for a day it has none for.
    """
    try:
        return await _load(lambda: day_curve_for_site(site, _site_samples(request, site), day))
    except DayNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="day_not_found") from None


@router.get("/energy", response_model=EnergyHistoryOut)
async def get_energy_history(request: Request, site: MySite) -> EnergyHistoryOut:
    """
    The user's daily solar/load/import/export energy and monthly totals (last 12 months), with the rates the
    tariff engine values it at and the latest month's bill estimate, both at the user's saved tariff.
    """
    today = utc_now().astimezone(PKT_TZ).date()
    valuation = request.app.state.site_soiling.valuation

    def load() -> EnergyHistoryOut:
        samples = _site_samples(request, site)
        history = energy_for_site(site, samples, today)
        return with_tariff(
            history, site, samples, valuation.engine, valuation.station_export_override_pkr_per_kwh
        )

    return await _load(load)


@router.get("/soiling", response_model=SiteSoilingOut)
async def get_soiling_history(request: Request, site: MySite, now: Now) -> SiteSoilingOut | JSONResponse:
    """
    The site's dust model since its latest clean event (a recorded wash, or washing rain): fitted to its own
    logged output, or the station's recorded model until its own has enough days. While the live model is
    still collecting days it answers 404 with detail "soiling_collecting" and the progress:
    {"detail", "clean_event": "wash"|"rain"|null, "clean_date": YYYY-MM-DD|null, "logged_days_since_clean",
    "days_needed"}. 503 weather_unavailable when the sunlight data can't be fetched.
    """
    service: SiteSoilingService = request.app.state.site_soiling
    try:
        soiling, _weather = await service.soiling(site, now)
    except SoilingCollectingError as exc:
        clean = exc.collecting.clean
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": "soiling_collecting",
                "clean_event": clean.kind if clean else None,
                "clean_date": clean.day.isoformat() if clean else None,
                "logged_days_since_clean": exc.collecting.fit_days,
                "days_needed": MIN_FIT_DAYS,
            },
        )
    except WeatherUnavailable:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="weather_unavailable") from None
    except DatasetUnavailable:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="data_unavailable") from None
    return soiling


@router.get("/rain", response_model=RainForecastOut)
async def get_rain_forecast(request: Request) -> RainForecastOut:
    """Days until rain heavy enough to wash the panels (Lahore forecast)."""
    service: RainForecastService = request.app.state.rain_forecast
    try:
        return await service.forecast(utc_now().astimezone(PKT_TZ).date())
    except RainUnavailable:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="rain_forecast_unavailable") from None
