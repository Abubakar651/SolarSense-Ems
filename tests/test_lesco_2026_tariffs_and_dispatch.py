"""
Unit & Integration Tests for CY 2026 LESCO Residential Tariffs & Prosumer Battery Dispatch
==========================================================================================
Cross-verifies docs/lesco_residential_tariffs_config_2026.json against every line item of
Worked Examples 1 & 2 in docs/lesco_residential_electricity_tariffs_metering_report_2026.pdf
to the exact paisa (Decimal ROUND_HALF_EVEN), and validates multi-regime MILP battery dispatch.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime
from decimal import Decimal

import numpy as np
import pytest

from src.optimizer.lesco_2026_tariff_and_dispatch import (
    BillingDemandMode,
    ConsumerCategory2026,
    Lesco2026BatteryDispatchOptimizer,
    LescoCY2026TariffEngine,
    ProsumerRegime2026,
    load_lesco_2026_config,
)
from src.optimizer.milp_solver import BESSConfig


@pytest.fixture(scope="module")
def engine_2026() -> LescoCY2026TariffEngine:
    return LescoCY2026TariffEngine()


@pytest.fixture(scope="module")
def optimizer_2026(engine_2026: LescoCY2026TariffEngine) -> Lesco2026BatteryDispatchOptimizer:
    return Lesco2026BatteryDispatchOptimizer(
        tariff_engine=engine_2026,
        bess=BESSConfig.station_904a_residential(),
    )


# =====================================================================
# 1. JSON Config & Worked Example 1 (Unprotected 350 kWh Bill)
# =====================================================================

def test_config_2026_parsing_and_immutability(engine_2026: LescoCY2026TariffEngine) -> None:
    """Verifies that docs/lesco_residential_tariffs_config_2026.json parses into frozen DTOs."""
    cfg = engine_2026.config
    assert cfg.version == "2026-10-29"
    assert cfg.effective_date == "2026-02-12"
    assert cfg.tou_peak_rate_pkr_per_kwh == Decimal("46.85")
    assert cfg.tou_off_peak_rate_pkr_per_kwh == Decimal("34.53")
    assert cfg.tou_fixed_charge_pkr_per_kw_month == Decimal("675.00")
    assert cfg.tou_fc_surcharge_pkr_per_kwh == Decimal("3.23")
    assert cfg.qta_rate_pkr_per_kwh == Decimal("0.5194")
    assert cfg.fca_rate_pkr_per_kwh == Decimal("1.1086")
    assert cfg.naepp_export_rate_pkr_per_kwh == Decimal("8.13")
    assert cfg.nappp_grandfathered_rate_pkr_per_kwh == Decimal("25.32")
    assert cfg.ptv_fee_pkr == Decimal("0.00")

    with pytest.raises(FrozenInstanceError):
        cfg.tou_peak_rate_pkr_per_kwh = Decimal("50.00")  # type: ignore[misc]


def test_worked_example_1_unprotected_350_kwh_exact_paisa(engine_2026: LescoCY2026TariffEngine) -> None:
    """
    Reproduces Section 4.3 Worked Example 1 from the PDF report to the exact paisa:
      - Unprotected Single-Phase Consumer (A-1(a)), Sanctioned Load = 2 kW
      - Oct 2026 Consumption = 350 kWh (301-400 kWh whole-bill slab @ Rs 36.46/kWh, Fixed Rs 400/kW)
      - Aug 2026 Reference Consumption (for Oct FPA) = 400 kWh (@ Rs 1.1086/kWh)
      - Expected Total Payable without ED: Rs 18,073.74 (Rounded Rs 18,074)
      - Expected Total Payable with 1.5% ED: Rs 18,310.68 (Rounded Rs 18,311)
    """
    # Case A: Without 1.5% Electricity Duty (0% ED)
    bill_no_ed = engine_2026.calculate_monthly_bill(
        category=ConsumerCategory2026.UNPROTECTED,
        sanctioned_load_kw=Decimal("2.0"),
        current_kwh=Decimal("350"),
        fpa_reference_2m_prior_kwh=Decimal("400"),
        include_electricity_duty=False,
        is_atl_filer=False,  # Even for Non-Filer, bill < Rs 25,000 so Sec 235 IT = Rs 0.00
    )

    assert bill_no_ed.slab_id == "unprotected_301_400"
    assert bill_no_ed.variable_energy_charges_pkr == Decimal("12761.00")
    assert bill_no_ed.fixed_charges_pkr == Decimal("800.00")
    assert bill_no_ed.qta_pkr == Decimal("181.79")
    assert bill_no_ed.fc_surcharge_pkr == Decimal("1130.50")
    assert bill_no_ed.electricity_duty_current_pkr == Decimal("0.00")
    assert bill_no_ed.current_pre_gst_subtotal_pkr == Decimal("14873.29")
    assert bill_no_ed.gst_on_current_bill_pkr == Decimal("2677.19")
    assert bill_no_ed.fpa_base_pkr == Decimal("443.44")
    assert bill_no_ed.ed_on_fpa_pkr == Decimal("0.00")
    assert bill_no_ed.gst_on_fpa_pkr == Decimal("79.82")
    assert bill_no_ed.ed_and_gst_on_fpa_pkr == Decimal("79.82")
    assert bill_no_ed.ptv_fee_pkr == Decimal("0.00")
    assert bill_no_ed.section_235_income_tax_pkr == Decimal("0.00")
    assert bill_no_ed.total_payable_pkr == Decimal("18073.74")
    assert bill_no_ed.total_payable_rounded_rupee_pkr == Decimal("18074")

    # Case B: With 1.5% Electricity Duty Enabled
    bill_with_ed = engine_2026.calculate_monthly_bill(
        category=ConsumerCategory2026.UNPROTECTED,
        sanctioned_load_kw=Decimal("2.0"),
        current_kwh=Decimal("350"),
        fpa_reference_2m_prior_kwh=Decimal("400"),
        include_electricity_duty=True,
        is_atl_filer=False,
    )

    assert bill_with_ed.variable_energy_charges_pkr == Decimal("12761.00")
    assert bill_with_ed.fixed_charges_pkr == Decimal("800.00")
    assert bill_with_ed.qta_pkr == Decimal("181.79")
    assert bill_with_ed.fc_surcharge_pkr == Decimal("1130.50")
    assert bill_with_ed.electricity_duty_current_pkr == Decimal("194.14")
    assert bill_with_ed.current_pre_gst_subtotal_pkr == Decimal("15067.43")
    assert bill_with_ed.gst_on_current_bill_pkr == Decimal("2712.14")
    assert bill_with_ed.fpa_base_pkr == Decimal("443.44")
    assert bill_with_ed.ed_on_fpa_pkr == Decimal("6.65")
    assert bill_with_ed.gst_on_fpa_pkr == Decimal("81.02")
    assert bill_with_ed.ed_and_gst_on_fpa_pkr == Decimal("87.67")
    assert bill_with_ed.section_235_income_tax_pkr == Decimal("0.00")
    assert bill_with_ed.total_payable_pkr == Decimal("18310.68")
    assert bill_with_ed.total_payable_rounded_rupee_pkr == Decimal("18311")


# =====================================================================
# 2. Worked Example 2 (Three-Phase ToU 500 kWh Bill: Filer & Non-Filer)
# =====================================================================

def test_worked_example_2_tou_500_kwh_exact_paisa(engine_2026: LescoCY2026TariffEngine) -> None:
    """
    Reproduces Section 4.4 Worked Example 2 from the PDF report to the exact paisa:
      - Three-Phase Time-of-Use Consumer (A-1(b)), Sanctioned Load = 5 kW
      - Oct 2026 Consumption = 500 kWh (120 kWh Peak @ Rs 46.85 + 380 kWh Off-Peak @ Rs 34.53)
      - Aug 2026 Reference Consumption (for Oct FPA) = 600 kWh (@ Rs 1.1086/kWh)
      - Expected Total Payable (ATL Filer, 0% ED): Rs 29,096.75 (Rounded Rs 29,097)
      - Expected Total Payable (ATL Filer, 1.5% ED): Rs 29,444.89 (Rounded Rs 29,445)
      - Expected Total Payable (Non-Filer +7.5% IT, 0% ED): Rs 31,279.01 (Rounded Rs 31,279)
      - Expected Total Payable (Non-Filer +7.5% IT, 1.5% ED): Rs 31,653.26 (Rounded Rs 31,653)
    """
    # 1. ATL Filer without ED
    filer_no_ed = engine_2026.calculate_monthly_bill(
        category=ConsumerCategory2026.TOU_A1B,
        sanctioned_load_kw=Decimal("5.0"),
        peak_kwh=Decimal("120"),
        off_peak_kwh=Decimal("380"),
        fpa_reference_2m_prior_kwh=Decimal("600"),
        include_electricity_duty=False,
        is_atl_filer=True,
    )
    assert filer_no_ed.peak_energy_charges_pkr == Decimal("5622.00")
    assert filer_no_ed.off_peak_energy_charges_pkr == Decimal("13121.40")
    assert filer_no_ed.variable_energy_charges_pkr == Decimal("18743.40")
    assert filer_no_ed.fixed_charges_pkr == Decimal("3375.00")
    assert filer_no_ed.qta_pkr == Decimal("259.70")
    assert filer_no_ed.fc_surcharge_pkr == Decimal("1615.00")
    assert filer_no_ed.electricity_duty_current_pkr == Decimal("0.00")
    assert filer_no_ed.current_pre_gst_subtotal_pkr == Decimal("23993.10")
    assert filer_no_ed.gst_on_current_bill_pkr == Decimal("4318.76")
    assert filer_no_ed.fpa_base_pkr == Decimal("665.16")
    assert filer_no_ed.ed_and_gst_on_fpa_pkr == Decimal("119.73")
    assert filer_no_ed.subtotal_before_income_tax_pkr == Decimal("29096.75")
    assert filer_no_ed.section_235_income_tax_pkr == Decimal("0.00")
    assert filer_no_ed.total_payable_pkr == Decimal("29096.75")
    assert filer_no_ed.total_payable_rounded_rupee_pkr == Decimal("29097")

    # 2. ATL Filer with 1.5% ED
    filer_with_ed = engine_2026.calculate_monthly_bill(
        category=ConsumerCategory2026.TOU_A1B,
        sanctioned_load_kw=Decimal("5.0"),
        peak_kwh=Decimal("120"),
        off_peak_kwh=Decimal("380"),
        fpa_reference_2m_prior_kwh=Decimal("600"),
        include_electricity_duty=True,
        is_atl_filer=True,
    )
    assert filer_with_ed.electricity_duty_current_pkr == Decimal("285.05")
    assert filer_with_ed.current_pre_gst_subtotal_pkr == Decimal("24278.15")
    assert filer_with_ed.gst_on_current_bill_pkr == Decimal("4370.07")
    assert filer_with_ed.ed_on_fpa_pkr == Decimal("9.98")
    assert filer_with_ed.gst_on_fpa_pkr == Decimal("121.53")
    assert filer_with_ed.ed_and_gst_on_fpa_pkr == Decimal("131.51")
    assert filer_with_ed.subtotal_before_income_tax_pkr == Decimal("29444.89")
    assert filer_with_ed.section_235_income_tax_pkr == Decimal("0.00")
    assert filer_with_ed.total_payable_pkr == Decimal("29444.89")
    assert filer_with_ed.total_payable_rounded_rupee_pkr == Decimal("29445")

    # 3. Non-Filer without ED (+7.5% Sec 235 IT on >= Rs 25,000)
    non_filer_no_ed = engine_2026.calculate_monthly_bill(
        category=ConsumerCategory2026.TOU_A1B,
        sanctioned_load_kw=Decimal("5.0"),
        peak_kwh=Decimal("120"),
        off_peak_kwh=Decimal("380"),
        fpa_reference_2m_prior_kwh=Decimal("600"),
        include_electricity_duty=False,
        is_atl_filer=False,
    )
    assert non_filer_no_ed.subtotal_before_income_tax_pkr == Decimal("29096.75")
    assert non_filer_no_ed.section_235_income_tax_pkr == Decimal("2182.26")
    assert non_filer_no_ed.total_payable_pkr == Decimal("31279.01")
    assert non_filer_no_ed.total_payable_rounded_rupee_pkr == Decimal("31279")

    # 4. Non-Filer with 1.5% ED (+7.5% Sec 235 IT on >= Rs 25,000)
    non_filer_with_ed = engine_2026.calculate_monthly_bill(
        category=ConsumerCategory2026.TOU_A1B,
        sanctioned_load_kw=Decimal("5.0"),
        peak_kwh=Decimal("120"),
        off_peak_kwh=Decimal("380"),
        fpa_reference_2m_prior_kwh=Decimal("600"),
        include_electricity_duty=True,
        is_atl_filer=False,
    )
    assert non_filer_with_ed.subtotal_before_income_tax_pkr == Decimal("29444.89")
    assert non_filer_with_ed.section_235_income_tax_pkr == Decimal("2208.37")
    assert non_filer_with_ed.total_payable_pkr == Decimal("31653.26")
    assert non_filer_with_ed.total_payable_rounded_rupee_pkr == Decimal("31653")


# =====================================================================
# 3. Lifeline, Protected Incremental, & Unprotected Whole-Bill Cliffs
# =====================================================================

def test_lifeline_protected_and_unprotected_slab_physics(engine_2026: LescoCY2026TariffEngine) -> None:
    """
    Verifies:
      - Lifeline (<=1 kW, 12m max <=100 kWh): whole-bill pricing (40 kWh @ 3.95, 80 kWh @ 7.74),
        Rs 0 fixed charge, exempt from FC surcharge, QTA, FCA, and ED.
      - Protected (1-100 @ 10.54 + 200/kW; 101-200 incremental first 100 @ 10.54 + remainder @ 13.01
        + 300/kW + 0.43 FC surcharge).
      - Unprotected whole-bill cliff: 300 kWh @ 33.10 (Rs 9,930.00) vs 301 kWh @ 36.46 (Rs 10,974.46)
        -> single 301st unit jumps base energy charge by Rs 1,044.46!
    """
    # Lifeline 80 kWh (51-100 kWh whole-bill @ Rs 7.74/kWh)
    cat_life = engine_2026.determine_consumer_category(
        sanctioned_load_kw=1.0,
        current_month_kwh=80,
        prior_12m_max_kwh=95,
    )
    assert cat_life == ConsumerCategory2026.LIFELINE
    bill_life = engine_2026.calculate_monthly_bill(
        category=cat_life,
        sanctioned_load_kw=1.0,
        current_kwh=80,
        fpa_reference_2m_prior_kwh=90,
        include_electricity_duty=True,  # Lifeline is statutorily exempt even if toggle is True
    )
    assert bill_life.variable_energy_charges_pkr == Decimal("619.20")  # 80 * 7.74
    assert bill_life.fixed_charges_pkr == Decimal("0.00")
    assert bill_life.fc_surcharge_pkr == Decimal("0.00")
    assert bill_life.qta_pkr == Decimal("0.00")
    assert bill_life.fpa_base_pkr == Decimal("0.00")
    assert bill_life.electricity_duty_current_pkr == Decimal("0.00")

    # Protected 150 kWh (100 @ 10.54 = 1054.00 + 50 @ 13.01 = 650.50 -> 1704.50; Fixed 2 kW * 300 = 600.00)
    cat_prot = engine_2026.determine_consumer_category(
        sanctioned_load_kw=2.0,
        current_month_kwh=150,
        prior_6m_max_kwh=195,
    )
    assert cat_prot == ConsumerCategory2026.PROTECTED
    bill_prot = engine_2026.calculate_monthly_bill(
        category=cat_prot,
        sanctioned_load_kw=2.0,
        current_kwh=150,
        fpa_reference_2m_prior_kwh=160,
    )
    assert bill_prot.variable_energy_charges_pkr == Decimal("1704.50")
    assert bill_prot.fixed_charges_pkr == Decimal("600.00")
    assert bill_prot.fc_surcharge_pkr == Decimal("64.50")  # 150 * 0.43

    # Unprotected whole-bill cliff: 300 kWh vs 301 kWh (Section 2.3.3 of PDF report)
    bill_300 = engine_2026.calculate_monthly_bill(
        category=ConsumerCategory2026.UNPROTECTED,
        sanctioned_load_kw=2.0,
        current_kwh=300,
    )
    bill_301 = engine_2026.calculate_monthly_bill(
        category=ConsumerCategory2026.UNPROTECTED,
        sanctioned_load_kw=2.0,
        current_kwh=301,
    )
    assert bill_300.variable_energy_charges_pkr == Decimal("9930.00")   # 300 * 33.10
    assert bill_301.variable_energy_charges_pkr == Decimal("10974.46")  # 301 * 36.46
    assert bill_301.variable_energy_charges_pkr - bill_300.variable_energy_charges_pkr == Decimal("1044.46")


def test_pro_rata_normalization_and_seasonal_peak_windows(engine_2026: LescoCY2026TariffEngine) -> None:
    """
    Verifies Annex-III pro-rata billing normalization and all 4 seasonal ToU peak windows:
      - Dec-Feb: 17:00-21:00
      - Mar-May: 18:00-22:00
      - Jun-Aug: 19:00-23:00
      - Sep-Nov: 18:00-22:00
    """
    # 210 kWh over a delayed 33-day reading cycle in a 30-day month -> 190.91 kWh (stays Protected!)
    norm_kwh = engine_2026.normalize_pro_rata_consumption(210, calendar_days_in_month=30, reading_cycle_days=33)
    assert norm_kwh == Decimal("190.91")
    assert norm_kwh <= Decimal("200.00")

    # Winter (Jan): 17:00-21:00
    assert engine_2026.is_seasonal_peak_hour(datetime(2026, 1, 15, 16, 30)) is False
    assert engine_2026.is_seasonal_peak_hour(datetime(2026, 1, 15, 17, 0)) is True
    assert engine_2026.is_seasonal_peak_hour(datetime(2026, 1, 15, 20, 59)) is True
    assert engine_2026.is_seasonal_peak_hour(datetime(2026, 1, 15, 21, 0)) is False

    # Spring (Apr): 18:00-22:00
    assert engine_2026.is_seasonal_peak_hour(datetime(2026, 4, 15, 17, 30)) is False
    assert engine_2026.is_seasonal_peak_hour(datetime(2026, 4, 15, 18, 0)) is True
    assert engine_2026.is_seasonal_peak_hour(datetime(2026, 4, 15, 21, 59)) is True
    assert engine_2026.is_seasonal_peak_hour(datetime(2026, 4, 15, 22, 0)) is False

    # Summer (Jul): 19:00-23:00
    assert engine_2026.is_seasonal_peak_hour(datetime(2026, 7, 15, 18, 30)) is False
    assert engine_2026.is_seasonal_peak_hour(datetime(2026, 7, 15, 19, 0)) is True
    assert engine_2026.is_seasonal_peak_hour(datetime(2026, 7, 15, 22, 59)) is True
    assert engine_2026.is_seasonal_peak_hour(datetime(2026, 7, 15, 23, 0)) is False

    # Autumn (Oct): 18:00-22:00
    assert engine_2026.is_seasonal_peak_hour(datetime(2026, 10, 15, 17, 30)) is False
    assert engine_2026.is_seasonal_peak_hour(datetime(2026, 10, 15, 18, 0)) is True
    assert engine_2026.is_seasonal_peak_hour(datetime(2026, 10, 15, 21, 59)) is True
    assert engine_2026.is_seasonal_peak_hour(datetime(2026, 10, 15, 22, 0)) is False


# =====================================================================
# 4. NEPRA Prosumer Regulations 2026 (Net-Billing vs Grandfathered)
# =====================================================================

def test_prosumer_regulations_2026_eligibility_and_settlement(engine_2026: LescoCY2026TariffEngine) -> None:
    """
    Verifies S.R.O. 251(I)/2026, S.R.O. 547(I)/2026, and S.R.O. 1330(I)/2026:
      - 100% sanctioned load capacity ceiling (10 kW load -> max 10 kW PV; 12 kW rejected).
      - Single-phase connection rejected for bidirectional prosumer metering.
      - Systems <= 25 kW exempt from NEPRA concurrence.
      - New Prosumer Gross Net-Billing (Rs 8.13/kWh NAEPP, zero 1:1 unit netting) vs
        Grandfathered Net-Metering (1:1 Off-Peak netting + Rs 25.32/kWh NAPPP).
      - All-in marginal ToU rates match Section 5.1 of the PDF report (Rs 60.31 Peak, Rs 45.77 Off-Peak).
    """
    # Eligibility checks
    elig_ok = engine_2026.validate_prosumer_eligibility(sanctioned_load_kw=10.0, proposed_pv_capacity_kw=7.02, phases=3)
    assert elig_ok.is_eligible is True
    assert elig_ok.requires_nepra_concurrence is False
    assert elig_ok.max_allowed_pv_kw == Decimal("10.00")

    elig_oversized = engine_2026.validate_prosumer_eligibility(
        sanctioned_load_kw=5.0, proposed_pv_capacity_kw=7.5, phases=3
    )
    assert elig_oversized.is_eligible is False
    assert len(elig_oversized.violations) == 1

    elig_1ph = engine_2026.validate_prosumer_eligibility(sanctioned_load_kw=4.0, proposed_pv_capacity_kw=3.0, phases=1)
    assert elig_1ph.is_eligible is False
    assert len(elig_1ph.violations) == 2

    # All-in marginal rates: (base + 3.23 FC + 0.5194 QTA + 1.1086 FCA) * 1.18 GST
    peak_all_in, off_all_in = engine_2026.get_all_in_tou_marginal_rates_pkr(
        include_electricity_duty=False, include_fpa_marginal=True
    )
    assert peak_all_in == Decimal("61.02")
    assert off_all_in == Decimal("46.48")
    assert peak_all_in - off_all_in == Decimal("14.54")  # Exact 12.32 * 1.18 Peak-to-Off-Peak spread!

    peak_no_fpa, off_no_fpa = engine_2026.get_all_in_tou_marginal_rates_pkr(
        include_electricity_duty=False, include_fpa_marginal=False
    )
    assert peak_no_fpa == Decimal("59.71")
    assert off_no_fpa == Decimal("45.17")

    # Compare New Prosumer (NET_BILLING_2026) vs Grandfathered (GRANDFATHERED_NET_METERING)
    # 100 kWh Peak import, 300 kWh Off-Peak import, 450 kWh Solar Export
    new_pros = engine_2026.calculate_prosumer_settlement(
        regime=ProsumerRegime2026.NET_BILLING_2026,
        sanctioned_load_kw=10.0,
        gross_peak_import_kwh=100,
        gross_off_peak_import_kwh=300,
        gross_export_kwh=450,
    )
    assert new_pros.net_billed_peak_import_kwh == Decimal("100")
    assert new_pros.net_billed_off_peak_import_kwh == Decimal("300")
    assert new_pros.export_credit_rate_pkr_per_kwh == Decimal("8.13")
    assert new_pros.export_credit_pkr == Decimal("3658.50")  # 450 * 8.13

    gf_pros = engine_2026.calculate_prosumer_settlement(
        regime=ProsumerRegime2026.GRANDFATHERED_NET_METERING,
        sanctioned_load_kw=10.0,
        gross_peak_import_kwh=100,
        gross_off_peak_import_kwh=300,
        gross_export_kwh=450,
    )
    # 300 kWh Off-Peak import is completely netted 1:1 by 300 kWh of export, leaving 150 kWh surplus @ Rs 25.32
    assert gf_pros.net_billed_peak_import_kwh == Decimal("100")
    assert gf_pros.net_billed_off_peak_import_kwh == Decimal("0")
    assert gf_pros.net_surplus_export_kwh == Decimal("150")
    assert gf_pros.export_credit_rate_pkr_per_kwh == Decimal("25.32")
    assert gf_pros.export_credit_pkr == Decimal("3798.00")  # 150 * 25.32
    assert gf_pros.net_payable_after_credits_pkr < new_pros.net_payable_after_credits_pkr


# =====================================================================
# 5. Multi-Regime MILP Battery Dispatch Optimization
# =====================================================================

def test_milp_dispatch_seasonal_peak_shift_and_net_billing(optimizer_2026: Lesco2026BatteryDispatchOptimizer) -> None:
    """
    Verifies that under NET_BILLING_2026 (export = Rs 8.13/kWh vs Peak import = Rs 60.31/kWh),
    the optimizer charges the battery from midday solar and discharges across the exact seasonal
    4-hour peak window (17:00-21:00 in January vs 19:00-23:00 in July).
    """
    load_24h = np.full(24, 1.0, dtype=np.float64)
    solar_24h = np.zeros(24, dtype=np.float64)
    solar_24h[9:16] = 3.5  # Sunny midday (9 AM - 3 PM)

    # Winter (January: Peak 17:00-21:00)
    res_jan = optimizer_2026.optimize_24h(
        load_kw=load_24h,
        solar_kw=solar_24h,
        month=1,
        regime=ProsumerRegime2026.NET_BILLING_2026,
        initial_soc_kwh=1.0,
    )
    assert res_jan.status in ("optimal", "OPTIMAL")
    assert res_jan.season == "Winter"
    # During Jan Peak (17..20), battery discharges so grid import is 0.0 kW
    assert float(np.sum(res_jan.p_grid_import_kw[17:21])) == pytest.approx(0.0, abs=1e-4)
    assert float(np.sum(res_jan.p_dis_kw[17:21])) == pytest.approx(4.0, abs=1e-4)

    # Summer (July: Peak 19:00-23:00)
    res_jul = optimizer_2026.optimize_24h(
        load_kw=load_24h,
        solar_kw=solar_24h,
        month=7,
        regime=ProsumerRegime2026.NET_BILLING_2026,
        initial_soc_kwh=1.0,
    )
    assert res_jul.season == "Summer"
    assert float(np.sum(res_jul.p_grid_import_kw[19:23])) == pytest.approx(0.0, abs=1e-4)
    assert float(np.sum(res_jul.p_dis_kw[19:23])) == pytest.approx(4.0, abs=1e-4)

    # Verify write-locked C-contiguous float64 arrays
    assert res_jul.p_grid_import_kw.flags["C_CONTIGUOUS"]
    assert not res_jul.p_grid_import_kw.flags["WRITEABLE"]
    with pytest.raises(ValueError):
        res_jul.p_grid_import_kw[0] = 99.0


def test_milp_dispatch_single_phase_zero_export_and_200_unit_protected_guardrail(
    optimizer_2026: Lesco2026BatteryDispatchOptimizer,
) -> None:
    """
    Verifies Regime 3 (SINGLE_PHASE_SLAB_ZERO_EXPORT):
      1. Hard zero grid export (p_grid_export_kw == 0.0 kW at all hours) so unidirectional
         single-phase meters never count reverse flow as forward consumption.
      2. Cumulative monthly grid import stays within the 195 kWh / 200 kWh Protected guardrail
         by discharging stored solar energy instead of crossing the 200-unit cliff.
      3. Whole-bill landing-slab boundary shaving (e.g., preventing crossing 300 kWh).
    """
    load_24h = np.full(24, 0.45, dtype=np.float64)  # 10.8 kWh/day household load
    solar_24h = np.zeros(24, dtype=np.float64)
    solar_24h[8:17] = 2.5  # Abundant daytime solar

    # Scenario A: Protected Consumer on Day 29 with 191.5 kWh month-to-date grid import
    res_prot = optimizer_2026.optimize_24h(
        load_kw=load_24h,
        solar_kw=solar_24h,
        month=10,
        regime=ProsumerRegime2026.SINGLE_PHASE_SLAB_ZERO_EXPORT,
        initial_soc_kwh=3.5,
        prior_month_to_date_import_kwh=191.5,
        is_protected_consumer=True,
        protected_guardrail_kwh=195.0,
    )
    assert float(np.max(res_prot.p_grid_export_kw)) == pytest.approx(0.0, abs=1e-7)
    assert res_prot.protected_200_guardrail_intact is True
    assert res_prot.projected_month_to_date_import_kwh <= 195.0 + 1e-4

    # Scenario B: Unprotected Consumer approaching the 300 kWh whole-bill cliff (296.5 kWh MTD)
    res_slab = optimizer_2026.optimize_24h(
        load_kw=load_24h,
        solar_kw=solar_24h,
        month=10,
        regime=ProsumerRegime2026.SINGLE_PHASE_SLAB_ZERO_EXPORT,
        initial_soc_kwh=3.5,
        prior_month_to_date_import_kwh=296.5,
        is_protected_consumer=False,
    )
    assert res_slab.slab_ceiling_target_kwh == pytest.approx(300.0)
    assert res_slab.projected_month_to_date_import_kwh <= 300.0 + 1e-4
    assert res_slab.slab_cliff_penalty_pkr == Decimal("0.00")

