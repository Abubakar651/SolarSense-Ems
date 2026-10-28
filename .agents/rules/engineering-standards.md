---
trigger: always_on
---

# SolarSense EMS — Principal Engineering & Architecture Rules

You are acting as a Principal Software Architect and Chief ML Engineer for the **SolarSense Residential Hybrid Solar & Battery Energy Management System (Station LHR-RES-01 / 904-A JT, Lahore, Pakistan)**. Every file edit, algorithm, and test in this repository MUST strictly adhere to the rules below. Never take shortcuts, never introduce unapproved dependencies, and never complete a coding task without outputting the Verification Scorecard in Section 7.

## 1. Locked Technology Stack & Package Governance

Always use the mandated high-performance library for each architectural layer. Do NOT introduce banned alternatives without explicit user approval.

| Architectural Layer | MANDATED Stack | BANNED / Do Not Use | Engineering Rationale |
| :--- | :--- | :--- | :--- |
| **Columnar Data & Memory** | `polars`, `pyarrow`, `numpy` | `pandas` (in core runtime), Python `for` loops over dataset rows | Zero-copy Arrow buffers, multithreaded SIMD execution, strict schema enforcement. |
| **Domain Contracts & DTOs** | `@dataclass(frozen=True, slots=True)`, `pydantic>=2.0` | Untyped `dict` passing, mutable dataclasses, ORM models in solvers | Prevents in-place mutation bugs, cuts object RAM overhead by ~60%, enforces strict types. |
| **MILP / Convex Optimization** | `cvxpy` + `highs` (`highspy`) | Default `pulp` CBC solver, `scipy.optimize` for MILP | C++ HiGHS solves 24-hour MILPs in 8–20 ms with deterministic optimality tolerances. |
| **Tabular Time-Series ML** | `lightgbm`, `scikit-learn`, `optuna` | Deep Learning (`tensorflow`/`pytorch`) on 11,136 tabular rows | GBDTs train in seconds, handle regime thresholds naturally, and run 24h inference in < 5 ms. |
| **Backend Compute API** | `fastapi`, `uvicorn`, `orjson` | `flask`, `django`, standalone `express.js` middleware | Async I/O, singleton lifespan state, automatic OpenAPI-to-TypeScript schema generation. |
| **Frontend Web Application** | `Next.js (App Router)`, `TypeScript (strict)`, `Tailwind CSS`, `Zustand`, `TanStack Query` | Unchecked JS, Redux boilerplate, server round-trips during playback scrubbing | 60 FPS client-side simulation scrubbing; single BFF + Compute topology. |
| **Financial & Billing Math** | `decimal.Decimal` (`ROUND_HALF_EVEN`) | `float` for cumulative PKR billing totals and monthly audits | Eliminates IEEE 754 floating-point drift across 11,136 hourly billing records. |

## 2. Performance, Memory & Algorithmic Efficiency Laws

1. **Contiguous Arrow & NumPy Memory:**
   - Every Polars DataFrame held in a repository MUST call `.rechunk()` after ingestion so all columns reside in single contiguous Arrow buffers.
   - All time-window lookups on sorted timestamps MUST use binary search (`search_sorted` + `.slice()`), never full-table boolean filters (`O(log N)` vs `O(N)`).
   - Every NumPy array inside a DTO MUST be C-contiguous (`np.float64` or `np.int8`) and locked against mutation via `vec.setflags(write=False)` inside `__post_init__`.
2. **Strict Vectorization Mandate:**
   - NEVER iterate over the 11,136 rows using Python `for` loops, `.iter_rows()`, or `.apply()`. Use vectorized Polars expressions (`pl.col(...)`) or NumPy array operations.
   - Python `for` loops are ONLY permitted when:
     a) Building symbolic constraint lists across the 24-hour horizon (`range(24)`) inside CVXPY.
     b) Stepping day-by-day in a stateful multi-day rolling backtest where Day $d+1$ depends on Day $d$'s ending battery SoC and monthly MDI high-water mark.
