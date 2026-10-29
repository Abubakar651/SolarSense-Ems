# AGENTS.md — SolarSense EMS Operational Guide for AI Agents

Welcome to the **SolarSense Energy Management System (Lahore, Pakistan)** repository. You are operating as a Principal Power Systems Software Architect & Senior ML Engineer. Every agent interacting with this repository MUST strictly follow the operational rules, domain physics, and verification protocols detailed below.

---

## 1. System Topology & Dual Operating Envelopes

The platform supports two complementary operational profiles:

### A. Station LHR-RES-01 / 904-A JT (Active Primary System — Empirical Residential Digital Twin)
* **Location:** Lahore, Pakistan ($31.52^\circ\text{ N}, 74.36^\circ\text{ E}$, Asia/Karachi UTC+05:00).
* **Hardware:** 
  * $7.02\text{ kWp}$ DC Bifacial PV Array ($12 \times 585\text{ W}$).
  * GoodWe ES / ES-Uniq Low-Voltage Hybrid Inverter (SN: `9010KESC253L0146`, rated up to $10.0\text{ kW}$).
  * $5.12\text{ kWh}$ LiFePO4 Battery Pack ($51.2\text{ V}, 100\text{ Ah}$, 1C / $5.0\text{ kW}$ charge/discharge, $15\%$ emergency reserve $= 0.768\text{ kWh}$, $55\%$ nocturnal blackout reserve $= 2.816\text{ kWh}$).
* **Tariff Framework:** LESCO / NEPRA Calendar Year 2026 Residential Tariff A-1 Time-of-Use & Solar Prosumer Regulations (`S.R.O. 279(I)/2026`, `S.R.O. 251(I)/2026`, `S.R.O. 547(I)/2026`):
  * Peak ToU (Seasonal: Dec–Feb 17–21h, Mar–May 18–22h, Jun–Aug 19–23h, Sep–Nov 18–22h): **$46.85\text{ PKR/kWh}$**
  * Off-Peak (remaining 20 hours): **$34.53\text{ PKR/kWh}$**
  * Fixed Demand Charge: **$675.00\text{ PKR/kW/month}$**; FC Surcharge: **$3.23\text{ PKR/kWh}$**; QTA: **$+0.5194\text{ PKR/kWh}$**; FCA (Aug 2026 units billed Oct 2026): **$+1.1086\text{ PKR/kWh}$**
  * Grandfathered Net-Metering (`< 09-02-2026`): 1:1 monthly Off-Peak kWh netting + **$25.32\text{ PKR/kWh}$** NAPPP surplus buyback (or contract rate e.g. **$27.00\text{ PKR/kWh}$** per `docs/station_profile_lhr_res_01.json`)
  * New Net-Billing (`\ge 09-02-2026`): Gross billing with zero 1:1 netting; export credited at **$8.13\text{ PKR/kWh}$** NAEPP
  * Single-Phase Non-ToU (< 5 kW): Hard zero-export limiting, 200-unit Protected guardrail (preserving $10.54\text{–}13.01\text{ PKR}$ slab vs. $28.91+\text{ PKR}$ cliff)
  * Sanctioned Load: **$10.0\text{ kW}$**; Demand Penalty: **$0.00\text{ PKR/kW}$**; Panel Cleaning Cost: **$1,500.0\text{ PKR}$**

### B. LESCO B3 Industrial Factory Microgrid Benchmark (Archived Benchmark — `archive/legacy_industrial/`)
* **Status:** Historical simulation benchmark segregated into `archive/legacy_industrial/`.
* **Facility Scale:** $500\text{ kWp}$ Solar PV, $600\text{ kWh} / 250\text{ kW}$ LiFePO4 BESS, $400\text{ kVA}$ Diesel Backup.
* **Tariff Framework:** LESCO B3 Industrial Time-of-Use (Winter 17–21h, Summer 19–23h, Spring/Autumn 18–22h):
  * Peak Rate: **$60.00\text{ PKR/kWh}$**; Off-Peak Rate: **$38.00\text{ PKR/kWh}$**
  * Sanctioned Ceiling: **$500.0\text{ kW}$**; Monthly MDI Ratchet Penalty: **$1,200.00\text{ PKR/kW}$**
  * Backup Diesel Generation: **$95.00\text{ PKR/kWh}$**

---

## 2. Locked Technology Stack & Architectural Invariants

