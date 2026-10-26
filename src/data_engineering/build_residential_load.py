"""
build_residential_load.py
=========================
SolarSense EMS — Residential Load Synthesis for Lahore & Urban Pakistan

Synthesizes an authentic, weather-correlated residential electrical demand profile
for a typical urban Pakistani household (5 kW – 10 kW sanctioned load)
operating under LESCO / NEPRA A-1 Residential Time-of-Use (ToU) tariff.

Physical & Demographic Characteristics:
  - Base load (continuous): 0.35–0.65 kW (refrigeration, Wi-Fi router, standby electronics)
  - Morning prep (06:30–09:00): 1.8–3.5 kW (water booster pump 1HP, kettle, toaster, geyser)
  - Daytime unoccupied / light (09:00–17:00): 1.0–2.8 kW (intermittent 1 AC in summer or passive)
  - Evening peak (17:00–22:00): 3.5–7.2 kW (lighting, fans, multiple 1.5-ton inverter ACs, TV, kitchen)
  - Night sleep (22:00–06:30): 1.5–4.0 kW in summer (bedroom AC cycling), 0.5–1.0 kW in winter
  - Temperature sensitivity: AC cooling demand scales above 26°C; water heating/space heat below 16°C
  - Monsoon humidity adder (July–August): additional compressor run-time for dehumidification

Date range: 2025-07-01 → 2026-10-07 (464 days × 24 hours = 11,136 rows)

Output:
  data/processed/residential_load/lahore_residential_load_hourly.csv
"""

from __future__ import annotations

import os
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
OUT_DIR = BASE / "data/processed/residential_load"
OUT_FILE = OUT_DIR / "lahore_residential_load_hourly.csv"
WEATHER_FILE = BASE / "data/processed/weather/lahore_historical_weather_hourly.csv"


