# SolarSense EMS — Daily Engineering Logs & Audit Trail

This directory contains automated and verifiable daily engineering logs for the **SolarSense Industrial Energy Management System**.

## 📅 Log Indexing
Each daily log is archived under `YYYY-MM-DD.md` and captures:
1. **Team Work Breakdown:** Individual contributions attributed to Abubakar (Lead / Systems & Optimization) and Zaeem (Computer Vision & Load Analytics).
2. **Commit Records:** Exact commit hashes and descriptions merged into `main`.
3. **Subsystems Impacted:** Breakdown across Battery Optimization (MILP), Forecasting models, Feature Store, and Computer Vision.
4. **Code Volume:** Granular diff statistics (`+lines / -lines`).

## 🤖 Automation Engine
- **Schedule:** Automated GitHub Action runs daily at `01:00 AM PKT` (`20:00 UTC`).
- **Generator Script:** [`scripts/generate_daily_report.py`](file:///home/bakar/Documents/Solar%20Sens%20EMS/scripts/generate_daily_report.py).
- **Manual Trigger:** Can also be triggered on demand via GitHub Actions (`workflow_dispatch`) or locally via:
  ```bash
  python scripts/generate_daily_report.py --hours 24
  ```
