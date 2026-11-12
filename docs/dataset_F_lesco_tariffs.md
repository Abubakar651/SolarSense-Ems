# Dataset F: LESCO / NEPRA Calendar Year 2026 Electricity Tariffs & Prosumer Regulations

*Last updated: October 2026*  
*Project: SolarSense EMS (Residential Hybrid Solar & Battery Digital Twin)*  
*Modules: CY 2026 Tariff Engine, Econometric Cleaning Trigger & Multi-Regime Battery Optimizer*  
*Primary Regulatory Authority: National Electric Power Regulatory Authority (NEPRA) & Ministry of Energy (Power Division)*  

---

## 1. Overview & Governing Regulatory Framework

In Pakistan, electricity tariffs are determined by **NEPRA** and notified by the Federal Government via Statutory Regulatory Orders (S.R.O.) in the official Gazette of Pakistan. **LESCO** (Lahore Electric Supply Company) enforces this uniform tariff across Lahore and Kasur.

### Statutory Notifications Governing CY 2026:
1. **Base Tariff & Fixed Charges:** [S.R.O. 279(I)/2026](https://nepra.org.pk/tariff/Tariff/Ex-WAPDA%20DISCOS/2026/TRF-100%20XWDISCOS%20AND%20KE%20RATIONALIZATION%20OF%20TARIFF%2011-02-2026%202935-57.pdf) (notified 12 Feb 2026, retroactive to 01 Jan 2026).
2. **Prosumer Net-Billing Regulations 2026:** [S.R.O. 251(I)/2026](https://nepra.org.pk/Legislation/3-Reg/3.35%20NEPRA%20%20Prosumer%20Regulations%202026/NEPRA%20Prosumer%20Regulations%20%28SRO%20251%28I%292026%29%2009-02-26.PDF) (effective 09 Feb 2026).
3. **Grandfathering of Legacy Net-Metering:** [S.R.O. 547(I)/2026](https://nepra.org.pk/Legislation/3-Reg/3.35%20NEPRA%20%20Prosumer%20Regulations%202026/S.R.O%20547%281%29%202026%20notification%20amendment%20in%20NEPRA%20%28Prosumer%29%20Regulations%2002-04-2026.PDF) (notified 02 Apr 2026, protects `< 09-02-2026` contracts).
4. **≤25 kW Distributed Generation Concurrence Exemption:** S.R.O. 1330(I)/2026 (notified 06 Aug 2026).
5. **Quarterly Tariff Adjustment (QTA):** S.R.O. 1501(I)/2026 (Q2 CY 2026 QTA billed Sep–Nov 2026: **+Rs 0.5194/kWh**).
6. **Fuel Charges Adjustment (FCA / FPA):** S.R.O. 1754(I)/2026 (August 2026 FCA billed in October 2026 bills: **+Rs 1.1086/kWh**).

---

## 2. Residential A-1 Tariffs & Consumer Categories

### A. Time-of-Use Tariff (A-1(b), Mandatory $\ge$ 5 kW 3-Phase, Optional < 5 kW)
*Station LHR-RES-01 primary operating profile (10.0 kW Sanctioned Load).*

| Component | Rate / Formula | Notes |
| :--- | :--- | :--- |
| **Peak Energy Rate** | **Rs 46.85 / kWh** | 4 hours daily during seasonal peak window |
| **Off-Peak Energy Rate** | **Rs 34.53 / kWh** | Remaining 20 hours daily |
| **Fixed Demand Charge** | **Rs 675.00 / kW / month** | Applied to Sanctioned Load (or Billing Demand) |
| **Financing Cost (FC) Surcharge** | **Rs 3.23 / kWh** | Universal debt service surcharge |
| **Quarterly Adjustment (QTA)** | **+Rs 0.5194 / kWh** | Current-month imported kWh |
| **Fuel Price Adjustment (FPA)** | **+Rs 1.1086 / kWh** | Billed 2 months in arrears on reference units |
| **General Sales Tax (GST)** | **18.0%** | Applied to energy, fixed, surcharges, and duties |
| **Electricity Duty (ED)** | **0.0% or 1.5%** | Configurable toggle (discontinued per policy, empirical on bills) |
| **Section 235 Income Tax** | **0.0% (Filer) / 7.5% (Non-Filer)** | Non-Filer rate applies only when bill $\ge \text{Rs } 25,000$ |
| **PTV License Fee** | **Rs 0.00 / month** | Abolished effective 01 July 2025 |

### B. Single-Phase Slab Tariffs (A-1(a), < 5 kW Non-ToU)

1. **Lifeline ($\le$ 1 kW Sanctioned Load, 12-month rolling max $\le$ 100 kWh):**
   - 1–50 units: **Rs 3.95 / kWh** (whole-bill)
   - 51–100 units: **Rs 7.74 / kWh** (whole-bill)
   - Fixed charge: **Rs 0.00**; exempt from FC surcharge, QTA, and FCA.
2. **Protected (< 5 kW, $\le$ 200 kWh/month for 6 consecutive months):**
   - 1–100 units: **Rs 10.54 / kWh** + Rs 200.00 / kW / month
   - 101–200 units: first 100 units @ **Rs 10.54 / kWh** + remainder @ **Rs 13.01 / kWh** + Rs 300.00 / kW / month
   - FC Surcharge: **Rs 0.43 / kWh**; subject to QTA and FCA.
3. **Unprotected (< 5 kW, > 200 kWh in any of past 6 months):**
   - *Whole-bill (landing-slab) pricing: every unit billed at the single rate of highest slab reached!*
   - 1–100 units: **Rs 22.44 / kWh** (Fixed: Rs 275/kW)
   - 101–200 units: **Rs 28.91 / kWh** (Fixed: Rs 300/kW)
   - 201–300 units: **Rs 33.10 / kWh** (Fixed: Rs 350/kW)
   - 301–400 units: **Rs 36.46 / kWh** (Fixed: Rs 400/kW)
   - 401–500 units: **Rs 38.95 / kWh** (Fixed: Rs 500/kW)
   - 501–600 units: **Rs 40.22 / kWh** (Fixed: Rs 675/kW)
   - 601–700 units: **Rs 41.85 / kWh** (Fixed: Rs 675/kW)
   - \> 700 units: **Rs 47.20 / kWh** (Fixed: Rs 675/kW)
   - FC Surcharge: **Rs 3.23 / kWh**; subject to QTA and FCA.

---

## 3. Solar Prosumer Regulations & Optimization Regimes

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   SOLARSENSE CY 2026 PROSUMER ARBITRAGE MATRIX                   │
├────────────────────────────────┬───────────────────┬─────────────────────────────┤
│ Prosumer Operating Regime      │ Solar Export Rate │ Dispatch Arbitrage Priority │
├────────────────────────────────┼───────────────────┼─────────────────────────────┤
│ 1. Grandfathered Net-Metering  │ 1:1 Netting +     │ Discharge battery across    │
│    (Agreement < 09-02-2026)    │ Rs 25.32 NAPPP    │ 4h seasonal peak window;    │
│                                │ (or custom 27.00) │ bank excess daytime 1:1.    │
├────────────────────────────────┼───────────────────┼─────────────────────────────┤
│ 2. New Prosumer Net-Billing    │ Rs 8.13 / kWh     │ Strictly prioritize battery │
│    (Agreement >= 09-02-2026)   │ (NAEPP Buyback)   │ self-consumption over export│
│                                │                   │ (saves Rs 52.18/kWh net).   │
├────────────────────────────────┼───────────────────┼─────────────────────────────┤
│ 3. Single-Phase Slab Consumer  │ 0.00 PKR (Hard    │ Enforce zero export; defend │
│    (< 5 kW Non-ToU)            │ Zero-Export)      │ 200-unit Protected guardrail│
│                                │                   │ & whole-bill slab boundary. │
└────────────────────────────────┴───────────────────┴─────────────────────────────┘
```

---

## 4. Official Seasonal Peak Hours Schedule (LESCO PKT UTC+05:00)

| Season | Months | Daily Peak Window | Off-Peak Window |
| :--- | :--- | :--- | :--- |
| **Winter** | Dec, Jan, Feb | **5:00 PM – 9:00 PM** (17:00–21:00) | Remaining 20 hours |
| **Spring** | Mar, Apr, May | **6:00 PM – 10:00 PM** (18:00–22:00) | Remaining 20 hours |
| **Summer** | Jun, Jul, Aug | **7:00 PM – 11:00 PM** (19:00–23:00) | Remaining 20 hours |
| **Autumn** | Sep, Oct, Nov | **6:00 PM – 10:00 PM** (18:00–22:00) | Remaining 20 hours |

---

## 5. Software Architecture & API Specifications

- **Single Source of Truth Config:** [`docs/lesco_residential_tariffs_config_2026.json`](lesco_residential_tariffs_config_2026.json)
- **Customer Station Profile:** [`docs/station_profile_lhr_res_01.json`](station_profile_lhr_res_01.json)
- **Core Engine:** [`src/optimizer/lesco_2026_tariff_and_dispatch.py`](../src/optimizer/lesco_2026_tariff_and_dispatch.py)
- **Month-to-Date Flow Engine:** [`src/data_engineering/month_to_date.py`](../src/data_engineering/month_to_date.py)
- **API Endpoints:**
  - `POST /api/v2/optimize`: 24h HiGHS MILP battery dispatch with automatic MTD lookup (< 20 ms).
  - `POST /api/v2/bill/estimate`: Exact-paisa bill calculation with itemized line items (< 2 ms).
  - `GET /api/v2/tariff/peak-window?month=`: Seasonal peak hours and active season lookup.
  - `POST /api/v2/prosumer/compare`: Counterfactual financial comparison of Grandfathered vs. Net-Billing.
