# SolarSense EMS — AI Agents & Multi-Agent Microgrid Architecture

The **SolarSense Energy Management System (Lahore, Pakistan)** operates as a high-performance multi-agent intelligent platform bridging physical power electronics, empirical hardware telemetry, and mixed-integer linear programming (MILP).

The system architecture combines a **Master Orchestrator Agent** with specialized domain sub-agents designed to manage energy arbitrage, demand charges, blackout resilience, panel maintenance, and forensic data auditing.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          SOLARSENSE MULTI-AGENT ARCHITECTURE                           │
│                                                                                        │
│                          ┌─────────────────────────────┐                               │
│                          │  Master Orchestrator Agent  │                               │
│                          │  (LLM + Tool-Use Gateway)   │                               │
│                          └──────────────┬──────────────┘                               │
│                                         │                                              │
│          ┌──────────────────┬───────────┴───────────┬──────────────────┐               │
│          ▼                  ▼                       ▼                  ▼               │
│  ┌───────────────┐  ┌───────────────┐       ┌───────────────┐  ┌───────────────┐       │
│  │ Sub-Agent A   │  │ Sub-Agent B   │       │ Sub-Agent C   │  │ Sub-Agent D   │       │
│  │ Peak Shaver   │  │ Maintenance   │       │ Vision        │  │ Forensic Data │       │
│  │ & Dispatcher  │  │ Oracle        │       │ Inspector     │  │ Auditor       │       │
│  │ (CVXPY/HiGHS) │  │ (CUSUM/Loss)  │       │ (EfficientNet)│  │ ("Argon")     │       │
│  └───────────────┘  └───────────────┘       └───────────────┘  └───────────────┘       │
│          │                  │                       │                  │               │
│          ▼                  ▼                       ▼                  ▼               │
│  5.12 kWh / 600 kWh  Soiling Loss &         5-Class Optical    16-Month Balance,       │
│  ToU Arbitrage &     Weather-Aware          Defect & Dust      Zero Phantom Leakage,   │
│  Peak Suppression    Cleaning Economics     Classifier         Hardware Invariants     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Master Orchestrator Agent (LLM + Tool Gateway)

**Role:** Natural Language User Interface & Strategic Microgrid Coordinator.
* **Function:** Serves as the interactive "Chat with your Microgrid" interface for factory executives or homeowners. Examples:
  * *"Why was our electricity bill 35% higher last week?"*
  * *"How much did the battery save us during yesterday evening's LESCO blackout?"*
  * *"Should we wash the solar panels this morning given the weather forecast?"*
