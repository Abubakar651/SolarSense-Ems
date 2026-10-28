"""
SolarSense EMS — Real-Time Soiling & Power Loss Calculator
Computes exact instantaneous kW lost, accumulated daily kWh lost,
and financial loss in PKR scaled to Station LHR-RES-01 (7.02 kWp Residential Array,
12 x 585W Bifacial PV, LESCO A-1 ToU Tariff) or configurable plant setups.
"""

import sys
from pathlib import Path
from datetime import datetime

# Ensure project root is on sys.path
sys.path.append(str(Path(__file__).resolve().parents[2]))

import pandas as pd
import numpy as np

# Import our LESCO tariff engine
from src.optimizer.tariff_engine import LescoTariffEngine


class SolarPlantLossCalculator:
    def __init__(
        self,
        plant_capacity_kw: float = 7.02,     # Default: 7.02 kWp Residential PV Array (12 x 585W)
        panel_rating_w: float = 585.0,       # Default: 585 Wp Bifacial panel (Station LHR-RES-01)
        wash_cost_pkr: float = 1500.0,       # Default: 1,500 PKR residential wash cost (lesco-tarrif.json)
        tariff_category: str = "A1_ToU",     # Default: LESCO A-1 Residential Time-of-Use
    ):
        self.plant_capacity_kw = plant_capacity_kw
        self.panel_rating_w = panel_rating_w
        self.num_panels = max(1, int(round((plant_capacity_kw * 1000.0) / panel_rating_w)))
        self.wash_cost_pkr = wash_cost_pkr
        self.tariff_category = tariff_category
        self.tariff_engine = LescoTariffEngine()

    def calculate_instantaneous_loss(
        self,
        poa_irradiance_wm2: float,
        ambient_temp_c: float,
        actual_power_kw: float,
        dt: datetime = None,
        category: str = None,
    ) -> dict:
        """
        Calculates instantaneous power lost RIGHT NOW (in kW and PKR/hr).
        Uses standard STC derate model adjusted for panel temperature.
        """
        if dt is None:
            dt = datetime.now()
        active_category = category or self.tariff_category

        # 1. Physics: Estimate Cell Temperature
        # T_cell = T_amb + G * (NOCT - 20) / 800 (NOCT = 45°C)
        t_cell_c = ambient_temp_c + (poa_irradiance_wm2 * 25.0 / 800.0)

        # 2. Temperature Derate (-0.40% / °C above 25°C STC)
        temp_loss_factor = 1.0 - 0.0040 * max(0.0, t_cell_c - 25.0)

        # 3. Theoretical Expected Clean Power for the entire plant (kW)
        # P_clean = Plant_Capacity_kW * (POA / 1000) * temp_loss_factor * system_efficiency (~85% inverter/wiring)
        system_efficiency = 0.85
        if poa_irradiance_wm2 > 20.0:
            expected_clean_kw = self.plant_capacity_kw * (poa_irradiance_wm2 / 1000.0) * temp_loss_factor * system_efficiency
        else:
            expected_clean_kw = 0.0

        # 4. Instantaneous Power Lost Right Now (kW)
        kw_lost_now = max(0.0, expected_clean_kw - actual_power_kw)
        soiling_derate_pct = (kw_lost_now / max(0.1, expected_clean_kw)) * 100.0 if expected_clean_kw > 0.1 else 0.0

        # 5. Financial Rate Right Now (PKR/kWh)
        # For A1_ToU residential, use the base NEPRA/LESCO ToU rate (34.53 off-peak / 46.85 peak)
        current_tariff_pkr = self.tariff_engine.get_base_rate_pkr(dt, category=active_category)
        financial_loss_rate_pkr_per_hr = kw_lost_now * current_tariff_pkr

        return {
            "timestamp": dt.strftime("%Y-%m-%d %H:%M"),
            "plant_capacity_kw": self.plant_capacity_kw,
            "total_plates": self.num_panels,
            "plate_rating_w": self.panel_rating_w,
            "actual_power_generated_kw": round(actual_power_kw, 3),
            "expected_clean_power_kw": round(expected_clean_kw, 3),
            "power_lost_right_now_kw": round(kw_lost_now, 3),
            "soiling_derate_percentage": round(soiling_derate_pct, 2),
            "current_tariff_pkr_per_kwh": current_tariff_pkr,
            "money_lost_per_hour_pkr": round(financial_loss_rate_pkr_per_hr, 2)
        }

    def evaluate_daily_cleaning_decision(
        self,
        daily_kwh_lost: float,
        days_until_rain: int = 7,
        category: str = None,
    ) -> dict:
        """
        Evaluates the economic wash trigger:
        Trigger Wash if: (Daily kWh Lost * Tariff * Days to Rain) > Total Cleaning Cost
        """
        now = datetime.now()
        active_category = category or self.tariff_category
        # Daytime solar generation occurs during off-peak hours (34.53 PKR/kWh for A1_ToU)
        effective_tariff = self.tariff_engine.get_base_rate_pkr(now.replace(hour=12), category=active_category)

        daily_revenue_lost_pkr = daily_kwh_lost * effective_tariff
        projected_loss_before_rain_pkr = daily_revenue_lost_pkr * days_until_rain

        net_savings_pkr = projected_loss_before_rain_pkr - self.wash_cost_pkr
        should_clean = net_savings_pkr > 0

        return {
            "daily_kwh_lost": round(daily_kwh_lost, 2),
            "tariff_category": active_category,
            "tariff_rate_pkr_per_kwh": effective_tariff,
            "daily_revenue_lost_pkr": round(daily_revenue_lost_pkr, 2),
            "days_until_next_rain": days_until_rain,
            "projected_loss_before_rain_pkr": round(projected_loss_before_rain_pkr, 2),
            "wash_cost_pkr": self.wash_cost_pkr,
            "net_cleaning_benefit_pkr": round(net_savings_pkr, 2),
            "decision": "TRIGGER CLEANING CREW" if should_clean else "HOLD (WAIT FOR NATURAL RAIN)"
        }


if __name__ == "__main__":
    calc = SolarPlantLossCalculator(plant_capacity_kw=7.02, panel_rating_w=585.0, wash_cost_pkr=1500.0)
    print("==================================================")
    print("SOLARSENSE EMS — REAL-TIME POWER LOSS ENGINE (LHR-RES-01)")
    print("==================================================")
    print(f"Plant Capacity : {calc.plant_capacity_kw} kWp")
    print(f"Total Plates   : {calc.num_panels:,} plates (each {calc.panel_rating_w} Wp)")
    print(f"Tariff Profile : {calc.tariff_category} (Wash Cost: PKR {calc.wash_cost_pkr:,.0f})")

    # Simulate peak noon condition: Irradiance = 850 W/m², Temp = 32°C, Inverter reading = 3.85 kW (dusty)
    now = datetime(2026, 10, 7, 12, 30)
    result = calc.calculate_instantaneous_loss(
        poa_irradiance_wm2=850.0,
        ambient_temp_c=32.0,
        actual_power_kw=3.85,
        dt=now
    )

    print("\n--- INSTANTANEOUS LOSS CALCULATION RIGHT NOW ---")
    for k, v in result.items():
        print(f"  {k:<32}: {v}")

    # Evaluate daily wash trigger
    # Suppose 7.02 kWp array lost 9.5 kWh today and rain is 7 days away
    decision = calc.evaluate_daily_cleaning_decision(daily_kwh_lost=9.5, days_until_rain=7)
    print("\n--- ECONOMETRIC WASH DECISION ---")
    for k, v in decision.items():
        print(f"  {k:<32}: {v}")
