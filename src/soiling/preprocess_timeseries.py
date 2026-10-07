"""
SolarSense EMS — Dataset B Time Series Preprocessing & Standardization Pipeline
Preprocesses and normalizes Laghouat soiling and Lahore generation datasets,
enforcing physical bounds, nighttime zero clamping, and canonical column naming.
"""

import pandas as pd
import numpy as np
from pathlib import Path

RAW_DIR = Path("data/raw/solar_timeseries")
PROCESSED_DIR = Path("data/processed/solar_timeseries")


def preprocess_laghouat():
    src_csv = RAW_DIR / "laghouat_soiling/Laghouat_2022_final.csv"
    dest_csv = PROCESSED_DIR / "soiling_ground_truth_laghouat.csv"

    print(f"[PREPROCESS] Standardizing Laghouat soiling ground truth...")
    df = pd.read_csv(src_csv)
    df["datetime"] = pd.to_datetime(df["datetime"], format="%d/%m/%Y %H:%M")
    df = df.sort_values("datetime").reset_index(drop=True)

    # Physical clamping
    df["p_clean_w"] = np.where(df["G_POA_Wm2"] <= 1.0, 0.0, df["P_clean_W"].clip(lower=0.0))
    df["p_dusty_w"] = np.where(df["G_POA_Wm2"] <= 1.0, 0.0, df["P_dusty_W"].clip(lower=0.0))

    # Empirical metrics
    day_mask = df["G_POA_Wm2"] > 20.0
    df["power_delta_w"] = np.where(day_mask, (df["p_clean_w"] - df["p_dusty_w"]).clip(lower=0.0), 0.0)
    df["soiling_derate_pct"] = np.where(day_mask & (df["p_clean_w"] > 1.0),
                                        (df["power_delta_w"] / df["p_clean_w"]) * 100, 0.0)
    df["soiling_ratio"] = np.where(day_mask & (df["p_clean_w"] > 1.0),
                                   (df["p_dusty_w"] / df["p_clean_w"]).clip(0.0, 1.0), 1.0)

    # Canonical columns
    rename_cols = {
        "G_POA_Wm2": "poa_irradiance_wm2",
        "temp_amb_C": "temp_ambient_c",
        "T_cell_C": "temp_cell_c",
        "RH_pct": "relative_humidity_pct",
        "wind_speed_ms": "wind_speed_ms",
        "cloud_cover_pct": "cloud_cover_pct",
        "precipitation_mm": "precipitation_mm",
        "dust_density_reconstructed_PCHIP_gm2": "dust_density_gm2"
    }
    df = df.rename(columns=rename_cols)

    keep_cols = [
        "datetime", "poa_irradiance_wm2", "temp_ambient_c", "temp_cell_c",
        "relative_humidity_pct", "wind_speed_ms", "cloud_cover_pct", "precipitation_mm",
        "dust_density_gm2", "p_clean_w", "p_dusty_w", "power_delta_w",
        "soiling_derate_pct", "soiling_ratio"
    ]
    df_clean = df[keep_cols]

    dest_csv.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(dest_csv, index=False)
    print(f"[SAVED] Standardized Laghouat soiling dataset saved to: {dest_csv} ({len(df_clean)} rows)")
    return dest_csv


def preprocess_lahore():
    src_csv = RAW_DIR / "lahore_fastpredictor/Lahore_Single_Panel_Dataset_with_Meteorological_Datas.csv"
    dest_csv = PROCESSED_DIR / "lahore_pv_generation_hourly.csv"

    print(f"[PREPROCESS] Standardizing Lahore PV generation dataset...")
    df = pd.read_csv(src_csv)
    df["datetime"] = pd.to_datetime(df["TimeStamp"])
    df = df.sort_values("datetime").reset_index(drop=True)

    # Canonical renaming
    rename_cols = {
        "Power": "pv_power_w",
        "Temperature": "temp_ambient_c",
        "Irradiance (G)": "ghi_wm2",
        "Irradiance (A)": "actual_irradiance_wm2",
        "Cloud": "cloud_fraction",
        "Prectotland": "precipitation_mm",
        "Rhoa": "air_density_kgm3"
    }
    df = df.rename(columns=rename_cols)

    # Nighttime zero clamping
    night_mask = df["actual_irradiance_wm2"] <= 1.0
    df.loc[night_mask, "pv_power_w"] = 0.0

    keep_cols = [
        "datetime", "pv_power_w", "temp_ambient_c", "ghi_wm2",
        "actual_irradiance_wm2", "cloud_fraction", "precipitation_mm", "air_density_kgm3"
    ]
    df_clean = df[keep_cols]

    dest_csv.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(dest_csv, index=False)
    print(f"[SAVED] Standardized Lahore generation dataset saved to: {dest_csv} ({len(df_clean)} rows)")
    return dest_csv


if __name__ == "__main__":
    preprocess_laghouat()
    preprocess_lahore()
