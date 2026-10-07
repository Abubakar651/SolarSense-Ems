# Dataset B Audit: Solar Generation & Soiling Time Series

*Last updated: October 2026*  
*Project: SolarSense EMS (Industrial AI Digital Twin & Data Engineering)*  
*Module: Solar Health & Econometric Cleaning Advisor (Physical Model Signal) & 24h Optimizer*  
*Owner: Team Lead*  

---

## 1. Candidate Comparison Table

| Candidate Name | Source / DOI | License | Total Size | Duration / Resolution | Soiling Reference? | Access | Verified? | Fit Score (1–5) |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **Laghouat PV Soiling Dataset** *(Candidate 1)* | Mendeley Data<br>`10.17632/4jdt83yy43.3` | CC BY 4.0 | 427 kB | 6 Months (Feb–Aug 2022)<br>Hourly (4,368 rows) | **YES**<br>Dual clean vs dusty panels, gravimetric dust (g/m²) | Open Public Download | **PASS (Protocol 2)** | **5.0 / 5.0** |
| **Lahore Single Panel & Weather** *(Candidate 2)* | Kaggle<br>`fastpredictor/solar-power-...` | Open Access | 111 kB | 72 Days (Oct–Dec 2014)<br>Hourly (1,745 rows) | *No* (Single panel; local generation reference) | Free (Kaggle API) | **PASS (Protocol 2)** | **4.5 / 5.0** |
| **Urban Bangladesh Rooftop Dual PV** *(Candidate 3)* | Mendeley Data<br>`10.17632/g6pxf8nnt6.1` | CC BY 4.0 | 45 MB | 1 Full Year (Nov 2019–Oct 2020)<br>30-sec resolution | **YES**<br>High-smog South Asian urban dual panels | Open Public Download | Reference Available | **4.5 / 5.0** |

---

## 2. Protocol 2 Verification Results

### A. Candidate 1: Laghouat Dual PV Soiling Dataset (Ground Truth for Soiling Derate)
Verified using [`src/soiling/verify_dataset_b.py`](file:///home/bakar/Documents/Solar%20Sens%20EMS/src/soiling/verify_dataset_b.py):

- **Temporal Coverage & Continuity:** Exactly **4,368 continuous hourly rows** across 182 days (100.00% continuity, zero missing timestamps).
- **Missing Values:** 0.00% across all 13 operational sensor channels. (Only raw manual gravimetric balance weighings had sparse gaps as expected, which are fully interpolated via PCHIP).
- **Nighttime Zero-Power Validation:** Exactly **0.00% violations** across 2,001 nighttime hours ($P_{\text{clean}} = 0$ W and $P_{\text{dusty}} = 0$ W whenever $\text{POA} \le 1.0\text{ W/m}^2$).
- **Diurnal Geometry Profile:** Symmetrical bell curve peaking at solar noon (**12:00**) at 884.5 $\text{W/m}^2$ mean POA irradiance.
  - Solar noon mean output: **64.04 W** (Clean) vs. **53.97 W** (Dusty).
- **Soiling Loss Quantification (1,860 Daylight Hours):**
  - **Mean Empirical Power Loss:** **5.64 W** (Max: **21.08 W**).
  - **Mean Soiling Derate:** **13.43%** (Max: **29.67%**, directly matching the local 15%–30% soiling reality in Part 1).
  - **Mean Soiling Ratio (SR):** **0.866** (Min: **0.703**).
  - **Dust Correlation:** $r = -0.750$ between dust density ($\text{g/m}^2$) and Soiling Ratio, confirming strong physical degradation causality.
- **Verification Plot:** [docs/samples/laghouat_soiling_verification.png](file:///home/bakar/Documents/Solar%20Sens%20EMS/docs/samples/laghouat_soiling_verification.png).

---

### B. Candidate 2: Lahore PV Generation & Weather Dataset (Local Lahore Ground Truth)
Verified using [`src/soiling/verify_dataset_b.py`](file:///home/bakar/Documents/Solar%20Sens%20EMS/src/soiling/verify_dataset_b.py):

- **Temporal Coverage:** 1,745 hourly rows (Oct 20, 2014 to Jan 1, 2015), capturing the critical **winter toxic smog period (Nov–Dec)** in Lahore.
- **Missing Values:** 0.00% missing values across all 8 columns.
- **Diurnal Profile in Lahore:**
  - Peak solar noon generation: **340.8 W** (for a 500W monocrystalline panel).
  - Mean ambient temperature at solar noon: **25.8 °C** (dropping to 3.4 °C in December).
- **Verification Plot:** [docs/samples/lahore_generation_verification.png](file:///home/bakar/Documents/Solar%20Sens%20EMS/docs/samples/lahore_generation_verification.png).

---

## 3. Definite Decision & Final Recommendation

> [!IMPORTANT]
> **Dual Dataset Strategy for SolarSense EMS:**
> 
> 1. **Primary Ground Truth for Module 1 (Soiling & Cleaning Advisor):**
>    Use `soiling_ground_truth_laghouat.csv` at `data/processed/solar_timeseries/`.
>    - *Why:* It is the only open dataset with side-by-side identical clean vs unwashed panels paired with continuous gravimetric dust density ($\text{g/m}^2$) and hourly rain events. It provides empirical ground truth to calibrate our `pvlib` derate engine:
>      $$\text{Trigger Wash if: } (\text{Daily Energy Lost [kWh]} \times \text{Tariff [PKR/kWh]} \times \text{Days to Rain}) > \text{Cleaning Cost}$$
> 
> 2. **Primary Ground Truth for Module 2 (24-Hour Day-Ahead Generation Forecaster):**
>    Use `lahore_pv_generation_hourly.csv` at `data/processed/solar_timeseries/`.
>    - *Why:* It grounds the machine learning models (LightGBM/XGBoost) directly in Lahore's local latitude (31.52° N), winter smog attenuation, and NASA MERRA-2 meteorological conditions.

---

## 4. Standardized Processed Datasets

Processed and standardized using [`src/soiling/preprocess_timeseries.py`](file:///home/bakar/Documents/Solar%20Sens%20EMS/src/soiling/preprocess_timeseries.py):

1. **`data/processed/solar_timeseries/soiling_ground_truth_laghouat.csv`** (4,368 rows):
   - `datetime`, `poa_irradiance_wm2`, `temp_ambient_c`, `temp_cell_c`, `relative_humidity_pct`, `wind_speed_ms`, `cloud_cover_pct`, `precipitation_mm`, `dust_density_gm2`, `p_clean_w`, `p_dusty_w`, `power_delta_w`, `soiling_derate_pct`, `soiling_ratio`
2. **`data/processed/solar_timeseries/lahore_pv_generation_hourly.csv`** (1,745 rows):
   - `datetime`, `pv_power_w`, `temp_ambient_c`, `ghi_wm2`, `actual_irradiance_wm2`, `cloud_fraction`, `precipitation_mm`, `air_density_kgm3`
