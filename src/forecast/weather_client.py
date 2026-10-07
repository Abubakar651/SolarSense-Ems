"""
SolarSense EMS — Open-Meteo Weather & Air Quality Client for Lahore, Pakistan
Coordinates: 31.5204° N, 74.3587° E
No API key required (Free open-access endpoints).
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

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
