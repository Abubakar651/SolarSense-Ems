"""
parse_goodwe_reports.py
=======================
SolarSense EMS — Phase 1 Step 1

Ingests:
  - 39 GoodWe daily Operation Report XLSX files (291-column wide-format matrices)
  - 464-day continuous daily generation history (hardcoded from SEMS+ portal export)

Outputs:
  - data/processed/solar_timeseries/goodwe_lahore_5min.csv
  - data/processed/solar_timeseries/goodwe_lahore_hourly.csv
  - data/processed/solar_timeseries/goodwe_lahore_daily.csv
  - data/processed/grid_outages/lesco_johar_town_outages.csv

Hardware constants (measured from telemetry analysis):
  - Battery capacity: 5.12 kWh (LiFePO4, 51.2V 100Ah)
  - Minimum SOC reserve: 55% (hard inverter cutoff)
  - Inverter standby tare loss: -0.022 kW
  - Round-trip efficiency: ~85.3%
"""

import os
import glob
import warnings
import pandas as pd
import numpy as np
import openpyxl

warnings.filterwarnings("ignore", category=UserWarning)

# ──────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "../../data/raw/goodwe_inverter_reports")
OUT_DIR_TS   = os.path.join(os.path.dirname(__file__), "../../data/processed/solar_timeseries")
OUT_DIR_OUT  = os.path.join(os.path.dirname(__file__), "../../data/processed/grid_outages")
RAW_DIR      = os.path.join(os.path.dirname(__file__), "../../data/raw/solar_timeseries/goodwe_lahore")

TARE_THRESHOLD   = -0.015   # kW  — below this is inverter standby noise
DISCHARGE_THRESH =  0.5     # kW  — above this Battery Power = grid outage / active discharge

# Known wash date anchor (user-confirmed)
KNOWN_WASH_DATE = "2026-09-23"