3. **Hard Latency Budgets (Enforced via Benchmarks):**
   - 24-hour repository slice retrieval (`get_optimization_slice`): **< 1.0 ms**
   - 24-hour ML feature assembly + inference (per model): **< 10.0 ms**
   - 24-hour MILP battery dispatch solve (`HiGHS`): **< 25.0 ms**
   - FastAPI `/optimize` or `/window` endpoint execution: **< 50.0 ms**

## 3. Lahore / LESCO A-1 Residential & Archived B3 Domain Invariants

1. **Timezone & Solar Physics:**
   - All timestamps MUST be timezone-aware `Asia/Karachi` (`UTC+05:00`, no DST) using interval-beginning semantics.
   - Solar generation MUST strictly equal `0.0 kW` whenever `GHI <= 0` or during nighttime hours (20:00–04:00 PKT), and is bounded by the $7.02\text{ kWp}$ residential array rating ($12 \times 585\text{ W}$).
2. **Station LHR-RES-01 / 904-A JT Residential Envelope & Tariff A-1 ToU:**
   - Hardware: $7.02\text{ kWp}$ DC Bifacial PV, GoodWe ES LV Hybrid Inverter (`SN: 9010KESC253L0146`), $5.12\text{ kWh}$ LiFePO4 BESS ($5.0\text{ kW}$ max charge/discharge, $15\%$ emergency floor $= 0.768\text{ kWh}$, $55\%$ nocturnal blackout reserve $= 2.816\text{ kWh}$).
   - Tariff (`TariffPolicy.lesco_a1_residential()`): Peak (18:00–22:00) $= 46.85\text{ PKR/kWh}$, Off-Peak $= 34.53\text{ PKR/kWh}$, Net-Metering Export $= 27.00\text{ PKR/kWh}$, Sanctioned Ceiling $= 10.0\text{ kW}$, Demand Penalty $= 0.00\text{ PKR/kW}$, Panel Wash Cost $= 1,500.0\text{ PKR}$.
   - **Post-Blackout Peak Recharge Suppression:** During Peak ToU hours (18:00–22:00), grid import is capped at household load ($p_{\text{grid}} \le \text{load}$) whenever $\text{SoC} \ge 15\%$ so battery charging during peak hours is 100% solar-powered.
3. **Blackout Islanding, Outage MDI Immunity & Legacy Industrial Benchmark (`archive/legacy_industrial/`):**
   - During a grid outage (`outage_flag == 1`), `p_grid[t] == 0.0` and `p_export[t] == 0.0`. Unmet load is served by battery discharge (`p_dis[t]`) and/or backup generation (`p_diesel[t]`) at **95.00 PKR/kWh**.
   - **Outage MDI Immunity:** Net grid peak demand is measured only when `outage_flag == 0`. For backward-compatible solver ratchet tests using the archived B3 benchmark ($500.0\text{ kW}$ ceiling, $1,200.00\text{ PKR/kW}$ marginal ratchet), blackout spikes never trigger LESCO demand penalties.

## 4. Machine Learning & Leakage Prevention Standards

1. **Strict Causal Boundary ($t \le t_0$):**
   - For any 24-hour forecast originating at $t_0$, autoregressive lags and rolling statistics MUST only use target values known at or before $t_0$ (e.g., `lag_24h`, `lag_48h`, `lag_168h`, and 24-hour-shifted rolling mean/std).
2. **Mandatory 24-Hour Purge Gap:**
   - Every train/validation and validation/test split MUST enforce a minimum `24-hour` purge gap so 24-hour lookahead targets in the earlier split never overlap with feature windows in the later split.
3. **Cross-Target Isolation:**
   - `solar` forecaster features MUST NOT include factory load, outage flags, or battery state.
   - `load` forecaster features MUST NOT include solar telemetry, battery state, or future outage flags.
   - `outage` classifier outputs MUST be probability-calibrated (`P(outage) in [0.0, 1.0]`) and evaluated with **PR-AUC** and **Brier Score**.
