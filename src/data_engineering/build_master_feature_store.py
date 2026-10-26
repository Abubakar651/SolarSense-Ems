"""
build_master_feature_store.py
=============================
SolarSense EMS — Phase 1 Step 5

Merges all silver-tier processed tables into the unified Gold-layer
Master EMS Feature Store.

Step 0 (new): runs repair_master_dataset.run_repair() — fixes nighttime phantom solar in the
5-min telemetry and reconstructs hourly PV for all 464 days, anchored to the daily portal log.
`solar_energy_kwh` is therefore complete (11,136 rows) and `solar_source` records provenance
('measured_5min' | 'reconstructed').

Input tables (all on hourly timestamp index):
  1. goodwe_lahore_hourly.csv       — Solar generation telemetry (39 high-res days)
  2. goodwe_lahore_daily.csv        — 464-day daily generation history
  3. lahore_historical_weather_hourly.csv — GHI, Temp, Rain, Wind
  4. soiling_analysis_lahore.csv    — Performance Ratio, Soiling Loss, Wash Events
  5. lahore_industrial_load_hourly.csv    — Factory demand profile
  6. lesco_johar_town_outages.csv   — Grid outage events (binary flag)

Output:
  data/processed/master_ems_timeseries.csv

Schema (one row per hour, 11,136 rows total):
  timestamp, date, hour, weekday, month,
  ghi_wm2, dni_wm2, dhi_wm2, temp_c, rain_mm, wind_ms,
  solar_energy_kwh, solar_peak_kw,              ← from 5-min data (39 days)
  generation_kwh_daily,                          ← from 464-day history
  e_clean_kwh_daily, performance_ratio, soiling_derate_pct, soiling_loss_kwh,
  soiling_loss_pkr, event_type, days_since_last_wash,
  battery_charged_kwh, battery_discharged_kwh,
  factory_load_kw, tariff_window, tariff_rate_pkr, electricity_cost_pkr,
  outage_flag, outage_energy_kwh,
  net_power_kw,                                  ← solar - load (positive = export)
  solar_cover_pct                                ← solar / load × 100
"""

import os
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

try:  # `python -m src.data_engineering.build_master_feature_store`
    from src.data_engineering.repair_master_dataset import run_repair, verify_master
except ImportError:  # `python src/data_engineering/build_master_feature_store.py`
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from src.data_engineering.repair_master_dataset import run_repair, verify_master

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

PATHS = {
    "hourly_5min": os.path.join(BASE, "data/processed/solar_timeseries/goodwe_lahore_hourly.csv"),
    "reconstructed": os.path.join(BASE, "data/processed/solar_timeseries/goodwe_lahore_hourly_reconstructed.csv"),
    "daily":       os.path.join(BASE, "data/processed/solar_timeseries/goodwe_lahore_daily.csv"),
    "weather":     os.path.join(BASE, "data/processed/weather/lahore_historical_weather_hourly.csv"),
    "soiling":     os.path.join(BASE, "data/processed/soiling/soiling_analysis_lahore.csv"),
    "residential": os.path.join(BASE, "data/processed/residential_load/lahore_residential_load_hourly.csv"),
    "outages":     os.path.join(BASE, "data/processed/grid_outages/lesco_johar_town_outages.csv"),
}
OUT_FILE = os.path.join(BASE, "data/processed/master_ems_timeseries.csv")
PARQUET_CACHE = os.path.join(BASE, "data/processed/master_ems_timeseries.parquet")


def load_all_tables() -> dict:
    tables = {}
    for name, path in PATHS.items():
        if os.path.exists(path):
            tables[name] = pd.read_csv(path)
            print(f"  ✓ Loaded {name:<15} → {len(tables[name]):>6,} rows  [{os.path.basename(path)}]")
        else:
            print(f"  ✗ Missing: {path}")
            tables[name] = pd.DataFrame()
    return tables


