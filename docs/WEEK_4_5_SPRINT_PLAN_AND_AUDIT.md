# SolarSense EMS — Master Sprint Plan & Project Audit
**Sprint Period:** October 19, 2026 – October 25, 2026  
**Execution Target:** Complete Remaining Milestone 4 Deliverables & Deliver Milestone 5 (AI & Optimization)  
**Team Allocation:** Abubakar (Systems, Forecast & Optimization) | Zaeem (Computer Vision & Load Analytics)  
**Academic Alignment:** 1.5 Weeks Ahead of University Schedule | 4-Week Fast-Track to Completion  

---

## 1. Project Standing & Timeline Alignment

### Current Status vs. University Milestones
* **University Schedule:** **Week 3 (Requirements, Data & System Design)**
* **SolarSense Team Reality:** **Boundary of Week 4 & Week 5**
  * **Week 1 (Project Idea & Target Users):** 100% COMPLETE
  * **Week 2 (Proposal, Scope & Limitations):** 100% COMPLETE
  * **Week 3 (Requirements & Architecture):** 95% COMPLETE
  * **Week 4 (Data Foundation & Backend):** 85% COMPLETE
  * **Week 5 (AI / Agent Development):** 10% COMPLETE (Architecture designed; model training starting this sprint)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        4-WEEK FAST-TRACK TO 8-WEEK COMPLETION                          │
