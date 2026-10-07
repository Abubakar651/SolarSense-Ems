# SolarSense EMS 🌞🔋
**AI-Powered Industrial Digital Twin & Energy Management System**

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Status](https://img.shields.io/badge/Status-Phase%201%20Complete-success.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

SolarSense EMS is an intelligent "Digital Twin" application designed to sit on top of standard hybrid solar inverters (e.g., GoodWe). By ingesting raw inverter telemetry, live satellite weather, and official utility tariffs, the AI acts as an intelligent brain—optimizing battery storage to save money, predicting factory load spikes, and visually diagnosing hardware defects.

## ⚠️ The Problem
Industrial consumers in Pakistan (LESCO B3) face severe financial challenges:
1. **Time-of-Use Tariffs:** Peak grid power costs **60 PKR/kWh**, while off-peak is 38 PKR.
2. **MDI Penalties:** Exceeding Sanctioned Demand limits (e.g., 500 kW) results in a **1,200 PKR/kW penalty**.
3. **Invisible Soiling:** Dust accumulation silently reduces yield, but managers don't know mathematically when to hire a cleaning crew (Cost: ~15,000 PKR).

## 💡 The Solution
This repository contains the data engineering and AI modeling pipelines to simulate an autonomous Energy Management System that solves these issues.

### Key Features
*   **True Financial Simulator:** Tracks exact PKR grid costs, diesel backup costs (at 95 PKR/kWh), and MDI penalties hour-by-hour.
*   **MDI Penalty Avoidance:** AI predictive logic that discharges the battery to keep grid draw below the sanctioned limit.
*   **Automated Maintenance Alerts:** A dynamic physics trigger that alerts the user exactly when a panel wash becomes mathematically profitable.
*   **Visual Defect Dashboard:** An interface powered by a CNN to instantly classify dust, bird droppings, and physical damage on solar panels.

## 📂 Project Structure
```text
SolarSense-Ems/
├── data/
│   ├── raw/                 # Raw GoodWe inverter reports and raw images (ignored in git)
│   └── processed/           # Master EMS feature store (11,136 hours) and clean datasets
├── docs/                    # Documentation, dataset audits, and agent architectures
├── notebooks/               # Jupyter notebooks for Exploratory Data Analysis (EDA)
├── src/                     # Core Python modules
│   ├── data_engineering/    # Data parsers, load synthesizers, and feature fusion
│   ├── forecast/            # Open-Meteo satellite weather API clients
│   ├── optimizer/           # Tariff engines and LESCO TOU configurations
│   ├── soiling/             # Physics-based dust degradation models
│   └── vision/              # Image hashing, deduplication, and preprocessing
└── tests/                   # Unit tests for data integrity
```

## 🚀 Quickstart
1. Clone the repository:
   ```bash
   git clone https://github.com/Abubakar651/SolarSense-Ems.git
   cd SolarSense-Ems
   ```
2. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the data fusion pipeline to generate the Master Feature Store:
   ```bash
   python3 src/data_engineering/build_master_feature_store.py
   python3 src/data_engineering/apply_nepra_tariffs.py
   ```

## 📈 Phase 1 Validation
The 464-day dataset has been successfully processed. The baseline scan reveals that without the AI, the target factory incurred **over 2.3 Million PKR in MDI penalties** and over **171 days** where dust caused severe financial loss.

**Next Up:** Phase 2 (AI & Agent Development). See `docs/agents.md` for the architecture.