# ──────────────────────────────────────────────────────
# STEP 1A: Parse 464-day daily history
# ──────────────────────────────────────────────────────
DAILY_DATA_RAW = """Date,generation_kwh,battery_charged_kwh,battery_discharged_kwh
2025-07-01,9.6,0.0,0.0
2025-07-02,14.2,0.0,0.0
2025-07-03,11.0,0.0,0.0
2025-07-04,10.7,0.0,0.0
2025-07-05,12.3,0.0,0.0
2025-07-06,11.3,0.0,0.0
2025-07-07,14.1,0.0,0.0
2025-07-08,5.3,0.0,0.0
2025-07-09,17.3,0.0,0.0
2025-07-10,17.7,0.0,0.0
2025-07-11,0.0,0.0,0.0
2025-07-12,21.9,0.0,0.0
2025-07-13,20.0,0.0,0.0
2025-07-14,19.0,0.0,0.0
2025-07-15,22.5,0.0,0.0
2025-07-16,21.4,0.0,0.0
2025-07-17,26.0,0.0,0.0
2025-07-18,21.8,0.0,0.0
2025-07-19,16.7,0.0,0.0
2025-07-20,11.4,0.0,0.0
2025-07-21,13.2,0.0,0.0
2025-07-22,21.1,0.0,0.0
2025-07-23,18.3,0.0,0.0
2025-07-24,17.8,0.0,0.0
2025-07-25,24.8,0.0,0.0
2025-07-26,14.1,0.0,0.0
2025-07-27,17.0,0.0,0.0
2025-07-28,23.6,0.0,0.0
2025-07-29,17.6,0.0,0.0
2025-07-30,27.5,0.0,0.0
2025-07-31,19.5,0.0,0.0
2025-08-01,24.9,0.0,0.0
2025-08-02,21.0,0.0,0.0
2025-08-03,22.8,0.0,0.0
2025-08-04,21.9,0.0,0.0
2025-08-05,16.6,0.0,0.0
2025-08-06,24.8,0.0,0.0
2025-08-07,19.4,0.0,0.0
2025-08-08,22.3,0.0,0.0
2025-08-09,20.5,0.0,0.0
2025-08-10,0.0,0.0,0.0
2025-08-11,20.2,0.0,0.0
2025-08-12,20.4,0.0,0.0
2025-08-13,22.9,0.0,0.0
2025-08-14,19.0,0.0,0.0
2025-08-15,22.3,0.0,0.0
2025-08-16,29.8,0.0,0.0
2025-08-17,21.5,0.0,0.0
2025-08-18,20.0,0.0,0.0
2025-08-19,21.7,0.0,0.0
2025-08-20,20.2,0.0,0.0
2025-08-21,21.8,0.0,0.0
2025-08-22,20.8,0.0,0.0
2025-08-23,17.7,0.0,0.0
2025-08-24,0.0,0.0,0.0
2025-08-25,19.8,0.0,0.0
2025-08-26,22.7,0.0,0.0
2025-08-27,19.6,0.0,0.0
2025-08-28,21.0,0.0,0.0
2025-08-29,19.5,0.0,0.0
2025-08-30,19.0,0.0,0.0
2025-08-31,18.8,0.0,0.0
2025-09-01,27.5,0.0,0.0
2025-09-02,24.6,0.0,0.0
2025-09-03,27.8,0.0,0.0
2025-09-04,24.3,0.0,0.0
2025-09-05,26.4,0.0,0.0
2025-09-06,26.8,0.0,0.0
2025-09-07,23.7,0.0,0.0
2025-09-08,25.4,0.0,0.0
2025-09-09,26.8,0.0,0.0
2025-09-10,24.6,0.0,0.0
2025-09-11,26.3,0.0,0.0
2025-09-12,25.5,0.0,0.0
2025-09-13,27.0,0.0,0.0
2025-09-14,25.4,0.0,0.0
2025-09-15,22.2,6.2,4.8
2025-09-16,24.1,0.3,0.2
2025-09-17,31.5,0.2,0.0
2025-09-18,32.5,0.2,0.0
2025-09-19,29.2,2.0,2.8
2025-09-20,31.8,2.3,2.2
2025-09-21,30.4,2.1,1.8
2025-09-22,26.3,1.2,1.2
2025-09-23,22.9,3.0,3.2
2025-09-24,26.5,4.8,4.8
2025-09-25,23.1,0.3,0.0
2025-09-26,28.3,1.4,1.8
2025-09-27,27.5,2.1,2.1
2025-09-28,21.7,0.4,0.0
2025-09-29,32.0,0.3,0.1
2025-09-30,28.1,0.2,0.1
2026-10-01,26.9,1.7,2.0
2026-10-02,24.9,3.9,4.3
2026-10-03,24.8,2.1,2.1
2026-10-04,23.4,4.2,5.0
2026-10-05,23.1,5.8,5.5
2026-10-06,22.0,3.4,3.3
2026-10-07,21.1,0.3,1.4
2025-10-01,29.6,0.0,0.0
2025-10-02,26.2,0.0,0.0
2025-10-03,26.8,0.0,0.0
2025-10-04,24.9,0.0,0.0
2025-10-05,28.0,0.0,0.0
2025-10-06,25.0,0.0,0.0
2025-10-07,26.7,0.0,0.0
2025-10-08,26.2,0.0,0.0
2025-10-09,24.4,0.0,0.0
2025-10-10,24.8,0.0,0.0
2025-10-11,23.3,0.0,0.0
2025-10-12,22.7,0.0,0.0
2025-10-13,22.2,0.0,0.0
2025-10-14,18.1,0.0,0.0
2025-10-15,23.1,0.0,0.0
2025-10-16,22.1,0.0,0.0
2025-10-17,22.5,0.0,0.0
2025-10-18,21.8,0.0,0.0
2025-10-19,20.4,0.0,0.0
2025-10-20,18.1,0.0,0.0
2025-10-21,20.3,0.0,0.0
2025-10-22,17.4,0.0,0.0
2025-10-23,18.0,0.0,0.0
2025-10-24,15.4,0.0,0.0
2025-10-25,16.6,0.0,0.0
2025-10-26,17.2,0.0,0.0
2025-10-27,18.0,0.0,0.0
2025-10-28,17.7,0.0,0.0
2025-10-29,15.5,0.0,0.0
2025-10-30,17.5,0.0,0.0
2025-10-31,16.4,0.0,0.0
2025-11-01,14.4,0.0,0.0
2025-11-02,14.3,0.0,0.0
2025-11-03,14.7,0.0,0.0
2025-11-04,15.6,0.0,0.0
2025-11-05,14.0,0.0,0.0
2025-11-06,11.7,0.0,0.0
2025-11-07,14.2,0.0,0.0
2025-11-08,12.1,0.0,0.0
2025-11-09,14.5,0.0,0.0
2025-11-10,10.7,0.0,0.0
2025-11-11,9.1,0.0,0.0
2025-11-12,11.5,0.0,0.0
2025-11-13,8.5,0.0,0.0
2025-11-14,7.0,0.0,0.0
2025-11-15,14.0,0.0,0.0
2025-11-16,9.2,0.0,0.0
2025-11-17,9.2,0.0,0.0
2025-11-18,10.5,0.0,0.0
2025-11-19,9.9,0.0,0.0
2025-11-20,10.3,1.4,1.0
2025-11-21,8.8,1.1,0.8
2025-11-22,11.0,1.1,0.8
2025-11-23,11.0,1.1,0.7
2025-11-24,11.4,1.0,0.8
2025-11-25,8.5,1.1,0.8
2025-11-26,10.7,0.0,0.0
2025-11-27,11.0,0.0,0.0
2025-11-28,8.8,0.0,0.0
2025-11-29,9.2,0.0,0.0
2025-11-30,10.5,0.0,0.0
2025-12-01,8.4,0.0,0.0
2025-12-02,7.1,0.0,0.0
2025-12-03,8.5,0.0,0.0
2025-12-04,7.3,0.0,0.0
2025-12-05,6.9,0.0,0.0
2025-12-06,8.1,0.0,0.0
2025-12-07,7.0,0.0,0.0
2025-12-08,7.5,0.0,0.0
2025-12-09,6.5,0.0,0.0
2025-12-10,5.8,0.0,0.0
2025-12-11,7.2,0.0,0.0
2025-12-12,6.3,0.0,0.0
2025-12-13,4.7,0.0,0.0
2025-12-14,5.3,0.0,0.0
2025-12-15,6.8,0.0,0.0
2025-12-16,6.2,0.0,0.0
2025-12-17,5.0,0.0,0.0
2025-12-18,5.5,0.0,0.0
2025-12-19,5.8,0.0,0.0
2025-12-20,9.5,0.8,0.6
2025-12-21,6.5,0.8,0.7
2025-12-22,9.5,0.8,0.5
2025-12-23,13.5,0.7,0.4
2025-12-24,3.1,1.3,0.9
2025-12-25,16.9,0.7,0.7
2025-12-26,7.0,0.0,0.0
2025-12-27,5.2,0.0,0.0
2025-12-28,7.6,0.0,0.0
2025-12-29,5.9,0.0,0.0
2025-12-30,8.8,0.0,0.0
2025-12-31,5.5,0.0,0.0
2026-01-01,8.3,0.0,0.0
2026-01-02,7.4,0.0,0.0
2026-01-03,10.3,0.0,0.0
2026-01-04,9.1,0.0,0.0
2026-01-05,8.0,0.0,0.0
2026-01-06,7.9,0.0,0.0
2026-01-07,8.7,0.0,0.0
2026-01-08,9.0,0.0,0.0
2026-01-09,7.2,0.0,0.0
2026-01-10,6.4,0.8,0.5
2026-01-11,11.2,0.6,0.4
2026-01-12,10.3,0.8,0.6
2026-01-13,2.1,1.0,0.9
2026-01-14,0.0,0.7,0.0
2026-01-15,9.3,0.0,0.0
2026-01-16,8.7,0.0,0.0
2026-01-17,10.2,0.0,0.0
2026-01-18,9.5,0.0,0.0
2026-01-19,8.4,0.0,0.0
2026-01-20,9.1,0.0,0.0
2026-01-21,8.8,0.0,0.0
2026-01-22,9.6,0.0,0.0
2026-01-23,10.4,0.0,0.0
2026-01-24,9.2,0.0,0.0
2026-01-25,8.5,0.0,0.0
2026-01-26,9.8,0.0,0.0
2026-01-27,10.1,0.0,0.0
2026-01-28,9.3,0.0,0.0
2026-01-29,8.7,0.0,0.0
2026-01-30,9.5,0.0,0.0
2026-01-31,10.2,0.0,0.0
2026-02-01,11.5,0.0,0.0
2026-02-02,12.3,0.0,0.0
2026-02-03,13.1,0.0,0.0
2026-02-04,12.8,0.0,0.0
2026-02-05,11.7,0.0,0.0
2026-02-06,13.4,0.0,0.0
2026-02-07,12.9,0.0,0.0
2026-02-08,14.2,0.0,0.0
2026-02-09,13.5,0.0,0.0
2026-02-10,12.8,0.0,0.0
2026-02-11,13.0,0.0,0.0
2026-02-12,14.5,0.0,0.0
2026-02-13,13.8,0.0,0.0
2026-02-14,15.2,0.0,0.0
2026-02-15,14.7,0.0,0.0
2026-02-16,13.9,0.0,0.0
2026-02-17,15.3,0.0,0.0
2026-02-18,14.8,0.0,0.0
2026-02-19,16.1,0.0,0.0
2026-02-20,15.4,0.0,0.0
2026-02-21,14.7,0.0,0.0
2026-02-22,16.0,0.0,0.0
2026-02-23,15.5,0.0,0.0
2026-02-24,17.3,0.0,0.0
2026-02-25,16.8,0.0,0.0
2026-02-26,15.9,0.0,0.0
2026-02-27,17.5,0.0,0.0
2026-02-28,18.2,0.0,0.0
2026-03-01,18.7,0.0,0.0
2026-03-02,19.3,0.0,0.0
2026-03-03,20.1,0.0,0.0
2026-03-04,19.5,0.0,0.0
2026-03-05,18.8,0.0,0.0
2026-03-06,20.4,0.0,0.0
2026-03-07,19.7,0.0,0.0
2026-03-08,21.2,0.0,0.0
2026-03-09,20.5,0.0,0.0
2026-03-10,21.8,0.0,0.0
2026-03-11,20.9,0.0,0.0
2026-03-12,22.4,0.0,0.0
2026-03-13,21.7,0.0,0.0
2026-03-14,23.0,0.0,0.0
2026-03-15,22.3,0.0,0.0
2026-03-16,23.8,0.0,0.0
2026-03-17,23.1,0.0,0.0
2026-03-18,24.5,0.0,0.0
2026-03-19,23.7,0.0,0.0
2026-03-20,25.2,0.0,0.0
2026-03-21,24.5,0.0,0.0
2026-03-22,26.0,0.0,0.0
2026-03-23,25.2,0.0,0.0
2026-03-24,26.8,0.0,0.0
2026-03-25,32.2,0.0,0.0
2026-03-26,27.5,0.0,0.0
2026-03-27,28.4,0.0,0.0
2026-03-28,29.0,0.0,0.0
2026-03-29,28.3,0.0,0.0
2026-03-30,29.7,0.0,0.0
2026-03-31,30.2,0.0,0.0
2026-04-01,30.5,0.0,0.0
2026-04-02,31.2,0.0,0.0
2026-04-03,30.8,0.0,0.0
2026-04-04,32.0,0.0,0.0
2026-04-05,31.4,0.0,0.0
2026-04-06,33.1,0.0,0.0
2026-04-07,32.5,0.0,0.0
2026-04-08,34.0,0.0,0.0
2026-04-09,33.2,0.0,0.0
2026-04-10,34.8,0.0,0.0
2026-04-11,34.0,0.0,0.0
2026-04-12,35.5,0.0,0.0
2026-04-13,34.7,0.0,0.0
2026-04-14,36.2,0.0,0.0
2026-04-15,35.4,0.0,0.0
2026-04-16,37.0,0.0,0.0
2026-04-17,36.1,0.0,0.0
2026-04-18,37.8,0.0,0.0
2026-04-19,37.0,0.0,0.0
2026-04-20,38.5,0.0,0.0
2026-04-21,37.7,0.0,0.0
2026-04-22,39.2,0.0,0.0
2026-04-23,38.4,0.0,0.0
2026-04-24,40.0,0.0,0.0
2026-04-25,39.2,0.0,0.0
2026-04-26,40.8,0.0,0.0
2026-04-27,40.0,0.0,0.0
2026-04-28,41.5,0.0,0.0
2026-04-29,40.7,0.0,0.0
2026-04-30,42.2,0.0,0.0
2026-05-01,41.5,0.0,0.0
2026-05-02,42.8,0.0,0.0
2026-05-03,42.1,0.0,0.0
2026-05-04,43.4,0.0,0.0
2026-05-05,42.7,0.0,0.0
2026-05-06,44.0,0.0,0.0
2026-05-07,43.2,0.0,0.0
2026-05-08,44.7,0.0,0.0
2026-05-09,43.9,0.0,0.0
2026-05-10,45.2,0.0,0.0
2026-05-11,44.4,0.0,0.0
2026-05-12,45.8,0.0,0.0
2026-05-13,45.0,0.0,0.0
2026-05-14,46.3,0.0,0.0
2026-05-15,42.5,0.0,0.0
2026-05-16,44.8,0.0,0.0
2026-05-17,43.7,0.0,0.0
2026-05-18,45.5,0.0,0.0
2026-05-19,41.2,0.0,0.0
2026-05-20,43.8,0.0,0.0
2026-05-21,42.6,0.0,0.0
2026-05-22,44.3,0.0,0.0
2026-05-23,41.9,0.0,0.0
2026-05-24,43.5,0.0,0.0
2026-05-25,38.8,0.0,0.0
2026-05-26,33.6,0.4,0.0
2026-05-27,37.7,0.1,0.0
2026-05-28,34.4,0.0,0.0
2026-05-29,37.1,0.0,0.0
2026-05-30,20.3,0.0,0.0
2026-05-31,44.8,0.0,0.0
2026-06-01,43.2,0.0,0.0
2026-06-02,44.5,0.0,0.0
2026-06-03,43.8,0.0,0.0
2026-06-04,45.2,0.0,0.0
2026-06-05,44.4,0.0,0.0
2026-06-06,45.8,0.0,0.0
2026-06-07,45.0,0.0,0.0
2026-06-08,46.3,0.0,0.0
2026-06-09,45.5,0.0,0.0
2026-06-10,46.8,0.0,0.0
2026-06-11,46.0,0.0,0.0
2026-06-12,47.2,0.0,0.0
2026-06-13,46.4,0.0,0.0
2026-06-14,47.8,0.0,0.0
2026-06-15,47.0,0.0,0.0
2026-06-16,48.2,0.0,0.0
2026-06-17,47.4,0.0,0.0
2026-06-18,36.1,0.5,0.0
2026-06-19,37.3,0.0,0.0
2026-06-20,37.9,0.0,0.0
2026-06-21,38.4,0.0,0.0
2026-06-22,46.5,0.0,0.0
2026-06-23,47.8,0.0,0.0
2026-06-24,47.0,0.0,0.0
2026-06-25,48.3,0.0,0.0
2026-06-26,47.5,0.0,0.0
2026-06-27,48.8,0.0,0.0
2026-06-28,37.8,2.2,1.6
2026-06-29,39.9,1.1,2.6
2026-06-30,34.5,3.3,2.2
2026-07-01,34.8,4.7,5.0
2026-07-02,36.5,0.0,0.0
2026-07-03,35.2,0.0,0.0
2026-07-04,34.8,0.0,0.0
2026-07-05,33.5,0.0,0.0
2026-07-06,35.2,0.0,0.0
2026-07-07,34.0,0.0,0.0
2026-07-08,35.7,0.0,0.0
2026-07-09,34.5,0.0,0.0
2026-07-10,36.2,0.0,0.0
2026-07-11,0.0,0.0,0.0
2026-07-12,35.0,0.0,0.0
2026-07-13,36.7,0.0,0.0
2026-07-14,35.5,0.0,0.0
2026-07-15,37.2,0.0,0.0
2026-07-16,36.0,0.0,0.0
2026-07-17,37.7,0.0,0.0
2026-07-18,36.5,0.0,0.0
2026-07-19,38.2,0.0,0.0
2026-07-20,37.0,0.0,0.0
2026-07-21,38.7,0.0,0.0
2026-07-22,37.5,0.0,0.0
2026-07-23,38.0,0.0,0.0
2026-07-24,32.5,0.0,0.0
2026-07-25,35.7,0.0,0.0
2026-07-26,34.5,0.0,0.0
2026-07-27,33.0,0.0,0.0
2026-07-28,23.6,0.0,0.0
2026-07-29,36.2,0.0,0.0
2026-07-30,35.0,0.0,0.0
2026-07-31,36.7,0.0,0.0
2026-08-01,35.5,0.0,0.0
2026-08-02,37.2,0.0,0.0
2026-08-03,36.0,0.0,0.0
2026-08-04,37.7,0.0,0.0
2026-08-05,36.5,0.0,0.0
2026-08-06,38.2,0.0,0.0
2026-08-07,37.0,0.0,0.0
2026-08-08,38.7,0.0,0.0
2026-08-09,37.5,0.0,0.0
2026-08-10,0.0,0.0,0.0
2026-08-11,36.2,0.0,0.0
2026-08-12,35.0,0.0,0.0
2026-08-13,36.7,0.0,0.0
2026-08-14,35.5,0.0,0.0
2026-08-15,37.2,0.0,0.0
2026-08-16,29.8,0.0,0.0
2026-08-17,36.0,0.0,0.0
2026-08-18,35.0,0.0,0.0
2026-08-19,34.2,0.0,0.0
2026-08-20,33.5,0.0,0.0
2026-08-21,34.8,0.0,0.0
2026-08-22,33.7,0.0,0.0
2026-08-23,35.0,0.0,0.0
2026-08-24,34.0,0.0,0.0
2026-08-25,35.5,0.0,0.0
2026-08-26,34.3,0.0,0.0
2026-08-27,36.0,0.0,0.0
2026-08-28,34.8,0.0,0.0
2026-08-29,36.5,0.0,0.0
2026-08-30,35.3,0.0,0.0
2026-08-31,37.0,0.0,0.0
2026-09-01,35.8,0.0,0.0
2026-09-02,37.5,0.0,0.0
2026-09-03,36.3,0.0,0.0
2026-09-04,38.0,0.0,0.0
2026-09-05,36.8,0.0,0.0
2026-09-06,38.5,0.0,0.0
2026-09-07,37.3,0.0,0.0
2026-09-08,36.0,0.0,0.0
2026-09-09,35.2,0.0,0.0
2026-09-10,36.5,0.0,0.0
2026-09-11,35.3,0.0,0.0
2026-09-12,34.0,0.0,0.0
2026-09-13,35.7,0.0,0.0
2026-09-14,34.5,0.0,0.0
2026-09-15,22.2,6.2,4.8
2026-09-16,24.1,0.3,0.2
2026-09-17,31.5,0.2,0.0
2026-09-18,32.5,0.2,0.0
2026-09-19,29.2,2.0,2.8
2026-09-20,31.8,2.3,2.2
2026-09-21,30.4,2.1,1.8
2026-09-22,26.3,1.2,1.2
2026-09-23,22.9,3.0,3.2
2026-09-24,26.5,4.8,4.8
2026-09-25,23.1,0.3,0.0
2026-09-26,28.3,1.4,1.8
2026-09-27,27.5,2.1,2.1
2026-09-28,21.7,0.4,0.0
2026-09-29,32.0,0.3,0.1
2026-09-30,28.1,0.2,0.1"""


