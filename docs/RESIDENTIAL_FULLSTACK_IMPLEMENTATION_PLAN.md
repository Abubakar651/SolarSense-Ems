# SolarSense EMS — Full-Stack Residential EMS Audit & Next-Phase Sprint Plan
**Target System:** Station LHR-RES-01 / 904-A JT (100% Residential Hybrid Solar & Battery EMS, Lahore, Pakistan)  
**Hardware Envelope:** $7.02\text{ kWp}$ DC Bifacial PV ($12 \times 585\text{ W}$) | GoodWe ES LV Hybrid Inverter (`SN: 9010KESC253L0146`) | $5.12\text{ kWh}$ LiFePO4 BESS ($51.2\text{ V}, 100\text{ Ah}$, $5.0\text{ kW}$ max charge/discharge)  
**Tariff Framework:** LESCO A-1 Time-of-Use & Net-Metering ($46.85\text{ PKR}$ Peak 18:00–22:00, $34.53\text{ PKR}$ Off-Peak, $27.00\text{ PKR}$ Export, $10.0\text{ kW}$ Sanctioned Load, $1,500\text{ PKR}$ Wash Cost)  
**Team Allocation:** Abubakar (Team Lead — Systems, Forecasting, MILP Optimization, FastAPI & LLM Orchestrator) | Zaeem (Computer Vision, CCTV Edge Inspector & Next.js Visual Analytics)

---

## 1. Executive Standing & Residential Product Architecture

