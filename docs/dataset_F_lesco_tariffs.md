# Dataset F Audit: LESCO / NEPRA Industrial & Residential Tariffs

*Last updated: October 2026*  
*Project: SolarSense EMS (Industrial AI Digital Twin & Data Engineering)*  
*Module: Econometric Cleaning Trigger & 24h Battery Arbitrage Optimizer*  
*Owner: Team Lead*  

---

## 1. Overview & Regulatory Structure

In Pakistan, electricity tariffs are determined by **NEPRA** (National Electric Power Regulatory Authority) and notified by the Federal Government via Statutory Regulatory Orders (S.R.O.). **LESCO** (Lahore Electric Supply Company) enforces this uniform tariff across Lahore.

### How Prices Change in Practice:
1. **Base Tariff:** Set periodically (typically valid for 6–12 months).
2. **Seasonal Peak Shifts:** 4-hour peak windows shift seasonally (4 times per year).
3. **Monthly Fuel Charges Adjustment (FCA):** Fluctuates monthly based on actual generation fuel costs (imported coal, RLNG, hydel share).
4. **Quarterly Tariff Adjustment (QTA):** Adjusted every 3 months for capacity charges.
5. **Statutory Taxes:** General Sales Tax (18%), Electricity Duty (1.5%), and Financing Cost Surcharge (Rs. 3.23/kWh).

---

## 2. Current Tariff Specifications (2026 Baseline)

### A. Industrial B3 Tariff (Sanctioned Load 500 kW – 5,000 kW at 11 kV / 33 kV)
*Target category for the SolarSense manufacturing facility in Lahore.*

| Component | Rate / Formula | Notes |
| :--- | :--- | :--- |
| **Fixed Demand Charge** | **Rs. 1,250 / kW / month** | Applied to Maximum Demand Indicator (MDI) |
| **Minimum Monthly Bill** | **Rs. 50,000** | Floor charge |
| **Base Peak Energy Rate** | **Rs. 35.68 / kWh** | 4 hours daily during peak window |
| **Base Off-Peak Energy Rate** | **Rs. 23.67 / kWh** | Remaining 20 hours daily |
| **Fuel Charge Adjustment (FCA)** | ~Rs. 3.40 / kWh | Updated monthly via NEPRA notification |
| **Quarterly Adjustment (QTA)** | ~Rs. 1.75 / kWh | Updated quarterly |
| **FC Surcharge** | Rs. 3.23 / kWh | Government financing surcharge |
| **Electricity Duty (ED)** | 1.5% | Provincial excise |
| **General Sales Tax (GST)** | 18.0% | Federal sales tax |
| **All-Inclusive Peak Rate** | **~Rs. 52.50 / kWh** | Total effective cost during peak hours |
| **All-Inclusive Off-Peak Rate** | **~Rs. 38.40 / kWh** | Total effective cost during off-peak hours |

### B. Residential A-1 Tariff (ToU $\ge$ 5 kW vs. Non-ToU Slabs)
- **ToU ($\ge$ 5 kW):**
  - Peak: Rs. 46.85 / kWh base (~Rs. 65 / kWh with taxes & surcharges)
  - Off-Peak: Rs. 34.53 / kWh base (~Rs. 51 / kWh with taxes & surcharges)
  - Fixed: Rs. 675 / kW / month
- **Non-ToU (< 5 kW Slabs):**
  - Protected (1–50 units): Rs. 3.95 / kWh
  - 51–100 units: Rs. 7.74 / kWh
  - 101–200 units: Rs. 10.06 / kWh
  - 201–300 units: Rs. 27.10 / kWh
  - 301–700 units: Rs. 35.80 / kWh
  - \>700 units: Rs. 47.20 / kWh

---

## 3. Official Seasonal Peak Hours Schedule (LESCO)

| Months | Season | Daily Peak Window | Off-Peak Window |
| :--- | :--- | :--- | :--- |
| **Dec – Feb** | Winter | **5:00 PM – 9:00 PM** (17:00–21:00) | Remaining 20 hours |
| **Mar – May** | Spring | **6:00 PM – 10:00 PM** (18:00–22:00) | Remaining 20 hours |
| **Jun – Aug** | Summer | **7:00 PM – 11:00 PM** (19:00–23:00) | Remaining 20 hours |
| **Sep – Nov** | Autumn / Smog | **6:00 PM – 10:00 PM** (18:00–22:00) | Remaining 20 hours |

---

## 4. Software Architecture & Dynamic Updates

To handle rate fluctuations without breaking the EMS:
1. **Dynamic Engine:** [`src/optimizer/tariff_engine.py`](file:///home/bakar/Documents/Solar%20Sens%20EMS/src/optimizer/tariff_engine.py) reads configuration from [`data/processed/tariffs/lesco_tariff_schedule.json`](file:///home/bakar/Documents/Solar%20Sens%20EMS/data/processed/tariffs/lesco_tariff_schedule.json).
2. **Instant Dynamic Adjustment:** Whenever NEPRA announces a monthly FCA change, call:
   ```python
   from src.optimizer.tariff_engine import LescoTariffEngine
   engine = LescoTariffEngine()
   engine.update_dynamic_adjustments(fca_pkr=3.85)  # updates configuration in real-time
   ```
