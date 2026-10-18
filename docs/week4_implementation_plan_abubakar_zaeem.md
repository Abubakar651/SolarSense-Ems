# SolarSense EMS — Sprint Plan: Week 4 (Ahead of Schedule)
**Target Milestone:** Milestone 4 (Data & Backend Foundation) + Fast-Track Prep for Milestone 5 (AI Models)  
**Timeline:** October 19 – October 25, 2026 (1-Month Fast-Track to Completion)  
**Team:** Abubakar (Lead / Systems & Optimization) & Zaeem (Computer Vision & Load Analytics)

---

## 1. Executive Context & Milestone Alignment

The university course outline is currently at **Week 3 (Requirements, Data & System Design)**.  
To maintain our strict policy of **staying 1 week ahead** and finishing the 8-week curriculum within our **1-month (4-week) deadline**, our sprint this week will execute and complete **Milestone 4 (Data & Backend Foundation)** while laying the exact scaffolding for **Milestone 5 (AI/Agent Development)**.

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                      4-WEEK COMPLETION ACCELERATION MAP                       │
├─────────────────┬───────────────────────────────┬─────────────────────────────┤
│ Calendar Week   │ University Course Milestone   │ SolarSense Team Execution   │
├─────────────────┼───────────────────────────────┼─────────────────────────────┤
│ This Week       │ Week 3: System Design & Specs │ WEEK 4: Data & Backend Done │
│ Next Week (+1)  │ Week 4: Data & Backend        │ WEEK 5: AI & Optimization   │
│ Following (+2)  │ Week 5: AI / Agents           │ WEEK 6: Streamlit UI App    │
│ Final Week (+3) │ Week 6-8: Integration & Demos │ WEEK 7-8: Testing & Defense │
└─────────────────┴───────────────────────────────┴─────────────────────────────┘
```

---

## 2. Weekly Sprint Objectives

By the end of this week (Sunday, 23:59), the project repository must contain:
1. **Unified Backend Access Layer:** A single Python data service exposing 24-hour lookahead windows from our 464-day master dataset.
2. **Dataset A (Images) Full Pipeline:** 100% verified, deduplicated, and split solar panel defect dataset with PyTorch data loaders ready for EfficientNet.
3. **Solar PV Generation Baseline Model:** Trained LightGBM regressor predicting hourly kW from satellite weather with benchmark evaluation metrics ($R^2$, RMSE, MAE).
4. **Industrial Load & MDI Analysis Report:** Quantitative EDA notebook proving the exact hours the 500 kW sanctioned limit was breached.
5. **Git Version Control & Schema Documentation:** Clean PRs merged into `main` with reproducible scripts.

---

## 3. Detailed Work Breakdown: Abubakar vs. Zaeem

```
                               TEAM WORKSTREAM DIVISION
                               
             ABUBAKAR                                    ZAEEM
  (Time-Series, Forecasting, Backend)     (Computer Vision, Image Data, Load EDA)
                  │                                         │
  ┌───────────────┴───────────────┐         ┌───────────────┴───────────────┐
  │ 1. Backend Data Engine (API)  │         │ 1. Dataset A Image Curation   │
  │ 2. Solar Forecast (LightGBM)  │         │ 2. CV DataLoader & Transforms │
  │ 3. Tariff & MDI Module        │         │ 3. Factory Load EDA Notebook  │
  │ 4. System Architecture Doc    │         │ 4. Defect Distribution Audit  │
  └───────────────────────────────┘         └───────────────────────────────┘
