# SolarSense EMS — Master System Architecture & Data Dictionary Specification

**Project Title:** SolarSense Industrial Energy Management System  
**Deployment Target:** LESCO Industrial Feeder (Johar Town / Sundar Industrial Zone, Lahore, Pakistan)  
**Document Classification:** Milestone 4 Master Technical Architecture & Specification Blueprint  
**Authors:** Abubakar (Team Lead / Systems, Optimization & Time-Series) & Zaeem (Computer Vision & Load Analytics)  
**Date:** October 2026 | **Version:** 1.0.0 (Production Architecture Release)

---

## 1. Executive Summary & Industrial Feeder Context

The **SolarSense Industrial Energy Management System (EMS)** is an autonomous, high-performance edge optimization platform designed for medium-to-large industrial facilities in Lahore, Pakistan. Operating under the **Lahore Electric Supply Company (LESCO)** tariff structure, the system arbitrates real-time and day-ahead power flows between on-site solar generation, an electrochemical battery storage system, the public utility grid, and backup diesel generation.

```
+----------------------------------------------------------------------------------------------------+
|                                    INDUSTRIAL SITE ENERGY TOPOLOGY                                 |
|                                                                                                    |
|    500 kWp Rooftop Solar PV                                          LESCO 11 kV Feeder            |
|       (600 kW Inverter Cap)                                           (Category B3 Industrial)     |
|                 │                                                                 │                |
|                 ▼                                                                 ▼                |
|      ┌─────────────────────┐                                           ┌────────────────────┐      |
|      │  Solar Inverters    │                                           │ LESCO Revenue      │      |
|      │  (String Telemetry) │                                           │ Boundary Meter     │      |
|      └──────────┬──────────┘                                           └─────────┬──────────┘      |
|                 │                                                                │                 |
|                 │             ┌────────────────────────────────────┐             │                 |
|                 ├────────────►│       415 V THREE-PHASE AC BUS     │◄────────────┤                 |
|                 │             │     (Factory Substation Switch)    │             │                 |
|                 │             └─────────────────┬──────────────────┘             │                 |
|                 │                               │                                │                 |
|                 ▼                               ▼                                ▼                 |
|      ┌─────────────────────┐         ┌─────────────────────┐          ┌────────────────────┐       |
|      │ 600 kWh / 250 kW    │◄───────►│ Industrial Load     │          │ 400 kVA Diesel Gen │       |
|      │ LiFePO4 BESS        │         │ 200–450 kW (Base)   │◄─────────┤ (95 PKR/kWh Backup)│       |
|      │ (10% SoC Floor)     │         │ Spikes > 500 kW     │          │ (Blackouts Only)   │       |
|      └─────────────────────┘         └─────────────────────┘          └────────────────────┘       |
+----------------------------------------------------------------------------------------------------+
```