def build_residential_load_profile(
    timestamps: pd.DatetimeIndex,
    weather_df: pd.DataFrame | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Build realistic hourly residential electricity load in kW for each timestamp,
    correlated with Lahore ambient temperature and diurnal residential routines.
    """
    rng = np.random.default_rng(seed)
    
    # Map temperature if weather data is available
    temp_map = {}
    if weather_df is not None and "temp_c" in weather_df.columns:
        w_ts = pd.to_datetime(weather_df["timestamp"]).dt.tz_localize(None)
        temp_map = dict(zip(w_ts, weather_df["temp_c"].astype(float)))

    loads = []
    tariff_windows = []
    base_rates = []

    for ts in timestamps:
        ts_naive = ts.tz_localize(None) if ts.tzinfo is not None else ts
        hour = ts.hour
        month = ts.month
        weekday = ts.weekday()  # 0=Mon, 4=Fri, 6=Sun
        temp_c = temp_map.get(ts_naive, 28.0)

        # ── 1. Base Load (always-on appliances) ──
        base = rng.uniform(0.38, 0.55)

        # ── 2. Time-of-Day Activity Pattern ──
        if 6 <= hour < 9:
            # Morning routine: water pump (0.75-1.0 kW), breakfast, geyser
            activity = rng.uniform(1.2, 2.2)
        elif 9 <= hour < 14:
            # Daytime work/school: moderate load
            activity = rng.uniform(0.5, 1.2)
        elif 14 <= hour < 17:
            # Afternoon return / rest: 1 AC or fans
            activity = rng.uniform(0.8, 1.8)
        elif 17 <= hour < 22:
            # Evening Family Peak: all rooms active, dinner, lighting, TV
            activity = rng.uniform(2.2, 3.8)
        elif 22 <= hour or hour < 6:
            # Night rest
            activity = rng.uniform(0.2, 0.6)
        else:
            activity = 0.5

        # ── 3. Weather & Climate Thermal Load ──
        thermal_load = 0.0
        if temp_c > 26.0:
            # Summer cooling: 1.5-ton inverter AC draws 0.8–1.8 kW depending on delta-T
            cooling_factor = min(2.5, (temp_c - 26.0) * 0.12)
            if 13 <= hour <= 23 or 0 <= hour <= 6:
                thermal_load = cooling_factor * rng.uniform(1.2, 2.0)
            else:
                thermal_load = cooling_factor * rng.uniform(0.5, 1.0)
        elif temp_c < 16.0:
            # Winter heating / electric geyser boost
            heating_factor = (16.0 - temp_c) * 0.10
            if 6 <= hour <= 9 or 18 <= hour <= 22:
                thermal_load = heating_factor * rng.uniform(1.0, 1.8)
            else:
                thermal_load = heating_factor * rng.uniform(0.2, 0.5)

        # ── 4. Weekend / Friday Adjustments ──
        if weekday == 6:  # Sunday (family at home all day)
            if 9 <= hour < 17:
                activity *= 1.35
        elif weekday == 4:  # Friday (afternoon prayers / early family gathering)
            if 13 <= hour < 16:
                activity *= 1.25

        # ── 5. Total Demand Calculation ──
        total_kw = base + activity + thermal_load
        
        # Add realistic ±4% stochastic fluctuation (refrigerator compressor cycling)
        total_kw *= rng.uniform(0.96, 1.04)
        
        # Enforce realistic residential bounds (0.4 kW min, 8.5 kW maximum household spike)
        total_kw = max(0.40, min(8.50, float(total_kw)))
        loads.append(round(total_kw, 3))

        # ── 6. LESCO Residential A-1 ToU Tariff Assignment ──
        # Official 4-hour seasonal peak window in Pakistan:
        # Dec-Feb: 17:00-21:00; Jun-Aug: 19:00-23:00; Mar-May & Sep-Nov: 18:00-22:00
        if month in (12, 1, 2):
            is_peak = (17 <= hour < 21)
        elif month in (6, 7, 8):
            is_peak = (19 <= hour < 23)
        else:
            is_peak = (18 <= hour < 22)

        if is_peak:
            tariff_windows.append("peak")
            base_rates.append(46.85)  # LESCO A-1 ToU Peak base rate PKR/kWh
        else:
            tariff_windows.append("off_peak")
            base_rates.append(34.53)  # LESCO A-1 ToU Off-peak base rate PKR/kWh

    df = pd.DataFrame({
        "timestamp": timestamps,
        "residential_load_kw": loads,
        "tariff_window": tariff_windows,
        "tariff_rate_pkr": base_rates,
    })
    df["electricity_cost_pkr"] = (df["residential_load_kw"] * df["tariff_rate_pkr"]).round(2)
    return df


def main():
    print("=" * 60)
    print("SolarSense EMS — Phase 1 Step 4: Residential Load Profile")
    print("=" * 60)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 11,136 continuous hourly timestamps matching project spine
    timestamps = pd.date_range(
        start="2025-07-01 00:00:00",
        end="2026-10-07 23:00:00",
        freq="h",
    )

    weather_df = None
    if WEATHER_FILE.exists():
        weather_df = pd.read_csv(WEATHER_FILE)
        print(f"  ✓ Weather file loaded: {len(weather_df):,} rows")

    print("\n[1/2] Synthesizing calibrated residential load profile...")
    df = build_residential_load_profile(timestamps, weather_df=weather_df, seed=42)

    print("\n[2/2] Summary Statistics:")
    print(f"  Total records       : {len(df):,} hours (464 days)")
    print(f"  Mean demand         : {df['residential_load_kw'].mean():.2f} kW")
    print(f"  Min demand (night)  : {df['residential_load_kw'].min():.2f} kW")
    print(f"  Max demand (peak)   : {df['residential_load_kw'].max():.2f} kW")
    print(f"  Daily average energy: {df['residential_load_kw'].sum() / 464:.1f} kWh/day")
    print(f"  Peak window hours   : {(df['tariff_window'] == 'peak').sum():,} hours")

    df.to_csv(OUT_FILE, index=False)
    print(f"\n✅ Saved clean residential load profile to:\n   {OUT_FILE}\n")
    return df


if __name__ == "__main__":
    main()
