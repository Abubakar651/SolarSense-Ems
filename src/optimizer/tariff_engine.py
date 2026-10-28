"""
SolarSense EMS — Dynamic LESCO / NEPRA Electricity Tariff Engine
Computes exact Time-of-Use (ToU) marginal and effective rates for Industrial (B3/B2)
and Residential (A1) consumers in Lahore, Pakistan, incorporating seasonal peak shifts,
monthly FCA, QTA, and statutory taxes.
"""

import json
from pathlib import Path
from datetime import datetime

CONFIG_PATH = Path("data/processed/tariffs/lesco_tariff_schedule.json")


class LescoTariffEngine:
    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config_path = config_path
        self.load_schedule()

    def load_schedule(self):
        with open(self.config_path, "r") as f:
            self.schedule = json.load(f)

    def is_peak_hour(self, dt: datetime) -> bool:
        """
        Determines if the given datetime falls within LESCO's official 4-hour peak window.
        Seasonal shift logic:
          - Dec to Feb: 17:00 – 21:00 (5:00 PM – 9:00 PM)
          - Mar to May: 18:00 – 22:00 (6:00 PM – 10:00 PM)
          - Jun to Aug: 19:00 – 23:00 (7:00 PM – 11:00 PM)
          - Sep to Nov: 18:00 – 22:00 (6:00 PM – 10:00 PM)
        """
        month = dt.month
        hour = dt.hour

        if month in [12, 1, 2]:
            return 17 <= hour < 21
        elif month in [3, 4, 5]:
            return 18 <= hour < 22
        elif month in [6, 7, 8]:
            return 19 <= hour < 23
        else:  # [9, 10, 11]
            return 18 <= hour < 22

    def get_base_rate_pkr(self, dt: datetime, category: str = "A1_ToU") -> float:
        """
        Returns the canonical LESCO Time-of-Use energy rate (PKR/kWh):
          - For A1_ToU (Station LHR-RES-01 Residential): 46.85 PKR/kWh (Peak 18:00-22:00) / 34.53 PKR/kWh (Off-Peak)
          - For B3/B2 Industrial: base_peak_rate_pkr_per_kwh / base_off_peak_rate_pkr_per_kwh
        """
        if category == "A1_ToU":
            t_info = self.schedule["residential_tariffs"]["A1_ToU"]
            is_res_peak = 18 <= dt.hour < 22
            return float(t_info["base_peak_rate_pkr_per_kwh"] if is_res_peak else t_info["base_off_peak_rate_pkr_per_kwh"])
        elif category in self.schedule["industrial_tariffs"]:
            t_info = self.schedule["industrial_tariffs"][category]
            is_peak = self.is_peak_hour(dt)
            return float(t_info["base_peak_rate_pkr_per_kwh"] if is_peak else t_info["base_off_peak_rate_pkr_per_kwh"])
        else:
            raise ValueError(f"Unsupported ToU tariff category: {category}")

    def get_effective_rate_pkr(self, dt: datetime, category: str = "A1_ToU", include_taxes: bool = True) -> float:
        """
        Calculates the exact marginal cost per kWh at a specific timestamp.
        Includes base variable rate + FCA + QTA + FC Surcharge + ED + GST.
        """
        is_peak = (18 <= dt.hour < 22) if category == "A1_ToU" else self.is_peak_hour(dt)

        if category in self.schedule["industrial_tariffs"]:
            t_info = self.schedule["industrial_tariffs"][category]
            base_rate = t_info["base_peak_rate_pkr_per_kwh"] if is_peak else t_info["base_off_peak_rate_pkr_per_kwh"]
        elif category == "A1_ToU":
            t_info = self.schedule["residential_tariffs"]["A1_ToU"]
            base_rate = t_info["base_peak_rate_pkr_per_kwh"] if is_peak else t_info["base_off_peak_rate_pkr_per_kwh"]
        else:
            raise ValueError(f"Unsupported ToU tariff category: {category}")

        fca = t_info["fuel_charge_adjustment_pkr_per_kwh"]
        qta = t_info["quarterly_tariff_adjustment_pkr_per_kwh"]
        fc_surcharge = t_info["financing_cost_surcharge_pkr_per_kwh"]

        variable_subtotal = base_rate + fca + qta + fc_surcharge

        if not include_taxes:
            return round(variable_subtotal, 2)

        ed_pct = t_info.get("electricity_duty_pct", 1.5) / 100.0
        gst_pct = t_info.get("general_sales_tax_pct", 18.0) / 100.0

        duty = variable_subtotal * ed_pct
        gst = (variable_subtotal + duty) * gst_pct
        effective_rate = variable_subtotal + duty + gst

        return round(effective_rate, 2)

    def calculate_residential_bill(
        self,
        peak_kwh: float,
        off_peak_kwh: float,
        export_kwh: float = 0.0,
        sanctioned_kw: float = 10.0,
    ) -> dict:
        """
        Computes a monthly LESCO A-1 Residential Time-of-Use & Net-Metering bill
        for Station LHR-RES-01 (46.85 PKR/kWh Peak, 34.53 PKR/kWh Off-Peak, 27.00 PKR/kWh Export).
        """
        t_info = self.schedule["residential_tariffs"]["A1_ToU"]
        peak_charge = peak_kwh * t_info["base_peak_rate_pkr_per_kwh"]
        off_peak_charge = off_peak_kwh * t_info["base_off_peak_rate_pkr_per_kwh"]
        export_credit = export_kwh * t_info.get("export_rate_pkr_per_kwh", 27.00)
        total_import_kwh = peak_kwh + off_peak_kwh
        gross_energy_pkr = peak_charge + off_peak_charge
        net_bill_pkr = gross_energy_pkr - export_credit

        return {
            "category": "A1_ToU",
            "sanctioned_load_kw": round(sanctioned_kw, 2),
            "peak_import_kwh": round(peak_kwh, 2),
            "off_peak_import_kwh": round(off_peak_kwh, 2),
            "export_kwh": round(export_kwh, 2),
            "peak_energy_charge_pkr": round(peak_charge, 2),
            "off_peak_energy_charge_pkr": round(off_peak_charge, 2),
            "net_metering_export_credit_pkr": round(export_credit, 2),
            "net_payable_pkr": round(net_bill_pkr, 2),
            "effective_import_rate_pkr_per_kwh": round(gross_energy_pkr / max(total_import_kwh, 1.0), 2),
        }

    def calculate_industrial_bill(
        self,
        peak_kwh: float,
        off_peak_kwh: float,
        mdi_kw: float,
        category: str = "B3"
    ) -> dict:
        """
        Computes a comprehensive monthly industrial electricity bill for LESCO B3 / B2 connections.
        """
        t_info = self.schedule["industrial_tariffs"][category]

        fixed_charges = mdi_kw * t_info["fixed_charges_per_kw_month"]
        min_charge = t_info.get("minimum_monthly_charge", 0.0)
        fixed_charges = max(fixed_charges, min_charge)

        peak_base = peak_kwh * t_info["base_peak_rate_pkr_per_kwh"]
        off_peak_base = off_peak_kwh * t_info["base_off_peak_rate_pkr_per_kwh"]
        total_kwh = peak_kwh + off_peak_kwh

        fca_total = total_kwh * t_info["fuel_charge_adjustment_pkr_per_kwh"]
        qta_total = total_kwh * t_info["quarterly_tariff_adjustment_pkr_per_kwh"]
        fc_surcharge = total_kwh * t_info["financing_cost_surcharge_pkr_per_kwh"]

        energy_subtotal = peak_base + off_peak_base + fca_total + qta_total + fc_surcharge
        total_before_tax = fixed_charges + energy_subtotal

        electricity_duty = energy_subtotal * (t_info["electricity_duty_pct"] / 100.0)
        gst = (total_before_tax + electricity_duty) * (t_info["general_sales_tax_pct"] / 100.0)
        total_bill = total_before_tax + electricity_duty + gst

        return {
            "category": category,
            "total_kwh": round(total_kwh, 2),
            "peak_kwh": round(peak_kwh, 2),
            "off_peak_kwh": round(off_peak_kwh, 2),
            "mdi_kw": round(mdi_kw, 2),
            "fixed_charges_pkr": round(fixed_charges, 2),
            "energy_charges_pkr": round(peak_base + off_peak_base, 2),
            "fca_pkr": round(fca_total, 2),
            "qta_pkr": round(qta_total, 2),
            "fc_surcharge_pkr": round(fc_surcharge, 2),
            "electricity_duty_pkr": round(electricity_duty, 2),
            "gst_pkr": round(gst, 2),
            "total_bill_pkr": round(total_bill, 2),
            "effective_cost_per_kwh": round(total_bill / max(total_kwh, 1.0), 2)
        }

    def update_dynamic_adjustments(self, fca_pkr: float = None, qta_pkr: float = None):
        """
        Dynamically updates Fuel Charges (FCA) or Quarterly Tariff Adjustments (QTA)
        when a new monthly NEPRA notification is issued.
        """
        for cat in self.schedule["industrial_tariffs"].values():
            if fca_pkr is not None:
                cat["fuel_charge_adjustment_pkr_per_kwh"] = fca_pkr
            if qta_pkr is not None:
                cat["quarterly_tariff_adjustment_pkr_per_kwh"] = qta_pkr

        res_tou = self.schedule["residential_tariffs"]["A1_ToU"]
        if fca_pkr is not None:
            res_tou["fuel_charge_adjustment_pkr_per_kwh"] = fca_pkr
        if qta_pkr is not None:
            res_tou["quarterly_tariff_adjustment_pkr_per_kwh"] = qta_pkr

        self.schedule["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(self.config_path, "w") as f:
            json.dump(self.schedule, f, indent=2)
        print(f"[UPDATED] Tariff schedule updated with FCA: {fca_pkr} PKR, QTA: {qta_pkr} PKR")


if __name__ == "__main__":
    engine = LescoTariffEngine()
    now = datetime.now()
    peak = engine.is_peak_hour(now)
    eff_rate = engine.get_effective_rate_pkr(now, category="B3")

    print("==================================================")
    print("SOLARSENSE EMS — LESCO TARIFF ENGINE TEST")
    print("==================================================")
    print(f"Current Timestamp (PKT): {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"Is Current Hour Peak?   : {'YES (PEAK RATE ACTIVE)' if peak else 'NO (OFF-PEAK)'}")
    print(f"Effective Rate (B3 Ind.): {eff_rate} PKR / kWh")

    # Sample monthly factory bill for 200,000 kWh consumption
    sim_bill = engine.calculate_industrial_bill(
        peak_kwh=40000,
        off_peak_kwh=160000,
        mdi_kw=500,
        category="B3"
    )
    print("\nSimulated Factory Bill (200,000 kWh, 500 kW MDI):")
    for k, v in sim_bill.items():
        print(f"  {k:<25}: {v}")