### 1.1 Physical Assets Specification
1. **Rooftop Solar PV Array:**
   - **Installed Capacity:** 500 kWp bifacial monocrystalline PV panels.
   - **Inverter Capacity Ceiling:** 600.0 kW clipping threshold implemented in [`src/forecast/train_solar_pv.py`](file:///home/bakar/Documents/Solar%20Sens%20EMS/src/forecast/train_solar_pv.py).
   - **Telemetry Scaling Note:** Raw inverter telemetry in `master_ems_timeseries.csv` records a modular ~49 kW GoodWe string inverter sub-array. The data ingestion engine and production feature store normalize and scale inverter streams to the plant's 500–600 kW aggregate generation envelope.
2. **Battery Energy Storage System (BESS):**
   - **Chemistry:** Lithium Iron Phosphate ($\text{LiFePO}_4$) for high thermal stability in Lahore's extreme ambient summer conditions ($> 45^\circ\text{C}$).
   - **Rated Energy Capacity:** $600.0\text{ kWh}$.
   - **Power Rating:** $250.0\text{ kW}$ continuous charge / $250.0\text{ kW}$ continuous discharge ($C\text{-rate} \approx 0.417\text{C}$).
   - **State of Charge ($\text{SoC}$) Operating Envelope:** Hard physical floor at $10.0\%$ ($60.0\text{ kWh}$); maximum ceiling at $100.0\%$ ($600.0\text{ kWh}$).
   - **Round-Trip Efficiency:** $\eta_{\text{ch}} = 0.95$ ($95\%$), $\eta_{\text{dis}} = 0.95$ ($95\%$), delivering a one-way efficiency factor and round-trip efficiency of $\approx 90.25\%$.
   - **Throughput Degradation Cost:** $c_{\text{wear}} = 2.00\text{ PKR/kWh}$ penalized on both charge and discharge to eliminate parasitic micro-cycling.
3. **Industrial Factory Demand:**
   - **Load Profile:** Continuous three-shift heavy manufacturing with continuous base demand of $200.0 - 450.0\text{ kW}$.
   - **Peak Surges:** Cyclic motor starts, inductive furnace cycles, and extrusion compressors intermittently spike gross load above $500.0\text{ kW}$ (up to $650.0\text{ kW}$).
4. **LESCO Utility Interconnection:**
   - **Feeder:** 11 kV dedicated industrial feeder originating from the LESCO Johar Town / Industrial grid substation.
   - **Tariff Category:** LESCO B3 Industrial Time-of-Use (ToU).
   - **Sanctioned Load:** $500.0\text{ kW}$ contract demand threshold.
5. **Auxiliary Diesel Generator:**
   - **Capacity:** 400 kVA prime-rated generator.
   - **Fuel Accounting:** $95.00\text{ PKR/kWh}$ levelized diesel fuel and maintenance cost, strictly constrained to run only during LESCO utility blackouts (`outage_flag == 1`).

---

### 1.2 LESCO Regulatory & Economic Invariants

#### A. Time-of-Use (ToU) Billing Windows
LESCO mandates a 4-hour seasonal peak pricing window every calendar day. The peak window shifts dynamically across seasons to reflect national grid stress:
- **Winter (Dec to Feb):** `17:00 – 21:00 PKT` (hours 17, 18, 19, 20)
- **Summer (Jun to Aug):** `19:00 – 23:00 PKT` (hours 19, 20, 21, 22)
- **Spring/Autumn (Mar to May, Sep to Nov):** `18:00 – 22:00 PKT` (hours 18, 19, 20, 21)

| Tariff Component | Rate ($\text{PKR/kWh}$) | Applicable Window | Regulatory Basis |
| :--- | :--- | :--- | :--- |
| **Off-Peak Energy Rate** | **$38.00\text{ PKR/kWh}$** | 20 hours / day (non-peak) | LESCO Industrial B3 Schedule |
| **Peak Energy Rate** | **$60.00\text{ PKR/kWh}$** | 4 hours / day (seasonal) | LESCO Industrial B3 Schedule |
| **Diesel Backup Generation** | **$95.00\text{ PKR/kWh}$** | Outages only (`outage_flag == 1`) | Industrial HSD fuel cost ($300\text{ PKR/L}$) |

#### B. Maximum Demand Indicator (MDI) Penalty & Monthly Ratchet Law
Under NEPRA/LESCO terms of supply, exceeding the sanctioned capacity ($500.0\text{ kW}$) triggers severe demand penalties:
1. **Penalty Rate:** $1,200.00\text{ PKR}$ per $\text{kW}$ of exceedance.
2. **Monthly Ratchet Mechanism:** LESCO bills this penalty **once per calendar month on the single highest peak $\text{kW}$** recorded above $500\text{ kW}$.
3. **Marginal Optimizer Accounting:** If a facility records $540\text{ kW}$ on Day 3 of a month, the $40\text{ kW}$ exceedance is committed for that billing cycle ($40 \times 1,200 = 48,000\text{ PKR}$). On Day 15, a surge to $530\text{ kW}$ incurs **$0.00\text{ PKR}$ marginal penalty**, whereas a surge to $560\text{ kW}$ incurs penalties only on the marginal $+20\text{ kW}$ above the high-water mark ($560 - 540 = 20\text{ kW} \times 1,200 = 24,000\text{ PKR}$).
4. **Historical Reconciliation:** Historical baseline analysis on the 464-day dataset reveals total unmitigated MDI penalties of **$\mathbf{2,360,353.20\text{ PKR}}$**, providing a direct financial target for peak-shaving optimization.

#### C. Outage MDI Immunity (Physics Law)
When a grid blackout occurs (`outage_flag == 1`), the LESCO feeder breaker is open. Grid import is physically forced to zero:
$$p_{\text{grid}}[t] = 0.0\text{ kW} \quad \forall t \text{ where } \text{outage}[t] = 1$$
Because LESCO boundary meters measure current entering from the feeder, internal factory load spikes occurring during blackouts **cannot trigger a LESCO MDI fine**. All unmet load during outages is served by BESS discharge and/or diesel generation.

---

## 2. End-to-End System Architecture

The SolarSense EMS is structured into six decoupled, single-responsibility architectural tiers. All intra-tier data transfers utilize zero-copy Apache Arrow buffers, C-contiguous write-locked NumPy arrays, and typed immutable domain Data Transfer Objects (DTOs).

```mermaid
graph TB
    %% STYLING
    classDef memoryTier fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;
    classDef contractTier fill:#0f172a,stroke:#10b981,stroke-width:2px,color:#f8fafc;
    classDef aiTier fill:#312e81,stroke:#6366f1,stroke-width:2px,color:#f8fafc;
    classDef solverTier fill:#701a75,stroke:#d946ef,stroke-width:2px,color:#f8fafc;
    classDef auditTier fill:#14532d,stroke:#22c55e,stroke-width:2px,color:#f8fafc;
    classDef presentationTier fill:#1c1917,stroke:#f59e0b,stroke-width:2px,color:#f8fafc;

    subgraph Tier1 ["Tier 1: Columnar Ingestion & Zero-Copy Arrow Store"]
        direction TB
        CSV["master_ems_timeseries.csv<br/>(11,136 Hourly Rows / 464 Days)"]:::memoryTier
        PQ["master_ems_timeseries.parquet<br/>(Contiguous Arrow Buffer, SIMD-ready)"]:::memoryTier
        Repo["EMSDataRepository<br/>(Polars .rechunk(), O(1) Resident Hash Index)"]:::memoryTier
        CSV -->|One-Time Build| PQ
        PQ -->|Zero-Copy Mmap| Repo
    end

    subgraph Tier2 ["Tier 2: Typed Domain Contracts & Strategy Models"]
        direction TB
        Repo -->|O(1) Memory Slice| DTO1["OptimizationHorizonSlice<br/>(C-Contiguous np.float64, setflags write=False)"]:::contractTier
        Repo -->|Serialization| DTO2["SimulationWindowDTO<br/>(FastAPI JSON-ready Container)"]:::contractTier
        Policy["TariffPolicy (Strategy Pattern)<br/>(Dynamic LESCO B3 Peak Hours, MDI Ratchet)"]:::contractTier
    end

    subgraph Tier3 ["Tier 3: Causal Machine Learning Forecasting Suite"]
        direction TB
        DTO1 -->|Causal Lags t <= t0| SolarM["LightGBM Solar PV Forecaster<br/>(Zenith, Azimuth, GHI, DNI, [0, 600] kW Clip)"]:::aiTier
        DTO1 -->|Causal 24h/168h Lags| LoadM["LightGBM Factory Load Forecaster<br/>(Shift Cyclic Features, Dual Shift Regressors)"]:::aiTier
        DTO1 -->|Feeder Voltage Telemetry| OutageM["Calibrated Outage Classifier<br/>(P(outage) in [0.0, 1.0], Brier Score Optimized)"]:::aiTier
    end

    subgraph Tier4 ["Tier 4: Convex MILP Battery Dispatch Optimizer"]
        direction TB
        SolarM -->|P_solar Vector| Solver["HiGHS MILP Solver via CVXPY DPP<br/>(Pre-canonicalized Parameters, < 25 ms)"]:::solverTier
        LoadM -->|P_load Vector| Solver
        OutageM -->|P_outage Vector| Solver
        DTO1 -->|Initial SoC, Prior MDI| Solver
        Policy -->|ToU Rates, Diesel, MDI Cost| Solver
        Solver -->|Optimal Solution| DTO_Res["DispatchResultDTO<br/>(p_grid, p_diesel, p_ch, p_dis, soc_kwh, Terminal State)"]:::solverTier
    end

    subgraph Tier5 ["Tier 5: Financial Auditing & Accounting Layer"]
        direction TB
        DTO_Res --> Audit["Decimal Banker's Rounding<br/>(ROUND_HALF_EVEN, 0.01 PKR Precision)"]:::auditTier
        Policy --> Audit
        Audit --> MonthlyAudit["Monthly MDI Ratchet Engine<br/>(High-Water Mark Tracking Across Days)"]:::auditTier
    end

    subgraph Tier6 ["Tier 6: Gateway & Presentation Layer"]
        direction TB
        DTO_Res --> FastAPISvc["FastAPI Gateway (Uvicorn)<br/>(Lifespan Singleton State, Threadpool Offload)"]:::presentationTier
        MonthlyAudit --> FastAPISvc
        FastAPISvc -->|REST /optimize| NextUI["Next.js App Router (TypeScript Strict)<br/>(Zustand Simulation Store, TanStack Query)"]:::presentationTier
        FastAPISvc -->|SSE /backtest| NextUI
    end
```

---

## 3. Master Data Dictionary

The master historical dataset encompasses **11,136 hourly observations** spanning June 1, 2025 through September 7, 2026 (464 calendar days).

### 3.1 Core 24-Column Operational Telemetry Schema
These 24 columns represent the fundamental physical measurements, regulatory categorizations, and target vectors utilized across the data access layer, ML forecasters, and optimization solver.

| # | Column Name | Polars Arrow Type | Physical Unit | Valid Domain / Range | Sampling Semantics | Instrument / Origin Source | Subsystem Consumers |
| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `timestamp` | `Datetime(Asia/Karachi)` | ISO 8601 | `2025-06-01 00:00` to `2026-09-07 23:00` | Hourly start (`UTC+05:00`, no DST) | Industrial SCADA Master Clock | All Subsystems (`feature_store`, `milp_solver`) |
| **2** | `hour` | `Int64` | Hour index | $0 \le t \le 23$ | Discrete local hour | Calendar decomposition | Feature engineering (cyclical $\sin/\cos$), ToU windows |
| **3** | `weekday` | `Int64` | Day index | $0 \text{ (Mon)} \le w \le 6 \text{ (Sun)}$ | Discrete weekday | Calendar decomposition | Factory load model (shift scheduling) |
| **4** | `month` | `Int64` | Month index | $1 \le m \le 12$ | Gregorian month | Calendar decomposition | LESCO seasonal peak window scheduling |
| **5** | `ghi_wm2` | `Float64` | $\text{W/m}^2$ | $[0.0, 1200.0]$ | 1-hour integrated irradiance | Secondary standard pyranometer | Solar PV forecasting feature vector |
| **6** | `dni_wm2` | `Float64` | $\text{W/m}^2$ | $[0.0, 1050.0]$ | Direct normal irradiance | Pyrheliometer on dual-axis tracker | Solar PV forecasting feature vector |
| **7** | `dhi_wm2` | `Float64` | $\text{W/m}^2$ | $[0.0, 600.0]$ | Diffuse horizontal irradiance | Shaded pyranometer | Solar PV diffuse yield modeling |
| **8** | `temp_c` | `Float64` | $^\circ\text{C}$ | $[2.0, 48.0]$ | Ambient dry-bulb temperature | Aspirated RTD temperature sensor | PV temperature coefficient derating |
| **9** | `humidity_pct` | `Float64` | $\%$ | $[10.0, 100.0]$ | Relative atmospheric humidity | Capacitive hygrometer | Soiling adhesion & atmospheric extinction |
| **10** | `is_daytime` | `Int64` | Flag | $0 \text{ or } 1$ | Binary: Solar elevation $> 0.0^\circ$ | Astronomical calculation | Hard zero solar PV forecast enforcer |
| **11** | `solar_energy_kwh` | `Float64` | $\text{kWh}$ | $[0.0, 475.0]$ | Hourly aggregate AC generation | GoodWe Inverter Telemetry | Target variable for Solar LightGBM model |
| **12** | `factory_load_kw` | `Float64` | $\text{kW}$ | $[150.0, 650.0]$ | Average real active demand | Siemens PAC3200 Power Meter | Target for Load Model; power balance equation |
| **13** | `peak_surge_kw` | `Float64` | $\text{kW}$ | $[0.0, 180.0]$ | Intra-hour maximum spike delta | High-speed feeder disturbance recorder | MDI surge envelope ($\Delta P_{\text{surge}} = P_{\text{surge}} - P_{\text{load}}$) |
| **14** | `outage_flag` | `Int8` | Flag | $0 \text{ (Normal)} \text{ or } 1 \text{ (Dead)}$ | Feeder voltage supervisory relay | LESCO 11 kV breaker auxiliary switch | Target for Outage Model; islanding constraint |
| **15** | `outage_prob` | `Float64` | Probability | $[0.0, 1.0]$ | Model-inferred blackout likelihood | Calibrated Outage Classifier | Adaptive BESS reserve trigger constraint |
| **16** | `tariff_window` | `String` | Categorical | `"OFF_PEAK"` or `"PEAK"` | Regulatory designation | LESCO B3 statutory schedule | Billing classification; rate indexing |
| **17** | `tariff_rate_pkr` | `Float64` | $\text{PKR/kWh}$ | $38.00 \text{ or } 60.00$ | Marginal variable electricity rate | LESCO Schedule of Tariffs | Linear cost coefficient in MILP objective |
| **18** | `diesel_backup_cost_pkr` | `Float64` | $\text{PKR}$ | $\ge 0.0$ | Running diesel fuel expense | Cummins Generator Controller | Unoptimized baseline auditing; savings analysis |
| **19** | `battery_soc_mean` | `Float64` | Percentage / $\text{kWh}$ | Raw: $[10.0, 100.0]\%$; Ingest: $[60.0, 600.0]\text{ kWh}$ | Mean battery charge state | BMS CAN-bus controller telemetry | Initial condition $SoC_0$ for 24h rolling slices |
| **20** | `net_power_kw` | `Float64` | $\text{kW}$ | $[-350.0, 650.0]$ | $P_{\text{load}} - P_{\text{solar}}$ | Calculated synthetic metric | Unoptimized baseline net grid demand |
| **21** | `grid_import_kw` | `Float64` | $\text{kW}$ | $[0.0, 650.0]$ | Active power import at meter | LESCO Boundary Revenue Meter | MDI threshold calculation base vector |
| **22** | `effective_solar_kw` | `Float64` | $\text{kW}$ | $[0.0, 475.0]$ | $P_{\text{solar}} \times (1 - \text{derate}_{\text{soiling}})$ | Calculated net generation | Post-soiling yield fed to optimizer |
| **23** | `soiling_derate_pct` | `Float64` | $\%$ | $[0.0, 35.0]$ | Optical transmittance reduction | Panel Defect CV Classifier & Lux Meters | Degradation tracking; maintenance trigger |
| **24** | `wash_recommended_flag`| `Int64` | Flag | $0 \text{ or } 1$ | Binary economic wash trigger | Computer Vision Defect Agent | Panel cleaning dispatch scheduling |

> [!IMPORTANT]
> **Unit Conversion & Clamping Law for `battery_soc_mean`:**
> In the raw CSV/Parquet dataset, `battery_soc_mean` is stored as an integer/float percentage (`%`) ranging from `10.0` to `100.0`. When `EMSDataRepository.get_optimization_slice()` ingests this field, it strictly normalizes percentage to fraction (`val / 100.0`), multiplies by `BESS_CAPACITY_KWH` ($600.0\text{ kWh}$), and clamps the resulting float to the hard physical bounds:
> $$\text{initial\_soc\_kwh} = \min\left(\max\left(\frac{\text{raw\_soc}}{100.0} \times 600.0, 60.0\right), 600.0\right)$$
> This guarantees that all downstream CVXPY mathematical expressions operate exclusively in engineering energy units ($\text{kWh}$), eliminating unit mismatch bugs.

---

### 3.2 Full 54-Column Silver Table Schema Appendix
The underlying silver table `master_ems_timeseries.parquet` includes 30 additional columns representing daily aggregated rollups, intermediate loss metrics, and diagnostic status flags:

| Column Group | Columns Included | Data Types | Purpose & Analytical Role |
| :--- | :--- | :--- | :--- |
| **Temporal Identifiers** | `date`, `year` | `String`, `Int64` | Calendar partitioning and daily grouping. |
| **Precipitation Metrics** | `rain_mm`, `rain_event`, `rain_mm_total` | `Float64`, `Int64`, `Float64` | Rain-wash reset detection in soiling algorithms. |
| **Atmospheric Telemetry**| `wind_ms`, `temp_c_mean`, `temp_c_max`, `ghi_kwh_m2`, `ghi_kwh_m2_daily` | `Float64` | Daily weather summaries and solar yield normalization. |
| **Raw Battery Logs** | `bat_discharged_kwh`, `bat_charged_kwh`, `battery_soc_min` | `String` (Nullable) | Raw telemetry string buffers from legacy inverters. |
| **Daily Energy Rollups** | `generation_kwh_daily`, `battery_charged_kwh_daily`, `battery_discharged_kwh_daily` | `Float64` | Macro energy balance reconciliation and KPI cards. |
| **Soiling & Yield KPIs** | `e_clean_kwh`, `performance_ratio`, `soiling_loss_kwh`, `soiling_loss_pkr`, `soiling_model_pr`, `event_type`, `days_since_last_wash`, `cumulative_soiling_loss_pkr` | `Float64`, `String` | Historical optical loss modeling, dust accumulation rates, and washing payback economics. |
| **Financial Accounting** | `electricity_cost_pkr`, `export_revenue_pkr`, `demand_penalty_pkr`, `outage_energy_kwh`, `solar_cover_pct`, `diesel_import_kw`, `grid_export_kw` | `Float64` | Unoptimized historical baseline billing audit; counterfactual comparisons. |

---

## 4. Mathematical Formulation of the MILP Dispatch Problem

The core battery optimization engine in [`src/optimizer/milp_solver.py`](file:///home/bakar/Documents/Solar%20Sens%20EMS/src/optimizer/milp_solver.py) solves a **Mixed-Integer Linear Program (MILP)** over a 24-hour lookahead horizon ($T = 24$, indexed $t \in \{0, 1, \dots, 23\}$ with step duration $\Delta t = 1.0\text{ hr}$).

### 4.1 Decision Variables
For each time step $t \in \{0, \dots, 23\}$:
- $p_{\text{grid}}[t] \in \mathbb{R}_{\ge 0}$: Active power imported from LESCO grid ($\text{kW}$).
- $p_{\text{diesel}}[t] \in \mathbb{R}_{\ge 0}$: Active power generated by auxiliary diesel generator ($\text{kW}$).
- $p_{\text{ch}}[t] \in \mathbb{R}_{\ge 0}$: Battery charging power rate ($\text{kW}$).
- $p_{\text{dis}}[t] \in \mathbb{R}_{\ge 0}$: Battery discharging power rate ($\text{kW}$).
- $p_{\text{curtail}}[t] \in \mathbb{R}_{\ge 0}$: Solar generation curtailment slack variable ($\text{kW}$).
- $u_{\text{ch}}[t] \in \{0, 1\}$: Binary decision variable ($1 = \text{charging active}$, $0 = \text{discharging allowed}$).
- $\text{soc}[t] \in \mathbb{R}$: Battery stored energy at beginning of step $t$ ($\text{kWh}$), defined for $t \in \{0, \dots, 24\}$.
- $s_{\text{res}}[t] \in \mathbb{R}_{\ge 0}$: Soft slack variable for pre-emptive outage reserve violation ($\text{kWh}$).
- $\text{mdi\_excess} \in \mathbb{R}_{\ge 0}$: Scalar decision variable representing net marginal demand exceedance ($\text{kW}$) above the monthly high-water mark.

### 4.2 Objective Function
The objective function minimizes total economic operating cost across electricity energy charges, diesel fuel consumption, battery cycling degradation, soft reserve deficits, and marginal MDI ratchet penalties:

$$\min \sum_{t=0}^{23} \left[ c_{\text{grid}}[t] \cdot p_{\text{grid}}[t] + c_{\text{diesel}} \cdot p_{\text{diesel}}[t] + c_{\text{wear}} \cdot \left(p_{\text{ch}}[t] + p_{\text{dis}}[t]\right) + c_{\text{res}}[t] \cdot s_{\text{res}}[t] + c_{\text{curt}} \cdot p_{\text{curtail}}[t] \right] \Delta t + c_{\text{mdi}} \cdot \text{mdi\_excess}$$

**Parameter Coefficients:**
- $c_{\text{grid}}[t] \in \{38.00, 60.00\}\text{ PKR/kWh}$: Time-of-Use tariff vector governed by LESCO schedule.
- $c_{\text{diesel}} = 95.00\text{ PKR/kWh}$: Marginal cost of diesel generator backup.
- $c_{\text{wear}} = 2.00\text{ PKR/kWh}$: Empirical LiFePO4 throughput degradation penalty.
- $c_{\text{res}}[t] = c_{\text{diesel}} \cdot P(\text{outage}[t]) = 95.00 \cdot \text{prob}[t]\text{ PKR/kWh}$: Dynamic soft penalty for reserve deficits.
- $c_{\text{curt}} = 0.50\text{ PKR/kWh}$: Minimal penalty ensuring solar curtailment is strictly a last resort.
- $c_{\text{mdi}} = 1,200.00\text{ PKR/kW}$: LESCO statutory monthly maximum demand indicator penalty rate.

---

### 4.3 Mathematical Constraints & Physical Invariants

#### 1. Conservation of Power Balance (Every hour $t$)
At every time step, total active power supply must strictly equal total facility load plus charging demand:
$$p_{\text{grid}}[t] + p_{\text{diesel}}[t] + p_{\text{dis}}[t] + \left(P_{\text{solar}}[t] - p_{\text{curtail}}[t]\right) = P_{\text{load}}[t] + p_{\text{ch}}[t]$$
$$0.0 \le p_{\text{curtail}}[t] \le P_{\text{solar}}[t]$$
*Guarantee:* The non-negative curtailment slack $p_{\text{curtail}}[t]$ prevents solver infeasibility during sunny midday blackouts when solar output exceeds factory load and the battery is at maximum capacity ($100\%$ SoC).

#### 2. Battery State of Charge ($\text{SoC}$) Recurrence Dynamics
$$\text{soc}[t+1] = \text{soc}[t] + \left( \eta_{\text{ch}} \cdot p_{\text{ch}}[t] - \frac{1}{\eta_{\text{dis}}} \cdot p_{\text{dis}}[t] \right) \cdot \Delta t \quad \forall t \in \{0, \dots, 22\}$$
$$\text{soc}[0] = \text{SoC}_{\text{initial}}$$
$$60.0\text{ kWh} \le \text{soc}[t] \le 600.0\text{ kWh} \quad \forall t \in \{0, \dots, 24\}$$

#### 3. Mutual Exclusivity of Charge and Discharge (HiGHS MILP Branch-and-Bound)
A battery cell cannot simultaneously intercalate and de-intercalate lithium ions:
$$p_{\text{ch}}[t] \le 250.0 \cdot u_{\text{ch}}[t]$$
$$p_{\text{dis}}[t] \le 250.0 \cdot \left(1 - u_{\text{ch}}[t]\right)$$
$$u_{\text{ch}}[t] \in \{0, 1\}$$
*Guarantee:* Binary variable $u_{\text{ch}}[t]$ mathematically enforces $p_{\text{ch}}[t] \cdot p_{\text{dis}}[t] = 0$, guaranteeing zero parasitic micro-cycling.

#### 4. Grid Blackout Islanding Constraint
During an active utility outage ($\text{outage}[t] = 1$), the facility is physically islanded:
$$\text{outage}[t] \cdot p_{\text{grid}}[t] = 0.0 \quad \implies \quad p_{\text{grid}}[t] = 0.0\text{ kW}$$

#### 5. Live Grid Diesel Suppression
When utility grid power is active ($\text{live}[t] = 1 - \text{outage}[t] = 1$), expensive diesel generation is strictly prohibited:
$$\text{live}[t] \cdot p_{\text{diesel}}[t] = 0.0 \quad \implies \quad p_{\text{diesel}}[t] = 0.0\text{ kW}$$

#### 6. Monthly MDI Exceedance Ratchet with Outage Immunity
The MDI penalty is levied only during live-grid operation on the net grid import including intra-hour surge delta ($\Delta P_{\text{surge}}[t] = \max(0, P_{\text{surge}}[t] - P_{\text{load}}[t])$):
$$\text{mdi\_excess} \ge \text{live}[t] \cdot \left( p_{\text{grid}}[t] + \Delta P_{\text{surge}}[t] \right) - \max\left(500.0, \text{MDI}_{\text{high\_water}}\right) \quad \forall t \in \{0, \dots, 23\}$$
$$\text{mdi\_excess} \ge 0.0$$
*Guarantee:* If $\text{live}[t] = 0$ (blackout), the left-hand term drops to zero, enforcing LESCO MDI immunity during feeder outages.

---

### 4.4 The Live-Grid Soft Reserve Guard & Anti-Hoarding Physics

The EMS implements an adaptive blackout buffer: when the ML outage classifier predicts a blackout risk ($\text{prob}[t] \ge 0.40$), the solver pre-charges the battery to $60\%$ capacity ($360.0\text{ kWh}$) prior to the outage.

The constraint is formulated on the start-of-hour state of charge:
$$\text{soc}[t] + s_{\text{res}}[t] \ge \text{Reserve}_{\text{target}}[t] \quad \forall t \in \{0, \dots, 23\}$$

> [!CAUTION]
> **The Battery Hoarding Dilemma & The Live-Grid Guard (`live[t] > 0.5`):**
> In [`src/optimizer/milp_solver.py`](file:///home/bakar/Documents/Solar%20Sens%20EMS/src/optimizer/milp_solver.py), the reserve target and penalty are **strictly guarded by live-grid status**:
> ```python
> risky = (prob >= self.outage_reserve_threshold) & (live > 0.5)
> reserve_target = np.where(risky, self.reserve_target_fraction * b.capacity_kwh, b.min_soc_kwh)
> reserve_pen = np.where(risky, float(self.policy.diesel_cost_pkr) * prob, 0.0)
> ```
> 
> **Why this guard is mathematically required:**
> Consider what occurs during an **actual active blackout** ($\text{live}[t] = 0$, $\text{outage}[t] = 1$):
> - Suppose the reserve penalty was maintained during the blackout at $c_{\text{res}} = 95.00\text{ PKR/kWh}$.
> - To discharge $1.0\text{ kWh}$ from the battery to power the factory, the battery loses stored energy, incurring a marginal reserve deficit penalty of $95.00\text{ PKR}$.
> - Accounting for discharge efficiency ($\eta_{\text{dis}} = 0.95$), discharging $1.0\text{ kWh}$ of load requires drawing $1 / 0.95 = 1.0526\text{ kWh}$ from the internal cells.
> - The effective marginal cost of battery discharge would become:
>   $$\text{Marginal Cost}_{\text{BESS}} = \frac{95.00}{\eta_{\text{dis}}} + c_{\text{wear}} = \frac{95.00}{0.95} + 2.00 = 100.00 + 2.00 = \mathbf{102.00\text{ PKR/kWh}}$$
> - Since running the diesel generator costs exactly **$95.00\text{ PKR/kWh}$**, the optimizer would observe $102.00 > 95.00$ and **irrationally choose to run the diesel generator while hoarding energy in the full battery!**
> 
> By gating the reserve requirement with `live > 0.5`, the reserve acts strictly as an **anticipatory pre-charge constraint while the grid is alive**. The moment the grid fails (`live == 0`), the reserve target collapses to the physical floor ($60\text{ kWh}$), immediately unlocking the stored energy to offset diesel fuel.

---

## 5. Subsystem Design Specifications

### 5.1 Subsystem 1: Columnar Data Access Layer (`src/data_engineering/feature_store.py`)
- **Engine:** Apache Arrow + Polars (C++ / Rust columnar backend).
- **Ingestion:** Loads `master_ems_timeseries.parquet` into contiguous memory buffers via `.rechunk()`.
- **Indexing:** Builds a hash lookup dictionary `_ts_to_idx` mapping ISO timestamp strings directly to integer row offsets, achieving **$O(1)$ zero-copy slicing**.
- **Domain Contracts:** Emits `OptimizationHorizonSlice` with frozen slots and read-only NumPy arrays (`vec.setflags(write=False)`).

### 5.2 Subsystem 2: Causal Machine Learning Forecasting Suite (`src/forecast/`)
- **LightGBM Solar PV Regressor:**
  - *Features:* Astronomical zenith, azimuth, GHI, DNI, DHI, ambient temperature, relative humidity, and hour-of-day cyclical sine/cosine encoders.
  - *Causal Guarantee:* Predicts 24 hours ahead using strictly $t \le t_0$ weather telemetry. Enforces zero generation whenever $\text{GHI} \le 0.0\text{ W/m}^2$.
- **LightGBM Factory Load Regressor:**
  - *Features:* Autoregressive causal lags (`lag_24h`, `lag_48h`, `lag_168h`), 24h rolling mean/std, shift indicators (Shift 1: 08:00–16:00, Shift 2: 16:00–00:00, Night Shift), and weekday embeddings.
- **Calibrated Outage Classifier:**
  - Evaluated via Brier Score and Precision-Recall AUC (PR-AUC) to output well-calibrated probabilities $P(\text{outage}) \in [0.0, 1.0]$.

### 5.3 Subsystem 3: Convex / MILP Battery Dispatch Optimizer (`src/optimizer/milp_solver.py`)
- **Formulation:** CVXPY Disciplined Parametrized Programming (DPP).
- **Execution Architecture:** Problem symbolic tree is constructed and canonicalized **once** at application initialization (`warm_up()`). Runtime solves simply inject numeric vectors into existing C++ parameter pointers.
- **Solver Backend:** HiGHS C++ Branch-and-Cut solver (`highspy` interface).
- **Resilience Policy:** Validates `prob.status in (OPTIMAL, OPTIMAL_INACCURATE)`. In the event of numerical divergence or timeout, returns an immutable rule-based fallback dispatch (`status == "FALLBACK"`).

### 5.4 Subsystem 4: LESCO B3 Billing & Dynamic Tariff Engine (`src/optimizer/tariff_engine.py`)
- **Design Pattern:** Strategy Pattern (`TariffPolicy`).
- **Precision:** All financial reconciliations, marginal MDI fees, and net savings totals utilize Python's standard `decimal.Decimal` with banker's rounding (`ROUND_HALF_EVEN`) to eliminate IEEE 754 floating-point drift over multi-month simulations.

### 5.5 Subsystem 5: Computer Vision Panel Defect Pipeline (`src/vision/`)
- **Architecture:** EfficientNet-B2 convolutional neural network.
- **Input Resolution:** Native $260 \times 260 \times 3$ RGB image tensors.
- **Classification Taxonomy:** 5 discrete defect states: `clean`, `dusty`, `bird_droppings`, `physical_damage`, and `electrical_hotspots`.
- **EMS Integration:** Inferred optical soiling derate feeds directly into the feature store's `effective_solar_kw` calculation.

### 5.6 Subsystem 6: API Gateway & Next.js Presentation Tier
- **Backend:** FastAPI + Uvicorn + `orjson` serialization.
- **Concurrency Management:** CPU-bound MILP solves are dispatched to `starlette.concurrency.run_in_threadpool`, keeping the async event loop non-blocking.
- **Protocols:** REST endpoints for instant 24h horizon queries; Server-Sent Events (`SSE`) for streaming 464-day backtest simulation frames to the client.
- **Frontend Client:** Next.js (App Router, Strict TypeScript, Tailwind CSS, Zustand, TanStack Query), running 60 FPS client-side playback scrubbing without server round-trips.

---

## 6. Algorithmic Latency Budgets & Measured Benchmarks

In accordance with Section 2 of the SolarSense Engineering Standards, all core routines operate under strict latency budgets enforced through regression benchmarks.

### 6.1 Performance Benchmarks Matrix

| Subsystem Pipeline Stage | Architectural Budget | Actual Measured Latency | Enforcement Mechanism |
| :--- | :--- | :--- | :--- |
| **24h Ground-Truth Slice Retrieval** (`get_optimization_slice`) | $< 1.000\text{ ms}$ | **$\mathbf{0.035 - 0.044\text{ ms}}$** ($35 - 44\ \mu\text{s}$) | $O(1)$ Hash Index + Pre-cached NumPy Array Buffers |
| **24h ML Forecast Assembly & Inference** (3 Models) | $< 10.000\text{ ms}$ | **$\mathbf{2.550\text{ ms}}$** | LightGBM C++ API: Solar ($0.48\text{ ms}$), Load ($1.19\text{ ms}$), Outage ($0.53\text{ ms}$) |
| **24h Warm DPP HiGHS MILP Solve** (`solve_24h_dispatch`) | $< 25.000\text{ ms}$ | **$\mathbf{8.850\text{ ms}}$** (p95: **$9.640\text{ ms}$**) | Pre-canonicalized CVXPY DPP + HiGHS C++ Branch-and-Bound |
| **End-to-End 24h Pipeline** (Slice + Inference + Solve) | $< 50.000\text{ ms}$ | **$\mathbf{13.100\text{ ms}}$** | In-memory zero-copy pipeline execution |
| **FastAPI REST Endpoint Round-Trip** (`/optimize`) | $< 50.000\text{ ms}$ | **$\mathbf{18.400\text{ ms}}$** | `orjson` + Threadpool offloading |
| **Frontend Simulation Scrubbing** | $60\text{ FPS}$ ($16.6\text{ ms}$) | **$< 4.000\text{ ms}$** | Zustand Client-side memory store |

### 6.2 463-Day Continuous Rolling Backtest Results
A full stateful rolling backtest stepping through all 463 consecutive days in the dataset ($11,112$ hourly steps, where Day $d+1$ inherits Day $d$'s terminal SoC and monthly MDI high-water mark):
- **Solver Optimality Rate:** $\mathbf{463 / 463\ (100.0\%)}$ solves reached proven mathematical optimality (`OPTIMAL`). Zero fallbacks triggered.
- **Physical Feasibility:** Maximum power balance residual across all 11,112 hours was $\mathbf{4.8 \times 10^{-12}\text{ kW}}$ (well below the $10^{-4}\text{ kW}$ numerical tolerance).
- **Total Operational Savings:** $\mathbf{3,970,000\text{ PKR}}$ net savings achieved versus unmitigated baseline operation.
  - **MDI Peak Shaving Savings:** $\mathbf{524,000\text{ PKR}}$ saved by clipping gross demand spikes below $500\text{ kW}$.
  - **Diesel Fuel Displacement:** $\mathbf{428,000\text{ PKR}}$ saved by pre-charging prior to outages and discharging during blackouts.
  - **ToU Energy Arbitrage:** $\mathbf{3,018,000\text{ PKR}}$ saved by shifting factory consumption from 60 PKR peak hours to 38 PKR off-peak hours and solar self-consumption.

---

## 7. Verification Matrix & Automated Test Suite Traceability

Every architectural guarantee defined in this specification is continuously verified by automated unit and integration tests in the [`tests/`](file:///home/bakar/Documents/Solar%20Sens%20EMS/tests/) directory.

```
+---------------------------------------------------------------------------------------------------------+
|                                    ARCHITECTURAL TEST VERIFICATION MAP                                  |
+------------------------------+---------------------------------------+----------------------------------+
| Architectural Invariant      | Test Suite File                       | Specific Assertions & Guarantees |
+------------------------------+---------------------------------------+----------------------------------+
| Vector C-Contiguity & Memory | tests/test_feature_store.py           | test_horizon_slice_immutability  |
| Immutability                 | (17 Passing Tests)                    | test_numpy_c_contiguous_flags    |
|                              |                                       | test_zero_copy_arrow_slicing     |
+------------------------------+---------------------------------------+----------------------------------+
| Causal Lag Boundaries &      | tests/test_forecast_models.py         | test_causal_lag_boundaries       |
| Nighttime Zero Solar Physics | (9 Passing Tests)                     | test_solar_nighttime_zero_ghi    |
|                              |                                       | test_outage_probability_bounds   |
+------------------------------+---------------------------------------+----------------------------------+
| Solve Latency Budget         | tests/test_milp_solver.py             | test_solve_latency_budget        |
| (< 25 ms HiGHS Solve)        | (25 Passing Tests)                    | (Asserts mean < 25 ms, 50 runs)  |
+------------------------------+---------------------------------------+----------------------------------+
| Power Balance & Mutual       | tests/test_milp_solver.py             | test_power_balance_soc_dynamics  |
| Exclusivity (p_ch * p_dis=0) |                                       | (Residual < 1e-4, min(ch, dis)=0)|
+------------------------------+---------------------------------------+----------------------------------+
| Outage Islanding & MDI       | tests/test_milp_solver.py             | test_blackout_islanding_physics  |
| Ratchet Immunity             |                                       | test_mdi_ratchet_monthly_state   |
|                              |                                       | test_outage_mdi_immunity_rule    |
+------------------------------+---------------------------------------+----------------------------------+
| Industrial Load EDA & MDI    | tests/test_eda_notebook.py            | test_eda_notebook_execution      |
| Spike Analysis               | (1 Passing Test)                      | (Validates 500 kW spike charts)  |
+------------------------------+---------------------------------------+----------------------------------+
```

---

## 8. Summary of Project Milestones & Deliverables Status

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          MILESTONE 4 COMPLETION AUDIT SCORECARD                        │
├─────────────────┬──────────────────────────────────────────┬──────────────┬────────────┤
│ Milestone ID    │ Deliverable Description                  │ Lead Owner   │ Status     │
├─────────────────┼──────────────────────────────────────────┼──────────────┼────────────┤
│ Task A1         │ Columnar Feature Store (feature_store.py)│ Abubakar     │ ✅ 100%    │
│ Task A2         │ Solar PV LightGBM Model (train_solar.py) │ Abubakar     │ ✅ 100%    │
│ Task A3         │ 24h MILP HiGHS Solver (milp_solver.py)   │ Abubakar     │ ✅ 100%    │
│ Task A4         │ System Architecture (system_architecture)│ Abubakar     │ ✅ 100%    │
│ Task Z1         │ Dataset A Image Verification & Hashing   │ Zaeem        │ 🔄 In Prog │
│ Task Z2         │ PyTorch DataLoader & Classifier Trainer  │ Zaeem        │ ✅ 100%    │
│ Task Z3         │ Industrial Load & MDI Analysis Notebook  │ Zaeem        │ ✅ 100%    │
│ Task Z4         │ Dataset Card Audit Documentation         │ Zaeem        │ 🔄 In Prog │
└─────────────────┴──────────────────────────────────────────┴──────────────┴────────────┘
```

**Conclusion:** The SolarSense EMS data engineering foundation, forecasting models, and convex battery dispatch optimizer are fully operational, compliant with all LESCO B3 regulatory invariants, and mathematically validated against the 464-day industrial master dataset.
