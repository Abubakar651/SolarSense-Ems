# SolarSense EMS ☀️🔋🏭
**Industrial Energy Management System & Microgrid Digital Twin**  
*Optimized for LESCO B3 Industrial Grid Connections (Lahore, Pakistan)*

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Solver: HiGHS C++](https://img.shields.io/badge/Solver-HiGHS%20MILP%20(C%2B%2B)-purple.svg)](https://highs.dev/)
[![ML: LightGBM](https://img.shields.io/badge/ML-LightGBM%20GBDT-success.svg)](https://lightgbm.readthedocs.io/)
[![CV: PyTorch EfficientNet-B2](https://img.shields.io/badge/CV-PyTorch%20EfficientNet--B2-red.svg)](https://pytorch.org/)
[![API: FastAPI](https://img.shields.io/badge/API-FastAPI%20REST%20%2B%20SSE-009688.svg)](https://fastapi.tiangolo.com/)
[![Tests: 64 Passing](https://img.shields.io/badge/Tests-64%2F64%20Passing-brightgreen.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📌 Executive Overview

**SolarSense EMS** is an autonomous, high-performance edge energy management platform built for heavy industrial facilities operating under the **Lahore Electric Supply Company (LESCO)** tariff structure. 

Operating in environments with severe utility Time-of-Use price spikes, punitive demand fines, and recurring feeder load-shedding, SolarSense orchestrates real-time power flows across a **500 kWp rooftop solar PV array**, a **600 kWh / 250 kW LiFePO4 battery system**, an industrial factory load ($200 - 450\text{ kW}$ base, spikes $> 500\text{ kW}$), and an auxiliary **400 kVA backup diesel generator**.

```text
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
*Engineered by Abubakar*
- **Zero-Copy Arrow Buffers:** Rechunked columnar layout via Polars and Apache Arrow with SIMD vectorization.
- **Microsecond Slicing:** Pre-computed hash indexing maps timestamps to array offsets, retrieving 24-hour simulation slices in **$35 - 44\ \mu\text{s}$** ($0.035\text{ ms}$).
- **Immutability Law:** All NumPy vectors inside domain DTOs (`OptimizationHorizonSlice`, `DispatchResultDTO`) are write-locked with `vec.setflags(write=False)`.
- **Dynamic Tariff Strategy:** Decouples NEPRA/LESCO B3 seasonal peak windows (Winter: 17–21h, Summer: 19–23h, Spring/Autumn: 18–22h) for counterfactual "what-if" simulations.

### 2. Causal Time-Series Machine Learning Suite ([`src/forecast/`](src/forecast/) & [`src/grid_outage/`](src/grid_outage/))
*Engineered by Abubakar*
- **Solar PV Forecaster (`train_solar_pv.py`):** LightGBM regressor predicting hourly generation from satellite weather (GHI, DNI, DHI, ambient temp, cyclic hour/month) achieving **$R^2 \ge 0.90$** with hard zero nighttime constraints.
- **Factory Load Forecaster (`train_factory_load.py`):** Autoregressive model capturing 3 industrial work shifts using strictly causal lags ($t \le t_0$: 24h, 48h, 168h lags and rolling statistics) with mandatory 24-hour purge gaps.
- **Calibrated Outage Classifier (`predict_outage.py`):** LightGBM classifier with Platt-sigmoid calibration evaluating blackout probability $P(\text{outage}) \in [0.0, 1.0]$ evaluated on PR-AUC and Brier score.

### 3. Mixed-Integer Linear Programming (MILP) Dispatch Solver ([`src/optimizer/milp_solver.py`](src/optimizer/milp_solver.py))
*Engineered by Abubakar*
- **High-Speed C++ HiGHS Backend:** Formulated in CVXPY using Disciplined Parametrized Programming (DPP). Problem canonicalization is compiled **once** at startup; hourly solves simply update numeric parameters, executing in **$8.85\text{ ms}$ mean** ($< 25\text{ ms}$ budget).
- **Physical Invariants Enforced:**
  - **Power Balance with Solar Curtailment Slack ($p_{\text{curtail}} \ge 0$):** Absorbs excess solar during sunny midday blackouts with a full battery.
  - **Mutual Exclusivity:** Enforced with binary variables ($u_{\text{ch}} \in \{0, 1\}$) to eliminate parasitic micro-cycling.
  - **Throughput Wear Penalty ($2.00\text{ PKR/kWh}$):** Minimizes battery degradation.
  - **Outage MDI Immunity:** Enforces $p_{\text{grid}} = 0$ during blackouts, ensuring load spikes during grid outages do not incur utility demand penalties.
  - **The Live-Grid Soft Reserve Guard (Anti-Hoarding Physics):** Start-of-hour blackout reserve is strictly gated by $\text{live}[t] > 0.5$. Mathematical proof: during an active blackout, battery discharge effective cost is $\frac{95.00}{0.95} + 2.00 = 102.00\text{ PKR/kWh} > 95.00\text{ PKR/kWh}$ diesel cost. Gating the reserve unlocks battery discharge the instant a blackout occurs, preventing irrational diesel hoarding.

### 4. High-Performance FastAPI Compute Gateway ([`src/api/`](src/api/))
*Engineered by Abubakar*
- **Singleton Lifespan State:** Pre-warms the HiGHS solver and loads master data once at boot.
- **Non-Blocking Compute:** Offloads CPU-bound MILP solves to `starlette.concurrency.run_in_threadpool`.
- **Sub-5ms Endpoints:** `GET /api/window` executes in **$1.37\text{ ms}$**; `POST /api/optimize` executes in **$12.36\text{ ms}$**.
- **Real-Time SSE Streaming:** `GET /api/backtest/stream` streams multi-day rolling backtest frames to the Next.js frontend via Server-Sent Events at 60 FPS client rate.

---

## 🔍 Computer Vision Panel Defect Classification ([`src/vision/`](src/vision/))
*Engineered by Zaeem*

The computer vision subsystem acts as an optical health monitor for the 500 kWp rooftop solar PV array, diagnosing physical defects, environmental soiling, and degradation to calculate dynamic optical derate coefficients for the EMS feature store.

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
1. **Protocol 1 Dataset Curation & Deduplication:**
   - Raw multi-source pool of 4,136 images was audited for byte-level and perceptual duplicates.
   - **Cross-Dataset Conflict Resolution:** Perceptual 64-bit difference hashing (`dHash` with Hamming distance $\le 2$) resolved critical label conflicts where identical panel photos were labeled "Dusty" in one repository and "Bird-drop" in another.
   - **Climate Adaptation:** Pruned 262 snow-covered images since Lahore's subtropical semi-arid climate experiences zero snowfall.
   - **Class Balance Enforcement:** Structured into 5 balanced classes satisfying the strict $\ge 10\%$ representation requirement: `Clean` (210), `Dusty` (210), `Electrical Damage` (78), `Bird Drop` (73), and `Physical Damage` (64).
2. **Defensive PyTorch DataLoader Architecture ([`src/vision/dataloader.py`](src/vision/dataloader.py)):**
   - **Orientation Invariance:** In solar panel defect recognition, cell cracks and bird drops appear identical under rotation. The training pipeline applies both `RandomHorizontalFlip` and `RandomVerticalFlip` as label-safe data augmentations.
   - **Class Index Synchronization Guard:** Automatically asserts `dataset.class_to_idx == loaders["train"].dataset.class_to_idx` across validation and holdout splits, preventing silent label drift if an OS directory traversal orders folders differently.
3. **Macro-F1 Supervised Training & Checkpointing ([`src/vision/train_classifier.py`](src/vision/train_classifier.py)):**
   - Because clean and dusty panels naturally outnumber rare severe physical cracks (~3:1 ratio), standard accuracy creates a false sense of security. Training checkpointing strictly monitors **Validation Macro-F1** to ensure equal penalization of false negatives on critical structural defects.
   - Checkpoints save complete metadata dictionaries: `model_state_dict`, `class_to_idx`, `arch="efficientnet_b2"`, `image_size=260`, `epoch`, `val_metrics`, and `trained_at`.
4. **Automated Unit Testing ([`tests/test_train_classifier.py`](tests/test_train_classifier.py)):**
   - Implements a fast synthetic image fixture generating test batches to verify state dictionary saving, class indexing round-trips, logit tensor dimensions `[B, 5]`, metric ratio boundaries, and missing split exception handling.

---

## 📈 Industrial Load Profiling, Shift Analytics & MDI Spike Physics
*Exploratory Data Analysis by Zaeem ([`notebooks/01_industrial_load_eda.ipynb`](notebooks/01_industrial_load_eda.ipynb))*

To design a mathematically rigorous peak-shaving algorithm, the industrial demand profile of the textile spinning and weaving facility was thoroughly analyzed across all **11,136 hourly observations** (464 days: July 1, 2025 – October 7, 2026).

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        24-HOUR DIURNAL LOAD CURVE & SHIFT STRUCTURE                    │
│                                                                                        │
│   Load (kW)                                                                            │
│     600 ┼                                                                              │
│         │                                        ╭─╮ ╭─╮  <-- MDI Breaches (> 500 kW)  │
│     500 ┼───────────────────────────────────────╭╯─╰─╯─╰────── LESCO Sanctioned Ceiling│
│         │                         ╭─────────────╯                                      │
│     400 ┼                       ╭─╯                                                    │
│         │       ╭───────────────╯                                                      │
│     300 ┼───────╯                                       ╭─────────────╮                │
│         │                                               │             ╰─────────╮      │
│     200 ┼                                               │                       ╰────  │
│         │                                                                              │
│       0 ┴─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┘      │
│        00:00 02:00 04:00 06:00 08:00 10:00 12:00 14:00 16:00 18:00 20:00 22:00 24:00      │
│               [   OFF-SHIFT   ] [        DAY SHIFT        ] [ EVENING SHIFT ] [OFF]    │
│               (Base Machinery)  (Heavy Spinning & Chilling) (Finishing/Pack)           │
│                                 ★ 100% of MDI Breaches Occur! ★ ToU Peak (60 PKR/kWh)  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Key Quantitative Findings:
1. **Three-Tier Operational Shift Schedule:**
   - **Day Shift (Peak Production: 08:00–17:00):** Heavy motorized spinning looms and chillers operate at maximum throughput. Average demand reaches $380 - 450\text{ kW}$, with severe spikes frequently breaching the $500\text{ kW}$ threshold.
   - **Evening Shift (Finishing & Packaging: 17:00–22:00):** Spinning ramps down; packaging lines run at $280 - 340\text{ kW}$.
   - **Off-Shift (Base Maintenance: 22:00–08:00):** Continuous base load of $180 - 240\text{ kW}$, with motors ramping up from 06:00.
   - **Weekend Derates:** Friday production is restricted to 65% load and Sunday to 40% load.
2. **The 100% Day Shift MDI Vulnerability Law:**
   - Analysis revealed exactly **169 hours** where grid import exceeded the $500.0\text{ kW}$ sanctioned ceiling.
   - **Crucial Distribution Insight:** **100.0% of all 169 MDI violations fall strictly inside the Day Shift (08:00–17:00).**
   - Zero violations occurred during the Evening Shift or Night Shift, and zero occurred on Fridays or Sundays.
   - **Seasonal Clustering:** 129 out of 169 breaches (76.3%) concentrated in July and August due to high ambient temperatures driving chiller loads.
   - **Economic Shift Dichotomy:** The Evening Shift (17:00–22:00) coincides with the LESCO Time-of-Use Peak Window ($60\text{ PKR/kWh}$ energy charge), while the Day Shift carries 100% of the MDI Peak Surcharge Risk ($1,200\text{ PKR/kW}$).
3. **Outage MDI Immunity & Baseline Loss Reconciliation:**
   - **Physics Proof:** Across 46 blackout hours, internal factory demand exceeded 500 kW. However, because the utility feeder was de-energized (`p_grid = 0.0 kW`), LESCO's boundary meter registered zero draw. Our pipeline correctly charged **0.00 PKR**, completely preventing **603,840.00 PKR in phantom fines**.
   - **Exact 2.36M PKR Reconciliation:** The historical baseline penalty of **2,360,353.20 PKR** (`demand_penalty_pkr`) was verified to stem 100% from grid-connected hours.
   - **Statutory Monthly Ratchet vs. Hourly Sum:** Under LESCO's actual monthly billing rule (billed on the single highest peak exceedance per calendar month), the billed fine is ~**239,028 PKR**, demonstrating the magnitude of savings achieved by targeted peak clipping.
4. **Empirical Battery Sizing for Peak Shaving:**
   - Shaving net grid import to a safe target of **495 kW** (5 kW safety buffer):
     - Peak shaving is required on **75 distinct days** across the year.
     - Total shaving energy required: **2,863.3 kWh**.
     - Per-day shaving requirement: median **25.5 kWh**, 95th percentile **62.4 kWh**, and worst-case day **106.3 kWh**.
     - Peak discharge power requirement: **43.0 kW**.
   - **Engineering Conclusion:** The legacy 5.12 kWh battery is physically incapable of industrial peak shaving. The upgraded **600 kWh / 250 kW LiFePO4 battery** provides ample headroom for both full peak shaving and multi-hour blackout backup.
5. **Continuous Headless Smoke Testing ([`tests/test_eda_notebook.py`](tests/test_eda_notebook.py)):**
   - Automatically executes all 17 cells of `notebooks/01_industrial_load_eda.ipynb` on every CI run via `nbformat`, verifying that all 169 breaches, 0 PKR blackout penalty, and the 2.36M PKR baseline assertions pass, exporting [`docs/samples/load_and_mdi_spikes.png`](docs/samples/load_and_mdi_spikes.png).

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
│       ├── master_ems_timeseries.csv
│       └── panel_images/
│           ├── solarsense_master_v1/ # Curated 635-image leak-free dataset
│           └── solarsense_hybrid_v1/ # 5-class stratified train/val/test splits
├── docs/                       # Formal Specifications & Audit Records
│   ├── daily_logs/             # Permanent, Git-tracked daily engineering audit logs
│   ├── samples/                # High-resolution verification charts & sample grids
│   │   ├── dataset_a_sample_grid.png
│   │   ├── load_and_mdi_spikes.png
│   │   ├── master_dataset_grid.png
│   │   └── solarsense_hybrid_v1_grid.png
│   ├── dataset_A_panel_images.md     # Protocol 1 image curation audit
│   ├── system_architecture.md        # Milestone 4 Master Architecture & Data Dictionary
│   └── week4_implementation_plan_abubakar_zaeem.md
├── models/                     # Trained GBDT weights and neural network checkpoints
│   ├── efficientnet_b2_defects.pth   # Best PyTorch model (val macro-F1 selected)
│   ├── factory_load_lightgbm.joblib
│   ├── outage_classifier.joblib
│   └── solar_pv_lightgbm.joblib
├── notebooks/                  # Reproducible EDA and MDI spike analysis notebooks
│   └── 01_industrial_load_eda.ipynb  # Comprehensive load profiling & MDI audit (Zaeem)
├── scripts/                    # Automation and DevOps utilities
│   ├── daily_standup.py        # Terminal daily standup & sprint progress tracker
│   └── generate_daily_report.py# Zero-API deterministic git daily report generator
├── src/                        # Production Source Modules
│   ├── api/                    # High-Performance FastAPI Compute Gateway (Abubakar)
│   │   ├── main.py             # REST endpoints and SSE streaming backtest
│   │   └── schemas.py          # Pydantic V2 Request & Response contracts
│   ├── data_engineering/       # High-performance Feature Store (Abubakar)
│   │   └── feature_store.py    # EMSDataRepository with microsecond slicing
│   ├── forecast/               # Causal ML Forecasters (Abubakar)
│   │   ├── train_factory_load.py # Autoregressive industrial load model
│   │   └── train_solar_pv.py   # Physics-bounded solar PV GBDT
│   ├── grid_outage/            # Calibrated Outage Risk Predictor (Abubakar)
│   │   └── predict_outage.py   # Platt-scaled blackout classifier
│   ├── optimizer/              # HiGHS MILP Solver & Tariff Engine (Abubakar)
│   │   ├── milp_solver.py      # CVXPY DPP 24h battery optimizer with reserve guard
│   │   └── tariff_engine.py    # Statutory LESCO B3 tariff calculator
│   └── vision/                 # Computer Vision Defect Pipeline (Zaeem)
│       ├── build_hybrid_dataset.py # SHA256 & dHash deduplication engine
│       ├── build_master_dataset.py # Raw Kaggle harvester & color normalizer
│       ├── dataloader.py       # PyTorch DataLoader with label-safe flip transforms
│       ├── download_datasets.py# Automated Kaggle dataset ingestion
│       ├── train_classifier.py # EfficientNet-B2 transfer learning & macro-F1 trainer
│       └── verify_dataset_a.py # Protocol 1 compliance & leakage test script
├── tests/                      # Automated Regression & Invariant Test Suite
│   ├── test_api_gateway.py     # FastAPI integration & SSE stream tests (8 tests)
│   ├── test_domain_stress_scenarios.py # Argon LESCO B3 stress tests (4 tests)
│   ├── test_eda_notebook.py    # Headless EDA notebook execution test (1 test - Zaeem)
│   ├── test_feature_store.py   # Arrow memory & immutability tests (17 tests)
│   ├── test_forecast_models.py # LightGBM inference & causality tests (9 tests)
│   ├── test_milp_solver.py     # HiGHS solver & blackout physics tests (25 tests)
│   └── test_train_classifier.py# PyTorch defect classifier trainer tests (4 tests - Zaeem)
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
Execute the automated regression test suite verifying Arrow memory contiguity, solver latency, blackout physics, and the EDA notebook:
```bash
pytest -v --ignore=tests/test_train_classifier.py
```
*(Expected: **64 passed in ~7 seconds**)*

> Note: `tests/test_train_classifier.py` requires PyTorch and Torchvision installed in your Python environment. To run with PyTorch enabled:
> ```bash
> pytest -v tests/test_train_classifier.py
> ```

### 3. Run the Computer Vision Training & Verification Pipeline
```bash
# 1. Verify Dataset A Protocol 1 compliance & zero leakage
python3 src/vision/verify_dataset_a.py

# 2. Test the PyTorch DataLoaders and inspect tensor shapes
python3 src/vision/dataloader.py

# 3. Train the EfficientNet-B2 Defect Classifier with Cosine Annealing LR
python3 src/vision/train_classifier.py
```

### 4. Run the Industrial Load & MDI Spike EDA
```bash
# Execute the EDA notebook headless smoke test
pytest -v tests/test_eda_notebook.py

# Or launch Jupyter Lab to inspect interactive visualizations
jupyter lab notebooks/01_industrial_load_eda.ipynb
```

### 5. Launch the FastAPI Compute Gateway
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

### 6. Terminal Standup & Daily Report Tools
```bash
# Print today's prioritized sprint agenda and recent git commits
python3 scripts/daily_standup.py

# Generate a daily engineering audit log from git diff metadata
python3 scripts/generate_daily_report.py --hours 24
```

---

## 👥 Engineering Team & Domain Ownership

SolarSense EMS is collaboratively engineered by:

| Engineer | Core Responsibilities & Commits | Key Deliverables & Modules |
| :--- | :--- | :--- |
| **Abubakar**<br>*(Team Lead / Systems & Optimization)* | • High-Performance Feature Store<br>• Causal Time-Series Forecasting Models<br>• HiGHS C++ MILP Battery Optimizer<br>• FastAPI Compute Gateway & SSE Streaming<br>• Argon LESCO B3 Stress Test Suite | • [`src/data_engineering/feature_store.py`](src/data_engineering/feature_store.py)<br>• [`src/forecast/`](src/forecast/) & [`src/grid_outage/`](src/grid_outage/)<br>• [`src/optimizer/milp_solver.py`](src/optimizer/milp_solver.py)<br>• [`src/api/main.py`](src/api/main.py) & [`schemas.py`](src/api/schemas.py)<br>• [`docs/system_architecture.md`](docs/system_architecture.md) |
| **Zaeem**<br>*(Computer Vision & Load Analytics)* | • Dataset A Solar Panel Image Curation<br>• PyTorch DataLoaders & Augmentations<br>• EfficientNet-B2 Defect Classification<br>• Industrial Load Profiling & Shift Analytics<br>• MDI Spike Analysis & Baseline Loss Reconciliation | • [`src/vision/dataloader.py`](src/vision/dataloader.py)<br>• [`src/vision/train_classifier.py`](src/vision/train_classifier.py)<br>• [`tests/test_train_classifier.py`](tests/test_train_classifier.py)<br>• [`notebooks/01_industrial_load_eda.ipynb`](notebooks/01_industrial_load_eda.ipynb)<br>• [`tests/test_eda_notebook.py`](tests/test_eda_notebook.py) |

- **Master Technical Specification:** Complete mathematical derivations, 24-column data dictionary, and architectural diagrams are available in [`docs/system_architecture.md`](docs/system_architecture.md).

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