SolarSense EMS has officially transitioned into a **100% Residential Hybrid Solar & Battery Energy Management System** anchored to real-world empirical telemetry from **Station LHR-RES-01 (904-A Johar Town, Lahore, Pakistan)**. All historical LESCO B3 industrial microgrid simulation scripts, notebooks, and redundant configuration aliases have been quarantined into `archive/legacy_industrial/`.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                  SOLARSENSE EMS — FULL-STACK RESIDENTIAL PRODUCT ARCHITECTURE                │
├───────────────────────────┬──────────────────────────────────┬───────────────────────────────┤
│ Layer                     │ Subsystems & Modules             │ Current Status                │
├───────────────────────────┼──────────────────────────────────┼───────────────────────────────┤
│ 1. Telemetry & Data Store │ Polars + PyArrow Feature Store   │ ✅ 100% Complete (0.035 ms)   │
│ 2. Soiling & Wash Engine  │ Perez POA + CUSUM + ROI Engine   │ ✅ 100% Complete (7.02 kWp)   │
│ 3. Computer Vision Suite  │ EfficientNet-B2 + CCTV Monitor   │ ✅ 100% Complete (95.4% Acc)  │
│ 4. Causal ML Forecasting  │ Solar, Load (P50/P90) & Outage   │ ✅ 100% Complete (2.72 ms)    │
│ 5. HiGHS MILP Optimizer   │ CVXPY DPP 5.12 kWh BESS Solver   │ ✅ 100% Complete (10.45 ms)   │
│ 6. FastAPI Compute Gateway│ REST + SSE Streaming Gateway     │ 🟢 85% Complete (Core Ready)  │
│ 7. Multi-Agent LLM Layer  │ Explainable Dispatch & Wash Brief│ 🔴 0% Built (Next Sprint)     │
│ 8. Next.js 14 Web App     │ App Router + Tailwind + Zustand  │ 🔴 0% Built (Next Sprint)     │
└───────────────────────────┴──────────────────────────────────┴───────────────────────────────┘
```

---

## 2. Module-Wise Completion Audit (Targeting a Full-Stack Web App)

### Module 1: Data Engineering, SEMS+ Telemetry & Arrow Feature Store (`src/data_engineering/`)
* **Status & Completion:** **100% Complete**
* **What Is Already Built & Verified:**
  * [`src/data_engineering/feature_store.py`](../src/data_engineering/feature_store.py): `EMSDataRepository`, `TariffPolicy.lesco_a1_residential()`, `OptimizationHorizonSlice`, `SimulationWindowDTO`, and `MLTaskSplits`.
  * [`src/data_engineering/repair_master_dataset.py`](../src/data_engineering/repair_master_dataset.py) & [`scripts/ingest_sems_agent_data.py`](../scripts/ingest_sems_agent_data.py): 11,136 hourly records (464 days) anchored to GoodWe SEMS+ portal daily totals ($7.02\text{ kWp}$ ceiling, $0.000000\text{ kW}$ nocturnal solar across all 5,193 night hours, 113 blackout events $\le 5.12\text{ kWh}$).
  * Sub-millisecond 24-hour slice retrieval: **$0.0346\text{ ms}$** (budget $< 1.0\text{ ms}$).
* **What Is Remaining for Final Web Product:**
  * None in core data engineering; ready for direct consumption by FastAPI and Next.js.

### Module 2: Physics Soiling & Econometric Wash Advisor (`src/soiling/`)
* **Status & Completion:** **100% Complete**
* **What Is Already Built & Verified:**
  * [`src/soiling/calibrate_soiling_model.py`](../src/soiling/calibrate_soiling_model.py): Calibrated for $7.02\text{ kWp}$ ($12 \times 585\text{ W}$), LESCO A-1 ToU rates ($34.53\text{ PKR/kWh}$ Off-Peak, $46.85\text{ PKR/kWh}$ Peak), and $1,500.0\text{ PKR}$ residential wash cost. Fitted post-wash exponential decay ($k = 1.211\%/\text{day}$) and CUSUM rain/wash event detection (`data/processed/soiling/soiling_analysis_lahore.csv`).
  * [`src/soiling/loss_calculator.py`](../src/soiling/loss_calculator.py): Upgraded `SolarPlantLossCalculator` to default to $7.02\text{ kWp}$, $585\text{ W}$ bifacial modules, $1,500\text{ PKR}$ wash cost, and `A1_ToU` tariff, fixing the low-power residential derate percentage threshold (`expected_clean_kw > 0.1`).
* **What Is Remaining for Final Web Product:**
  * Expose `SolarPlantLossCalculator` via a dedicated FastAPI endpoint (`GET /api/soiling/status`) for the Next.js Soiling & Maintenance ROI card.

### Module 3: Computer Vision Defect & Dust Inspector (`src/vision/` — *Frozen / Completed*)
* **Status & Completion:** **100% Complete (Frozen per Guardrail 1)**
* **What Is Already Built & Verified:**
  * [`src/vision/train_classifier.py`](../src/vision/train_classifier.py), [`src/vision/evaluate_classifier.py`](../src/vision/evaluate_classifier.py), [`src/vision/cctv_panel_monitor.py`](../src/vision/cctv_panel_monitor.py), and `models/efficientnet_b2_defects.pth`.
  * Holdout Test Accuracy: **`95.40%`** (`Macro-F1 = 0.9547` standard; **`97.70%`** with 4-pass TTA feature fusion), zero cross-split leakage across 580 curated hybrid images.
* **What Is Remaining for Final Web Product:**
  * Keep `src/vision/` untouched; add a read-only FastAPI wrapper route (`POST /api/vision/inspect` & `GET /api/vision/latest`) calling `CCTVPanelMonitor.predict_pil_image()` so users can upload or select a panel frame in the Next.js UI.

### Module 4: Causal ML Forecasting & Outage Risk Suite (`src/forecast/`, `src/grid_outage/`)
* **Status & Completion:** **100% Complete**
* **What Is Already Built & Verified:**
  * [`src/forecast/train_solar_pv.py`](../src/forecast/train_solar_pv.py): Upgraded physical capacity clipping to $7.02\text{ kWp}$ (`RESIDENTIAL_ARRAY_KWP = 7.02`) and `TariffPolicy.lesco_a1_residential()`. Holdout $R^2 = 0.9578$, $\text{MAE} = 0.1552\text{ kW}$, $\text{RMSE} = 0.3118\text{ kW}$, Peak-Window $\text{MAE} = 0.0491\text{ kW}$, 24h inference latency $= 0.4183\text{ ms}$.
  * [`src/forecast/train_residential_load.py`](../src/forecast/train_residential_load.py): Dual point + P90 quantile LightGBM bundle with non-crossing guarantee ($p_{90} \ge p_{\text{point}} \ge 0$). Holdout $R^2 = 0.8845$, $\text{MAE} = 0.2777\text{ kW}$, $\text{RMSE} = 0.3707\text{ kW}$, Peak-Window $\text{MAE} = 0.4760\text{ kW}$, P90 coverage $= 84.7\%$, 24h latency $= 1.6185\text{ ms}$.
  * [`src/grid_outage/predict_outage.py`](../src/grid_outage/predict_outage.py): Platt-sigmoid calibrated LightGBM blackout risk predictor. Holdout Brier Score $= 0.0312$, PR-AUC $= 0.0495$, cost-optimal reserve threshold $= 0.0500$, 24h latency $= 0.7376\text{ ms}$.
* **What Is Remaining for Final Web Product:**
  * None in core ML training/inference; already wired into `EMSDataRepository.get_optimization_slice(use_forecasts=True)` ($2.722\text{ ms}$ combined).

### Module 5: HiGHS C++ MILP Battery Dispatch Optimizer (`src/optimizer/`)
* **Status & Completion:** **100% Complete**
* **What Is Already Built & Verified:**
  * [`src/optimizer/milp_solver.py`](../src/optimizer/milp_solver.py): CVXPY Disciplined Parametrized Programming (DPP) + HiGHS C++ solver supporting `BESSConfig.station_904a_residential()` ($5.12\text{ kWh}$ capacity, $15\%$ min SoC $= 0.768\text{ kWh}$, $5.0\text{ kW}$ max charge/discharge, $55\%$ nocturnal blackout reserve $= 2.816\text{ kWh}$, and Post-Blackout Peak Recharge Suppression $p_{\text{grid}} \le \text{load}$ during 18:00–22:00).
  * [`src/optimizer/tariff_engine.py`](../src/optimizer/tariff_engine.py): Updated with `get_base_rate_pkr()` and `calculate_residential_bill()` defaulting to `A1_ToU` ($46.85\text{ PKR}$ Peak, $34.53\text{ PKR}$ Off-Peak, $27.00\text{ PKR}$ Export).
  * Warm 24h residential MILP solve time: **$10.446\text{ ms}$** (budget $< 25.0\text{ ms}$).
* **What Is Remaining for Final Web Product:**
  * None in core solver math.

### Module 6: FastAPI Compute Gateway (`src/api/`)
* **Status & Completion:** **85% Complete**
* **What Is Already Built & Verified:**
  * [`src/api/main.py`](../src/api/main.py) & [`src/api/schemas.py`](../src/api/schemas.py): `lifespan` now initializes `TariffPolicy.lesco_a1_residential()` and `BESSConfig.station_904a_residential()` with `10.0 kW` sanctioned ceiling in `/api/backtest/stream` and net-metering export vectors (`p_export_kw`, `export_revenue_pkr`) in `OptimizationResponse`.
  * Measured HTTP round-trip: `GET /api/window` in **$1.286\text{ ms}$**, `POST /api/optimize` in **$13.260\text{ ms}$** (budget $< 50.0\text{ ms}$).
* **What Is Remaining for Final Web Product (15%):**
  * Add 3 lightweight BFF endpoints for the Full-Stack UI:
    1. `GET /api/soiling/status?date=YYYY-MM-DD`: Returns daily soiling PR, kWh/PKR lost, and wash ROI decision from `SolarPlantLossCalculator`.
    2. `POST /api/vision/inspect`: Accepts an uploaded image or sample ID and returns the 5-class `CCTVPanelMonitor` defect diagnostic + optical derate.
    3. `POST /api/agent/advisory`: Invokes the `src/llm_agents/` orchestrator to generate an executive natural-language dispatch & maintenance briefing.

### Module 7: Multi-Agent LLM Explanation & Advisory Layer (`src/llm_agents/`)
* **Status & Completion:** **0% Complete (Unbuilt — Scheduled for Next Sprint)**
* **What Is Already Built & Verified:**
  * Directory `src/llm_agents/` exists as a placeholder; agent responsibilities are specified in `docs/agents.md`.
* **What Is Remaining for Final Web Product (100%):**
  * Implement deterministic + LLM-backed multi-agent orchestrator (`src/llm_agents/ems_copilot.py`) with 3 specialized roles:
    1. **Grid & Tariff Arbitrage Analyst:** Explains 24h battery charge/discharge schedule, ToU savings vs. GoodWe stock firmware, and peak recharge suppression.
    2. **Blackout Resilience & SoC Guard Advisor:** Explains pre-emptive charging ahead of high $P(\text{outage})$ windows and islanded autonomy hours.
    3. **PV Health & Wash ROI Advisor:** Synthesizes `SolarPlantLossCalculator` and `CCTVPanelMonitor` outputs into a concrete maintenance action plan (with deterministic template fallback when offline/no API key is set).

### Module 8: Next.js 14 Full-Stack Web Dashboard (`frontend/`)
* **Status & Completion:** **0% Complete (Unbuilt — Scheduled for Next Sprint)**
* **What Is Already Built & Verified:**
  * Backend CORS, `SimulationWindowResponse`, `OptimizationResponse`, and SSE `/api/backtest/stream` payloads are already shaped for 60 FPS client playback.
* **What Is Remaining for Final Web Product (100%):**
  * Scaffold and build `frontend/` using **Next.js 14 (App Router), TypeScript (strict), Tailwind CSS, Zustand, TanStack Query, and Recharts / Lucide**:
    1. **Live Station 904-A Power Flow & Telemetry Deck:** Animated PV $\rightarrow$ Inverter $\rightarrow$ BESS / Home Load / LESCO Net-Metering topology with 24h interactive scrubber.
    2. **HiGHS MILP Dispatch vs. Stock GoodWe Firmware Comparator:** Dual-trace SoC trajectory ($15\%$–$100\%$ of $5.12\text{ kWh}$), Peak ToU window shading (18:00–22:00), blackout islanding badges, and PKR savings ledger.
    3. **Multi-Day SSE Rolling Backtest Player:** Real-time streaming simulation across the 464-day dataset with cumulative PKR net savings counter.
    4. **Optical Defect & Soiling Wash ROI Console:** Interactive panel image inspector (5 defect classes + HUD overlay) coupled with the $1,500\text{ PKR}$ wash break-even calculator.
    5. **AI Copilot Drawer:** Natural-language executive briefing powered by `POST /api/agent/advisory`.

---

## 3. Unnecessary / Quarantined Files Log

During Step 1 of this audit, the following redundant, duplicate, or legacy industrial files were cleaned or quarantined into `archive/legacy_industrial/`:

| Original Path | Action Taken | Engineering Rationale |
| :--- | :--- | :--- |
| `src/lesco tarrif.json` *(with space)* | Moved to `archive/legacy_industrial/lesco_tarrif_legacy_space.json` | Unreferenced legacy NEPRA slab draft; `src/lesco-tarrif.json` (with hyphen) is the canonical Station LHR-RES-01 residential config. |
| `src/optimization/` (`__init__.py`, `milp_solver.py`) | Moved to `archive/legacy_industrial/src_optimization_alias/` | Redundant 8-line package alias duplicating `src/optimizer/milp_solver.py`; zero active imports across `src/` or `tests/`. |
| `scratch/` | Removed empty directory | Temporary scratch directory in repository root with zero files. |
| `notebooks/panel_defect_classification_colab.ipynb` & `01_industrial_load_eda.ipynb` | Removed / Archived in prior commit `593b91d` | Replaced by local CLI scripts (`src/vision/train_classifier.py`) and archived industrial EDA. |

---

## 4. Next-Phase Implementation Plan & Task Breakdown (Abubakar vs. Zaeem)

```
                                 NEXT-PHASE SPRINT DIVISION
                                
              ABUBAKAR (Lead)                               ZAEEM
   (FastAPI BFF, LLM Agents, Optimizer UI)     (Next.js UI Shell, CV Inspector, Charts)
                   │                                         │
   ┌───────────────┴───────────────┐         ┌───────────────┴───────────────┐
   │ Task A1: FastAPI Extended API │         │ Task Z1: Next.js 14 App Shell │
   │ Task A2: LLM Agent Copilot    │         │ Task Z2: Power Flow & Charts  │
   │ Task A3: SSE Backtest Store   │         │ Task Z3: CV & Soiling Console │
   │ Task A4: End-to-End API Tests │         │ Task Z4: Responsive UI Polish │
   └───────────────────────────────┘         └───────────────────────────────┘
