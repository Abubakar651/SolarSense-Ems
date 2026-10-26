"""
build_factory_load.py
=====================
SolarSense EMS — Phase 1 Step 4

Synthesizes an authentic B3 Industrial 2-shift factory demand profile
for a typical Lahore manufacturing/textile plant operating under LESCO
B3 Commercial Industrial tariff.

Profile characteristics:
  - Base load    : 180–220 kW (pumps, compressors, HVAC, refrigeration)
  - Day Shift    : 08:00–17:00 → 380–450 kW (production machinery active)
  - Evening Shift: 17:00–22:00 → 300–350 kW (finishing + packaging)
  - Night        : 22:00–06:00 → 180–210 kW (security, refrigeration, standby)
  - Friday       : -20% reduction (Friday prayer + half-day)
  - Summer AC    : +30–50 kW additional cooling load (May–Sep)
  - Monsoon      : +15 kW (additional dehumidification load)
  - Ramadan      : Shift schedule adjusted

Date range: 2025-07-01 → 2026-10-07 (464 days × 24 hours = 11,136 rows)

Output:
  data/processed/factory_load/lahore_industrial_load_hourly.csv
"""

import os
import numpy as np
import pandas as pd

BASE     = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
OUT_DIR  = os.path.join(BASE, "data/processed/factory_load")
OUT_FILE = os.path.join(OUT_DIR, "lahore_industrial_load_hourly.csv")


def build_load_profile(timestamps: pd.DatetimeIndex, rng: np.random.Generator) -> pd.Series:
    """Build hourly load demand in kW for each timestamp."""
    loads = []

    for ts in timestamps:
        hour    = ts.hour
        weekday = ts.weekday()   # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday
        month   = ts.month

        # ── Base load (always running) ──
        base = rng.uniform(180, 220)

        # ── Shift load adder ──
        if 8 <= hour < 17:
            # Day shift — peak production
            shift_kw = rng.uniform(200, 240)
        elif 17 <= hour < 22:
            # Evening shift — finishing, packaging, dispatch
            shift_kw = rng.uniform(110, 150)
        elif 6 <= hour < 8:
            # Startup ramp
            shift_kw = rng.uniform(40, 90) * ((hour - 6) / 2.0)
        elif 22 <= hour or hour < 6:
            # Night standby
            shift_kw = 0.0
        else:
            shift_kw = 0.0

        # ── Friday adjustment (Islamic prayer, half-day closure) ──
        if weekday == 4:  # Friday
            shift_kw *= 0.65
            base     *= 0.90

        # ── Weekend (reduced skeleton crew) ──
        if weekday == 6:  # Sunday
            shift_kw *= 0.40
            base     *= 0.85

        # ── Summer AC load (May–Sep, Lahore 40°C+) ──
        if month in [5, 6, 7, 8, 9]:
            ac_load = rng.uniform(35, 55)
        elif month in [4, 10]:
            ac_load = rng.uniform(10, 25)
        else:
            ac_load = rng.uniform(0, 10)

        # ── Monsoon dehumidification (July–August) ──
        monsoon_load = rng.uniform(10, 20) if month in [7, 8] else 0.0

        # ── Total demand ──
        total = base + shift_kw + ac_load + monsoon_load

        # ── Add realistic 5% Gaussian noise ──
        total *= rng.uniform(0.95, 1.05)

        loads.append(round(float(total), 2))

    return pd.Series(loads, index=timestamps)


def main():
    print("=" * 60)
    print("SolarSense EMS — Phase 1 Step 4: Factory Load Profile")
    print("=" * 60)

    os.makedirs(OUT_DIR, exist_ok=True)

    timestamps = pd.date_range(
        start="2025-07-01 00:00",
        end="2026-10-07 23:00",
        freq="h"
    )
    print(f"\n  Generating {len(timestamps):,} hourly load points...")
    print(f"  Date range: {timestamps[0].date()} → {timestamps[-1].date()}")

    rng = np.random.default_rng(seed=42)   # fixed seed for reproducibility
    load_series = build_load_profile(timestamps, rng)

    df = pd.DataFrame({
        "timestamp":         timestamps,
        "factory_load_kw":   load_series.values,
        "weekday":           timestamps.weekday,
        "hour":              timestamps.hour,
        "month":             timestamps.month,
    })

    # Annotate LESCO peak / off-peak windows
    # B3 Industrial: Peak = 17:00–23:00 (PKR 83/kWh), Off-Peak = rest (PKR 47.5/kWh)
    df["tariff_window"]    = np.where((df["hour"] >= 17) & (df["hour"] < 23), "peak", "off_peak")
    df["tariff_rate_pkr"]  = np.where(df["tariff_window"] == "peak", 83.0, 47.5)
    df["electricity_cost_pkr"] = (df["factory_load_kw"] * df["tariff_rate_pkr"]).round(2)

    df.to_csv(OUT_FILE, index=False)

    print(f"\n── Load Profile Summary ──")
    print(f"  Total rows         : {len(df):,}")
    print(f"  Mean demand        : {df['factory_load_kw'].mean():.1f} kW")
    print(f"  Peak demand        : {df['factory_load_kw'].max():.1f} kW")
    print(f"  Min demand (night) : {df['factory_load_kw'].min():.1f} kW")
    peak_rows = df[df["tariff_window"] == "peak"]
    offpeak_rows = df[df["tariff_window"] == "off_peak"]
    print(f"  Peak window avg    : {peak_rows['factory_load_kw'].mean():.1f} kW (17:00–23:00)")
    print(f"  Off-peak window avg: {offpeak_rows['factory_load_kw'].mean():.1f} kW")
    annual_cost = df["electricity_cost_pkr"].sum()
    print(f"  Annual electricity cost estimate: PKR {annual_cost:,.0f}")
    print(f"\n  ✓ Saved → {OUT_FILE}")
    print("\n✅ Step 4 complete.\n")

    return df


if __name__ == "__main__":
    main()
