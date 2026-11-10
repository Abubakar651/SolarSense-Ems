"""
GoodWe SEMS Cloud Historical Data Ingestion Engine
=================================================
Automates full-history retrieval of daily energy balances, station yield,
monthly summaries, and telemetry directly from GoodWe's SEMS / SEMS+ cloud platform.

Features:
- Automated multi-region login (semsportal.com -> hk.semsportal.com regional gateway).
- Station auto-discovery (locates Station 904-A JT / SN: 9010KESC253L0146).
- Batch downloads daily station balance from commissioning date (2025-07-01) to today.
- Monthly & yearly macro performance metrics aggregation.
- Exports structured, clean CSV and JSON datasets to data/raw/goodwe_inverter_reports/.
- Zero plaintext password leakage in logs or git commits.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import zoneinfo

import requests
from dotenv import load_dotenv

load_dotenv()

_TZ = zoneinfo.ZoneInfo("Asia/Karachi")
BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "data/raw/goodwe_inverter_reports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_LOGIN_GATEWAY = "https://www.semsportal.com"


class GoodWeSEMSCloudClient:
    """Session manager and client for GoodWe SEMS Cloud API."""

    def __init__(self, account: str, password: str, gateway_url: Optional[str] = None) -> None:
        self.account = account
        self.password = password
        self.gateway_url = gateway_url or DEFAULT_LOGIN_GATEWAY
        self.session = requests.Session()
        self.token_header: Optional[str] = None
        self.user_data: Dict[str, Any] = {}
        self.api_base: str = "https://hk.semsportal.com/api"
        self.station_id: Optional[str] = None
        self.station_name: str = "Station 904-A JT"

    def login(self) -> bool:
        """Authenticates with SEMS Portal CrossLogin across regional gateways."""
        token_payload = json.dumps({
            "version": "v3.1.1",
            "client": "ios",
            "language": "en",
        })
        
        body = {
            "account": self.account,
            "pwd": self.password,
        }

        url = f"{self.gateway_url}/api/v2/Common/CrossLogin"
        headers = {
            "Content-Type": "application/json",
            "Token": token_payload,
            "User-Agent": "SEMS Portal/3.1.1 (iPhone; iOS 17.5.1; Scale/3.00)",
        }
        
        try:
            resp = self.session.post(url, json=body, headers=headers, timeout=12)
            if resp.status_code == 200:
                res_json = resp.json()
                if res_json.get("code") == 0 or res_json.get("hasError") is False:
                    self.user_data = res_json.get("data") or {}
                    
                    # Set active token
                    token_data = self.user_data
                    self.token_header = json.dumps({
                        "version": token_data.get("version", "v3.1.1"),
                        "client": token_data.get("client", "ios"),
                        "language": token_data.get("language", "en"),
                        "timestamp": token_data.get("timestamp"),
                        "uid": token_data.get("uid"),
                        "token": token_data.get("token"),
                    })

                    # Update regional API base (e.g. https://hk.semsportal.com/api/)
                    api_override = res_json.get("api") or self.user_data.get("api")
                    if api_override and api_override.startswith("http"):
                        self.api_base = api_override.rstrip("/")

                    return True
                else:
                    msg = res_json.get("msg") or "Authentication rejected by server"
                    print(f"⚠️ Gateway {self.gateway_url} returned: {msg}")
        except Exception as e:
            print(f"⚠️ Gateway {self.gateway_url} error: {e}")

        return False

    def get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Token": self.token_header or "{}",
            "User-Agent": "SEMS Portal/3.1.1 (iPhone; iOS 17.5.1; Scale/3.00)",
        }

    def discover_station(self) -> Optional[Dict[str, Any]]:
        """Discovers primary station metadata and installation date."""
        # Check standard station ID
        known_id = "064f10e9-b719-437d-996a-203937c0ba9b"
        ep = f"{self.api_base}/v1/PowerStation/GetMonitorDetailByPowerstationId"
        try:
            resp = self.session.post(ep, json={"powerStationId": known_id}, headers=self.get_headers(), timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("data") or {}
                if "info" in data:
                    info = data["info"]
                    self.station_id = info.get("powerstation_id", known_id)
                    self.station_name = info.get("stationname", "904-A JT")
                    return data
        except Exception as e:
            print(f"Discovery error: {e}")

        self.station_id = known_id
        return None

    def fetch_monthly_balances(self) -> List[Dict[str, Any]]:
        """Fetches monthly station generation breakdown."""
        if not self.station_id:
            return []
        
        ep = f"{self.api_base}/PowerStationMonitor/GetPowerStationPowerAndIncomeByMonth"
        try:
            resp = self.session.post(ep, json={"powerstation_id": self.station_id}, headers=self.get_headers(), timeout=10)
            if resp.status_code == 200:
                return resp.json().get("data") or []
        except Exception as e:
            print(f"Monthly balance error: {e}")
        return []

    def fetch_daily_generation_history(
        self,
        start_date: str = "2025-07-01",
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Iterates over all months from start_date to end_date, extracting daily generation (kWh)
        and income (PKR) for every single day since installation.
        """
        if not self.station_id:
            raise RuntimeError("Station not identified. Call discover_station() first.")

        if end_date is None:
            end_date = datetime.now(_TZ).strftime("%Y-%m-%d")

        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        # Build monthly query milestones (1st of each month + 1 month buffer)
        query_dates = []
        cur = datetime(start_dt.year, start_dt.month, 1)
        end_milestone = datetime(end_dt.year, end_dt.month, 1) + timedelta(days=32)
        while cur <= end_milestone:
            query_dates.append(cur.strftime("%Y-%m-01"))
            if cur.month == 12:
                cur = datetime(cur.year + 1, 1, 1)
            else:
                cur = datetime(cur.year, cur.month + 1, 1)

        print(f"📥 Querying {len(query_dates)} monthly periods from {start_date} to {end_date}...")
        url = f"{self.api_base}/PowerStationMonitor/GetPowerStationPowerAndIncomeByDay"
        
        days_map: Dict[str, Dict[str, Any]] = {}

        for q_date in query_dates:
            try:
                r = self.session.post(
                    url,
                    json={"powerstation_id": self.station_id, "date": q_date},
                    headers=self.get_headers(),
                    timeout=10,
                )
                if r.status_code == 200:
                    items = r.json().get("data") or []
                    for item in items:
                        raw_d = item.get("d")  # format: MM/DD/YYYY
                        p_kwh = float(item.get("p") or 0.0)
                        income_pkr = float(item.get("i") or 0.0)
                        if raw_d:
                            parts = raw_d.split("/")
                            if len(parts) == 3:
                                iso_d = f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
                                if start_date <= iso_d <= end_date:
                                    days_map[iso_d] = {
                                        "date": iso_d,
                                        "generation_kwh": round(p_kwh, 3),
                                        "income_pkr": round(income_pkr, 2),
                                    }
                time.sleep(0.15)  # Rate limiting protection
            except Exception as e:
                print(f"⚠️ Error fetching month {q_date}: {e}")

        # Return sorted by date
        return [days_map[k] for k in sorted(days_map.keys())]