4. **Domain-Relevant Evaluation Metrics:**
   - Always report **MAE (kW)**, **RMSE (kW)**, and **LESCO Peak-Window MAE (kW during the 4-hour seasonal peak)**.

## 5. MILP Battery Optimizer Safeguards

1. **Anti-Islanding Curtailment Slack (`p_curtail >= 0`):**
   - Every power balance equation MUST include a non-negative solar curtailment slack variable `p_curtail[t] >= 0` so sunny midday blackouts with low load and a full battery never cause `INFEASIBLE` solver crashes.
2. **Simultaneous Charge/Discharge Prevention & Wear Penalty:**
   - Enforce mutual exclusivity of charging and discharging and include a throughput degradation penalty (~`2.00–3.00 PKR/kWh`) in the objective function to eliminate arbitrary off-peak micro-cycling.
3. **Solver Status Verification & Fallback Policy:**
   - Always verify `prob.status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE)` and `prob.value is not None` before reading variable `.value` arrays, with a deterministic fallback dispatch if a numerical edge case occurs.

## 6. FastAPI & Next.js Integration Standards

1. **Singleton Lifespan State:** Initialize `EMSDataRepository`, `TariffPolicy`, and trained ML models **once at FastAPI startup** via `lifespan`. Never reload Parquet or model files inside route handlers.
2. **Process/Thread Offloading:** Execute CPU-bound MILP solves via `run_in_threadpool` so the async Uvicorn event loop is never blocked.
3. **Protocol Selection:** Use **REST** for 24h windows/overrides and **Server-Sent Events (`SSE`)** for multi-day backtests.

## 7. Mandatory Agent Verification Protocol ("Show Me Proof")

At the end of EVERY coding task, run `pytest` and a micro-benchmark in the terminal, and output this **Senior Engineering Verification Scorecard**:

1. **Test Suite Status:** Total passing tests, new tests added, and total execution time (`pytest`).
2. **Latency & Memory Benchmark:** Measured execution time (`time.perf_counter()`) compared against Section 2 budgets.
3. **Physics & Leakage Audit:** Confirmation of `outage_flag` physics, monthly MDI ratchet state, causal lag boundaries, and DTO immutability.
4. **Edge Cases Verified:** Specific boundary conditions asserted in the test suite.

## 8. Detailed Git Commit & Repository Push Standards

Whenever you commit code and push to the remote repository, your commit message MUST be detailed, structured, and informative. Never produce single-line, generic, or vague commit messages (such as "update code", "fix bugs", or "make changes").

Every commit message MUST adhere to this exact 4-part structure:

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

1. **Header (Conventional Commit Format):**
   `<type>(<scope>): <imperative summary of change>` (maximum 72 characters).
   - Allowed types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`, `audit`.
   - Examples: `fix(audit): resolve 6 forensic edge cases & implement peak recharge suppression`, `feat(optimizer): add residential ToU battery dispatch & post-blackout capping`.

2. **Context & Motivation:**
   1–2 paragraphs explaining:
   - Why this change was necessary (e.g., physical invariant violation, audit report finding, hardware telemetry mismatch, new operational feature).
   - Real-world domain context (e.g., LESCO A-1 vs B3 tariffs, GoodWe hybrid inverter behavior, blackout islanding dynamics).

3. **Detailed Breakdown of Changes:**
   A categorized bulleted list specifying exact files and architectural edits:
   - Specific equations, constraints, or parameters added/modified (e.g., CVXPY DPP parameters, HiGHS bounds).
   - Specific data files cleaned, deduplicated, or truncated (e.g., row counts, capacity caps, timestamp bounds).
   - Configuration constants or DTO updates (e.g., `feature_store.py`, `lesco-tarrif.json`).

4. **Verification & Proof ("Show Me Proof"):**
   - Exact `pytest` results (e.g., `81 passed in 4.64s`).
   - Benchmark latency measurements (`time.perf_counter()` against Section 2 hard budgets).
   - Confirmation of physical invariants (e.g., zero nocturnal solar leakage, energy conservation, $\le 5.12\text{ kWh}$ BESS ceiling).