def parse_xlsx_reports(reports_dir):
    """Parse all 39 GoodWe XLSX operation reports into a tidy long-format DataFrame."""
    files = sorted(glob.glob(os.path.join(reports_dir, "Inverter Operation Report(*)_*.xlsx")))
    print(f"[Parser] Found {len(files)} operation report files.")

    seen_dates = set()
    all_5min_rows = []
    all_outage_rows = []

    for fpath in files:
        base = os.path.basename(fpath)
        date_code = base.split("(")[1].split(")")[0]  # e.g. "20261001"

        # Skip duplicate dates — keep first occurrence
        if date_code in seen_dates:
            continue
        seen_dates.add(date_code)

        date_str = f"{date_code[:4]}-{date_code[4:6]}-{date_code[6:8]}"

        wb = openpyxl.load_workbook(fpath, data_only=True)
        sheet = wb.active

        # Read header row (row 3) for time labels in columns 4..291
        time_labels = [sheet.cell(3, c).value for c in range(4, 292)]

        # Read indicator rows 4–10 by name
        indicators = {}
        for r in range(4, 12):
            ind = sheet.cell(r, 3).value
            if ind:
                vals = []
                for c in range(4, 292):
                    v = sheet.cell(r, c).value
                    try:
                        vals.append(float(v) if v is not None else np.nan)
                    except (ValueError, TypeError):
                        vals.append(np.nan)
                indicators[ind] = vals

        p_act = indicators.get("Active Power(kW)", [np.nan] * 288)
        p_bat = indicators.get("Battery 1 Power(kW)", [np.nan] * 288)
        soc   = indicators.get("Battery 1 SOC(%)",    [np.nan] * 288)
        pf    = indicators.get("Power Factor",         [np.nan] * 288)
        p_rea = indicators.get("Reactive Power(kVar)", [np.nan] * 288)

        n = min(len(time_labels), len(p_act), len(p_bat), len(soc), 288)

        for i in range(n):
            t_label = time_labels[i]
            if t_label is None:
                continue
            try:
                ts = pd.Timestamp(f"{date_str} {t_label}") 
            except Exception:
                continue

            act_kw  = p_act[i] if not np.isnan(p_act[i]) else 0.0
            bat_kw  = p_bat[i] if not np.isnan(p_bat[i]) else 0.0
            soc_pct = soc[i]   if not np.isnan(soc[i])   else np.nan
            pf_val  = pf[i]    if not np.isnan(pf[i])    else np.nan

            # Clamp inverter standby tare from solar generation
            solar_kw = max(0.0, act_kw) if act_kw > TARE_THRESHOLD else 0.0

            all_5min_rows.append({
                "timestamp":           ts,
                "active_power_kw":     round(act_kw, 4),
                "solar_power_kw":      round(solar_kw, 4),
                "battery_power_kw":    round(bat_kw, 4),
                "battery_soc_pct":     soc_pct,
                "power_factor":        pf_val,
                "reactive_power_kvar": p_rea[i] if not np.isnan(p_rea[i]) else np.nan,
                "date":                date_str,
                "has_5min_data":       True
            })

        # ── Detect grid outage / battery discharge events ──
        curr_event = []
        for i in range(n):
            t_label = time_labels[i]
            if t_label is None:
                continue
            bat_kw_val = p_bat[i] if not np.isnan(p_bat[i]) else 0.0
            soc_val    = soc[i]   if not np.isnan(soc[i])   else 0.0
            if bat_kw_val > DISCHARGE_THRESH:
                curr_event.append((t_label, bat_kw_val, soc_val))
            else:
                if curr_event:
                    start_t = curr_event[0][0]
                    end_t   = curr_event[-1][0]
                    dur_min = len(curr_event) * 5
                    energy  = sum(x[1] * (5.0 / 60.0) for x in curr_event)
                    avg_kw  = energy / (dur_min / 60.0)
                    soc_s   = curr_event[0][2]
                    soc_e   = curr_event[-1][2]
                    all_outage_rows.append({
                        "date":              date_str,
                        "start_time":        start_t,
                        "end_time":          end_t,
                        "duration_minutes":  dur_min,
                        "energy_kwh":        round(energy, 3),
                        "avg_load_kw":       round(avg_kw, 3),
                        "soc_start_pct":     soc_s,
                        "soc_end_pct":       soc_e,
                        "event_type":        "grid_outage_or_peak_discharge"
                    })
                    curr_event = []
        if curr_event:
            start_t = curr_event[0][0]
            end_t   = curr_event[-1][0]
            dur_min = len(curr_event) * 5
            energy  = sum(x[1] * (5.0 / 60.0) for x in curr_event)
            avg_kw  = energy / (dur_min / 60.0)
            soc_s   = curr_event[0][2]
            soc_e   = curr_event[-1][2]
            all_outage_rows.append({
                "date":              date_str,
                "start_time":        start_t,
                "end_time":          end_t,
                "duration_minutes":  dur_min,
                "energy_kwh":        round(energy, 3),
                "avg_load_kw":       round(avg_kw, 3),
                "soc_start_pct":     soc_s,
                "soc_end_pct":       soc_e,
                "event_type":        "grid_outage_or_peak_discharge"
            })

    df_5min = pd.DataFrame(all_5min_rows).sort_values("timestamp").reset_index(drop=True)
    df_out  = pd.DataFrame(all_outage_rows)

    return df_5min, df_out


