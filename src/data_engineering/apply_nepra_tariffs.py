"""
apply_nepra_tariffs.py
======================
SolarSense EMS — Phase 1 (Update)

Injects official NEPRA/LESCO tariff configurations from the JSON files
directly into the Master EMS Feature Store. Re-calculates all financial 
metrics (Grid Cost, Export Revenue, MDI Penalties, Diesel Costs, and 
Maintenance/Wash triggers) dynamically.
"""

import os
import json
import numpy as np
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
CSV_PATH = os.path.join(BASE_DIR, "data/processed/master_ems_timeseries.csv")
JSON_PATH = os.path.join(BASE_DIR, "src/lesco-tarrif.json")

def load_tariff_config():
    with open(JSON_PATH, 'r') as f:
        data = json.load(f)
    return data["energy_cost_config"]

def main():
    print("=" * 60)
    print("SolarSense EMS — Applying Official LESCO/NEPRA Tariffs")
    print("=" * 60)

    # 1. Load Data
    config = load_tariff_config()
    df = pd.read_csv(CSV_PATH)
    
    # Extract config variables
    peak_rate = config["tariff_rates_pkr_per_kwh"]["peak_rate"]
    off_peak_rate = config["tariff_rates_pkr_per_kwh"]["off_peak_rate"]
    export_rate = config["tariff_rates_pkr_per_kwh"]["solar_export_rate"]
    
    p_start = config["peak_hours_schedule"]["peak_start_hour"]
    p_end = config["peak_hours_schedule"]["peak_end_hour"]
    
    demand_limit = config["demand_limit_and_penalties"]["sanctioned_demand_limit_kw"]
    demand_penalty = config["demand_limit_and_penalties"]["demand_penalty_pkr_per_kw"]
    
    diesel_rate = config["backup_and_outage_costs"]["diesel_generator_cost_pkr_per_kwh"]
    wash_cost = config["maintenance_costs"]["solar_cleaning_cost_pkr"]

    print(f"  ✓ Loaded Config: Peak {p_start}:00-{p_end}:00 ({peak_rate} PKR), Limit {demand_limit}kW")

    # 2. Update Tariff Window & Rates
    df["tariff_window"] = np.where((df["hour"] >= p_start) & (df["hour"] < p_end), "peak", "off_peak")
    df["tariff_rate_pkr"] = np.where(df["tariff_window"] == "peak", peak_rate, off_peak_rate)

    # 3. Calculate Power Flow
    # net_power_kw is: positive = exporting to grid, negative = drawing from grid
    grid_import = np.where(df["net_power_kw"] < 0, -df["net_power_kw"], 0.0)
    grid_export = np.where(df["net_power_kw"] > 0, df["net_power_kw"], 0.0)

    # If outage, import comes from Diesel, not Grid
    df["diesel_import_kw"] = np.where(df["outage_flag"] == 1, grid_import, 0.0)
    df["grid_import_kw"]   = np.where(df["outage_flag"] == 0, grid_import, 0.0)
    df["grid_export_kw"]   = np.where(df["outage_flag"] == 0, grid_export, 0.0)

    # 4. Financial Calculations
    df["electricity_cost_pkr"] = df["grid_import_kw"] * df["tariff_rate_pkr"]
    df["export_revenue_pkr"]   = df["grid_export_kw"] * export_rate
    df["diesel_backup_cost_pkr"] = df["diesel_import_kw"] * diesel_rate
    
    # 5. Sanctioned Demand Penalty (Calculated strictly on grid import)
    df["demand_penalty_pkr"] = np.where(
        df["grid_import_kw"] > demand_limit,
        (df["grid_import_kw"] - demand_limit) * demand_penalty,
        0.0
    )

    # 6. Maintenance Trigger (Cumulative Soiling Loss)
    # The soiling_loss_pkr in the CSV is a DAILY total, repeated 24 times for each hour. 
    # To track cumulatively, we need to add it once per day.
    
    # Create a daily tracking dataframe
    daily_df = df.groupby("date").first().reset_index()
    
    cum_loss = 0.0
    daily_cum_loss = []
    wash_flag = []
    
    for _, row in daily_df.iterrows():
        ev_type = str(row.get("event_type", ""))
        # Reset if washed
        if "wash" in ev_type:
            cum_loss = 0.0
            
        cum_loss += float(row.get("soiling_loss_pkr", 0.0))
        daily_cum_loss.append(cum_loss)
        
        # Trigger wash if cumulative loss exceeds the 15,000 PKR cleaning cost
        if cum_loss >= wash_cost:
            wash_flag.append(1)
        else:
            wash_flag.append(0)
            
    daily_df["cumulative_soiling_loss_pkr"] = daily_cum_loss
    daily_df["wash_recommended_flag"] = wash_flag
    
    # Map back to hourly dataset
    df = df.drop(columns=["cumulative_soiling_loss_pkr", "wash_recommended_flag"], errors="ignore")
    df = df.merge(daily_df[["date", "cumulative_soiling_loss_pkr", "wash_recommended_flag"]], on="date", how="left")

    # Save over the master CSV
    df.to_csv(CSV_PATH, index=False)
    
    print("\n── Financial Integration Summary ──")
    print(f"  Total Rows Updated      : {len(df):,}")
    print(f"  Total Electricity Cost  : PKR {df['electricity_cost_pkr'].sum():,.0f}")
    print(f"  Total Export Revenue    : PKR {df['export_revenue_pkr'].sum():,.0f}")
    print(f"  Total Diesel Cost       : PKR {df['diesel_backup_cost_pkr'].sum():,.0f}")
    print(f"  Total MDI Penalties     : PKR {df['demand_penalty_pkr'].sum():,.0f}")
    print(f"  Days Wash Recommended   : {df.groupby('date')['wash_recommended_flag'].first().sum()} days")
    print(f"  ✓ Saved directly into: {os.path.basename(CSV_PATH)}")
    print("\n✅ Dataset successfully updated with official JSON logic.\n")

if __name__ == "__main__":
    main()
