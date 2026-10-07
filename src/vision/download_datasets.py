"""
SolarSense EMS — Automated Kaggle Ingestion for Dataset A Candidates
Downloads alicjalena/pv-panel-defect-dataset and hemanthsai7/solar-panel-dust-detection
directly into data/raw/panel_images/
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load local .env credentials
load_dotenv()

import kaggle
from kaggle.api.kaggle_api_extended import KaggleApi

def main():
    print("==================================================")
    print("SOLARSENSE EMS — AUTOMATED DATASET INGESTION")
    print("==================================================")

    api = KaggleApi()
    api.authenticate()
    print("[AUTH] Successfully authenticated with Kaggle API.")

    raw_dir = Path("data/raw/panel_images")
    raw_dir.mkdir(parents=True, exist_ok=True)

    datasets = [
        {
            "id": "alicjalena/pv-panel-defect-dataset",
            "name": "alicjalena",
            "path": raw_dir / "alicjalena"
        },
        {
            "id": "hemanthsai7/solar-panel-dust-detection",
            "name": "hemanthsai7",
            "path": raw_dir / "hemanthsai7"
        }
    ]

    for ds in datasets:
        target_path = ds["path"]
        print(f"\n[DOWNLOAD] Starting download for: {ds['id']}")
        print(f"[TARGET] Destination: {target_path}")

        if target_path.exists() and any(target_path.iterdir()):
            print(f"[SKIP] Directory already exists and is non-empty: {target_path}")
            continue

        target_path.mkdir(parents=True, exist_ok=True)
        try:
            api.dataset_download_files(
                dataset=ds["id"],
                path=str(target_path),
                unzip=True,
                quiet=False
            )
            print(f"[SUCCESS] Downloaded and extracted {ds['id']} into {target_path}")
        except Exception as e:
            print(f"[ERROR] Failed to download {ds['id']}: {e}")
            sys.exit(1)

    print("\n[COMPLETE] All candidate image datasets downloaded successfully.")

if __name__ == "__main__":
    main()
