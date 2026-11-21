"""
SolarSense EMS — Open-Meteo Weather & Air Quality Client for Lahore, Pakistan
Coordinates: 31.5204° N, 74.3587° E
No API key required (Free open-access endpoints).
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import date, datetime
from typing import Any, Dict

import httpx

from src.forecast.live_forecast import WEATHER_VARIABLES

LAHORE_LAT = 31.5204
LAHORE_LON = 74.3587
TIMEZONE = "Asia/Karachi"

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_lahore_forecast(forecast_days: int = 3) -> pd.DataFrame:
    """
    Fetches hourly solar irradiance, temperature, wind, and rain forecast for Lahore.
    """
    params = {
        "latitude": LAHORE_LAT,
        "longitude": LAHORE_LON,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "precipitation_probability",
            "cloud_cover",
            "shortwave_radiation",        # Global Horizontal Irradiance (GHI)
            "direct_normal_irradiance",   # DNI
            "global_tilted_irradiance",   # POA / Tilted solar plane
            "wind_speed_10m"
        ],
        "timezone": TIMEZONE,
        "forecast_days": forecast_days
    }

    resp = requests.get(FORECAST_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()["hourly"]

    df = pd.DataFrame(data)
    df["time"] = pd.to_datetime(df["time"])
    return df


async def fetch_lahore_day_forecast(client: httpx.AsyncClient, day: date) -> Dict[str, Any]:
    """
    Open-Meteo hourly forecast for one local day, with the variables and units the forecasters were
    trained on (src/forecast/fetch_lahore_weather.py: same variables from the archive API, wind in m/s).
    """
    params = {
        "latitude": LAHORE_LAT,
        "longitude": LAHORE_LON,
        "hourly": ",".join(WEATHER_VARIABLES),
        "timezone": TIMEZONE,
        "wind_speed_unit": "ms",
        "start_date": day.isoformat(),
        "end_date": day.isoformat(),
    }
    resp = await client.get(FORECAST_URL, params=params, timeout=10.0)
    resp.raise_for_status()
    return resp.json()


async def fetch_lahore_daily_rain(client: httpx.AsyncClient, forecast_days: int = 16) -> Dict[str, Any]:
    """Open-Meteo daily precipitation totals (mm) for Lahore, starting today."""
    params = {
        "latitude": LAHORE_LAT,
        "longitude": LAHORE_LON,
        "daily": "precipitation_sum",
        "timezone": TIMEZONE,
        "forecast_days": forecast_days,
    }
    resp = await client.get(FORECAST_URL, params=params, timeout=10.0)
    resp.raise_for_status()
    return resp.json()


async def fetch_lahore_recent_weather(
    client: httpx.AsyncClient, past_days: int, forecast_days: int
) -> Dict[str, Any]:
    """
    Open-Meteo hourly GHI (W/m2) and daily precipitation (mm) for Lahore, from `past_days` before today
    (modelled from observations) through `forecast_days` from today (forecast). Local days, Asia/Karachi.
    """
    params = {
        "latitude": LAHORE_LAT,
        "longitude": LAHORE_LON,
        "hourly": "shortwave_radiation",
        "daily": "precipitation_sum",
        "timezone": TIMEZONE,
        "past_days": past_days,
        "forecast_days": forecast_days,
    }
    resp = await client.get(FORECAST_URL, params=params, timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def fetch_lahore_air_quality(forecast_days: int = 3) -> pd.DataFrame:
    """
    Fetches particulate matter (PM10, PM2.5) and dust concentration for Lahore smog tracking.
    """
    params = {
        "latitude": LAHORE_LAT,
        "longitude": LAHORE_LON,
        "hourly": [
            "pm10",
            "pm2_5",
            "dust",
            "aerosol_optical_depth"
        ],
        "timezone": TIMEZONE,
        "forecast_days": forecast_days
    }

    resp = requests.get(AIR_QUALITY_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()["hourly"]

    df = pd.DataFrame(data)
    df["time"] = pd.to_datetime(df["time"])
    return df


def get_combined_lahore_stream(forecast_days: int = 3) -> pd.DataFrame:
    """
    Combines meteorological and air quality forecasts into a unified dataframe.
    """
    df_weather = fetch_lahore_forecast(forecast_days)
    df_aq = fetch_lahore_air_quality(forecast_days)
    combined = pd.merge(df_weather, df_aq, on="time", how="inner")
    return combined


if __name__ == "__main__":
    print("[FETCH] Querying live Lahore weather and smog data from Open-Meteo...")
    df = get_combined_lahore_stream(forecast_days=2)
    print(f"[SUCCESS] Received {len(df)} hourly forecast steps.")
    print("\nNext 12 Hours Forecast in Lahore:")
    cols_to_show = ["time", "temperature_2m", "shortwave_radiation", "precipitation", "pm2_5", "dust"]
    print(df[cols_to_show].head(12).to_string(index=False))