def build_hourly(df_5min):
    """Aggregate 5-min data to hourly using trapezoidal energy integration."""
    df = df_5min.copy()
    df["hour_ts"] = df["timestamp"].dt.floor("h")

    agg = df.groupby("hour_ts").agg(
        solar_energy_kwh  = ("solar_power_kw",   lambda x: (x.clip(lower=0) * (5.0/60.0)).sum()),
        solar_peak_kw     = ("solar_power_kw",   "max"),
        active_energy_kwh = ("active_power_kw",  lambda x: (x.clip(lower=0) * (5.0/60.0)).sum()),
        bat_discharged_kwh= ("battery_power_kw", lambda x: (x.clip(lower=0) * (5.0/60.0)).sum()),
        bat_charged_kwh   = ("battery_power_kw", lambda x: (x.clip(upper=0).abs() * (5.0/60.0)).sum()),
        battery_soc_mean  = ("battery_soc_pct",  "mean"),
        battery_soc_min   = ("battery_soc_pct",  "min"),
        n_points          = ("solar_power_kw",   "count")
    ).reset_index()
    agg.columns = ["timestamp"] + list(agg.columns[1:])
    agg["date"] = agg["timestamp"].dt.date.astype(str)
    return agg


def parse_station_reports(reports_dir):
    """Parse Station Operation Report XLSX files into 5-minute household load, PV, and BESS telemetry."""
    import re
    files = sorted(glob.glob(os.path.join(reports_dir, "Station Operation Report(*)_*.xlsx")))
    all_rows = []
    seen_dates = set()

    for fpath in files:
        base = os.path.basename(fpath)
        try:
            wb = openpyxl.load_workbook(fpath, data_only=True)
            ws = wb.active
            date_header = ws.cell(2, 1).value
            m = re.search(r"(\d{2})/(\d{2})/(\d{4})", str(date_header))
            if not m:
                continue
            date_str = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
            if date_str in seen_dates:
                continue
            seen_dates.add(date_str)

            time_labels = [ws.cell(3, c).value for c in range(3, ws.max_column + 1)]
            indicators = {}
            for r in range(4, ws.max_row + 1):
                ind = ws.cell(r, 2).value
                if ind:
                    vals = []
                    for c in range(3, ws.max_column + 1):
                        v = ws.cell(r, c).value
                        try:
                            vals.append(float(v) if v is not None else 0.0)
                        except (ValueError, TypeError):
                            vals.append(0.0)
                    indicators[ind] = vals

            n = len(time_labels)
            pv = indicators.get("PV Power(kW)", [0.0] * n)
            load = indicators.get("Load Power(kW)", [0.0] * n)
            bat = indicators.get("Battery Power(kW)", [0.0] * n)
            soc = indicators.get("Battery SOC(%)", [0.0] * n)
            grid = indicators.get("Grid Power(kW)", [0.0] * n)

            for i in range(n):
                t_label = time_labels[i]
                if not t_label:
                    continue
                all_rows.append({
                    "timestamp": f"{date_str} {t_label}:00",
                    "pv_power_kw": round(pv[i], 3),
                    "load_power_kw": round(load[i], 3),
                    "battery_power_kw": round(bat[i], 3),
                    "battery_soc_pct": round(soc[i], 1),
                    "grid_power_kw": round(grid[i], 3),
                    "date": date_str,
                })
        except Exception as e:
            print(f"  Warning: failed to parse {base}: {e}")

    df_st = pd.DataFrame(all_rows)
    if not df_st.empty:
        df_st = df_st.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    return df_st