def main():
    print("=" * 60)
    print("SolarSense EMS — Phase 1 Step 5: Master Feature Store")
    print("=" * 60)

    print("\n[0/6] Forensic repair + weather-anchored PV reconstruction...")
    run_repair(verbose=True)

    print("\n[1/6] Loading all silver-tier tables...")
    T = load_all_tables()

    # ── Establish master hourly timestamp spine ──
    print("\n[2/6] Building master hourly timestamp spine...")
    master_ts = pd.date_range(
        start="2025-07-01 00:00",
        end  ="2026-10-07 23:00",
        freq ="h"
    )
    df = pd.DataFrame({"timestamp": master_ts})
    df["date"]    = df["timestamp"].dt.date.astype(str)
    df["hour"]    = df["timestamp"].dt.hour
    df["weekday"] = df["timestamp"].dt.weekday     # 0=Mon, 6=Sun
    df["month"]   = df["timestamp"].dt.month
    df["year"]    = df["timestamp"].dt.year
    print(f"  Spine: {len(df):,} hourly rows | {df['date'].iloc[0]} → {df['date'].iloc[-1]}")

    # ── Merge 1: Weather (hourly) ──
    print("\n[3/6] Merging weather data...")
    wx = T["weather"].copy()
    if len(wx):
        wx["timestamp"] = pd.to_datetime(wx["timestamp"])
        wx_cols = ["timestamp", "ghi_wm2", "dni_wm2", "dhi_wm2", "temp_c",
                   "rain_mm", "wind_ms", "humidity_pct", "ghi_kwh_m2",
                   "is_daytime", "rain_event"]
        wx_cols = [c for c in wx_cols if c in wx.columns]
        df = df.merge(wx[wx_cols], on="timestamp", how="left")
        print(f"  → Weather merged: {df['ghi_wm2'].notna().sum():,} non-null GHI values")

    # ── Merge 2: Residential load (hourly) ──
    print("\n[4/6] Merging residential load profile...")
    rl = T.get("residential", pd.DataFrame()).copy()
    if len(rl):
        rl["timestamp"] = pd.to_datetime(rl["timestamp"])
        rl_cols = ["timestamp", "residential_load_kw", "tariff_window",
                   "tariff_rate_pkr", "electricity_cost_pkr"]
        rl_cols = [c for c in rl_cols if c in rl.columns]
        df = df.merge(rl[rl_cols], on="timestamp", how="left")
        # Backwards-compatible alias for existing endpoints
        df["factory_load_kw"] = df["residential_load_kw"]
        print(f"  → Residential load merged: mean {df['residential_load_kw'].mean():.2f} kW (peak {df['residential_load_kw'].max():.2f} kW)")

    # ── Merge 3: High-resolution 5-min aggregated hourly solar data ──
    print("\n[5/6] Merging GoodWe 5-min solar telemetry (39 days)...")
    hr = T["hourly_5min"].copy()
    if len(hr):
        hr["timestamp"] = pd.to_datetime(hr["timestamp"])
        hr_cols = ["timestamp", "solar_energy_kwh", "solar_peak_kw",
                   "bat_discharged_kwh", "bat_charged_kwh",
                   "battery_soc_mean", "battery_soc_min"]
        hr_cols = [c for c in hr_cols if c in hr.columns]
        df = df.merge(hr[hr_cols], on="timestamp", how="left")
        print(f"  → 5-min telemetry merged: {df['solar_energy_kwh'].notna().sum():,} non-null hourly solar records")

    # Replace the 39-day telemetry-only solar column with the 464-day anchored reconstruction
    rec = T["reconstructed"].copy()
    if len(rec):
        rec["timestamp"] = pd.to_datetime(rec["timestamp"])
        df = df.drop(columns=["solar_energy_kwh", "solar_peak_kw"], errors="ignore").merge(
            rec[["timestamp", "solar_energy_kwh", "solar_peak_kw", "solar_source"]],
            on="timestamp", how="left")
        print(f"  → Reconstructed PV merged: {df['solar_energy_kwh'].notna().sum():,} non-null hourly solar records "
              f"({(df['solar_source'] == 'reconstructed').sum():,} reconstructed hours)")

    # ── Merge 4: Daily soiling analysis ──
    print("\n[6/6] Merging soiling analysis and 464-day generation history...")
    soil = T["soiling"].copy()
    if len(soil):
        soil["date"] = pd.to_datetime(soil["date"]).dt.date.astype(str)
        soil_cols = ["date", "generation_kwh", "battery_charged_kwh",
                     "battery_discharged_kwh", "e_clean_kwh", "performance_ratio",
                     "soiling_derate_pct", "soiling_loss_kwh", "soiling_loss_pkr",
                     "event_type", "days_since_last_wash", "soiling_model_pr",
                     "ghi_kwh_m2_daily", "temp_c_mean", "temp_c_max", "rain_mm_total"]
        soil_cols = [c for c in soil_cols if c in soil.columns]
        df = df.merge(soil[soil_cols], on="date", how="left")
        # Rename to clarify daily vs hourly
        df.rename(columns={
            "generation_kwh":          "generation_kwh_daily",
            "battery_charged_kwh":     "battery_charged_kwh_daily",
            "battery_discharged_kwh":  "battery_discharged_kwh_daily",
        }, inplace=True)
        print(f"  → Soiling/daily history merged: {df['generation_kwh_daily'].notna().sum():,} non-null daily gen records")

    # ── Build outage flag (hourly) ──
    out = T["outages"].copy()
    df["outage_flag"]      = 0
    df["outage_energy_kwh"]= 0.0
    if len(out):
        out["date"] = out["date"].astype(str)
        for _, ev in out.iterrows():
            try:
                ev_start = pd.Timestamp(f"{ev['date']} {ev['start_time']}")
                ev_end   = pd.Timestamp(f"{ev['date']} {ev['end_time']}")
                mask = (df["timestamp"] >= ev_start) & (df["timestamp"] <= ev_end)
                df.loc[mask, "outage_flag"]       = 1
                df.loc[mask, "outage_energy_kwh"] = float(ev.get("energy_kwh", 0)) / max(mask.sum(), 1)
            except Exception:
                continue
        print(f"  → Outage flags: {df['outage_flag'].sum()} flagged hours across 464 days")

    # ── Derived EMS columns ──
    # Net power: positive = solar exports to grid / charges battery
    #            negative = factory drawing from grid
    # Use hourly solar if available, otherwise distribute daily evenly across daylight hours
    df["solar_kwh_for_net"] = df["solar_energy_kwh"].fillna(
        pd.Series(np.where(df["generation_kwh_daily"].notna() & (df["is_daytime"] == 1),
                           df["generation_kwh_daily"] / 10.0, 0.0), index=df.index)
    )
    df["net_power_kw"]    = (df["solar_kwh_for_net"] - df["residential_load_kw"]).round(3)
    df["solar_cover_pct"] = np.where(
        df["residential_load_kw"] > 0,
        (df["solar_kwh_for_net"] / df["residential_load_kw"] * 100).clip(0, 500),
        0.0
    ).round(1)

    # ── Final column ordering ──
    ordered_cols = [
        "timestamp", "date", "hour", "weekday", "month", "year",
        # Weather
        "ghi_wm2", "dni_wm2", "dhi_wm2", "temp_c", "rain_mm", "wind_ms",
        "humidity_pct", "ghi_kwh_m2", "is_daytime", "rain_event",
        # Solar (hourly telemetry — 39 high-res days)
        "solar_energy_kwh", "solar_peak_kw", "solar_source",
        "bat_discharged_kwh", "bat_charged_kwh",
        "battery_soc_mean", "battery_soc_min",
        # Solar (daily macro — 464 days)
        "generation_kwh_daily", "battery_charged_kwh_daily", "battery_discharged_kwh_daily",
        # Soiling physics
        "e_clean_kwh", "performance_ratio", "soiling_derate_pct",
        "soiling_loss_kwh", "soiling_loss_pkr", "soiling_model_pr",
        "event_type", "days_since_last_wash",
        "ghi_kwh_m2_daily", "temp_c_mean", "temp_c_max", "rain_mm_total",
        # Residential demand (primary) and backward-compatible alias
        "residential_load_kw", "factory_load_kw", "tariff_window", "tariff_rate_pkr", "electricity_cost_pkr",
        # Grid
        "outage_flag", "outage_energy_kwh",
        # EMS derived
        "net_power_kw", "solar_cover_pct",
    ]
    ordered_cols = [c for c in ordered_cols if c in df.columns]
    df = df[ordered_cols]

    # ── Save ──
    df.to_csv(OUT_FILE, index=False)
    if os.path.exists(PARQUET_CACHE):  # derived cache of the previous CSV; EMSDataRepository recompiles it
        os.remove(PARQUET_CACHE)
        print("  ↻ Invalidated stale master_ems_timeseries.parquet cache")

    # ── Validation Report ──
    print("\n" + "═" * 60)
    print("  MASTER FEATURE STORE — VALIDATION REPORT")
    print("═" * 60)
    print(f"  Rows          : {len(df):,} hourly records")
    print(f"  Columns       : {len(df.columns)}")
    print(f"  Date range    : {df['date'].iloc[0]} → {df['date'].iloc[-1]}")
    print(f"  Timestamp gaps: {(df['timestamp'].diff().dt.total_seconds().dropna() != 3600).sum()} (expect 0)")
    print(f"\n  Solar Coverage:")
    print(f"    High-res 5-min telemetry  : {df['solar_energy_kwh'].notna().sum():,} hours ({df['solar_energy_kwh'].notna().sum()/len(df)*100:.1f}%)")
    print(f"    464-day daily history     : {df['generation_kwh_daily'].notna().sum():,} hours ({df['generation_kwh_daily'].notna().sum()/len(df)*100:.1f}%)")
    print(f"  Weather coverage            : {df['ghi_wm2'].notna().sum():,} hours ({df['ghi_wm2'].notna().sum()/len(df)*100:.1f}%)")
    print(f"  Residential load coverage   : {df['residential_load_kw'].notna().sum():,} hours ({df['residential_load_kw'].notna().sum()/len(df)*100:.1f}%)")
    print(f"  Soiling data coverage       : {df['performance_ratio'].notna().sum():,} days")
    print(f"  Grid outage flagged hours   : {df['outage_flag'].sum()}")
    print(f"\n  Energy Totals (464-day history):")
    total_gen  = df.groupby("date")["generation_kwh_daily"].first().sum()
    total_load = df["residential_load_kw"].sum()  # kWh
    print(f"    Total Solar Generated   : {total_gen:.1f} kWh  ({total_gen/1000:.2f} MWh)")
    print(f"    Total Residential Load  : {total_load:.1f} kWh ({total_load/1000:.2f} MWh)")
    print(f"    Solar Self-Coverage     : {total_gen / total_load * 100:.1f}% of residential demand")
    audit = verify_master(OUT_FILE)
    print(f"\n  Physics audit (master CSV):")
    print(f"    Solar nulls                 : {audit['solar_nulls']:.0f} (expect 0)")
    print(f"    Night rows with solar > 0   : {audit['night_rows_with_solar']:.0f} (expect 0)")
    print(f"    Max hourly solar            : {audit['max_hourly_kw']:.3f} kW")
    print(f"    Max |daily sum - portal log|: {audit['max_abs_daily_err_kwh']:.2e} kWh")
    print(f"\n  ✓ Saved → {OUT_FILE}")
    print("\n✅ Step 5 complete — Phase 1 DONE!\n")

    return df


if __name__ == "__main__":
    main()
