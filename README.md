# SolarSense EMS ☀️🔋🏡
**Autonomous Residential Energy Management System & Empirical Digital Twin**  
*Engineered for LESCO A-1 Residential ToU & Net-Metering (Lahore, Pakistan)*

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Solver: HiGHS C++](https://img.shields.io/badge/Solver-HiGHS%20MILP%20(C%2B%2B)-purple.svg)](https://highs.dev/)
[![ML: LightGBM](https://img.shields.io/badge/ML-LightGBM%20GBDT-success.svg)](https://lightgbm.readthedocs.io/)
[![CV: PyTorch EfficientNet-B2](https://img.shields.io/badge/CV-PyTorch%20EfficientNet--B2-red.svg)](https://pytorch.org/)
[![API: FastAPI](https://img.shields.io/badge/API-FastAPI%20REST%20%2B%20SSE-009688.svg)](https://fastapi.tiangolo.com/)
[![Tests: 81 Passing](https://img.shields.io/badge/Tests-81%2F81%20Passing-brightgreen.svg)](tests/)
[![Auditor: Argon Verified](https://img.shields.io/badge/Auditor-Argon%20Forensic%20Audit%20(100%25%20Pass)-teal.svg)](docs/DATASET_INSPECTION_AND_ARGON_AUDIT_BRIEF.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📌 Executive Overview

**SolarSense EMS** is an autonomous, high-performance edge energy management platform and empirical digital twin engineered specifically for residential grid connections operating under the **Lahore Electric Supply Company (LESCO)** tariff structure.

The platform is anchored to real-world empirical hardware telemetry from **Station LHR-RES-01** in Lahore, Pakistan ($31.52^\circ\text{ N}, 74.36^\circ\text{ E}$, Asia/Karachi UTC+05:00):
- **PV Generation:** $7.02\text{ kWp}$ DC Bifacial PV Array ($12 \times 585\text{ W}$, Canadian / Jinko Bifacial).
- **Hybrid Inverter:** GoodWe ES / ES-Uniq Low-Voltage Hybrid Inverter (SN: `9010KESC253L0146`, rated up to $10.0\text{ kW}$).
- **BESS Energy Storage:** $5.12\text{ kWh}$ LiFePO4 Battery Pack ($51.2\text{ V}, 100\text{ Ah}$, 1C / $5.0\text{ kW}$ charge/discharge rating, 15% reserve floor).
- **Tariff Framework:** LESCO / NEPRA Residential Tariff A-1 Time-of-Use (ToU) & Net-Metering:
  - **Peak Hours (18:00–22:00 PKT):** **$46.85\text{ PKR/kWh}$**
  - **Off-Peak Hours (00:00–18:00 & 22:00–24:00 PKT):** **$34.53\text{ PKR/kWh}$**
  - **Net-Metering Export Credit:** **$27.00\text{ PKR/kWh}$**
  - **Sanctioned Connected Load:** **$10.0\text{ kW}$**

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   STATION LHR-RES-01 RESIDENTIAL MICROGRID TOPOLOGY                    │
│                                                                                        │
│   Bifacial PV Array (7.02 kWp)                             LESCO Grid Feeder           │
│   (12 x 585W DC Bifacial)                                  (Tariff A-1 ToU)            │
│              │                                                     │                   │
│              ▼                                                     ▼                   │
│   ┌─────────────────────────┐                           ┌─────────────────────┐        │
│   │  GoodWe Hybrid Inverter │                           │ Bidirectional Meter │        │
│   │  (SN: 9010KESC253L0146) │                           │ (Net-Metering ToU)  │        │
│   └────────────┬────────────┘                           └──────────┬──────────┘        │
│                │                                                   │                   │
│                ├──────────────────► AC COMMON BUS ◄────────────────┤                   │
│                │                                                   │                   │
│                ▼                                                   ▼                   │
│   ┌─────────────────────────┐                           ┌─────────────────────┐        │
│   │   5.12 kWh LiFePO4 BESS │◄─────────────────────────►│  Household Demand  │        │
│   │   (51.2V 100Ah / 15% Fl)│                           │  (Connected Load)   │        │
│   └─────────────────────────┘                           └─────────────────────┘        │
│                                                                                        │
│   * Anti-Islanding Protection: Zero grid draw & zero export during outages             │
│   * Post-Blackout Peak Suppression: Grid import capped at load during Peak ToU         │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚠️ The Residential Energy Problem in Lahore, Pakistan

Urban residential prosumers in Lahore face four compounding operational and financial challenges:

1. **Severe Peak Time-of-Use Surcharge:** LESCO A-1 ToU charges **$46.85\text{ PKR/kWh}$** during the 4-hour evening peak (18:00–22:00 PKT), a **35.7% surcharge** over the off-peak rate of **$34.53\text{ PKR/kWh}$**.
2. **Asymmetric Net-Metering Arbitrage:** Exporting surplus solar to the grid yields only **$27.00\text{ PKR/kWh}$**, while purchasing power during evening hours costs **$46.85\text{ PKR/kWh}$** (a 73.5% premium to buy back exported energy). Storing midday solar surplus in the battery yields a net arbitrage margin of **$+12.96\text{ PKR/kWh cycled}$** ($0.853 \times 46.85 - 27.00$).
3. **Frequent Feeder Blackouts & Anti-Islanding:** Unscheduled distribution feeder outages disconnect the grid (`outage_flag == 1`). Inverter anti-islanding mandates $p_{\text{grid}} = 0\text{ kW}$ and $p_{\text{export}} = 0\text{ kW}$. The battery must dynamically manage state-of-charge (SoC) to supply critical domestic loads throughout outages without depleting below the 15% reserve floor.
4. **GoodWe Stock Firmware Flaw (Peak Grid Recharge Waste):** Empirical telemetry on October 26, 2026 proved that GoodWe's default firmware draws up to **$3.18\text{ kW}$ from the grid** immediately after a blackout during peak hours ($18:25\text{ PKT}$) to top off a 95% full battery at the punitive rate of $46.85\text{ PKR/kWh}$. SolarSense EMS enforces **Post-Blackout Peak Recharge Suppression** ($p_{\text{grid}}[t] \le \text{load}[t]$ when $\text{SoC} \ge 15\%$), saving **27.64% per day** ($517.46\text{ PKR/day}$).

---

## 💡 Key Architectural Subsystems & Innovations

### 1. In-Memory Columnar Feature Store ([`src/data_engineering/feature_store.py`](src/data_engineering/feature_store.py))
*Engineered by Abubakar*
- **Zero-Copy Arrow Buffers:** Rechunked columnar layout via Polars and Apache Arrow with SIMD vectorization.
- **Microsecond Slicing:** Pre-computed hash indexing maps timestamps to array offsets, retrieving 24-hour simulation slices in **$35 - 44\ \mu\text{s}$** ($0.035\text{ ms}$).
- **Immutability Law:** All NumPy vectors inside domain DTOs (`OptimizationHorizonSlice`, `DispatchResultDTO`) are write-locked with `vec.setflags(write=False)`.
- **Dynamic Tariff Strategy:** Encapsulates NEPRA/LESCO A-1 ToU schedules (Peak: 18:00–22:00, Off-Peak: 00:00–18:00 & 22:00–24:00, Net-Metering: 27.00 PKR/kWh) for deterministic financial accounting.

### 2. Causal Time-Series Machine Learning Suite ([`src/forecast/`](src/forecast/) & [`src/grid_outage/`](src/grid_outage/))
*Engineered by Abubakar*
- **Solar PV Forecaster (`train_solar_pv.py`):** LightGBM regressor predicting hourly generation from satellite weather (GHI, DNI, DHI, ambient temp, cyclic hour/month) achieving **$R^2 \ge 0.90$** with hard zero nighttime constraints.
- **Calibrated Outage Classifier (`predict_outage.py`):** LightGBM classifier with Platt-sigmoid calibration evaluating blackout probability $P(\text{outage}) \in [0.0, 1.0]$, evaluated on PR-AUC and Brier score.
- **Strict Causality ($t \le t_0$):** All features enforce strict causal boundaries with mandatory 24-hour purge gaps between splits.

### 3. Mixed-Integer Linear Programming (MILP) Dispatch Solver ([`src/optimizer/milp_solver.py`](src/optimizer/milp_solver.py))
*Engineered by Abubakar*
- **High-Speed C++ HiGHS Backend:** Formulated in CVXPY using Disciplined Parametrized Programming (DPP). Problem canonicalization is compiled **once** at startup; hourly solves simply update numeric parameters, executing in **$12.06\text{ ms}$ mean** ($< 25\text{ ms}$ budget).
- **Physical Invariants Enforced:**
  - **Power Balance with Solar Curtailment Slack ($p_{\text{curtail}} \ge 0$):** Absorbs excess solar during sunny midday blackouts with a full battery.
  - **Mutual Exclusivity:** Enforced with binary variables ($u_{\text{ch}} \in \{0, 1\}$) to eliminate parasitic micro-cycling.
  - **Throughput Wear Penalty ($2.00\text{ PKR/kWh}$):** Minimizes battery degradation.
  - **Anti-Islanding Blackout Isolation:** During outages (`outage_flag == 1`), strictly enforces $p_{\text{grid}} = 0\text{ kW}$ and $p_{\text{export}} = 0\text{ kW}$.
  - **Live-Grid Soft Reserve Guard (Anti-Hoarding Physics):** Start-of-hour blackout reserve is strictly gated by $\text{live}[t] > 0.5$. Gating the reserve unlocks battery discharge the instant a blackout occurs, preventing unserved domestic load.
  - **Post-Blackout Peak Recharge Suppression:** Capping peak grid import ($p_{\text{grid}}[t] \le \text{load}[t]$) during Peak ToU hours (18:00–22:00) when $\text{SoC} \ge 15\%$ prevents grid-to-battery charging at 46.85 PKR/kWh. Eliminates the GoodWe stock firmware flaw and delivers **27.64% daily savings**.

### 4. High-Performance FastAPI Compute Gateway ([`src/api/`](src/api/))
*Engineered by Abubakar*
- **Singleton Lifespan State:** Pre-warms the HiGHS solver and loads master data once at boot.
- **Non-Blocking Compute:** Offloads CPU-bound MILP solves to `starlette.concurrency.run_in_threadpool`.
- **Sub-5ms Endpoints:** `GET /api/window` executes in **$1.37\text{ ms}$**; `POST /api/optimize` executes in **$12.36\text{ ms}$**.
- **Real-Time SSE Streaming:** `GET /api/backtest/stream` streams multi-day rolling backtest frames to the frontend via Server-Sent Events at 60 FPS client rate.

### 5. Independent Forensic Energy Audit by Argon ([`docs/DATASET_INSPECTION_AND_ARGON_AUDIT_BRIEF.md`](docs/DATASET_INSPECTION_AND_ARGON_AUDIT_BRIEF.md))
*Audited by Argon (Principal Microgrid Architect & Power Systems Data Auditor)*
- **16-Month Macroscopic Energy Balance (Pass):** $\sum \text{Load} (16,127.5\text{ kWh}) = \text{PV} (12,135.1) + \text{Purchased} (10,404.2) - \text{Sold} (5,243.2) - \text{Losses} (1,168.6\text{ kWh})$. Physical loss residual of **$2.42\text{ kWh/day}$** ($5.18\%$ of gross input) decomposes into inverter tare ($1.56\text{ kWh/day}$), BESS dissipation ($0.44\text{ kWh/day}$), and conversion losses ($0.42\text{ kWh/day}$).
- **Zero Nocturnal / Phantom Solar (Pass):** Strictly $0.000000\text{ kW}$ across all 5,193 zero-GHI and night hours.
- **Blackout Feeder Isolation & Islanding (Pass):** Zero grid import or export across all 48 blackout hours.
- **Physical Storage Bounds (Pass):** 113 confirmed blackout events with 0 breaches of the $5.12\text{ kWh}$ battery capacity ceiling ($\max \le 3.73\text{ kWh}$).
- **Telemetry Ingestion Sanity (Pass):** Continuous 5-minute station telemetry ending cleanly with 100% battery SoC.

---

## 🔍 Computer Vision Panel Defect Classification ([`src/vision/`](src/vision/))
*Engineered by Zaeem*

The computer vision subsystem acts as an optical health monitor for the solar PV array, diagnosing physical defects, environmental soiling, and degradation to calculate dynamic optical derate coefficients for the EMS feature store.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DATASET A & COMPUTER VISION PIPELINE ARCHITECTURE               │
│                                                                                        │
│   Kaggle Sources:                                                                      │
│   • alicjalena (PV Defect Dataset - 1,574 imgs)                                        │
│   • hemanthsai7 (Dust Detection - 2,562 imgs)                                          │
│                                │                                                       │
│                                ▼                                                       │
│   ┌────────────────────────────────────────────────────────────┐                       │
│   │   Rigorous Protocol 1 Curation Engine (build_hybrid_dataset)│                       │
│   │   • SHA-256 byte deduplication (1,026 exact duplicates dropped)│                   │
│   │   • 64-bit dHash perceptual pruning (329 near-dupes removed) │                       │
│   │   • Climate context pruning (262 snow images discarded)     │                       │
│   │   • Color space unification (RGBA/palette -> 3-channel RGB)│                       │
│   └────────────────────────────┬───────────────────────────────┘                       │
│                                │                                                       │
│                                ▼                                                       │
│   ┌────────────────────────────────────────────────────────────┐                       │
│   │   Stratified Leak-Free ImageFolder Layout (solarsense_v1)  │                       │
│   │   • 5 Classes (>= 10% each): Clean, Dusty, Bird Drop,      │                       │
│   │     Electrical Damage, Physical Damage                     │                       │
│   │   • Split Ratio: 70% Train / 15% Val / 15% Test            │                       │
│   └────────────────────────────┬───────────────────────────────┘                       │
│                                │                                                       │
│                                ▼                                                       │
│   ┌────────────────────────────────────────────────────────────┐                       │
│   │   PyTorch High-Performance DataLoader (src/vision/dataloader)│                       │
│   │   • Resize to 260x260 px (EfficientNet-B2 native geometry) │                       │
│   │   • Label-safe RandomHorizontalFlip & RandomVerticalFlip   │                       │
│   │   • ImageNet normalization (mean=[0.485, 0.456, 0.406])    │                       │
│   │   • Cross-split class indexing synchronization assertion   │                       │
│   └────────────────────────────┬───────────────────────────────┘                       │
│                                │                                                       │
│                                ▼                                                       │
│   ┌────────────────────────────────────────────────────────────┐                       │
│   │   EfficientNet-B2 Fine-Tuning Engine (train_classifier.py)  │                       │
│   │   • ImageNet-1K pretrained backbone (full fine-tuning)     │                       │
│   │   • Adapted linear classification head: Linear(1408, 5)    │                       │
│   │   • Adam Optimizer (lr=3e-4) + CosineAnnealingLR (T_max=15) │                       │
│   │   • Checkpoint selection on Validation Macro-F1 score      │                       │
│   │   • Target: Test Accuracy >= 94.0%, Macro-F1 >= 0.92       │                       │
│   └────────────────────────────────────────────────────────────┘                       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Key Technical Innovations:
1. **Protocol 1 Dataset Curation & Deduplication:** Raw pool of 4,136 images audited for byte-level and perceptual duplicates using 64-bit difference hashing (`dHash` Hamming distance $\le 2$). Pruned 262 snow images (unrealistic for Lahore). Enforced 5 balanced classes ($\ge 10\%$ representation each).
2. **Defensive PyTorch DataLoader Architecture ([`src/vision/dataloader.py`](src/vision/dataloader.py)):** Orientation-invariant label-safe transforms (`RandomHorizontalFlip`, `RandomVerticalFlip`) with automated cross-split class indexing synchronization assertions.
3. **Macro-F1 Supervised Training & Checkpointing ([`src/vision/train_classifier.py`](src/vision/train_classifier.py)):** Checkpointing monitors Validation Macro-F1 to equally penalize false negatives on critical structural defects.
4. **Automated Unit Testing ([`tests/test_train_classifier.py`](tests/test_train_classifier.py)):** Synthetic image fixture verifies state dict saving, class indexing round-trips, and logit tensor shapes `[B, 5]`.

---

## 📊 Measured Latency Benchmarks & Performance Matrix

### Latency Performance Matrix
| Pipeline Stage / Endpoint | Target Budget | Actual Measured Latency | Library / Acceleration |
| :--- | :--- | :--- | :--- |
| **24h Telemetry Slice Retrieval** | $< 1.000\text{ ms}$ | **$0.035 - 0.044\text{ ms}$** ($35 - 44\ \mu\text{s}$) | Polars Arrow Binary Index |
| **24h ML Inference (Solar + Outage)** | $< 10.000\text{ ms}$ | **$2.550\text{ ms}$** | LightGBM C++ API |
| **24h Warm DPP HiGHS MILP Solve** | $< 25.000\text{ ms}$ | **$12.060\text{ ms}$** (p95: $15.200\text{ ms}$) | HiGHS C++ Branch-and-Bound |
| **`GET /api/window` (HTTP)** | $< 5.000\text{ ms}$ | **$1.372\text{ ms}$** (p95: $1.770\text{ ms}$) | FastAPI + In-Memory Slice |
| **`POST /api/optimize` (HTTP)** | $< 25.000\text{ ms}$ | **$12.360\text{ ms}$** (p95: $14.100\text{ ms}$) | FastAPI + Threadpool Offload |
| **`GET /health`** | $< 1.000\text{ ms}$ | **$0.380\text{ ms}$** | FastAPI Uvicorn |

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
├── archive/
│   └── legacy_industrial/      # Archived LESCO B3 Industrial Simulation & Notebooks
│       ├── data/factory_load/
│       ├── notebooks/01_industrial_load_eda.ipynb
│       ├── src/data_engineering/build_factory_load.py
│       ├── src/forecast/train_factory_load.py
│       └── tests/test_eda_notebook.py
├── data/
│   ├── raw/                    # Raw telemetry and panel images (git ignored)
│   └── processed/              # Processed timeseries & hybrid image dataset
│       ├── master_ems_timeseries.csv
│       └── panel_images/
│           ├── solarsense_master_v1/ # Curated 635-image leak-free dataset
│           └── solarsense_hybrid_v1/ # 5-class stratified train/val/test splits
├── docs/                       # Formal Specifications & Audit Records
│   ├── ARGON_AUDIT_PROMPT.md   # Prompt template for Argon audit sessions
│   ├── DATASET_INSPECTION_AND_ARGON_AUDIT_BRIEF.md # Argon forensic audit brief
│   ├── daily_logs/             # Permanent, Git-tracked daily engineering audit logs
│   ├── samples/                # High-resolution verification charts & sample grids
│   ├── dataset_A_panel_images.md     # Protocol 1 image curation audit
│   └── system_architecture.md        # Master Architecture & Data Dictionary
├── models/                     # Trained GBDT weights and neural network checkpoints
│   ├── efficientnet_b2_defects.pth   # Best PyTorch model (val macro-F1 selected)
│   ├── outage_classifier.joblib
│   └── solar_pv_lightgbm.joblib
├── scripts/                    # Automation and DevOps utilities
│   ├── create_argon_audit_bundle.py  # Zero-leakage codebase & telemetry archiver
│   ├── ingest_sems_agent_data.py     # Live SEMS Portal 5-min telemetry parser
│   ├── daily_standup.py        # Terminal daily standup & sprint progress tracker
│   └── generate_daily_report.py# Zero-API deterministic git daily report generator
├── src/                        # Production Source Modules
│   ├── api/                    # High-Performance FastAPI Compute Gateway (Abubakar)
│   │   ├── main.py             # REST endpoints and SSE streaming backtest
│   │   └── schemas.py          # Pydantic V2 Request & Response contracts
│   ├── data_engineering/       # High-performance Feature Store (Abubakar)
│   │   └── feature_store.py    # EMSDataRepository with microsecond slicing
│   ├── forecast/               # Causal ML Forecasters (Abubakar)
│   │   └── train_solar_pv.py   # Physics-bounded solar PV GBDT
│   ├── grid_outage/            # Calibrated Outage Risk Predictor (Abubakar)
│   │   └── predict_outage.py   # Platt-scaled blackout classifier
│   ├── optimizer/              # HiGHS MILP Solver & Tariff Engine (Abubakar)
│   │   ├── milp_solver.py      # CVXPY DPP 24h battery optimizer with reserve guard
│   │   └── tariff_engine.py    # Statutory ToU tariff calculator
│   └── vision/                 # Computer Vision Defect Pipeline (Zaeem)
│       ├── build_hybrid_dataset.py # SHA256 & dHash deduplication engine
│       ├── build_master_dataset.py # Raw Kaggle harvester & color normalizer
│       ├── dataloader.py       # PyTorch DataLoader with label-safe flip transforms
│       ├── download_datasets.py# Automated Kaggle dataset ingestion
│       ├── train_classifier.py # EfficientNet-B2 transfer learning & macro-F1 trainer
│       └── verify_dataset_a.py # Protocol 1 compliance & leakage test script
├── tests/                      # Automated Regression & Invariant Test Suite (81 Tests)
│   ├── test_api_gateway.py     # FastAPI integration & SSE stream tests (8 tests)
│   ├── test_argon_audit_fixes.py # Post-audit residential invariants & latency (6 tests)
│   ├── test_domain_stress_scenarios.py # Grid outage & ToU stress tests (4 tests)
│   ├── test_feature_store.py   # Arrow memory & immutability tests (17 tests)
│   ├── test_forecast_models.py # LightGBM inference & causality tests (9 tests)
│   ├── test_milp_solver.py     # HiGHS solver & blackout physics tests (33 tests)
│   └── test_train_classifier.py# PyTorch defect classifier trainer tests (4 tests)
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
Execute the automated regression test suite verifying Arrow memory contiguity, solver latency, blackout physics, and post-blackout recharge suppression:
```bash
pytest -v --ignore=tests/test_train_classifier.py
```
*(Expected: **77 passed in ~10 seconds**)*

> Note: `tests/test_train_classifier.py` requires PyTorch and Torchvision installed. To run with PyTorch enabled:
> ```bash
> pytest -v tests/test_train_classifier.py
> ```
> *(Combined: **81 passed**)*

### 3. Run the Computer Vision Training & Verification Pipeline
```bash
# 1. Verify Dataset A Protocol 1 compliance & zero leakage
python3 src/vision/verify_dataset_a.py

# 2. Test the PyTorch DataLoaders and inspect tensor shapes
python3 src/vision/dataloader.py

# 3. Train the EfficientNet-B2 Defect Classifier with Cosine Annealing LR
python3 src/vision/train_classifier.py
```

### 4. Launch the FastAPI Compute Gateway
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

### 5. Ingest Live Telemetry
```bash
# Ingest live GoodWe SEMS Portal 5-minute telemetry
python3 scripts/ingest_sems_agent_data.py
```

---

## 👥 Engineering Team & Domain Ownership

SolarSense EMS is collaboratively engineered by:

| Engineer | Core Responsibilities & Commits | Key Deliverables & Modules |
| :--- | :--- | :--- |
| **Abubakar**<br>*(Team Lead / Systems & Optimization)* | • High-Performance Feature Store<br>• Causal Solar Time-Series Forecasting Models<br>• HiGHS C++ MILP Residential Battery Optimizer<br>• FastAPI Compute Gateway & SSE Streaming<br>• Post-Blackout Peak Recharge Suppression<br>• Argon Forensic Energy Audit Integration | • [`src/data_engineering/feature_store.py`](src/data_engineering/feature_store.py)<br>• [`src/forecast/train_solar_pv.py`](src/forecast/train_solar_pv.py)<br>• [`src/optimizer/milp_solver.py`](src/optimizer/milp_solver.py)<br>• [`src/api/main.py`](src/api/main.py) & [`schemas.py`](src/api/schemas.py)<br>• [`docs/DATASET_INSPECTION_AND_ARGON_AUDIT_BRIEF.md`](docs/DATASET_INSPECTION_AND_ARGON_AUDIT_BRIEF.md) |
| **Zaeem**<br>*(Computer Vision & Solar Analytics)* | • Dataset A Solar Panel Image Curation<br>• PyTorch DataLoaders & Augmentations<br>• EfficientNet-B2 Defect Classification<br>• Macro-F1 Checkpointing Engine | • [`src/vision/dataloader.py`](src/vision/dataloader.py)<br>• [`src/vision/train_classifier.py`](src/vision/train_classifier.py)<br>• [`tests/test_train_classifier.py`](tests/test_train_classifier.py)<br>• [`docs/dataset_A_panel_images.md`](docs/dataset_A_panel_images.md) |

---

## 📦 Historical Benchmark & Archive

Prior proof-of-concept simulation studies investigating an industrial factory microgrid benchmark ($500\text{ kWp}$ solar array, $600\text{ kWh}$ BESS, LESCO B3 industrial Time-of-Use tariff with Maximum Demand Indicator ratchet penalties) have been segregated into [`archive/legacy_industrial/`](archive/legacy_industrial/) for historical reference:
- `archive/legacy_industrial/notebooks/01_industrial_load_eda.ipynb`
- `archive/legacy_industrial/src/forecast/train_factory_load.py`
- `archive/legacy_industrial/src/data_engineering/build_factory_load.py`
- `archive/legacy_industrial/tests/test_eda_notebook.py`

This separation ensures the core SolarSense EMS repository remains strictly focused on the empirical **Station LHR-RES-01** digital twin and residential edge deployment.

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
