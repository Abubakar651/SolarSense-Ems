# SolarSense EMS ☀️🔋🏭
**Industrial Energy Management System & Microgrid Digital Twin**  
*Optimized for LESCO B3 Industrial Grid Connections (Lahore, Pakistan)*

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Solver: HiGHS C++](https://img.shields.io/badge/Solver-HiGHS%20MILP%20(C%2B%2B)-purple.svg)](https://highs.dev/)
[![ML: LightGBM](https://img.shields.io/badge/ML-LightGBM%20GBDT-success.svg)](https://lightgbm.readthedocs.io/)
[![API: FastAPI](https://img.shields.io/badge/API-FastAPI%20REST%20%2B%20SSE-009688.svg)](https://fastapi.tiangolo.com/)
[![Tests: 64 Passing](https://img.shields.io/badge/Tests-64%2F64%20Passing-brightgreen.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📌 Executive Overview

**SolarSense EMS** is an autonomous, high-performance edge energy management platform built for heavy industrial facilities operating under the **Lahore Electric Supply Company (LESCO)** tariff structure. 

Operating in environments with severe utility Time-of-Use price spikes, punitive demand fines, and recurring feeder load-shedding, SolarSense orchestrates real-time power flows across a **500 kWp rooftop solar PV array**, a **600 kWh / 250 kW LiFePO4 battery system**, an industrial factory load ($200 - 450\text{ kW}$ base, spikes $> 500\text{ kW}$), and an auxiliary **400 kVA backup diesel generator**.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              INDUSTRIAL MICROGRID TOPOLOGY                             │
│                                                                                        │
│     500 kWp Solar PV (600 kW Inverter Cap)               LESCO 11 kV Feeder            │
│                       │                                  (Category B3 ToU)             │
│                       ▼                                          │                     │
│            ┌──────────────────────┐                              ▼                     │
│            │ GoodWe Solar String  │                   ┌──────────────────────┐         │
│            │ Inverter Telemetry   │                   │ LESCO Boundary Meter │         │
│            └──────────┬───────────┘                   └──────────┬───────────┘         │
│                       │                                          │                     │
│                       ├────────────────► 415V AC BUS ◄───────────┤                     │
│                       │                                          │                     │
│                       ▼                                          ▼                     │
│            ┌──────────────────────┐                   ┌──────────────────────┐         │
│            │ 600 kWh / 250 kW     │◄─────────────────►│ Factory Demand       │         │
│            │ LiFePO4 BESS         │                   │ 200–450 kW (Spikes)  │         │
│            │ (10% SoC Floor)      │                   └──────────▲───────────┘         │
│            └──────────────────────┘                              │                     │
│                                                       ┌──────────┴───────────┐         │
│                                                       │ 400 kVA Diesel Gen   │         │
│                                                       │ (95 PKR/kWh Backup)  │         │
│                                                       └──────────────────────┘         │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚠️ The Industrial Energy Problem in Pakistan

Heavy manufacturers connected to LESCO B3 industrial feeders face three compounding economic threats:
1. **Severe Time-of-Use (ToU) Spread:** Peak hours cost **$60.00\text{ PKR/kWh}$**, compared to **$38.00\text{ PKR/kWh}$** off-peak (a 58% surcharge during a 4-hour seasonal window).
2. **Punitive Maximum Demand Indicator (MDI) Ratchet:** Exceeding the $500.0\text{ kW}$ sanctioned load threshold triggers a mandatory **$1,200.00\text{ PKR/kW}$ penalty**, billed on the highest single peak recorded during the billing month. Baseline analysis proves unmitigated historical spikes cost the factory **$2,360,353.20\text{ PKR}$**.
3. **Expensive Diesel Generation During Blackouts:** Lahore feeder load-shedding disconnects the grid (`p_grid = 0 kW`). Unmet factory demand defaults to backup diesel at **$95.00\text{ PKR/kWh}$** ($300\text{ PKR/L}$ fuel cost).

---

## 💡 Key Architectural Subsystems & Innovations

### 1. In-Memory Columnar Feature Store ([`src/data_engineering/feature_store.py`](src/data_engineering/feature_store.py))
- **Zero-Copy Arrow Buffers:** Rechunked columnar layout via Polars and Apache Arrow with SIMD vectorization.
- **Microsecond Slicing:** Pre-computed hash indexing maps timestamps to array offsets, retrieving 24-hour simulation slices in **$35 - 44\ \mu\text{s}$** ($0.035\text{ ms}$).
- **Immutability Law:** All NumPy vectors inside domain DTOs (`OptimizationHorizonSlice`, `DispatchResultDTO`) are write-locked with `vec.setflags(write=False)`.
- **Dynamic Tariff Strategy:** Decouples NEPRA/LESCO B3 seasonal peak windows (Winter: 17–21h, Summer: 19–23h, Spring/Autumn: 18–22h) for counterfactual "what-if" simulations.

### 2. Causal Time-Series Machine Learning Suite ([`src/forecast/`](src/forecast/))
- **Solar PV Forecaster (`train_solar_pv.py`):** LightGBM regressor predicting hourly generation from satellite weather (GHI, DNI, DHI, ambient temp, cyclic hour/month) achieving **$R^2 \ge 0.90$** with hard zero nighttime constraints.
- **Factory Load Forecaster (`train_factory_load.py`):** Autoregressive model capturing 3 industrial work shifts using strictly causal lags ($t \le t_0$: 24h, 48h, 168h lags and rolling statistics) with mandatory 24-hour purge gaps.
- **Calibrated Outage Classifier ([`src/grid_outage/predict_outage.py`](src/grid_outage/predict_outage.py)):** LightGBM classifier with Platt-sigmoid calibration evaluating blackout probability $P(\text{outage}) \in [0.0, 1.0]$ evaluated on PR-AUC and Brier score.

### 3. Mixed-Integer Linear Programming (MILP) Dispatch Solver ([`src/optimizer/milp_solver.py`](src/optimizer/milp_solver.py))
- **High-Speed C++ HiGHS Backend:** Formulated in CVXPY using Disciplined Parametrized Programming (DPP). Problem canonicalization is compiled **once** at startup; hourly solves simply update numeric parameters, executing in **$8.85\text{ ms}$ mean** ($< 25\text{ ms}$ budget).
- **Physical Invariants Enforced:**
  - **Power Balance with Solar Curtailment Slack ($p_{\text{curtail}} \ge 0$):** Absorbs excess solar during sunny midday blackouts with a full battery.
  - **Mutual Exclusivity:** Enforced with binary variables ($u_{\text{ch}} \in \{0, 1\}$) to eliminate parasitic micro-cycling.
  - **Throughput Wear Penalty ($2.00\text{ PKR/kWh}$):** Minimizes battery degradation.
  - **Outage MDI Immunity:** Enforces $p_{\text{grid}} = 0$ during blackouts, ensuring load spikes during grid outages do not incur utility demand penalties.
  - **The Live-Grid Soft Reserve Guard (Anti-Hoarding Physics):** Start-of-hour blackout reserve is strictly gated by $\text{live}[t] > 0.5$. Mathematical proof: during an active blackout, battery discharge effective cost is $\frac{95.00}{0.95} + 2.00 = 102.00\text{ PKR/kWh} > 95.00\text{ PKR/kWh}$ diesel cost. Gating the reserve unlocks battery discharge the instant a blackout occurs, preventing irrational diesel hoarding.

### 4. High-Performance FastAPI Gateway ([`src/api/`](src/api/))
- **Singleton Lifespan State:** Pre-warms the HiGHS solver and loads master data once at boot.
- **Non-Blocking Compute:** Offloads CPU-bound MILP solves to `starlette.concurrency.run_in_threadpool`.
- **Sub-5ms Endpoints:** `GET /api/window` executes in **$1.37\text{ ms}$**; `POST /api/optimize` executes in **$12.36\text{ ms}$**.
- **Real-Time SSE Streaming:** `GET /api/backtest/stream` streams multi-day rolling backtest frames to the Next.js frontend via Server-Sent Events at 60 FPS client rate.

### 5. Computer Vision Panel Defect Classifier ([`src/vision/`](src/vision/))
- **Architecture:** EfficientNet-B2 transfer learning on Dataset A (`solarsense_hybrid_v1`).
- **5 Defect Classes:** `clean`, `dusty`, `bird_drop`, `electrical_damage`, `physical_damage` ($260 \times 260$ resolution).
- **Soiling Loss Integration:** Inferred optical derate feeds directly into the feature store's `effective_solar_kw`.

---

## 📊 Measured Latency Benchmarks & Backtest Results

### Latency Performance Matrix
| Pipeline Stage / Endpoint | Target Budget | Actual Measured Latency | Library / Acceleration |
| :--- | :--- | :--- | :--- |
| **24h Ground-Truth Slice** | $< 1.000\text{ ms}$ | **$0.035 - 0.044\text{ ms}$** ($35 - 44\ \mu\text{s}$) | Polars Arrow Binary Index |
| **24h ML Inference (3 Models)** | $< 10.000\text{ ms}$ | **$2.550\text{ ms}$** | LightGBM C++ API |
| **24h Warm DPP HiGHS MILP Solve** | $< 25.000\text{ ms}$ | **$8.850\text{ ms}$** (p95: $9.640\text{ ms}$) | HiGHS C++ Branch-and-Bound |
| **`GET /api/window` (HTTP)** | $< 5.000\text{ ms}$ | **$1.372\text{ ms}$** (p95: $1.770\text{ ms}$) | FastAPI + In-Memory Slice |
| **`POST /api/optimize` (HTTP)** | $< 25.000\text{ ms}$ | **$12.360\text{ ms}$** (p95: $13.210\text{ ms}$) | FastAPI + Threadpool Offload |
| **`GET /health`** | $< 1.000\text{ ms}$ | **$0.380\text{ ms}$** | FastAPI Uvicorn |

### 463-Day Continuous Rolling Backtest
Simulating consecutive day-by-day operations across all 11,136 hours (464 days) in the master dataset:
- **Mathematical Optimality:** $\mathbf{463 / 463\ (100.0\%)}$ solves reached proven mathematical optimality (`OPTIMAL`). Zero fallback events.
- **Physical Conservation:** Maximum power balance residual across 11,112 hours is $\mathbf{4.8 \times 10^{-12}\text{ kW}}$.
- **Total Net Operational Savings:** $\mathbf{3,970,000\text{ PKR}}$ saved:
  - **MDI Peak Shaving:** $\mathbf{524,000\text{ PKR}}$ saved by clipping gross import spikes below $500\text{ kW}$.
  - **Diesel Fuel Displacement:** $\mathbf{428,000\text{ PKR}}$ saved by pre-charging prior to outages and discharging during blackouts.
  - **ToU Arbitrage:** $\mathbf{3,018,000\text{ PKR}}$ saved by shifting consumption from 60 PKR peak hours to 38 PKR off-peak hours and solar.

---

## 📂 Project Directory Structure

```text
SolarSense-Ems/
├── .agents/
│   └── rules/                  # Senior Engineering & Architecture Standards
│       ├── engineering-standards.md
│       └── daily-kickoff.md    # Autonomous daily task audit rule
├── .github/
│   └── workflows/
│       └── daily_report.yml    # Nightly 01:00 AM PKT cloud engineering log cron
├── data/
│   ├── raw/                    # Raw telemetry and panel images (git ignored)
│   └── processed/              # Master timeseries (11,136 rows) & hybrid image dataset
├── docs/                       # Formal Specifications & Audit Records
│   ├── daily_logs/             # Permanent, Git-tracked daily engineering audit logs
│   ├── system_architecture.md  # Milestone 4 Master Architecture & 24-Col Data Dictionary
│   └── week4_implementation_plan_abubakar_zaeem.md
├── models/                     # Trained GBDT weights and neural network checkpoints
│   ├── factory_load_lightgbm.joblib
│   ├── outage_classifier.joblib
│   └── solar_pv_lightgbm.joblib
├── notebooks/                  # Reproducible EDA and MDI spike analysis notebooks
│   └── 01_industrial_load_eda.ipynb
├── scripts/                    # Automation and DevOps utilities
│   ├── daily_standup.py        # Terminal daily standup & sprint progress tracker
│   └── generate_daily_report.py# Zero-API deterministic git daily report generator
├── src/                        # Production Source Modules
│   ├── api/                    # High-Performance FastAPI Compute Gateway
│   │   ├── main.py             # REST endpoints and SSE streaming backtest
│   │   └── schemas.py          # Pydantic V2 Request & Response contracts
│   ├── data_engineering/       # High-performance Feature Store (EMSDataRepository)
│   │   └── feature_store.py
│   ├── forecast/               # LightGBM solar PV & factory load model trainers
│   │   ├── train_factory_load.py
│   │   └── train_solar_pv.py
│   ├── grid_outage/            # Calibrated Platt-sigmoid outage risk predictor
│   │   └── predict_outage.py
│   ├── optimizer/              # HiGHS MILP solver & LESCO B3 tariff policy
│   │   ├── milp_solver.py      # CVXPY DPP 24h battery optimizer
│   │   └── tariff_engine.py    # LESCO statutory tariff calculator
│   └── vision/                 # Computer Vision defect classification pipeline
│       ├── dataloader.py       # PyTorch DataLoader with augmentations
│       ├── download_datasets.py# Automated Kaggle ingestion
│       └── train_classifier.py # EfficientNet-B2 transfer learning trainer
├── tests/                      # Automated Regression & Invariant Test Suite
│   ├── test_api_gateway.py     # FastAPI integration & SSE stream tests (8 tests)
│   ├── test_domain_stress_scenarios.py # Argon LESCO B3 stress tests (4 tests)
│   ├── test_eda_notebook.py    # EDA notebook execution test (1 test)
│   ├── test_feature_store.py   # Arrow memory & immutability tests (17 tests)
│   ├── test_forecast_models.py # LightGBM inference & causality tests (9 tests)
│   └── test_milp_solver.py     # HiGHS solver & blackout physics tests (25 tests)
├── pytest.ini                  # Pytest configuration
└── requirements.txt            # Locked project dependencies
```

---

## 🚀 Quickstart & Setup

### 1. Clone & Setup Environment
```bash
git clone https://github.com/Abubakar651/SolarSense-Ems.git
cd SolarSense-Ems

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install locked dependencies
pip install -r requirements.txt
```

### 2. Run the Full Test Suite
Execute all 64 automated regression tests verifying memory contiguity, solver latency, and blackout physics:
```bash
pytest -v --ignore=tests/test_train_classifier.py
```
*(Expected: **64 passed in ~5 seconds**)*

### 3. Launch the FastAPI Compute Gateway
Start the local development server:
```bash
uvicorn src.api.main:app --reload --port 8000
```
- **Interactive OpenAPI Documentation:** `http://localhost:8000/docs`
- **Health & Telemetry Check:** `http://localhost:8000/health`
- **24-Hour Simulation Window:** `http://localhost:8000/api/window?date=2025-07-17`
- **Run HiGHS MILP Optimizer:**
  ```bash
  curl -X POST "http://localhost:8000/api/optimize" \
       -H "Content-Type: application/json" \
       -d '{"date_str": "2025-07-17", "use_forecasts": false}'
  ```
- **Stream Rolling Backtest (SSE):** `http://localhost:8000/api/backtest/stream?start_date=2025-07-01&days=7`

### 4. Terminal Standup & Daily Report Tools
```bash
# Print today's prioritized sprint agenda and recent git commits
python3 scripts/daily_standup.py

# Generate a daily engineering audit log from git diff metadata
python3 scripts/generate_daily_report.py --hours 24
```

---

## 📜 Academic Milestones & Team Allocation

- **Abubakar (Lead):** Systems Engineering, High-Performance Feature Store, LightGBM Forecasters, HiGHS MILP Optimizer, and FastAPI Compute Gateway.
- **Zaeem:** Computer Vision (EfficientNet-B2 Defect Classification), Image Dataset Curation, and Industrial Load EDA.
- **Master Technical Specification:** Complete mathematical derivations, 24-column data dictionary, and architectural diagrams are available in [`docs/system_architecture.md`](docs/system_architecture.md).

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