def run_historical_download(
    account: str,
    password: str,
    start_date: str = "2025-07-01",
    end_date: Optional[str] = None,
) -> bool:
    print("=" * 75)
    print("☀️  SolarSense EMS — GoodWe SEMS Cloud Full Historical Ingestion")
    print("=" * 75)
    
    # Hide user account details in logs
    masked_acc = f"{account[:3]}***@{account.split('@')[-1]}" if "@" in account else "***"
    print(f"Account: {masked_acc}")
    
    client = GoodWeSEMSCloudClient(account, password)
    if not client.login():
        print("❌ Login failed. Please verify SEMS credentials.")
        return False

    print(f"✅ Authenticated via regional gateway: {client.api_base}")

    detail = client.discover_station()
    if detail:
        info = detail.get("info", {})
        print(f"📍 Station: {info.get('stationname')} | ID: {client.station_id}")
        print(f"   • Address: {info.get('address')}")
        print(f"   • Commissioning Date: {info.get('create_time')}")
        print(f"   • Turn-on Time: {info.get('turnon_time')}")
        print(f"   • Battery Capacity: {info.get('battery_capacity')} kWh")
    else:
        print(f"📍 Station: {client.station_name} | ID: {client.station_id}")

    if end_date is None:
        end_date = datetime.now(_TZ).strftime("%Y-%m-%d")

    print("-" * 75)
    print(f"📅 Downloading Full Historical Daily Records: {start_date} ──► {end_date}")
    print("-" * 75)

    records = client.fetch_daily_generation_history(start_date=start_date, end_date=end_date)
    if not records:
        print("⚠️ No historical records retrieved.")
        return False

    # Calculate macro totals
    total_kwh = sum(r["generation_kwh"] for r in records)
    total_pkr = sum(r["income_pkr"] for r in records)
    active_days = sum(1 for r in records if r["generation_kwh"] > 0)

    print(f"✅ Retrieved {len(records)} daily records ({active_days} active generation days).")
    print(f"⚡ Lifetime Generation: {total_kwh:,.2f} kWh")
    print(f"💰 Lifetime Financial Income: {total_pkr:,.2f} PKR")

    # Export to CSV
    csv_path = OUTPUT_DIR / "sems_cloud_daily_pv_full_history.csv"
    import polars as pl
    df = pl.DataFrame(records)
    df.write_csv(csv_path)
    print(f"📁 Daily History Saved: {csv_path}")

    # Export Metadata Summary
    meta_path = OUTPUT_DIR / "sems_cloud_history_metadata.json"
    metadata = {
        "station_id": client.station_id,
        "station_name": client.station_name,
        "gateway_url": client.api_base,
        "start_date": start_date,
        "end_date": end_date,
        "total_days_recorded": len(records),
        "active_generation_days": active_days,
        "total_generation_kwh": round(total_kwh, 2),
        "total_income_pkr": round(total_pkr, 2),
        "updated_at_utc": datetime.now(zoneinfo.ZoneInfo("UTC")).isoformat(),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"📁 Metadata Saved: {meta_path}")

    print("=" * 75)
    print("🎉 GoodWe SEMS Cloud Full Historical Ingestion Completed Successfully!")
    print("=" * 75)
    return True


def main():
    parser = argparse.ArgumentParser(description="GoodWe SEMS Cloud Full History Ingestion")
    parser.add_argument("--account", "-u", default=os.getenv("SEMS_ACCOUNT"), help="SEMS Portal Email/Username")
    parser.add_argument("--password", "-p", default=os.getenv("SEMS_PASSWORD"), help="SEMS Portal Password")
    parser.add_argument("--start", "-s", default="2025-07-01", help="Start Date (YYYY-MM-DD, defaults to 2025-07-01)")
    parser.add_argument("--end", "-e", default=None, help="End Date (YYYY-MM-DD, defaults to today)")
    
    args = parser.parse_args()

    account = args.account
    if not account:
        account = input("Enter your SEMS Portal Email / Account: ").strip()

    password = args.password
    if not password:
        password = getpass.getpass("Enter your SEMS Portal Password: ").strip()

    if not account or not password:
        print("❌ Error: Both SEMS account and password are required.")
        sys.exit(1)

    run_historical_download(
        account=account,
        password=password,
        start_date=args.start,
        end_date=args.end,
    )


if __name__ == "__main__":
    main()
