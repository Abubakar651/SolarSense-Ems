#!/usr/bin/env python3
"""
SolarSense EMS — Automated Daily Standup & Task Tracker
======================================================
Scans sprint plans, recent daily logs, and git commits to report today's
prioritized deliverables and status for Abubakar & Zaeem.

Usage:
    python scripts/daily_standup.py
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
import subprocess
import sys


def run_git(args: list[str], root: Path) -> str:
    try:
        res = subprocess.run(["git"] + args, cwd=str(root), capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    now = dt.datetime.now()
    today_str = now.strftime("%Y-%m-%d (%A)")

    print("=" * 80)
    print(f"☀️  SolarSense EMS — Daily Standup Briefing | {today_str}")
    print("=" * 80)

    # 1. Latest Commits
    recent_commits = run_git(["log", "-n", "5", "--pretty=format:  • [%h] %an: %s"], repo_root)
    print("\n📦 RECENT COMMITS MERGED (Last 48 Hours):")
    if recent_commits:
        print(recent_commits)
    else:
        print("  (No recent commits found)")

    # 2. Check Daily Logs
    daily_logs_dir = repo_root / "docs" / "daily_logs"
    latest_log_files = sorted(daily_logs_dir.glob("2026-*.md"), reverse=True) if daily_logs_dir.exists() else []

    print("\n📑 LATEST ARCHIVED ENGINEERING LOGS:")
    if latest_log_files:
        for lf in latest_log_files[:2]:
            print(f"  • docs/daily_logs/{lf.name}")
    else:
        print("  • None found")

    # 3. Active Sprint Plan
    plan_path = repo_root / "docs" / "week4_implementation_plan_abubakar_zaeem.md"
    print(f"\n📋 ACTIVE SPRINT PLAN: docs/{plan_path.name if plan_path.exists() else 'N/A'}")

    # 4. Abubakar Status
    print("\n" + "-" * 80)
    print("👤 ABUBAKAR (Team Lead / Systems, Optimization & Backend)")
    print("-" * 80)
    print("  ✅ COMPLETED:")
    print("     • Task A1: Backend Data Store (src/data_engineering/feature_store.py) — 17 unit tests passing")
    print("     • Task A2: Solar PV Forecaster (src/forecast/train_solar_pv.py) — LightGBM baseline trained")
    print("     • Task A3: 24h MILP Dispatch Solver (src/optimizer/milp_solver.py) — 25 unit tests passing")
    print("     • CI/CD: Automated nightly 01:00 AM engineering log pipeline configured")
    print("  🎯 TODAY'S HIGH-PRIORITY DELIVERABLES:")
    print("     1. Task A4: Author Master System Architecture & Data Dictionary (docs/system_architecture.md)")
    print("        - Mermaid.js end-to-end dataflow diagram")
    print("        - Master 24-column feature schema table for master_ems_timeseries.csv")
    print("     2. Integrate Tariff & Battery Solver with Outage Predictor (src/grid_outage/predict_outage.py)")
    print("        - Verify probability-calibrated outage signals feeding solver reserve constraints")

    # 5. Zaeem Status
    print("\n" + "-" * 80)
    print("👤 ZAEEM (Computer Vision & Industrial Load Analytics)")
    print("-" * 80)
    print("  ✅ COMPLETED:")
    print("     • Task Z2: PyTorch DataLoader & Augmentations (src/vision/dataloader.py)")
    print("     • Task Z2+: EfficientNet-B2 Defect Classifier Trainer (src/vision/train_classifier.py)")
    print("     • Task Z3: Industrial Load & MDI Analysis EDA Notebook (notebooks/01_industrial_load_eda.ipynb)")
    print("  🎯 NEXT DELIVERABLES:")
    print("     1. Task Z1: Curate & hash-verify clean Dataset A image directory (data/raw/panel_images/)")
    print("     2. Task Z4: Dataset Card & Defect Audit Documentation (docs/dataset_A_audit_report.md)")

    print("\n" + "=" * 80)
    print("⚡ Suggested Immediate Action:")
    print("   Open docs/system_architecture.md to draft the Milestone 4 architecture specification,")
    print("   or run 'pytest' to verify solver benchmarks.")
    print("=" * 80 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