* **Workflow:**
  1. Parses intent and extracts temporal/hardware entities.
  2. Queries the [`EMSDataRepository`](file:///home/bakar/Documents/Solar%20Sens%20EMS/src/data_engineering/feature_store.py) or invokes specialized sub-agents via function-calling.
  3. Synthesizes an executive diagnostic advisory report with actionable financial recommendations.
* **Engine:** LLM equipped with structured schema tool-calling, anchored to real-time telemetry and solver outputs.

---

## 2. Specialized Domain Sub-Agents

### 🤖 Sub-Agent A: Peak Shaver & Battery Dispatch Optimizer (CVXPY + HiGHS)
**Role:** Optimal 24-Hour Real-Time Power Flow Controller.
* **Dual Operating Envelopes:**
  * **Station LHR-RES-01 Residential Envelope:** 7.02 kWp bifacial PV, GoodWe ES hybrid inverter (SN: `9010KESC253L0146`), 5.12 kWh LiFePO4 battery ($51.2\text{ V}, 100\text{ Ah}$, 1C / 5.0 kW rating), LESCO A-1 ToU (Peak $46.85\text{ PKR}$, Off-Peak $34.53\text{ PKR}$, Net Export $27.00\text{ PKR}$, $10.0\text{ kW}$ sanctioned load).
  * **LESCO B3 Industrial Benchmark (Archived Legacy — `archive/legacy_industrial/`):** 500 kWp PV, 600 kWh / 250 kW BESS, 500 kW sanctioned load ceiling with punitive $1,200\text{ PKR/kW}$ monthly MDI ratchet fines.
* **Core Algorithmic Guarantees:**
  1. **Post-Blackout Peak Recharge Suppression:** Unlike GoodWe's stock firmware (which pulled 3.18 kW from the grid at 18:25 on Oct 26 to recharge a 95% battery during the expensive 46.85 PKR peak window), the optimizer enforces $p_{\text{grid}}[t] \le \text{load}[t]$ whenever $\text{SoC} \ge 15\%$, deferring battery recharge to off-peak hours (22:00 @ 34.53 PKR) or morning solar (27.00 PKR opportunity cost).
  2. **Pre-Peak Solar Arbitrage:** Storing midday solar surplus rather than exporting captures a net positive margin of **+12.96 PKR/kWh cycled** ($0.853 \times 46.85 - 27.00 = +12.96\text{ PKR}$).
  3. **Anti-Hoarding Soft Outage Reserve:** Reserve floor is strictly gated by $\text{live}[t] > 0.5$. Mathematical proof: during active blackout, effective discharge cost is lower than 95.00 PKR/kWh diesel, unlocking full battery support immediately.
  4. **Latency:** Solves the full 24-hour horizon in **$12.06\text{ ms}$** via compiled CVXPY DPP parameters.

---

### 🧽 Sub-Agent B: Maintenance Oracle (Physics-Informed Cleaning Economics)
**Role:** Soiling Loss Modeler & Cleaning Profitability Analyst.
* **The Economic Tradeoff:**
  * Residential washing cost: **1,500 PKR**; Industrial washing cost: **15,000 PKR**.
  * Dust and atmospheric particulate matter slowly degrade panel performance ratio ($\text{PR}$).
* **Function:** Monitors the `soiling_model_pr` and `cumulative_soiling_loss_pkr` feature store channels. Cross-references 7-day Open-Meteo precipitation forecasts. Evaluates whether a cleaning event will generate a net positive ROI before the next rain event washes the array naturally.
* **Model Type:** Physics-informed kinetic deposition model + CUSUM statistical breakpoint detector.

---

### 👁️ Sub-Agent C: Vision Inspector (Computer Vision Diagnostics)
**Role:** Optical Array Health & Hardware Defect Diagnostician.
* **The Problem:** Physical cracks, bird soiling, localized hotspots, and severe dust accumulation degrade PV strings invisibly.
* **Function:** Ingests smartphone or drone images of solar panels and classifies them into one of 5 operational classes:
  1. `Clean`
  2. `Dusty`
  3. `Bird Droppings`
  4. `Physical Damage`
  5. `Electrical Damage`
* **Model Type:** PyTorch EfficientNet-B2 fine-tuned on Dataset A/B with test-time augmentation, outputting confidence scores and estimated derating factors for the feature store.

---

### 🛡️ Sub-Agent D: Forensic Data Auditor ("Argon")
**Role:** Independent Mathematical & Physical Invariant Verifier.
* **Function:** Runs continuous background checks on raw SEMS+ portal logs and master feature stores:
  1. **Macroscopic Energy Conservation:** Asserts $\text{PV} + \text{Purchased} - \text{Sold} = \text{Home Load} + \text{Losses}$ ($2.42\text{ kWh/day}$ hardware loss baseline).
  2. **Zero Nocturnal Solar Leakage:** Enforces $0.000000\text{ kW}$ solar output across all zero-GHI and night hours (eliminating synthetic phantom bleed).
  3. **Outage Feeder Isolation:** Validates $p_{\text{grid}} == 0\text{ kW}$ and $p_{\text{export}} == 0\text{ kW}$ during all grid blackouts (IEEE 1547 compliance).
  4. **Physical Bounds Sanity:** Caps all blackout battery deliveries at $\le 5.12\text{ kWh}$ nameplate capacity.
* **Evaluation Tooling:** Automated pytest audit suites and multi-panel verification dashboards.

---

## 3. Real-World Multi-Agent Scenario: October 26 Blackout Event

1. **2026-10-25 21:48 (Outage Detected):** LESCO 11 kV feeder trips (under-voltage & grid loss).
2. **Sub-Agent D (Forensic Auditor):** Logs confirmed blackout event in [`lesco_johar_town_outages.csv`](file:///home/bakar/Documents/Solar%20Sens%20EMS/data/processed/grid_outages/lesco_johar_town_outages.csv).
3. **Sub-Agent A (Dispatcher):** Islanding contactor opens ($p_{\text{grid}} = 0\text{ kW}$). Discharges 2.406 kWh from battery to carry household load, ending at 53.0% SoC at 01:14 when feeder restores.
4. **2026-10-26 18:04 (Peak Blackout):** 16-minute blackout during Peak ToU (46.85 PKR). Battery supplies 0.260 kWh (SoC 99% $\to$ 95%).
5. **2026-10-26 18:20 (Grid Restored in Peak Window):**
   * *Stock Firmware Mistake:* Immediately charged battery at -0.91 kW, pulling 3.18 kW peak grid power!
   * *Sub-Agent A Action:* Applies $p_{\text{grid}} \le \text{load}$, strictly suppressing grid recharge during Peak ToU. Recharging is deferred to 22:00 off-peak (34.53 PKR), saving 27.6% on the daily bill.
6. **Orchestrator Notification:** Emits dispatch report: *"Peak recharge suppressed; avoided 46.85 PKR/kWh charging spike. Day cost reduced from 1,872 PKR to 1,355 PKR."*