| Layer | MANDATED Stack | BANNED / Strictly Prohibited | Engineering Rationale |
| :--- | :--- | :--- | :--- |
| **Columnar Data** | `polars`, `pyarrow`, `numpy` | `pandas` (in core solvers), Python `for` loops over rows | Zero-copy Arrow buffers, multithreaded SIMD execution, strict schema enforcement. |
| **Domain Contracts** | `@dataclass(frozen=True, slots=True)` | Mutable dataclasses, untyped `dict` | Prevents in-place mutation bugs, cuts object RAM overhead by ~60%. |
| **MILP Optimization** | `cvxpy` + `highs` (`highspy`) | CBC solver, `scipy.optimize` | C++ HiGHS solves 24h MILPs in 8–15 ms with deterministic optimality tolerances. |
| **Financial Math** | `decimal.Decimal` (`ROUND_HALF_EVEN`) | `float` for cumulative PKR billing totals | Eliminates IEEE 754 floating-point drift across thousands of billing hours. |

### Memory & Immutability Law:
All 1D NumPy arrays stored inside DTOs (`OptimizationHorizonSlice`, `DispatchResultDTO`) MUST be C-contiguous `float64` and write-locked with:
```python
vec.setflags(write=False)
```

---

## 3. Physical Laws & Domain Rules

1. **Zero Nocturnal Solar Leakage:** Whenever $\text{GHI} \le 0$ or during astronomical night hours (20:00–04:00 PKT), solar generation MUST strictly equal $0.000000\text{ kW}$.
2. **Anti-Islanding Blackout Isolation:** During grid outages (`outage_flag == 1`), $p_{\text{grid}} == 0.0\text{ kW}$ and $p_{\text{export}} == 0.0\text{ kW}$. The inverter never back-feeds a de-energized feeder.
3. **Outage MDI Immunity:** Net grid peak demand is only measured when the grid is connected (`outage_flag == 0`). Factory demand spikes during blackouts cannot incur LESCO demand fines.
4. **Post-Blackout Peak Recharge Suppression:** During Peak ToU hours (18:00–22:00), grid import is capped at household load ($p_{\text{grid}} \le \text{load}$) whenever $\text{SoC} \ge 15\%$. Grid power is NEVER imported to recharge the battery at peak rates (46.85 PKR/kWh); battery charging during peak hours must be 100% solar-powered.
5. **BESS Capacity Ceiling:** Battery energy delivery during any single blackout event CANNOT exceed nameplate capacity ($5.12\text{ kWh}$ for residential, $600.0\text{ kWh}$ for industrial).

---

## 4. Hard Latency Budgets (Enforced via Tests)

* **24-hour repository slice retrieval (`get_optimization_slice`):** **< 1.0 ms** (measured: $0.035\text{ ms}$)
* **24-hour ML feature assembly + inference (`use_forecasts=True`):** **< 10.0 ms** (measured: $2.72\text{ ms}$)
* **24-hour HiGHS MILP solve (`BESSConfig.station_904a_residential()`):** **< 25.0 ms** (measured: $10.45\text{ ms}$)
* **FastAPI endpoint round-trip (`/api/window` & `/api/optimize`):** **< 50.0 ms** (measured: $1.29\text{ ms}$ / $13.26\text{ ms}$)

---

## 5. Detailed Git Commit & Push Standards

Whenever you commit and push to the remote repository, your commit message MUST be detailed and follow this structure:

```text
<type>(<scope>): <concise imperative summary>

Context & Motivation:
<1-2 paragraphs detailing why this change was made, relevant domain physics,
audit findings, or hardware telemetry insights>

Detailed Changes:
- <file1>: <description of equations, constants, or methods added/modified>
- <file2>: <description of data filtering, deduplication, or schema fixes>

Verification & Proof:
- <test count and time: e.g., 81 passed in 4.64s>
- <micro-benchmark latency measurements>
- <confirmation of physical and financial invariants verified>
```

---

## 6. Mandatory Senior Engineering Verification Scorecard

At the end of EVERY coding task, execute `.venv/bin/pytest tests/` and terminal latency benchmarks, and output the **Senior Engineering Verification Scorecard** containing:
1. **Test Suite Status:** Passing tests, new tests added, total execution time.
2. **Latency & Memory Benchmark:** Measured execution time (`time.perf_counter()`) vs. budgets.
3. **Physics & Leakage Audit:** Confirmation of outage isolation, nocturnal solar zeroing, and DTO immutability.
4. **Edge Cases Verified:** Specific boundary conditions asserted in the test suite.