├─────────────────┬───────────────────────────────┬──────────────────────────────────────┤
│ Calendar Week   │ University Course Milestone   │ SolarSense Team Sprint Target        │
├─────────────────┼───────────────────────────────┼──────────────────────────────────────┤
│ Oct 19 – Oct 25 │ Week 3: System Design & Specs │ WEEK 4/5: Close Backend & Train AI   │
│ Oct 26 – Nov 01 │ Week 4: Data & Backend        │ WEEK 5/6: Agents & Battery Optimizer │
│ Nov 02 – Nov 08 │ Week 5: AI & Agent Testing    │ WEEK 6/7: Full Streamlit Web UI App  │
│ Nov 09 – Nov 15 │ Week 6–8: Integration & Final │ WEEK 7/8: System Evaluation & Defense│
└─────────────────┴───────────────────────────────┴──────────────────────────────────────┘
```

---

## 2. Comprehensive Project Audit: Done vs. Not Done

### ✅ What Has Been Completed (Assets & Code)
1. **Gold-Tier Master Feature Store (`data/processed/master_ems_timeseries.csv`):**
   * 11,136 hourly rows (464 days) combining 5-minute inverter telemetry, Open-Meteo satellite weather, LESCO B3 tariffs, synthetic 2-shift factory load, and grid blackout flags.
2. **Empirical Soiling Physics Model (`src/soiling/calibrate_soiling_model.py`):**
   * Mathematical Perez POA irradiance and module temperature derates calibrated against the verified 2026-09-23 cleaning event. CUSUM change-point detection active.
3. **NEPRA / LESCO Tariff Engine (`src/optimizer/tariff_engine.py`):**
   * Accurate modeling of 60 PKR peak vs. 38 PKR off-peak hours, 1,200 PKR/kW MDI penalties, and 95 PKR/kWh diesel costs. Validated historical baseline loss of **2.36 Million PKR**.
4. **Curated & Split Panel Image Dataset (`data/processed/panel_images/solarsense_hybrid_v1/`):**
   * Fully partitioned into `train/`, `val/`, and `test/` across 5 defect classes: `clean`, `dusty`, `bird_drop`, `electrical_damage`, and `physical_damage`.
5. **Image Verification Suite (`src/vision/verify_dataset_a.py`):**
   * PIL integrity check, duplicate SHA-256 detection, and split leakage verification script.
6. **Project Infrastructure & Presentations:**
   * Clean Git repo pushed to GitHub (`Abubakar651/SolarSense-Ems`), professional `README.md`, pitch decks (`docs/SolarSense_Industrial_EMS.pptx` & `SolarSense_EMS_Pitch_Deck2.pptx`), and agent specs in `docs/agents.md`.

---

### ❌ What Has NOT Been Completed (Gaps to Close)
1. **AI Models Not Yet Trained (Milestone 5 Gap):**
   * `src/forecast/train_solar_pv.py` (LightGBM solar model) is not written or trained.
   * `src/forecast/train_factory_load.py` (Demand forecasting model) is not written or trained.
   * `src/vision/train_classifier.py` (EfficientNet-B2 transfer learning) has not been trained on Dataset A.
   * `src/optimizer/battery_scheduler.py` (MILP optimization solver via PuLP) is not yet implemented.
2. **Empty Folders:**
   * `notebooks/`: 0 notebooks present (no reproducible visual EDA or benchmark charts).
   * `tests/`: 0 unit tests present (no automated test suite).
   * `src/grid_outage/`: Module empty (no outage probability predictor).
   * `src/llm_agents/`: Module empty (no LLM reasoning or report generation script).
3. **Data Access Layer:**
   * No reusable object-oriented class (`EMSDataStore`) to serve 24-hour simulation windows to the models and upcoming UI.

---

## 3. Work Allocation: Abubakar vs. Zaeem

```
                                TEAM WORKSTREAM DIVISION
                               
             ABUBAKAR                                    ZAEEM
  (Time-Series, Forecasting, Backend)     (Computer Vision, Image Data, Load EDA)
                  │                                         │
  ┌───────────────┴───────────────┐         ┌───────────────┴───────────────┐
  │ 1. Backend Data Store (API)   │         │ 1. PyTorch Dataset & Loader   │
  │ 2. Automated Test Suite       │         │ 2. Industrial Load EDA (Jupyter│
  │ 3. LightGBM Solar Forecast    │         │ 3. EfficientNet-B2 Classifier │
  │ 4. MILP Battery Optimizer     │         │ 4. Vision Evaluation & Matrix │
  │ 5. Outage Risk Classifier     │         │ 5. Dataset A Documentation    │
  └───────────────────────────────┘         └───────────────────────────────┘
```

---

## 4. Day-by-Day Sprint Schedule & Deadlines

### 🗓️ Monday, October 19, 2026 — Foundation & Pipelines
* **Abubakar (Lead)** — *Deadline: 23:59*
  * Create `src/data_engineering/feature_store.py`.
  * Build the `EMSDataStore` class providing clean accessors:
    * `get_day_slice(date_str)`: Returns a 24-hour DataFrame of weather, solar, load, and grid flags.
    * `get_tariff_window(date_str)`: Returns hourly PKR prices.
    * `get_features_for_training()`: Returns formatted feature/label arrays for model training.
* **Zaeem (Vision & Load)** — *Deadline: 23:59*
  * Create `src/vision/dataloader.py`.
  * Implement PyTorch `ImageFolder` with transforms:
    * Resize to $260 \times 260$ (EfficientNet-B2 standard).
    * Data augmentations: Random horizontal/vertical flip, rotation ($\pm 15^\circ$), ImageNet normalization.
    * Batch generation: Verify shape `[B, 3, 260, 260]` and label integrity.

---

### 🗓️ Tuesday, October 20, 2026 — Testing & Load Analytics
* **Abubakar (Lead)** — *Deadline: 23:59*
  * Create `tests/test_data_integrity.py` and `tests/test_tariff_engine.py`.
  * Write unit tests ensuring:
    * `master_ems_timeseries.csv` has 0 missing/NaN values.
    * Solar energy is 0 W at night (GHI = 0).
    * `TariffEngine` accurately calculates 1,200 PKR/kW fines when grid draw $> 500$ kW.
* **Zaeem (Vision & Load)** — *Deadline: 23:59*
  * Create `notebooks/01_industrial_load_and_mdi_eda.ipynb`.
  * Conduct exploratory data analysis on the 200–450 kW factory load curve:
    * Shift 1 (08:00–16:00) vs. Shift 2 (16:00–00:00) vs. Night Shift.
    * Visualize the historical spikes exceeding the 500 kW ceiling.
    * Export plot to `docs/samples/load_and_mdi_spikes.png`.

---

### 🗓️ Wednesday, October 21, 2026 — Core AI Model Training
* **Abubakar (Lead)** — *Deadline: 23:59*
  * Implement and execute `src/forecast/train_solar_pv.py` using **LightGBM**.
  * Train using features: GHI, DNI, DHI, ambient temperature, relative humidity, cloud cover, hour, and month.
  * Evaluate on holdout test set (target: $R^2 \ge 0.90$, $\text{RMSE} \le 0.45\text{ kW}$).
  * Save model weights to `models/solar_pv_lightgbm.pkl`.
* **Zaeem (Vision & Load)** — *Deadline: 23:59*
  * Implement and execute `src/vision/train_classifier.py` using **EfficientNet-B2** (`torchvision.models`).
  * Set up transfer learning with cross-entropy loss, Adam optimizer, and cosine learning rate decay.
  * Train for 15 epochs on `solarsense_hybrid_v1`.
  * Save best checkpoint to `models/efficientnet_b2_defects.pth`.

---

### 🗓️ Thursday, October 22, 2026 — Optimization & Vision Metrics
* **Abubakar (Lead)** — *Deadline: 23:59*
  * Implement `src/optimizer/battery_scheduler.py` using **Mixed-Integer Linear Programming (MILP)** with `PuLP`.
  * Objective function:
    $$\min \sum_{t=1}^{24} \left[ P_{\text{grid}}(t) \cdot \text{Tariff}(t) + \text{Penalty}_{\text{MDI}}(t) + P_{\text{diesel}}(t) \cdot 95 \right]$$
  * Enforce constraints: $20\% \le SoC(t) \le 100\%$, charge/discharge limits ($\le 2.5\text{ kW}$), and peak hour discharge priority.
  * Demonstrate that the optimizer successfully prevents historical 500 kW MDI fines.
* **Zaeem (Vision & Load)** — *Deadline: 23:59*
  * Implement `src/vision/evaluate_classifier.py`.
  * Evaluate on the holdout test set: compute confusion matrix, precision, recall, and F1-score across all 5 classes.
  * Export visual confusion matrix to `docs/samples/confusion_matrix_efficientnet.png`.
  * Document findings in `docs/dataset_A_audit_report.md`.

---

### 🗓️ Friday, October 23, 2026 — Outage Classifier & System Benchmark
* **Abubakar (Lead)** — *Deadline: 23:59*
  * Implement `src/grid_outage/predict_outage.py` using **Random Forest Classifier**.
  * Predict hourly outage probability $P(\text{outage}) \in [0.0, 1.0]$.
  * Connect outage risk to the battery optimizer: when $P(\text{outage}) > 0.60$, reserve battery charge at 100% to avoid the 95 PKR/kWh diesel generator cost.
* **Zaeem (Vision & Load)** — *Deadline: 23:59*
  * Create `notebooks/02_model_performance_benchmarks.ipynb`.
  * Compile unified performance tables:
    * LightGBM Solar Forecast ($R^2$, MAE, RMSE)
    * EfficientNet-B2 Defect Classifier (Accuracy, F1-Score)
    * MILP Financial Savings Comparison (PKR Baseline vs. PKR Optimized)

---

### 🗓️ Saturday, October 24, 2026 — Code Review, Git Merge & Documentation
* **Joint Abubakar & Zaeem** — *Deadline: 18:00*
  * Push all feature branches to GitHub.
  * Open and cross-review Pull Requests.
  * Ensure all scripts follow consistent PEP 8 formatting and preserve existing docstrings.
  * Merge all PRs into `main` and verify pipeline execution with:
    ```bash
    pytest tests/
    python3 src/forecast/train_solar_pv.py
    python3 src/optimizer/battery_scheduler.py
    ```

---

### 🗓️ Sunday, October 25, 2026 — Milestone 5 Review & Retrospective
* **Joint Abubakar & Zaeem** — *Deadline: 20:00*
  * Audit all acceptance criteria listed below.
  * Tag Git release: `v0.5.0-milestone5`.
  * Hold a 30-minute sync to preview **Week 6 (Streamlit Dashboard & Web Application Integration)**.

---

## 5. Quantitative Acceptance Criteria

| Component | Target Metric / Deliverable | Verification Method |
| :--- | :--- | :--- |
| **Data Integrity** | 100% passing automated unit tests | Run `pytest tests/` |
| **Solar Forecast Model** | $R^2 \ge 0.90$, $\text{RMSE} \le 0.45\text{ kW}$ | `src/forecast/train_solar_pv.py` evaluation log |
| **Panel Defect Classifier**| Test Accuracy $\ge 94\%$, Macro F1 $\ge 0.92$ | `docs/samples/confusion_matrix_efficientnet.png` |
| **Battery Dispatch Solver**| $100\%$ MDI violation elimination on test day; solve time $< 1\text{s}$ | `src/optimizer/battery_scheduler.py` output |
| **Exploratory Data Analysis**| Clean, runnable Jupyter notebook reproducing the 2.36M PKR penalty | `notebooks/01_industrial_load_and_mdi_eda.ipynb` |
| **Code Hygiene** | Clean Git commit history, 0 merge conflicts, updated documentation | GitHub repository status |

---

## 6. Execution Commands Reference

```bash
# 1. Run Automated Test Suite
pytest tests/ -v

# 2. Train Solar PV Forecasting Model (LightGBM)
python3 src/forecast/train_solar_pv.py

# 3. Train Panel Defect Classifier (EfficientNet-B2)
python3 src/vision/train_classifier.py

# 4. Evaluate Vision Model & Generate Confusion Matrix
python3 src/vision/evaluate_classifier.py

# 5. Run 24-Hour MILP Battery Optimization Simulation
python3 src/optimizer/battery_scheduler.py
```