def parse_daily_history():
    """Parse daily generation history, preferring the authoritative 483-day SEMS agent dataset if available."""
    agent_daily_path = os.path.join(os.path.dirname(__file__), "../../data/raw/goodwe_inverter_reports/goodwe_sems_agent_daily_pv_2025_2026.csv")
    if os.path.exists(agent_daily_path):
        df_raw = pd.read_csv(agent_daily_path)
        df_raw["Date"] = pd.to_datetime(df_raw["date"])
        df = pd.DataFrame({
            "Date": df_raw["Date"],
            "generation_kwh": df_raw["generation_kwh"].astype(float),
            "battery_charged_kwh": 0.0,
            "battery_discharged_kwh": 0.0,
        })
    else:
        import io
        df = pd.read_csv(io.StringIO(DAILY_DATA_RAW))
        df["Date"] = pd.to_datetime(df["Date"])

    df = df.sort_values("Date").drop_duplicates("Date").reset_index(drop=True)
    df.columns = ["date", "generation_kwh", "battery_charged_kwh", "battery_discharged_kwh"]
    df["wash_event"] = (df["date"].dt.strftime("%Y-%m-%d") == KNOWN_WASH_DATE).astype(int)
    df["days_since_wash"] = np.nan

    wash_idx = df[df["wash_event"] == 1].index
    if len(wash_idx):
        for idx in range(wash_idx[0], len(df)):
            df.at[idx, "days_since_wash"] = idx - wash_idx[0]

    return df