```

---

### Task List for Abubakar (Team Lead)
**Primary Focus:** Backend Data Access, Time-Series Forecasting Model, Tariff Logic

#### Task A1: Build Backend Data Access Layer (`src/data_engineering/feature_store.py`)
- **Objective:** Wrap `data/processed/master_ems_timeseries.csv` into a clean object-oriented class (`EMSDataStore`).
- **Deliverables:**
  - Method `get_simulation_day(date_str)`: Returns a 24-hour slice containing solar generation, factory demand, ambient temperature, irradiance, and grid status.
  - Method `get_tariff_profile(date_str)`: Returns hourly PKR prices (38 PKR off-peak, 60 PKR peak).
  - Method `get_mdi_spikes(threshold_kw=500)`: Returns all timestamp intervals where net factory load exceeded 500 kW.
- **Verification:** Unit test in `tests/test_feature_store.py` passing with 100% assertion coverage.

#### Task A2: Train & Evaluate Solar Generation Model (`src/forecast/train_solar_pv.py`)
- **Objective:** Build the primary 24-hour solar generation forecasting model using **LightGBM**.
- **Deliverables:**
  - Feature engineering pipeline: Solar zenith/azimuth, GHI, DNI, ambient temperature, relative humidity, cloud cover, and hour-of-day cyclical features ($\sin/\cos$).
  - Train/Validation/Test temporal split: First 350 days for training, next 50 days validation, final 64 days holdout testing.
  - Performance Metrics: Compute RMSE, MAE, and $R^2$ score against baseline naive persistence.
  - Save trained model weights to `models/solar_pv_lightgbm.pkl`.

#### Task A3: Finalize Deterministic LESCO B3 Tariff Engine (`src/optimizer/tariff_engine.py`)
- **Objective:** Implement the exact NEPRA/LESCO billing rules as an imported module.
- **Deliverables:**
  - Class `TariffEngine` that calculates:
    - Base energy charge: $\text{kWh} \times \text{Rate}(t)$
    - MDI Penalty: $\max(0, P_{\text{grid}} - 500) \times 1200 \text{ PKR}$
    - Diesel Generator Cost: $\text{kWh}_{\text{outage}} \times 95 \text{ PKR}$
    - Net Solar Savings vs. pure grid baseline.

#### Task A4: System Architecture & Data Dictionary (`docs/system_architecture.md`)
- **Objective:** Fulfill the formal Milestone 3 & 4 documentation requirements for submission.
- **Deliverables:**
  - End-to-end data pipeline diagram (Mermaid.js).
  - Master feature dictionary documenting all 24 columns in `master_ems_timeseries.csv`.

---

### Task List for Zaeem (Team Member 2)
**Primary Focus:** Computer Vision Pipeline, Image Dataset Verification, Factory Load EDA

#### Task Z1: Curate & Verify Dataset A (Solar Panel Images)
- **Objective:** Establish the clean, multi-class panel image dataset for defect classification.
- **Deliverables:**
  - Structure `data/raw/panel_images/` into 5 clean class folders:
    1. `clean/`
    2. `dusty/`
    3. `bird_droppings/`
    4. `physical_damage/`
    5. `electrical_hotspots/`
  - Write and run verification script `src/vision/verify_dataset_a.py`:
    - PIL integrity check (detect corrupt files).
    - Image hashing (MD5/SHA256) to remove duplicate or near-identical photos.
    - Class balance report (log counts and percentages per class).
  - Export sample grid artifact to `docs/samples/dataset_a_sample_grid.png`.

#### Task Z2: Build PyTorch Data Pipelines for EfficientNet (`src/vision/dataloader.py`)
- **Objective:** Prepare the training pipeline so model training can start without delay in Week 5.
- **Deliverables:**
  - Create stratified Train / Validation / Test splits ($70\% / 15\% / 15\%$) ensuring zero data leakage.
  - Implement PyTorch `transforms.Compose` pipeline:
    - Resize to $260 \times 260$ (EfficientNet-B2 native resolution).
    - Data augmentations: Random horizontal/vertical flip, slight color jitter, affine rotation ($\pm 15^\circ$).
    - ImageNet normalization (`mean=[0.485, 0.456, 0.406]`, `std=[0.229, 0.224, 0.225]`).
  - Write test harness verifying batch shape: `[batch_size, 3, 260, 260]` and labels `[batch_size]`.

#### Task Z3: Industrial Load Profile & MDI Deep Dive (`notebooks/02_industrial_load_eda.ipynb`)
- **Objective:** Deeply analyze the 200–450 kW factory demand curve and the historical MDI penalties.
- **Deliverables:**
  - Jupyter notebook analyzing:
    - Hourly average factory load across Shift 1 (08:00–16:00), Shift 2 (16:00–00:00), and Night Shift.
    - Distribution of peak shaving requirements: How many kWh of battery capacity are needed to shave the spikes down to 495 kW?
    - Visualization of the top 10 worst MDI penalty days.
  - Export publication-quality charts to `docs/samples/load_profile_and_spikes.png`.

#### Task Z4: Dataset Card Documentation (`docs/dataset_A_audit_report.md`)
- **Objective:** Formal dataset documentation required for university grading.
- **Deliverables:**
  - Resolution statistics (min, max, median resolution).
  - Licensing confirmation (CC-BY / MIT / academic research usage).
  - Limitations of camera angles and lighting conditions.

---

## 4. Day-by-Day Execution Schedule

| Day | Abubakar (Lead) | Zaeem (Vision & Load) | Sync Goal |
| :--- | :--- | :--- | :--- |
| **Mon (Day 1)** | Design `EMSDataStore` class interface; set up test harnesses. | Download & organize Dataset A images into class directories. | Align on class folder names and schema definitions. |
| **Tue (Day 2)** | Implement `feature_store.py` & query functions; verify data cuts. | Write and execute `verify_dataset_a.py` (integrity, hashes, count). | Confirm zero corrupted images and zero data leakage. |
| **Wed (Day 3)** | Feature engineering & temporal train/val split for LightGBM. | Build PyTorch `DataLoader` with augmentations for EfficientNet-B2. | Mid-week checkpoint: Data pipelines 100% operational. |
| **Thu (Day 4)** | Train LightGBM solar model; record RMSE/$R^2$ metrics. | Execute EDA notebook on industrial load & plot 500 kW breaches. | Cross-validate solar generation curves against factory load. |
| **Fri (Day 5)** | Implement `TariffEngine` class; calculate cost comparisons. | Finalize Dataset A verification report and sample grid graphic. | Commit code to GitHub; review each other's Pull Requests. |
| **Sat (Day 6)** | Write `system_architecture.md`; update master documentation. | Package notebook findings and charts into `docs/`. | Combine deliverables into a cohesive Milestone 4 package. |
| **Sun (Day 7)** | Review full project repo; tag release `v0.4.0-milestone4`. | Dry run of Week 5 tasks (model training scripts). | **Weekly Retrospective & Milestone 5 kickoff.** |

---

## 5. Verification Checklist & Acceptance Criteria

Before closing Week 4, verify that every item below passes:

- [ ] `src/data_engineering/feature_store.py` runs without error and returns 24-hour slices.
- [ ] `src/forecast/train_solar_pv.py` trains LightGBM and achieves $R^2 \ge 0.90$ on holdout test data.
- [ ] `src/optimizer/tariff_engine.py` reproduces the historical 2.36 Million PKR MDI penalty calculation.
- [ ] `data/raw/panel_images/` has 0 corrupt images, 0 cross-split duplicates, and balanced classes.
- [ ] `src/vision/dataloader.py` outputs PyTorch tensors of shape `[B, 3, 260, 260]`.
- [ ] `notebooks/02_industrial_load_eda.ipynb` runs from top to bottom with clean visualizations.
- [ ] All code committed and pushed to GitHub with clear commit messages.
- [ ] Milestone 4 submission report ready in `docs/` folder.
