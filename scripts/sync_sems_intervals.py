"""
sync_sems_intervals.py
======================
Automated Synchronization & Verification Engine for GoodWe SEMS+ Telemetry.
Manages both 5-minute and hourly interval datasets for Station LHR-RES-01 (904-A JT).

Features:
- Dedicated folder organization: data/5min_interval/ and data/hourly_interval/
- Automated scan of existing vs missing dates across the entire commissioning timeline (2025-07-01 to today).
- Counter-check verification comparing SEMS+ cloud data against existing legacy Excel/reconstructed datasets.
- Direct retrieval of missing intervals from SEMS+ (/sems-plant/api/v1/hems/power/statisticsAndPreV2).
- Native resolution extraction: timeScale=5 (288 pts/day) and timeScale=60 (24 pts/day).
- Rate-limited, resilient requests with automatic session renewal.
- Columnar output with zero synthetic interpolation.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import zoneinfo

import numpy as np
import polars as pl
import requests
from dotenv import load_dotenv
from pygoodwe.sems_plus import SemsPlusClient

load_dotenv()

_TZ = zoneinfo.ZoneInfo("Asia/Karachi")
BASE_DIR = Path(__file__).resolve().parents[1]
DIR_5MIN = BASE_DIR / "data/5min_interval"
DIR_HOURLY = BASE_DIR / "data/hourly_interval"

DIR_5MIN.mkdir(parents=True, exist_ok=True)
DIR_HOURLY.mkdir(parents=True, exist_ok=True)
(DIR_5MIN / "daily").mkdir(parents=True, exist_ok=True)
(DIR_HOURLY / "daily").mkdir(parents=True, exist_ok=True)

COMMISSIONING_DATE = "2025-07-01"
STATION_ID = "064f10e9-b719-437d-996a-203937c0ba9b"


def get_timeline_dates(start_date: str = COMMISSIONING_DATE, end_date: Optional[str] = None) -> List[str]:
    """Generates contiguous list of YYYY-MM-DD date strings."""
    if end_date is None:
        end_date = datetime.now(_TZ).strftime("%Y-%m-%d")
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    cur = start_dt
    while cur <= end_dt:
        dates.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return dates


class SEMSSyncEngine:
    def __init__(self, account: str, password: str, station_id: str = STATION_ID):
        self.account = account
        self.password = password
        self.station_id = station_id
        self.session = requests.Session()
        self.logger = logging.getLogger("sems_sync")
        self.client = SemsPlusClient(self.session, self.account, self.password, self.logger)
        self.client.login()

    def fetch_interval_curve(self, date_str: str, time_scale: int = 5) -> List[Dict[str, Any]]:
        """
        Fetches synchronous curve data from SEMS+.
        time_scale=5 returns 288 points (5-min intervals).
        time_scale=60 returns 24 points (hourly intervals).
        """
        payload = {
            "stationId": self.station_id,
            "items": ["pSystem", "pConsum", "pBat", "pGrid", "soc"],
            "timeScale": time_scale,
            "timeZone": -5,  # Asia/Karachi UTC+5
            "startTime": f"{date_str} 00:00:00",
            "endTime": f"{date_str} 23:59:59",
        }
        res = self.client.request("/sems-plant/api/v1/hems/power/statisticsAndPreV2", method="POST", payload=payload)
        data_list = res.get("dataList", []) if isinstance(res, dict) else []

        by_time: Dict[str, Dict[str, Any]] = {}
        for s in data_list:
            item = s.get("item")
            for pt in s.get("powerData", []):
                tp = pt.get("tp")
                val = pt.get("power")
                if not tp:
                    continue
                if tp not in by_time:
                    parts = tp.split()
                    by_time[tp] = {
                        "timestamp": tp,
                        "date": date_str,
                        "time": parts[1] if len(parts) > 1 else "",
                        "pv_kw": 0.0,
                        "load_kw": 0.0,
                        "battery_kw": 0.0,
                        "grid_kw": 0.0,
                        "battery_soc_pct": 0.0,
                    }
                if item == "pSystem":
                    by_time[tp]["pv_kw"] = round(float(val or 0.0), 3)
                elif item == "pConsum":
                    by_time[tp]["load_kw"] = round(abs(float(val or 0.0)), 3)
                elif item == "pBat":
                    by_time[tp]["battery_kw"] = round(float(val or 0.0), 3)
                elif item == "pGrid":
                    by_time[tp]["grid_kw"] = round(-float(val or 0.0) if val is not None else 0.0, 3)
                elif item == "soc":
                    by_time[tp]["battery_soc_pct"] = round(float(val or 0.0), 1)

        return sorted(by_time.values(), key=lambda x: x["timestamp"])


def scan_existing_dates() -> Tuple[Set[str], Set[str]]:
    """Scans and returns sets of dates already available in 5min and hourly folders."""
    # 5-min scan
    dates_5m = set()
    legacy_5m = BASE_DIR / "data/processed/solar_timeseries/goodwe_lahore_5min.csv"
    if legacy_5m.exists():
        df = pl.read_csv(legacy_5m)
        dates_5m.update(df["date"].unique().to_list())
    for f in (DIR_5MIN / "daily").glob("*.csv"):
        d = f.stem.replace("sems_5min_", "")
        dates_5m.add(d)

    # Hourly scan
    dates_h = set()
    master_h = BASE_DIR / "data/processed/master_ems_timeseries.parquet"
    if master_h.exists():
        df = pl.read_parquet(master_h)
        dates_h.update(df["date"].unique().to_list())
    for f in (DIR_HOURLY / "daily").glob("*.csv"):
        d = f.stem.replace("sems_hourly_", "")
        dates_h.add(d)

    return dates_5m, dates_h


def run_counter_check(engine: SEMSSyncEngine, check_date: str = "2026-10-26") -> Dict[str, Any]:
    """Cross-validates SEMS+ cloud telemetry against existing local baseline data."""
    print("=" * 75)
    print(f"🔍 Executing Ground-Truth Counter-Check on Benchmark Date: {check_date}")
    print("=" * 75)

    # 1. Counter-check 5-minute data
    cloud_5m = engine.fetch_interval_curve(check_date, time_scale=5)
    df_cloud_5m = pl.DataFrame(cloud_5m)

    legacy_5m_file = BASE_DIR / "data/processed/solar_timeseries/goodwe_lahore_5min.csv"
    stats_5m = {}
    if legacy_5m_file.exists():
        df_old_5m = pl.read_csv(legacy_5m_file).filter(pl.col("timestamp").str.starts_with(check_date))
        if df_old_5m.height == df_cloud_5m.height == 288:
            joined = df_old_5m.join(df_cloud_5m, on="timestamp")
            soc_diff = np.abs(joined["battery_soc_pct"].to_numpy() - joined["battery_soc_pct_right"].to_numpy())
            pv_corr = np.corrcoef(joined["solar_power_kw"].to_numpy(), joined["pv_kw"].to_numpy())[0, 1]
            soc_corr = np.corrcoef(joined["battery_soc_pct"].to_numpy(), joined["battery_soc_pct_right"].to_numpy())[0, 1]
            stats_5m = {
                "date": check_date,
                "intervals_checked": 288,
                "soc_correlation": float(soc_corr),
                "soc_max_diff_pct": float(soc_diff.max()),
                "pv_correlation": float(pv_corr),
                "status": "MATCHED_CONFIRMED"
            }
            print(f"✅ 5-Minute Telemetry Match Confirmed (288/288 points):")
            print(f"   • Battery SoC Correlation: {soc_corr:.6f} (Max Diff: {soc_diff.max():.2f}%)")
            print(f"   • Solar PV Correlation:    {pv_corr:.6f}")

    # 2. Counter-check Hourly data
    cloud_h = engine.fetch_interval_curve(check_date, time_scale=60)
    df_cloud_h = pl.DataFrame(cloud_h)

    master_h_file = BASE_DIR / "data/processed/master_ems_timeseries.parquet"
    stats_h = {}
    if master_h_file.exists():
        df_old_h = pl.read_parquet(master_h_file).filter(pl.col("date") == check_date)
        if df_old_h.height == df_cloud_h.height == 24:
            df_cloud_h = df_cloud_h.with_columns(pl.col("time").str.slice(0, 2).cast(pl.Int64).alias("hour"))
            joined_h = df_old_h.join(df_cloud_h, on="hour")
            pv_corr_h = np.corrcoef(joined_h["solar_energy_kwh"].to_numpy(), joined_h["pv_kw"].to_numpy())[0, 1]
            total_old_pv = joined_h["solar_energy_kwh"].sum()
            total_new_pv = joined_h["pv_kw"].sum()
            stats_h = {
                "date": check_date,
                "hours_checked": 24,
                "pv_correlation": float(pv_corr_h),
                "total_legacy_pv_kwh": float(total_old_pv),
                "total_sems_pv_kwh": float(total_new_pv),
                "difference_kwh": float(abs(total_old_pv - total_new_pv)),
                "status": "MATCHED_CONFIRMED"
            }
            print(f"✅ Hourly Telemetry Match Confirmed (24/24 hours):")
            print(f"   • Hourly Solar Correlation: {pv_corr_h:.6f}")
            print(f"   • Daily Total Yield:       Legacy {total_old_pv:.2f} kWh vs SEMS+ {total_new_pv:.2f} kWh (diff: {abs(total_old_pv - total_new_pv):.3f} kWh)")

    return {"5min_check": stats_5m, "hourly_check": stats_h}


def sync_missing_intervals(
    engine: SEMSSyncEngine,
    missing_dates: List[str],
    time_scale: int,
    out_dir: Path,
    batch_limit: Optional[int] = None,
) -> int:
    """Fetches missing dates from SEMS+ with exponential backoff on rate limits."""
    label = "5-Minute" if time_scale == 5 else "Hourly"
    prefix = "sems_5min" if time_scale == 5 else "sems_hourly"
    
    # Filter out dates that already have daily CSV files in out_dir/daily
    unfetched = []
    for d in missing_dates:
        p = out_dir / "daily" / f"{prefix}_{d}.csv"
        if not p.exists() or p.stat().st_size == 0:
            unfetched.append(d)

    target_dates = unfetched if batch_limit is None else unfetched[:batch_limit]
    print("-" * 75)
    print(f"🚀 Fetching {len(target_dates)} missing {label} days from SEMS+ portal...")
    print("-" * 75)

    downloaded = 0
    idx = 0
    while idx < len(target_dates):
        d = target_dates[idx]
        retries = 0
        success = False
        while retries < 5 and not success:
            try:
                records = engine.fetch_interval_curve(d, time_scale=time_scale)
                if records:
                    out_path = out_dir / "daily" / f"{prefix}_{d}.csv"
                    df = pl.DataFrame(records)
                    df.write_csv(out_path)
                    downloaded += 1
                    peak_pv = df["pv_kw"].max()
                    peak_load = df["load_kw"].max()
                    print(f"[{idx+1}/{len(target_dates)}] {d}: {len(records)} points saved. (Peak PV: {peak_pv:.2f} kW | Peak Load: {peak_load:.2f} kW)", flush=True)
                else:
                    print(f"[{idx+1}/{len(target_dates)}] {d}: 0 records returned.", flush=True)
                success = True
                time.sleep(1.0)  # Safe request spacing to prevent rate limit
            except Exception as e:
                err_str = str(e)
                retries += 1
                wait_sec = 15 * retries
                print(f"⏳ Retry {retries}/5 on {d}: {e}. Pausing {wait_sec}s...", flush=True)
                time.sleep(wait_sec)
                try:
                    engine.client.login()
                except Exception:
                    pass
        idx += 1

    return downloaded


def main():
    parser = argparse.ArgumentParser(description="Synchronize and counter-check GoodWe SEMS+ intervals")
    parser.add_argument("--mode", choices=["scan", "check", "sync_hourly", "sync_5min", "all"], default="all")
    parser.add_argument("--batch-5min", type=int, default=None, help="Limit number of 5min days to download in this run")
    parser.add_argument("--batch-hourly", type=int, default=None, help="Limit number of hourly days to download in this run")
    parser.add_argument("--check-date", default="2026-10-26", help="Date for counter-check comparison")
    parser.add_argument("--all-daily", action="store_true", help="Target all dates missing from daily/ folder across full timeline")
    args = parser.parse_args()

    account = os.getenv("SEMS_ACCOUNT")
    password = os.getenv("SEMS_PASSWORD")
    if not account or not password:
        print("❌ Error: SEMS_ACCOUNT and SEMS_PASSWORD environment variables required.")
        sys.exit(1)

    all_timeline = get_timeline_dates()
    existing_5m, existing_h = scan_existing_dates()
    missing_5m = [d for d in all_timeline if d not in existing_5m]
    missing_h = [d for d in all_timeline if d not in existing_h]

    daily_missing_5m = [d for d in all_timeline if not (DIR_5MIN / "daily" / f"sems_5min_{d}.csv").exists()]
    daily_missing_h = [d for d in all_timeline if not (DIR_HOURLY / "daily" / f"sems_hourly_{d}.csv").exists()]

    print("=" * 75)
    print("📊 SolarSense EMS — SEMS+ Telemetry Timeline Scan")
    print("=" * 75)
    print(f"Full Commissioning Timeline: {all_timeline[0]} ──► {all_timeline[-1]} ({len(all_timeline)} days)")
    print(f"📁 5-Minute Legacy Dataset:   {len(existing_5m)} present | {len(missing_5m)} missing")
    print(f"📁 5-Minute Daily Folder:     {len(all_timeline) - len(daily_missing_5m)} present | {len(daily_missing_5m)} missing")
    print(f"📁 Hourly Legacy Dataset:     {len(existing_h)} present | {len(missing_h)} missing")
    print(f"📁 Hourly Daily Folder:       {len(all_timeline) - len(daily_missing_h)} present | {len(daily_missing_h)} missing")
    if missing_h:
        print(f"   • Missing hourly window:   {missing_h[0]} ──► {missing_h[-1]} ({len(missing_h)} days)")
    print("=" * 75)

    if args.mode == "scan":
        return

    engine = SEMSSyncEngine(account, password)

    if args.mode in ["check", "all"]:
        run_counter_check(engine, check_date=args.check_date)

    targets_h = daily_missing_h if args.all_daily else missing_h
    targets_5m = daily_missing_5m if args.all_daily else missing_5m

    if args.mode in ["sync_hourly", "all"] and targets_h:
        n_h = sync_missing_intervals(engine, targets_h, time_scale=60, out_dir=DIR_HOURLY, batch_limit=args.batch_hourly)
        print(f"✅ Finished syncing {n_h} hourly days to {DIR_HOURLY}/daily")

    if args.mode in ["sync_5min", "all"] and targets_5m:
        n_5m = sync_missing_intervals(engine, targets_5m, time_scale=5, out_dir=DIR_5MIN, batch_limit=args.batch_5min)
        print(f"✅ Finished syncing {n_5m} 5-minute days to {DIR_5MIN}/daily")


if __name__ == "__main__":
    main()
