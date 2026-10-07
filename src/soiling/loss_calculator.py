"""
SolarSense EMS — Real-Time Soiling & Power Loss Calculator
Computes exact instantaneous kW lost, accumulated daily kWh lost,
and financial loss in PKR scaled to any industrial factory solar setup.
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
        plant_capacity_kw: float = 500.0,    # Default: 500 kW industrial plant
        panel_rating_w: float = 500.0,       # Default: 500 Wp per panel
        wash_cost_pkr: float = 15000.0       # Labor + demineralized water cost per wash
    ):
        self.plant_capacity_kw = plant_capacity_kw
        self.panel_rating_w = panel_rating_w
        self.num_panels = int((plant_capacity_kw * 1000.0) / panel_rating_w)
        self.wash_cost_pkr = wash_cost_pkr
        self.tariff_engine = LescoTariffEngine()

    def calculate_instantaneous_loss(
        self,
        poa_irradiance_wm2: float,
        ambient_temp_c: float,
        actual_power_kw: float,
        dt: datetime = None
    ) -> dict:
        """
        Calculates instantaneous power lost RIGHT NOW (in kW and PKR/hr).
        Uses standard STC derate model adjusted for panel temperature.
        """
        if dt is None:
            dt = datetime.now()

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
        soiling_derate_pct = (kw_lost_now / max(1.0, expected_clean_kw)) * 100.0 if expected_clean_kw > 10.0 else 0.0

        # 5. Financial Rate Right Now (PKR/kWh)
        current_tariff_pkr = self.tariff_engine.get_effective_rate_pkr(dt, category="B3")
        financial_loss_rate_pkr_per_hr = kw_lost_now * current_tariff_pkr

        return {
            "timestamp": dt.strftime("%Y-%m-%d %H:%M"),
            "plant_capacity_kw": self.plant_capacity_kw,
            "total_plates": self.num_panels,
            "plate_rating_w": self.panel_rating_w,
            "actual_power_generated_kw": round(actual_power_kw, 2),
            "expected_clean_power_kw": round(expected_clean_kw, 2),
            "power_lost_right_now_kw": round(kw_lost_now, 2),
            "soiling_derate_percentage": round(soiling_derate_pct, 2),
            "current_tariff_pkr_per_kwh": current_tariff_pkr,
            "money_lost_per_hour_pkr": round(financial_loss_rate_pkr_per_hr, 2)
        }

    def evaluate_daily_cleaning_decision(
        self,
        daily_kwh_lost: float,
        days_until_rain: int = 7
    ) -> dict:
        """
        Evaluates the economic wash trigger:
        Trigger Wash if: (Daily kWh Lost * Tariff * Days to Rain) > Total Cleaning Cost
        """
        now = datetime.now()
        effective_tariff = self.tariff_engine.get_effective_rate_pkr(now, category="B3")

        daily_revenue_lost_pkr = daily_kwh_lost * effective_tariff
        projected_loss_before_rain_pkr = daily_revenue_lost_pkr * days_until_rain

        net_savings_pkr = projected_loss_before_rain_pkr - self.wash_cost_pkr
        should_clean = net_savings_pkr > 0

        return {
            "daily_kwh_lost": round(daily_kwh_lost, 2),
            "daily_revenue_lost_pkr": round(daily_revenue_lost_pkr, 2),
            "days_until_next_rain": days_until_rain,
            "projected_loss_before_rain_pkr": round(projected_loss_before_rain_pkr, 2),
            "wash_cost_pkr": self.wash_cost_pkr,
            "net_cleaning_benefit_pkr": round(net_savings_pkr, 2),
            "decision": "TRIGGER CLEANING CREW" if should_clean else "HOLD (WAIT FOR NATURAL RAIN)"
        }


if __name__ == "__main__":
    calc = SolarPlantLossCalculator(plant_capacity_kw=500.0, panel_rating_w=500.0)
    print("==================================================")
    print("SOLARSENSE EMS — REAL-TIME POWER LOSS ENGINE")
    print("==================================================")
    print(f"Plant Capacity : {calc.plant_capacity_kw} kW")
    print(f"Total Plates   : {calc.num_panels:,} plates (each {calc.panel_rating_w} Wp)")

    # Simulate peak noon condition: Irradiance = 850 W/m², Temp = 32°C, Inverter reading = 265 kW (dusty)
    now = datetime(2026, 10, 7, 12, 30)
    result = calc.calculate_instantaneous_loss(
        poa_irradiance_wm2=850.0,
        ambient_temp_c=32.0,
        actual_power_kw=265.0,
        dt=now
    )

    print("\n--- INSTANTANEOUS LOSS CALCULATION RIGHT NOW ---")
    for k, v in result.items():
        print(f"  {k:<32}: {v}")

    # Evaluate daily wash trigger
    # Suppose plant lost 300 kWh today and rain is 5 days away
    decision = calc.evaluate_daily_cleaning_decision(daily_kwh_lost=300.0, days_until_rain=5)
    print("\n--- ECONOMETRIC WASH DECISION ---")
    for k, v in decision.items():
        print(f"  {k:<32}: {v}")