```

### Phase 1: Complete Remaining Backend Hooks & Multi-Agent LLM Layer (Days 1–2)
* **Task A1 (Abubakar): Extend FastAPI Gateway (`src/api/main.py` & `src/api/schemas.py`)**
  * Add `GET /api/soiling/status` (queries `soiling_analysis_lahore.csv` + `SolarPlantLossCalculator` for any date).
  * Add `POST /api/vision/inspect` & `GET /api/vision/samples` (invokes `CCTVPanelMonitor.predict_pil_image` without modifying `src/vision/`).
  * Add `GET /api/dates` returning available date bounds (`2025-07-01` to `2026-10-07`) and notable blackout/wash anchor dates (`2026-09-23`, `2026-08-10`, `2025-12-21`).
* **Task A2 (Abubakar): Build Multi-Agent LLM Advisory Layer (`src/llm_agents/`)**
  * Create `src/llm_agents/__init__.py` and `src/llm_agents/ems_copilot.py`.
  * Implement structured Pydantic output (`EMSAdvisoryReport`) combining deterministic physics diagnostics with optional Gemini / OpenAI LLM synthesis (and zero-latency deterministic fallback when no API key is configured).
  * Wire `POST /api/agent/advisory` into `src/api/main.py` and add unit tests in `tests/test_llm_agents.py`.

### Phase 2: Build Next.js 14 Production Web Application (Days 3–5)
* **Task Z1 (Zaeem): Scaffold Next.js 14 App Router + Tailwind + TypeScript (`frontend/`)**
  * Initialize `frontend/` with strict TypeScript, Tailwind CSS dark industrial/residential glassmorphism theme, `lucide-react`, `recharts`, `zustand`, and `@tanstack/react-query`.
  * Build typed API client (`frontend/src/lib/api.ts`) matching `src/api/schemas.py`.
* **Task A3 (Abubakar): Zustand Simulation Store & 60 FPS Timeline Scrubber (`frontend/src/store/`)**
  * Build client-side state store managing selected date (`2025-07-01` to `2026-10-07`), `use_forecasts` toggle, tariff overrides, 24-hour playback scrubber, and SSE `/api/backtest/stream` consumer.
* **Task Z2 (Zaeem): Interactive Power Dispatch & Battery SoC Charts (`frontend/src/components/charts/`)**
  * Render 24-hour stacked power balance chart ($\text{PV}$, $\text{Load}$, $p_{\text{grid}}$, $p_{\text{export}}$, $p_{\text{ch}}$, $p_{\text{dis}}$), $5.12\text{ kWh}$ BESS SoC trajectory with $15\%$ floor and $55\%$ blackout reserve line, and LESCO Peak ToU (18:00–22:00) highlight bands.
* **Task Z3 (Zaeem): Computer Vision Defect & Soiling Wash ROI Console (`frontend/src/components/vision/`)**
  * Build interactive panel inspection widget displaying 5-class probability bars (`clean`, `dusty`, `bird_drop`, `electrical_damage`, `physical_damage`), OpenCV HUD preview, and $1,500\text{ PKR}$ wash break-even calculator.

### Phase 3: Full-Stack Integration, Verification & Defense Readiness (Days 6–7)
* **Task A4 & Z4 (Joint): End-to-End Integration & Benchmark Verification**
  * Verify all FastAPI routes under `< 50 ms` latency budget, zero console/TypeScript errors (`npm run build` & `tsc --noEmit`), and `100%` passing `pytest` suite.

---

## 5. Quantitative Acceptance Criteria & Verification Commands

| Subsystem | Target Acceptance Metric | Verification Command / Proof |
| :--- | :--- | :--- |
| **Non-CV Automated Tests** | $100\%$ passing ($\ge 87$ tests, $0$ failures) | `.venv/bin/pytest --ignore=tests/test_train_classifier.py` |
| **24h Telemetry Slice** | $< 1.00\text{ ms}$ retrieval latency | Measured: **$0.0346\text{ ms}$** (`feature_store.py`) |
| **24h 3-Model ML Inference** | $< 10.00\text{ ms}$ combined latency | Measured: **$2.7220\text{ ms}$** (`Solar` + `Load` + `Outage`) |
| **24h Residential MILP Solve**| $< 25.00\text{ ms}$ warm HiGHS solve | Measured: **$10.4462\text{ ms}$** (`5.12 kWh` BESS) |
| **FastAPI `/api/optimize`** | $< 50.00\text{ ms}$ HTTP round-trip | Measured: **$13.2596\text{ ms}$** (`TestClient`) |
| **Next.js Production Build** | $0$ TypeScript or ESLint errors | `cd frontend && npm run build` |

```bash
# 1. Run Non-CV Test Suite (Mandatory Guardrail Command)
.venv/bin/pytest --ignore=tests/test_train_classifier.py -v

# 2. Calibrate Residential Soiling Model & Test Wash ROI Calculator
.venv/bin/python src/soiling/calibrate_soiling_model.py
.venv/bin/python src/soiling/loss_calculator.py

# 3. Train & Benchmark Causal ML Forecasters (7.02 kWp Solar, Residential Load, Outage Risk)
.venv/bin/python src/forecast/train_solar_pv.py
.venv/bin/python src/forecast/train_residential_load.py
.venv/bin/python src/grid_outage/predict_outage.py

# 4. Launch FastAPI Residential Compute Gateway
.venv/bin/uvicorn src.api.main:app --reload --port 8000
```

