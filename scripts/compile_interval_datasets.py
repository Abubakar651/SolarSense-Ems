"""
compile_interval_datasets.py
=============================
Compiles and validates unified master columnar datasets (Parquet + CSV)
for both 5-minute and hourly interval telemetry from Station LHR-RES-01 (904-A JT).

Outputs:
- data/5min_interval/master_sems_5min.parquet
- data/5min_interval/master_sems_5min.csv
- data/hourly_interval/master_sems_hourly.parquet
- data/hourly_interval/master_sems_hourly.csv
"""

from __future__ import annotations

import glob
from pathlib import Path
import polars as pl
import numpy as np

BASE_DIR = Path(__file__).resolve().parents[1]
DIR_5MIN = BASE_DIR / "data/5min_interval"
DIR_HOURLY = BASE_DIR / "data/hourly_interval"


def compile_5min_dataset() -> pl.DataFrame:
    """Concatenates all daily 5-minute SEMS+ CSV files into a unified master dataset."""
    pattern = str(DIR_5MIN / "daily" / "sems_5min_*.csv")
    files = sorted(glob.glob(pattern))
    if not files:
        print("⚠️ No daily 5-minute files found to compile.")
        return pl.DataFrame()

    print(f"📦 Compiling {len(files)} daily 5-minute telemetry files...")
    
    # Read and concatenate
    dfs = []
    for f in files:
        df_day = pl.read_csv(f)
        if df_day.height > 0:
            dfs.append(df_day)
            
    if not dfs:
        return pl.DataFrame()

    master_5m = pl.concat(dfs).sort("timestamp").unique(subset=["timestamp"]).rechunk()
    
    # Cast types and enforce contiguous Arrow layout
    master_5m = master_5m.with_columns([
        pl.col("timestamp").str.strptime(pl.Datetime(time_unit="ms"), "%Y-%m-%d %H:%M:%S").dt.replace_time_zone("Asia/Karachi"),
        pl.col("date").cast(pl.String),
        pl.col("time").cast(pl.String),
        pl.col("pv_kw").cast(pl.Float64),
        pl.col("load_kw").cast(pl.Float64),
        pl.col("battery_kw").cast(pl.Float64),
        pl.col("grid_kw").cast(pl.Float64),
        pl.col("battery_soc_pct").cast(pl.Float64),
    ])

    out_parquet = DIR_5MIN / "master_sems_5min.parquet"
    out_csv = DIR_5MIN / "master_sems_5min.csv"
    master_5m.write_parquet(out_parquet, compression="zstd")
    master_5m.write_csv(out_csv)

    print(f"✅ 5-Minute Master Dataset Compiled:")
    print(f"   • Total Rows:     {master_5m.height:,} points")
    print(f"   • Unique Dates:   {master_5m['date'].n_unique():,} days")
    print(f"   • Timestamp Span: {master_5m['timestamp'].min()} ──► {master_5m['timestamp'].max()}")
    print(f"   • Parquet File:   {out_parquet} ({out_parquet.stat().st_size / 1024:.1f} KB)")
    print(f"   • CSV File:       {out_csv} ({out_csv.stat().st_size / (1024*1024):.1f} MB)")
    return master_5m


def compile_hourly_dataset() -> pl.DataFrame:
    """Concatenates all daily hourly SEMS+ CSV files into a unified master dataset."""
    pattern = str(DIR_HOURLY / "daily" / "sems_hourly_*.csv")
    files = sorted(glob.glob(pattern))
    if not files:
        print("⚠️ No daily hourly files found to compile.")
        return pl.DataFrame()

    print(f"📦 Compiling {len(files)} daily hourly telemetry files...")
    
    dfs = []
    for f in files:
        df_day = pl.read_csv(f)
        if df_day.height > 0:
            dfs.append(df_day)
            
    if not dfs:
        return pl.DataFrame()

    master_h = pl.concat(dfs).sort("timestamp").unique(subset=["timestamp"]).rechunk()
    
    master_h = master_h.with_columns([
        pl.col("timestamp").str.strptime(pl.Datetime(time_unit="ms"), "%Y-%m-%d %H:%M:%S").dt.replace_time_zone("Asia/Karachi"),
        pl.col("date").cast(pl.String),
        pl.col("time").cast(pl.String),
        pl.col("pv_kw").cast(pl.Float64),
        pl.col("load_kw").cast(pl.Float64),
        pl.col("battery_kw").cast(pl.Float64),
        pl.col("grid_kw").cast(pl.Float64),
        pl.col("battery_soc_pct").cast(pl.Float64),
    ])

    out_parquet = DIR_HOURLY / "master_sems_hourly.parquet"
    out_csv = DIR_HOURLY / "master_sems_hourly.csv"
    master_h.write_parquet(out_parquet, compression="zstd")
    master_h.write_csv(out_csv)

    print(f"✅ Hourly Master Telemetry Dataset Compiled:")
    print(f"   • Total Rows:     {master_h.height:,} hours")
    print(f"   • Unique Dates:   {master_h['date'].n_unique():,} days")
    print(f"   • Timestamp Span: {master_h['timestamp'].min()} ──► {master_h['timestamp'].max()}")
    print(f"   • Parquet File:   {out_parquet} ({out_parquet.stat().st_size / 1024:.1f} KB)")
    print(f"   • CSV File:       {out_csv} ({out_csv.stat().st_size / 1024:.1f} KB)")
    return master_h


if __name__ == "__main__":
    compile_hourly_dataset()
    compile_5min_dataset()