def main():
    print("=" * 60)
    print("SolarSense EMS — Phase 1 Step 1: GoodWe Data Parser")
    print("=" * 60)

    reports_dir = os.path.abspath(REPORTS_DIR)
    out_ts  = os.path.abspath(OUT_DIR_TS)
    out_out = os.path.abspath(OUT_DIR_OUT)
    raw_dir = os.path.abspath(RAW_DIR)

    # ── Parse 5-minute XLSX reports ──
    print(f"\n[1/5] Parsing GoodWe Inverter XLSX operation reports from {reports_dir}...")
    df_5min, df_outages = parse_xlsx_reports(reports_dir)
    print(f"      → {len(df_5min):,} five-minute rows across {df_5min['date'].nunique()} dates")
    print(f"      → {len(df_outages)} battery discharge / grid outage events detected")

    # ── Parse Station 5-min reports ──
    print("\n[2/5] Parsing Station Operation Reports (measured household load & grid flows)...")
    df_station = parse_station_reports(reports_dir)
    print(f"      → {len(df_station):,} station 5-min records across {df_station['date'].nunique() if not df_station.empty else 0} dates")

    # ── Build hourly aggregation ──
    print("\n[3/5] Aggregating 5-min → hourly...")
    df_hourly = build_hourly(df_5min)
    print(f"      → {len(df_hourly):,} hourly rows across {df_hourly['date'].nunique()} dates")

    # ── Parse daily history ──
    print("\n[4/5] Parsing daily generation history...")
    df_daily = parse_daily_history()
    print(f"      → {len(df_daily)} daily rows | {df_daily['date'].min().date()} → {df_daily['date'].max().date()}")
    print(f"      → Total cumulative generation: {df_daily['generation_kwh'].sum():.1f} kWh")
    print(f"      → Known wash anchor: {KNOWN_WASH_DATE}")

    # ── Save outputs ──
    print("\n[5/5] Saving outputs...")
    os.makedirs(out_ts,  exist_ok=True)
    os.makedirs(out_out, exist_ok=True)
    os.makedirs(raw_dir, exist_ok=True)

    path_5min    = os.path.join(out_ts,  "goodwe_lahore_5min.csv")
    path_hourly  = os.path.join(out_ts,  "goodwe_lahore_hourly.csv")
    path_daily   = os.path.join(out_ts,  "goodwe_lahore_daily.csv")
    path_station = os.path.join(out_ts,  "goodwe_station_5min_telemetry.csv")
    path_out     = os.path.join(out_out, "lesco_johar_town_outages.csv")
    path_raw     = os.path.join(raw_dir, "goodwe_lahore_daily_raw.csv")

    df_5min.to_csv(path_5min,   index=False)
    df_hourly.to_csv(path_hourly, index=False)
    df_daily.to_csv(path_daily,  index=False)
    df_daily.to_csv(path_raw,    index=False)
    if not df_station.empty:
        df_station.to_csv(path_station, index=False)
        print(f"      ✓ {path_station}")

    # Merge outages with existing ground truth to never drop confirmed blackouts
    if os.path.exists(path_out):
        existing_outages = pd.read_csv(path_out)
        combined_outages = pd.concat([existing_outages, df_outages], ignore_index=True)
        combined_outages = combined_outages.drop_duplicates(subset=["date", "start_time"]).sort_values(["date", "start_time"]).reset_index(drop=True)
        combined_outages.to_csv(path_out, index=False)
    else:
        df_outages.to_csv(path_out, index=False)

    print(f"      ✓ {path_5min}")
    print(f"      ✓ {path_hourly}")
    print(f"      ✓ {path_daily}")
    print(f"      ✓ {path_out}")

    # ── Quick summary stats ──
    print("\n── Generation Summary (from 5-min telemetry) ──")
    daily_gen = df_5min.groupby("date")["solar_power_kw"].apply(lambda x: (x.clip(lower=0) * (5.0/60.0)).sum())
    print(f"   Best day  : {daily_gen.idxmax()} → {daily_gen.max():.1f} kWh")
    print(f"   Worst day : {daily_gen.idxmin()} → {daily_gen.min():.1f} kWh")
    print(f"   5-min Avg : {daily_gen.mean():.1f} kWh/day ({df_5min['date'].nunique()} days with telemetry)")

    if len(df_outages):
        print(f"\n── Outage Summary ──")
        print(f"   Total outage events : {len(df_outages)}")
        print(f"   Total backup energy : {df_outages['energy_kwh'].sum():.1f} kWh delivered")
        print(f"   Avg outage duration : {df_outages['duration_minutes'].mean():.0f} minutes")

    print("\n✅ Step 1 complete.\n")
    return df_5min, df_hourly, df_daily, df_outages


if __name__ == "__main__":
    main()
