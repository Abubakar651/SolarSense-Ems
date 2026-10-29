"""
SolarSense EMS — CY 2026 LESCO Residential Tariff & Prosumer Battery Dispatch Module
=====================================================================================
Single-source-of-truth implementation of Lahore Electric Supply Company (LESCO) & NEPRA
Calendar Year 2026 residential tariff structures, billing formulas, seasonal Time-of-Use
(ToU) peak windows, and Solar Prosumer Regulations 2026 based on:
  - docs/lesco_residential_tariffs_config_2026.json
  - docs/lesco_residential_electricity_tariffs_metering_report_2026.pdf
  - docs/lesco_residential_tariffs_llm_context_2026.md

Regulatory Authorities & Statutory Notifications:
  - S.R.O. 279(I)/2026 (eff. 12 Feb 2026): National Schedule of Electricity Tariffs (A-1)
  - S.R.O. 251(I)/2026 (eff. 09 Feb 2026): NEPRA Prosumer Regulations 2026 (Gross Net-Billing @ Rs 8.13/kWh)
  - S.R.O. 547(I)/2026 (eff. 31 Mar 2026): Prosumer Amendment (Grandfathered <9 Feb 2026 1:1 Off-Peak + Rs 25.32/kWh)
  - S.R.O. 1330(I)/2026 (eff. 31 Jul 2026): 2nd Amendment (<=25 kW NEPRA concurrence exemption)
  - S.R.O. 1501(I)/2026 (Sep-Nov 2026): FY2025-26 Q4 QTA = +Rs 0.5194/kWh
  - S.R.O. 1754(I)/2026 (Oct 2026 bills): Aug 2026 FCA/FPA = +Rs 1.1086/kWh (billed 2 months in arrears)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_EVEN
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import cvxpy as cp
import numpy as np
import numpy.typing as npt

from src.optimizer.milp_solver import BESSConfig

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CONFIG_2026_PATH = PROJECT_ROOT / "docs" / "lesco_residential_tariffs_config_2026.json"

FloatVec = npt.NDArray[np.float64]

_PAISA = Decimal("0.01")
_RATE_PREC = Decimal("0.0001")
_ZERO = Decimal("0.00")


def _d(val: object) -> Decimal:
    """Safely converts float/int/str/Decimal into an exact Decimal."""
    if isinstance(val, Decimal):
        return val
    if isinstance(val, (int, str)):
        return Decimal(val)
    return Decimal(repr(round(float(val), 8)))


def _round_pkr(val: Decimal) -> Decimal:
    """Quantises a PKR amount to 0.01 (exact paisa) using ROUND_HALF_EVEN."""
    return val.quantize(_PAISA, rounding=ROUND_HALF_EVEN)


def _round_whole_rupee(val: Decimal) -> Decimal:
    """Quantises payable bill total to nearest whole Rupee (Rs 1)."""
    return val.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)


def _ro_vec(values: Sequence[float] | npt.ArrayLike, length: Optional[int] = None) -> FloatVec:
    """Converts input to a C-contiguous, write-locked float64 1D NumPy array."""
    arr = np.ascontiguousarray(np.asarray(values, dtype=np.float64).reshape(-1), dtype=np.float64)
    if length is not None and arr.shape[0] != length:
        raise ValueError(f"Expected vector of length {length}, got {arr.shape[0]}.")
    arr.setflags(write=False)
    return arr


# =====================================================================
# 1. Enumerations & Strongly Typed Frozen Domain Contracts
# =====================================================================

class ConsumerCategory2026(str, Enum):
    """LESCO CY 2026 Residential Tariff A-1 Categories (S.R.O. 279(I)/2026)."""
    LIFELINE = "LIFELINE"          # <= 1 kW sanctioned load, 12-month max <= 100 kWh
    PROTECTED = "PROTECTED"        # < 5 kW Non-ToU, <= 200 kWh/month for 6 consecutive months
    UNPROTECTED = "UNPROTECTED"    # < 5 kW Non-ToU, > 200 kWh in any of last 6 months
    TOU_A1B = "TOU_A1B"            # >= 5 kW mandatory 3-phase ToU (or optional < 5 kW ToU)
    PREPAID_A1C = "PREPAID_A1C"    # Optional Pre-Paid Residential Supply Tariff


class ProsumerRegime2026(str, Enum):
    """NEPRA Prosumer Regulations 2026 & Metering Regimes."""
    NONE = "NONE"
    NET_BILLING_2026 = "NET_BILLING_2026"                      # S.R.O. 251(I)/2026 (>= 9 Feb 2026, NAEPP Rs 8.13/kWh)
    GRANDFATHERED_NET_METERING = "GRANDFATHERED_NET_METERING"  # S.R.O. 547(I)/2026 (< 9 Feb 2026, 1:1 Off-Peak + NAPPP Rs 25.32/kWh)
    SINGLE_PHASE_SLAB_ZERO_EXPORT = "SINGLE_PHASE_SLAB_ZERO_EXPORT"  # < 5 kW single-phase Non-ToU with hard zero export


class BillingDemandMode(str, Enum):
    """Fixed charge billing demand basis under S.R.O. 279(I)/2026."""
    FULL_SANCTIONED_LOAD = "FULL_SANCTIONED_LOAD"  # Default residential formula: Sanctioned Load (kW) * rate
    MAX_50PCT_OR_MDI = "MAX_50PCT_OR_MDI"          # Annex-III standard: max(0.50 * Sanctioned Load, Actual MDI)
    MAX_25PCT_OR_MDI = "MAX_25PCT_OR_MDI"          # Smart bi-directional meter: max(0.25 * Sanctioned Load, Actual MDI)


@dataclass(frozen=True, slots=True)
class SlabBracketDTO:
    """Immutable definition of a residential consumption slab (S.R.O. 279(I)/2026)."""
    slab_id: str
    min_kwh: int
    max_kwh: Optional[int]  # None means unbounded (> 700 kWh)
    pricing_mechanism: str  # "whole_bill_rate" or "incremental_one_previous_slab"
    variable_rate_pkr_per_kwh: Decimal
    first_100_rate_pkr_per_kwh: Optional[Decimal]
    excess_over_100_rate_pkr_per_kwh: Optional[Decimal]
    fixed_charge_pkr_per_kw_month: Decimal
    fc_surcharge_pkr_per_kwh: Decimal


@dataclass(frozen=True, slots=True)
class SeasonalPeakWindowDTO:
    """Immutable seasonal Time-of-Use 4-hour peak schedule (PKT UTC+05:00)."""
    season: str
    months: Tuple[int, ...]
    peak_start_hour: int
    peak_end_hour: int


@dataclass(frozen=True, slots=True)
class Lesco2026ConfigDTO:
    """Immutable in-memory representation of docs/lesco_residential_tariffs_config_2026.json."""
    version: str
    effective_date: str
    lifeline_max_sanctioned_load_kw: Decimal
    lifeline_max_12m_kwh: int
    lifeline_minimum_monthly_charge_pkr: Decimal
    lifeline_slabs: Tuple[SlabBracketDTO, ...]
    protected_max_sanctioned_load_kw: Decimal
    protected_max_6m_consecutive_kwh: int
    protected_slabs: Tuple[SlabBracketDTO, ...]
    unprotected_max_sanctioned_load_kw: Decimal
    unprotected_slabs: Tuple[SlabBracketDTO, ...]
    tou_peak_rate_pkr_per_kwh: Decimal
    tou_off_peak_rate_pkr_per_kwh: Decimal
    tou_fixed_charge_pkr_per_kw_month: Decimal
    tou_fc_surcharge_pkr_per_kwh: Decimal
    prepaid_variable_rate_pkr_per_kwh: Decimal
    prepaid_fixed_charge_pkr_per_kw_month: Decimal
    prepaid_fc_surcharge_pkr_per_kwh: Decimal
    seasonal_peak_windows: Tuple[SeasonalPeakWindowDTO, ...]
    qta_rate_pkr_per_kwh: Decimal
    fca_rate_pkr_per_kwh: Decimal
    gst_rate: Decimal
    electricity_duty_rate: Decimal
    ptv_fee_pkr: Decimal
    income_tax_non_filer_threshold_pkr: Decimal
    income_tax_non_filer_rate: Decimal
    naepp_export_rate_pkr_per_kwh: Decimal
    nappp_grandfathered_rate_pkr_per_kwh: Decimal
    prosumer_max_capacity_ratio_of_sanctioned_load: Decimal
    prosumer_concurrence_exemption_max_kw: Decimal


@dataclass(frozen=True, slots=True)
class ResidentialBillBreakdownDTO:
    """Exact paisa-level monthly LESCO residential electricity bill breakdown."""
    category: ConsumerCategory2026
    slab_id: str
    sanctioned_load_kw: Decimal
    billing_demand_kw: Decimal
    current_total_kwh: Decimal
    current_peak_kwh: Decimal
    current_off_peak_kwh: Decimal
    fpa_reference_2m_prior_kwh: Decimal
    include_electricity_duty: bool
    is_atl_filer: bool
    # Line-by-line PKR ledger (quantised to 0.01 PKR with ROUND_HALF_EVEN)
    peak_energy_charges_pkr: Decimal
    off_peak_energy_charges_pkr: Decimal
    variable_energy_charges_pkr: Decimal
    fixed_charges_pkr: Decimal
    qta_pkr: Decimal
    fc_surcharge_pkr: Decimal
    electricity_duty_current_pkr: Decimal
    current_pre_gst_subtotal_pkr: Decimal
    gst_on_current_bill_pkr: Decimal
    fpa_base_pkr: Decimal
    ed_on_fpa_pkr: Decimal
    gst_on_fpa_pkr: Decimal
    ed_and_gst_on_fpa_pkr: Decimal
    ptv_fee_pkr: Decimal
    subtotal_before_income_tax_pkr: Decimal
    section_235_income_tax_pkr: Decimal
    total_payable_pkr: Decimal
    total_payable_rounded_rupee_pkr: Decimal
    effective_all_in_rate_pkr_per_kwh: Decimal


@dataclass(frozen=True, slots=True)
class ProsumerEligibilityDTO:
    """Validation result for NEPRA Prosumer Regulations 2026 interconnection eligibility."""
    is_eligible: bool
    requires_nepra_concurrence: bool
    max_allowed_pv_kw: Decimal
    violations: Tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProsumerMonthlySettlementDTO:
    """Monthly billing & export credit settlement for New (Net-Billing) vs Grandfathered Prosumers."""
    regime: ProsumerRegime2026
    gross_peak_import_kwh: Decimal
    gross_off_peak_import_kwh: Decimal
    gross_export_kwh: Decimal
    net_billed_peak_import_kwh: Decimal
    net_billed_off_peak_import_kwh: Decimal
    net_surplus_export_kwh: Decimal
    export_credit_rate_pkr_per_kwh: Decimal
    gross_retail_import_bill_pkr: Decimal
    export_credit_pkr: Decimal
    previous_credit_balance_pkr: Decimal
    net_payable_after_credits_pkr: Decimal
    closing_credit_carryforward_pkr: Decimal
    retail_bill_breakdown: ResidentialBillBreakdownDTO


@dataclass(frozen=True, slots=True)
class Lesco2026DispatchResultDTO:
    """Immutable 24-hour MILP battery dispatch trajectory under CY 2026 LESCO rules."""
    regime: ProsumerRegime2026
    season: str
    status: str
    solve_time_ms: float
    # Write-locked C-contiguous float64 vectors
    p_grid_import_kw: FloatVec
    p_grid_export_kw: FloatVec
    p_ch_kw: FloatVec
    p_dis_kw: FloatVec
    p_curtail_kw: FloatVec
    p_backup_kw: FloatVec
    soc_kwh: FloatVec
    is_peak_mask: FloatVec
    # State & cumulative guardrail tracking
    initial_soc_kwh: float
    terminal_soc_kwh: float
    prior_month_to_date_import_kwh: float
    projected_month_to_date_import_kwh: float
    slab_ceiling_target_kwh: Optional[float]
    protected_200_guardrail_intact: bool
    # Financial summary (Decimal 0.01 PKR)
    import_energy_cost_pkr: Decimal
    export_revenue_credit_pkr: Decimal
    slab_cliff_penalty_pkr: Decimal
    battery_wear_cost_pkr: Decimal
    net_horizon_cost_pkr: Decimal
    # Transparency & counterfactual (no-battery) baseline under the same tariff/export valuation
    export_rate_used_pkr_per_kwh: Decimal = Decimal("0.00")
    baseline_no_battery_cost_pkr: Decimal = Decimal("0.00")
    net_savings_pkr: Decimal = Decimal("0.00")


# =====================================================================
# 2. JSON Parser & CY 2026 LESCO Tariff Engine
# =====================================================================

_MONTH_NAME_TO_INT: Dict[str, int] = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def load_lesco_2026_config(config_path: Path = DEFAULT_CONFIG_2026_PATH) -> Lesco2026ConfigDTO:
    """Loads and validates docs/lesco_residential_tariffs_config_2026.json into an immutable DTO."""
    with open(config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    meta = raw["metadata"]
    base_sro_meta = meta["latest_governing_notifications"]["base_tariff_and_fixed_charges"]
    topic_a = raw["topic_A_residential_slab_tariff_A1a"]
    cats = topic_a["categories"]
    lifeline_raw = cats["lifeline"]
    protected_raw = cats["protected"]
    unprotected_raw = cats["unprotected"]
    tou_raw = raw["topic_B_time_of_use_residential_tariff_A1b"]
    prepaid_raw = tou_raw["prepaid_residential_tariff_A1c"]
    topic_c = raw["topic_C_bill_components_and_taxes"]
    topic_d = raw["topic_D_solar_prosumer_net_billing_rules"]

    lifeline_slabs = tuple(
        SlabBracketDTO(
            slab_id=str(s["slab_id"]),
            min_kwh=int(s["min_kwh"]),
            max_kwh=int(s["max_kwh"]) if s["max_kwh"] is not None else None,
            pricing_mechanism=str(lifeline_raw["slab_application_mode"]),
            variable_rate_pkr_per_kwh=_d(s["gop_applicable_variable_rate_pkr_per_kwh"]),
            first_100_rate_pkr_per_kwh=None,
            excess_over_100_rate_pkr_per_kwh=None,
            fixed_charge_pkr_per_kw_month=_d(s["fixed_charge_pkr_per_kw_month"]),
            fc_surcharge_pkr_per_kwh=_d(s["fc_surcharge_pkr_per_kwh"]),
        )
        for s in lifeline_raw["slabs"]
    )

    first_100_prot_rate = _d(protected_raw["slabs"][0]["gop_applicable_variable_rate_pkr_per_kwh"])
    protected_slabs = tuple(
        SlabBracketDTO(
            slab_id=str(s["slab_id"]),
            min_kwh=int(s["min_kwh"]),
            max_kwh=int(s["max_kwh"]) if s["max_kwh"] is not None else None,
            pricing_mechanism=str(protected_raw["slab_application_mode"]),
            variable_rate_pkr_per_kwh=_d(s["gop_applicable_variable_rate_pkr_per_kwh"]),
            first_100_rate_pkr_per_kwh=(first_100_prot_rate if int(s["min_kwh"]) > 100 else None),
            excess_over_100_rate_pkr_per_kwh=(
                _d(s["gop_applicable_variable_rate_pkr_per_kwh"]) if int(s["min_kwh"]) > 100 else None
            ),
            fixed_charge_pkr_per_kw_month=_d(s["fixed_charge_pkr_per_kw_month"]),
            fc_surcharge_pkr_per_kwh=_d(s["fc_surcharge_pkr_per_kwh"]),
        )
        for s in protected_raw["slabs"]
    )

    unprotected_slabs = tuple(
        SlabBracketDTO(
            slab_id=str(s["slab_id"]),
            min_kwh=int(s["min_kwh"]),
            max_kwh=int(s["max_kwh"]) if s["max_kwh"] is not None else None,
            pricing_mechanism=str(unprotected_raw["slab_application_mode"]),
            variable_rate_pkr_per_kwh=_d(s["gop_applicable_variable_rate_pkr_per_kwh"]),
            first_100_rate_pkr_per_kwh=None,
            excess_over_100_rate_pkr_per_kwh=None,
            fixed_charge_pkr_per_kw_month=_d(s["fixed_charge_pkr_per_kw_month"]),
            fc_surcharge_pkr_per_kwh=_d(s["fc_surcharge_pkr_per_kwh"]),
        )
        for s in unprotected_raw["slabs"]
    )

    seasonal_windows = tuple(
        SeasonalPeakWindowDTO(
            season=str(w["season"]),
            months=tuple(
                int(m) if isinstance(m, int) else _MONTH_NAME_TO_INT[str(m).strip().lower()]
                for m in w["months"]
            ),
            peak_start_hour=int(str(w["peak_start_24h"]).split(":")[0]),
            peak_end_hour=int(str(w["peak_end_24h"]).split(":")[0]),
        )
        for w in tou_raw["seasonal_peak_windows_pkt"]
    )

    fc_raw = topic_c["financing_cost_fc_surcharge"]
    qta_raw = topic_c["quarterly_tariff_adjustment_qta"]
    fpa_raw = topic_c["fuel_price_adjustment_fpa"]
    gst_raw = topic_c["general_sales_tax_gst"]
    ptv_raw = topic_c["tv_license_fee_ptv"]
    it_raw = topic_c["withholding_income_tax_section_235"]
    new_pros_raw = topic_d["new_prosumers_on_or_after_2026_02_09"]
    gf_pros_raw = topic_d["grandfathered_prosumers_before_2026_02_09"]

    return Lesco2026ConfigDTO(
        version=str(meta["as_of_date"]),
        effective_date=str(base_sro_meta["effective_date"]),
        lifeline_max_sanctioned_load_kw=Decimal("1.0"),
        lifeline_max_12m_kwh=100,
        lifeline_minimum_monthly_charge_pkr=Decimal("75.00"),
        lifeline_slabs=lifeline_slabs,
        protected_max_sanctioned_load_kw=Decimal("5.0"),
        protected_max_6m_consecutive_kwh=200,
        protected_slabs=protected_slabs,
        unprotected_max_sanctioned_load_kw=Decimal("5.0"),
        unprotected_slabs=unprotected_slabs,
        tou_peak_rate_pkr_per_kwh=_d(tou_raw["peak_rate_pkr_per_kwh"]),
        tou_off_peak_rate_pkr_per_kwh=_d(tou_raw["off_peak_rate_pkr_per_kwh"]),
        tou_fixed_charge_pkr_per_kw_month=_d(tou_raw["fixed_charge_pkr_per_kw_month"]),
        tou_fc_surcharge_pkr_per_kwh=_d(fc_raw["unprotected_and_tou_rate_pkr_per_kwh"]),
        prepaid_variable_rate_pkr_per_kwh=_d(prepaid_raw["gop_variable_rate_pkr_per_kwh"]),
        prepaid_fixed_charge_pkr_per_kw_month=_d(prepaid_raw["fixed_charge_pkr_per_kw_month"]),
        prepaid_fc_surcharge_pkr_per_kwh=_d(fc_raw["unprotected_and_tou_rate_pkr_per_kwh"]),
        seasonal_peak_windows=seasonal_windows,
        qta_rate_pkr_per_kwh=_d(qta_raw["sep_to_nov_2026_rate_pkr_per_kwh"]),
        fca_rate_pkr_per_kwh=_d(fpa_raw["october_2026_bill_rate_pkr_per_kwh"]),
        gst_rate=_d(gst_raw["rate"]),
        electricity_duty_rate=Decimal("0.015"),
        ptv_fee_pkr=_d(ptv_raw["rate_pkr_per_month"]),
        income_tax_non_filer_threshold_pkr=Decimal("25000.00"),
        income_tax_non_filer_rate=_d(it_raw["non_filer_25000_pkr_and_above_bill"]),
        naepp_export_rate_pkr_per_kwh=_d(new_pros_raw["export_buyback_rate_pkr_per_kwh"]),
        nappp_grandfathered_rate_pkr_per_kwh=_d(gf_pros_raw["export_buyback_rate_pkr_per_kwh"]),
        prosumer_max_capacity_ratio_of_sanctioned_load=Decimal("1.00"),
        prosumer_concurrence_exemption_max_kw=Decimal("25.0"),
    )


class LescoCY2026TariffEngine:
    """
    Strongly typed CY 2026 LESCO Residential Tariff & Prosumer Settlement Engine.
    Uses exact Decimal (ROUND_HALF_EVEN) arithmetic and reproduces all statutory
    S.R.O. 279(I)/2026, S.R.O. 1501(I)/2026, S.R.O. 1754(I)/2026, and S.R.O. 251/547(I)/2026
    billing calculations to the exact paisa.
    """

    def __init__(self, config_path: Path = DEFAULT_CONFIG_2026_PATH) -> None:
        self.config_path = config_path
        self.config: Lesco2026ConfigDTO = load_lesco_2026_config(config_path)
        self._month_to_window: Dict[int, SeasonalPeakWindowDTO] = {}
        for w in self.config.seasonal_peak_windows:
            for m in w.months:
                self._month_to_window[m] = w

    # -----------------------------------------------------------------
    # Seasonal ToU Peak Window & Pro-Rata Normalization
    # -----------------------------------------------------------------

    def get_seasonal_window(self, month: int) -> SeasonalPeakWindowDTO:
        """Returns the SeasonalPeakWindowDTO for a calendar month (1..12)."""
        if month not in self._month_to_window:
            raise ValueError(f"Invalid calendar month: {month}. Must be in 1..12.")
        return self._month_to_window[month]

    def is_seasonal_peak_hour(self, dt: datetime) -> bool:
        """
        Determines whether a timestamp falls within LESCO's 4-hour seasonal ToU peak window:
          - Dec–Feb (Winter): 17:00–21:00
          - Mar–May (Spring): 18:00–22:00
          - Jun–Aug (Summer): 19:00–23:00
          - Sep–Nov (Autumn): 18:00–22:00
        """
        w = self.get_seasonal_window(dt.month)
        return w.peak_start_hour <= dt.hour < w.peak_end_hour

    def build_24h_seasonal_peak_mask(self, month: int, start_hour: int = 0, horizon: int = 24) -> FloatVec:
        """Builds a write-locked 1D float64 mask (1.0 = Peak, 0.0 = Off-Peak) for a 24h horizon."""
        w = self.get_seasonal_window(month)
        hours = (np.arange(horizon, dtype=np.int64) + int(start_hour)) % 24
        mask = ((hours >= w.peak_start_hour) & (hours < w.peak_end_hour)).astype(np.float64)
        return _ro_vec(mask, horizon)

    @staticmethod
    def normalize_pro_rata_consumption(
        actual_metered_kwh: float | Decimal,
        calendar_days_in_month: int = 30,
        reading_cycle_days: int = 30,
    ) -> Decimal:
        """
        Applies the statutory Annex-III pro-rata billing normalization formula:
          Pro-Rata Consumption = Actual Metered Units * (Calendar Days in Month / Reading Cycle Days)
        Prevents delayed meter reading cycles (e.g., 33-day reading spans) from unfairly pushing
        consumers over the 200-unit Protected threshold or into higher Unprotected slabs.
        """
        if reading_cycle_days <= 0 or calendar_days_in_month <= 0:
            raise ValueError("calendar_days_in_month and reading_cycle_days must be positive integers.")
        actual = _d(actual_metered_kwh)
        ratio = Decimal(calendar_days_in_month) / Decimal(reading_cycle_days)
        return (actual * ratio).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)

    # -----------------------------------------------------------------
    # Consumer Classification & Eligibility
    # -----------------------------------------------------------------

    def determine_consumer_category(
        self,
        sanctioned_load_kw: float | Decimal,
        current_month_kwh: float | Decimal,
        prior_6m_max_kwh: Optional[float | Decimal] = None,
        prior_12m_max_kwh: Optional[float | Decimal] = None,
        is_tou_meter: bool = False,
        is_prepaid: bool = False,
        is_single_phase: bool = True,
    ) -> ConsumerCategory2026:
        """
        Classifies a LESCO residential consumer under S.R.O. 279(I)/2026:
          1. PREPAID_A1C if is_prepaid=True.
          2. TOU_A1B if sanctioned_load_kw >= 5.0 kW (mandatory 3-phase ToU) or is_tou_meter=True.
          3. LIFELINE if single-phase, sanctioned_load_kw <= 1.0 kW, current_month_kwh <= 100,
             and 12-month rolling max <= 100 kWh.
          4. PROTECTED if sanctioned_load_kw < 5.0 kW, Non-ToU, current_month_kwh <= 200,
             and past 6 consecutive months max <= 200 kWh.
          5. UNPROTECTED otherwise (< 5.0 kW Non-ToU).
        """
        load_kw = _d(sanctioned_load_kw)
        cur_kwh = _d(current_month_kwh)

        if is_prepaid:
            return ConsumerCategory2026.PREPAID_A1C

        if is_tou_meter or load_kw >= self.config.unprotected_max_sanctioned_load_kw:
            return ConsumerCategory2026.TOU_A1B

        if (
            is_single_phase
            and load_kw <= self.config.lifeline_max_sanctioned_load_kw
            and cur_kwh <= Decimal(self.config.lifeline_max_12m_kwh)
            and prior_12m_max_kwh is not None
            and _d(prior_12m_max_kwh) <= Decimal(self.config.lifeline_max_12m_kwh)
        ):
            return ConsumerCategory2026.LIFELINE

        max_6m = _d(prior_6m_max_kwh) if prior_6m_max_kwh is not None else cur_kwh
        if (
            load_kw < self.config.protected_max_sanctioned_load_kw
            and cur_kwh <= Decimal(self.config.protected_max_6m_consecutive_kwh)
            and max_6m <= Decimal(self.config.protected_max_6m_consecutive_kwh)
        ):
            return ConsumerCategory2026.PROTECTED

        return ConsumerCategory2026.UNPROTECTED

    def get_slab_bracket(
        self,
        category: ConsumerCategory2026,
        consumption_kwh: float | Decimal,
    ) -> SlabBracketDTO:
        """Selects the exact SlabBracketDTO for Lifeline, Protected, or Unprotected consumption."""
        kwh = _d(consumption_kwh)
        if category == ConsumerCategory2026.LIFELINE:
            slabs = self.config.lifeline_slabs
        elif category == ConsumerCategory2026.PROTECTED:
            slabs = self.config.protected_slabs
        elif category == ConsumerCategory2026.UNPROTECTED:
            slabs = self.config.unprotected_slabs
        else:
            raise ValueError(f"Category {category} is not a slab-based Non-ToU tariff.")

        if kwh <= _ZERO:
            return slabs[0]

        for s in slabs:
            if s.max_kwh is None:
                if kwh > Decimal(s.min_kwh - 1):
                    return s
            else:
                if kwh <= Decimal(s.max_kwh):
                    return s
        return slabs[-1]

    @staticmethod
    def compute_billing_demand_kw(
        sanctioned_load_kw: float | Decimal,
        actual_mdi_kw: Optional[float | Decimal] = None,
        demand_mode: BillingDemandMode = BillingDemandMode.FULL_SANCTIONED_LOAD,
    ) -> Decimal:
        """
        Computes billing demand (kW) for monthly fixed charges:
          - FULL_SANCTIONED_LOAD: 100% of Sanctioned Load (default residential practice)
          - MAX_50PCT_OR_MDI: max(50% of Sanctioned Load, Actual MDI) (Annex-III Clause 5)
          - MAX_25PCT_OR_MDI: max(25% of Sanctioned Load, Actual MDI) (Smart Bi-Directional Meter)
        """
        s_kw = _d(sanctioned_load_kw)
        if demand_mode == BillingDemandMode.FULL_SANCTIONED_LOAD or actual_mdi_kw is None:
            return s_kw
        mdi = _d(actual_mdi_kw)
        if demand_mode == BillingDemandMode.MAX_50PCT_OR_MDI:
            return max(Decimal("0.50") * s_kw, mdi)
        if demand_mode == BillingDemandMode.MAX_25PCT_OR_MDI:
            return max(Decimal("0.25") * s_kw, mdi)
        return s_kw

    # -----------------------------------------------------------------
    # Exact Paisa-Level Bill Calculation (Worked Examples 1 & 2)
    # -----------------------------------------------------------------

    def calculate_monthly_bill(
        self,
        category: ConsumerCategory2026,
        sanctioned_load_kw: float | Decimal,
        current_kwh: float | Decimal = 0,
        peak_kwh: float | Decimal = 0,
        off_peak_kwh: float | Decimal = 0,
        fpa_reference_2m_prior_kwh: float | Decimal = 0,
        include_electricity_duty: bool = False,
        is_atl_filer: bool = True,
        qta_rate_override: Optional[float | Decimal] = None,
        fca_rate_override: Optional[float | Decimal] = None,
        actual_mdi_kw: Optional[float | Decimal] = None,
        demand_mode: BillingDemandMode = BillingDemandMode.FULL_SANCTIONED_LOAD,
    ) -> ResidentialBillBreakdownDTO:
        """
        Computes a complete monthly LESCO residential bill under CY 2026 rules.
        Matches Worked Example 1 (Unprotected 350 kWh) and Worked Example 2 (ToU 500 kWh)
        from docs/lesco_residential_electricity_tariffs_metering_report_2026.pdf to the exact paisa.
        """
        load_kw = _d(sanctioned_load_kw)
        billing_kw = self.compute_billing_demand_kw(load_kw, actual_mdi_kw, demand_mode)
        ref_fpa_kwh = _d(fpa_reference_2m_prior_kwh)

        r_qta = _d(qta_rate_override) if qta_rate_override is not None else self.config.qta_rate_pkr_per_kwh
        r_fca = _d(fca_rate_override) if fca_rate_override is not None else self.config.fca_rate_pkr_per_kwh

        if category == ConsumerCategory2026.TOU_A1B:
            e_peak = _d(peak_kwh)
            e_off = _d(off_peak_kwh)
            e_cur = e_peak + e_off
            slab_id = "TOU_A1B"
            peak_energy_pkr = _round_pkr(e_peak * self.config.tou_peak_rate_pkr_per_kwh)
            off_peak_energy_pkr = _round_pkr(e_off * self.config.tou_off_peak_rate_pkr_per_kwh)
            variable_energy_pkr = peak_energy_pkr + off_peak_energy_pkr
            fixed_charges_pkr = _round_pkr(billing_kw * self.config.tou_fixed_charge_pkr_per_kw_month)
            r_fc = self.config.tou_fc_surcharge_pkr_per_kwh
            exempt_adjustments = False
        elif category == ConsumerCategory2026.PREPAID_A1C:
            e_cur = _d(current_kwh) if _d(current_kwh) > _ZERO else (_d(peak_kwh) + _d(off_peak_kwh))
            e_peak = _ZERO
            e_off = e_cur
            slab_id = "PREPAID_A1C"
            peak_energy_pkr = _ZERO
            off_peak_energy_pkr = _round_pkr(e_cur * self.config.prepaid_variable_rate_pkr_per_kwh)
            variable_energy_pkr = off_peak_energy_pkr
            fixed_charges_pkr = _round_pkr(billing_kw * self.config.prepaid_fixed_charge_pkr_per_kw_month)
            r_fc = self.config.prepaid_fc_surcharge_pkr_per_kwh
            exempt_adjustments = True
        else:
            e_cur = _d(current_kwh) if _d(current_kwh) > _ZERO else (_d(peak_kwh) + _d(off_peak_kwh))
            e_peak = _ZERO
            e_off = e_cur
            bracket = self.get_slab_bracket(category, e_cur)
            slab_id = bracket.slab_id
            peak_energy_pkr = _ZERO

            if (
                category == ConsumerCategory2026.PROTECTED
                and bracket.first_100_rate_pkr_per_kwh is not None
                and bracket.excess_over_100_rate_pkr_per_kwh is not None
                and e_cur > Decimal("100")
            ):
                # Incremental one-previous-slab calculation for Protected 101-200 kWh
                first_100_pkr = _round_pkr(Decimal("100") * bracket.first_100_rate_pkr_per_kwh)
                rem_pkr = _round_pkr((e_cur - Decimal("100")) * bracket.excess_over_100_rate_pkr_per_kwh)
                off_peak_energy_pkr = first_100_pkr + rem_pkr
            else:
                # Whole-bill landing-slab rate (Unprotected, Lifeline, or Protected 1-100)
                off_peak_energy_pkr = _round_pkr(e_cur * bracket.variable_rate_pkr_per_kwh)

            variable_energy_pkr = off_peak_energy_pkr

            if category == ConsumerCategory2026.LIFELINE:
                fixed_charges_pkr = _ZERO
                if e_cur == _ZERO and variable_energy_pkr == _ZERO:
                    variable_energy_pkr = self.config.lifeline_minimum_monthly_charge_pkr
                    off_peak_energy_pkr = variable_energy_pkr
                r_fc = _ZERO
                exempt_adjustments = True
            else:
                fixed_charges_pkr = _round_pkr(billing_kw * bracket.fixed_charge_pkr_per_kw_month)
                r_fc = bracket.fc_surcharge_pkr_per_kwh
                exempt_adjustments = False

        # Adjustments & Surcharges
        if exempt_adjustments:
            qta_pkr = _ZERO
            fc_surcharge_pkr = _round_pkr(e_cur * r_fc)
            fpa_base_pkr = _ZERO
        else:
            qta_pkr = _round_pkr(e_cur * r_qta)
            fc_surcharge_pkr = _round_pkr(e_cur * r_fc)
            fpa_base_pkr = _round_pkr(ref_fpa_kwh * r_fca)

        # Electricity Duty (1.5% on variable energy + QTA when enabled; Lifeline exempt)
        if include_electricity_duty and category != ConsumerCategory2026.LIFELINE:
            ed_cur_pkr = _round_pkr(self.config.electricity_duty_rate * (variable_energy_pkr + qta_pkr))
            ed_on_fpa_pkr = _round_pkr(self.config.electricity_duty_rate * fpa_base_pkr)
        else:
            ed_cur_pkr = _ZERO
            ed_on_fpa_pkr = _ZERO

        # Current Pre-GST Subtotal & 18% GST on Current Bill
        current_pre_gst_subtotal_pkr = (
            variable_energy_pkr + fixed_charges_pkr + qta_pkr + fc_surcharge_pkr + ed_cur_pkr
        )
        gst_cur_pkr = _round_pkr(self.config.gst_rate * current_pre_gst_subtotal_pkr)

        # GST on FPA (18% on FPA Base + ED on FPA)
        gst_on_fpa_pkr = _round_pkr(self.config.gst_rate * (fpa_base_pkr + ed_on_fpa_pkr))
        ed_and_gst_on_fpa_pkr = ed_on_fpa_pkr + gst_on_fpa_pkr

        # Subtotal Before Section 235 Income Tax (PTV Fee = Rs 0.00 in CY 2026)
        ptv_fee_pkr = self.config.ptv_fee_pkr
        subtotal_before_it_pkr = (
            current_pre_gst_subtotal_pkr + gst_cur_pkr + fpa_base_pkr + ed_and_gst_on_fpa_pkr + ptv_fee_pkr
        )

        # Section 235 Income Tax (0% for ATL Filer or < Rs 25,000; 7.5% for Non-Filer >= Rs 25,000)
        if not is_atl_filer and subtotal_before_it_pkr >= self.config.income_tax_non_filer_threshold_pkr:
            sec_235_it_pkr = _round_pkr(self.config.income_tax_non_filer_rate * subtotal_before_it_pkr)
        else:
            sec_235_it_pkr = _ZERO

        total_payable_pkr = subtotal_before_it_pkr + sec_235_it_pkr
        total_rounded_rupee_pkr = _round_whole_rupee(total_payable_pkr)
        denom = e_cur if e_cur > _ZERO else Decimal("1")
        eff_rate_pkr = _round_pkr(total_payable_pkr / denom)

        return ResidentialBillBreakdownDTO(
            category=category,
            slab_id=slab_id,
            sanctioned_load_kw=load_kw,
            billing_demand_kw=billing_kw,
            current_total_kwh=e_cur,
            current_peak_kwh=e_peak,
            current_off_peak_kwh=e_off,
            fpa_reference_2m_prior_kwh=ref_fpa_kwh,
            include_electricity_duty=include_electricity_duty,
            is_atl_filer=is_atl_filer,
            peak_energy_charges_pkr=peak_energy_pkr,
            off_peak_energy_charges_pkr=off_peak_energy_pkr,
            variable_energy_charges_pkr=variable_energy_pkr,
            fixed_charges_pkr=fixed_charges_pkr,
            qta_pkr=qta_pkr,
            fc_surcharge_pkr=fc_surcharge_pkr,
            electricity_duty_current_pkr=ed_cur_pkr,
            current_pre_gst_subtotal_pkr=current_pre_gst_subtotal_pkr,
            gst_on_current_bill_pkr=gst_cur_pkr,
            fpa_base_pkr=fpa_base_pkr,
            ed_on_fpa_pkr=ed_on_fpa_pkr,
            gst_on_fpa_pkr=gst_on_fpa_pkr,
            ed_and_gst_on_fpa_pkr=ed_and_gst_on_fpa_pkr,
            ptv_fee_pkr=ptv_fee_pkr,
            subtotal_before_income_tax_pkr=subtotal_before_it_pkr,
            section_235_income_tax_pkr=sec_235_it_pkr,
            total_payable_pkr=total_payable_pkr,
            total_payable_rounded_rupee_pkr=total_rounded_rupee_pkr,
            effective_all_in_rate_pkr_per_kwh=eff_rate_pkr,
        )

    # -----------------------------------------------------------------
    # NEPRA Prosumer Regulations 2026 Eligibility & Settlement
    # -----------------------------------------------------------------

    def validate_prosumer_eligibility(
        self,
        sanctioned_load_kw: float | Decimal,
        proposed_pv_capacity_kw: float | Decimal,
        phases: int = 3,
    ) -> ProsumerEligibilityDTO:
        """
        Validates technical interconnection eligibility under S.R.O. 251(I)/2026 & S.R.O. 1330(I)/2026:
          - Must be a 3-phase connection (phases == 3) with sanctioned_load_kw >= 5.0 kW.
          - Proposed PV capacity <= 100% (1.0x) of Sanctioned Load (replaces old 1.5x rule).
          - Systems <= 25.0 kW are exempt from individual NEPRA concurrence (S.R.O. 1330(I)/2026).
        """
        load_kw = _d(sanctioned_load_kw)
        pv_kw = _d(proposed_pv_capacity_kw)
        max_pv_kw = _round_pkr(load_kw * self.config.prosumer_max_capacity_ratio_of_sanctioned_load)
        violations: List[str] = []

        if phases != 3:
            violations.append("Single-phase meters are ineligible for bidirectional prosumer billing; 3-phase required.")
        if load_kw < Decimal("5.0"):
            violations.append(f"Sanctioned load ({load_kw} kW) is below the 5.0 kW 3-phase ToU threshold.")
        if pv_kw > max_pv_kw:
            violations.append(
                f"Proposed PV capacity ({pv_kw} kW) exceeds 100% of sanctioned load ({max_pv_kw} kW) under S.R.O. 251(I)/2026."
            )

        requires_concurrence = pv_kw > self.config.prosumer_concurrence_exemption_max_kw
        return ProsumerEligibilityDTO(
            is_eligible=(len(violations) == 0),
            requires_nepra_concurrence=requires_concurrence,
            max_allowed_pv_kw=max_pv_kw,
            violations=tuple(violations),
        )

    def calculate_prosumer_settlement(
        self,
        regime: ProsumerRegime2026,
        sanctioned_load_kw: float | Decimal,
        gross_peak_import_kwh: float | Decimal,
        gross_off_peak_import_kwh: float | Decimal,
        gross_export_kwh: float | Decimal,
        fpa_reference_2m_prior_kwh: float | Decimal = 0,
        previous_credit_balance_pkr: float | Decimal = 0,
        include_electricity_duty: bool = False,
        is_atl_filer: bool = True,
    ) -> ProsumerMonthlySettlementDTO:
        """
        Computes monthly prosumer settlement under either:
          1. NET_BILLING_2026 (S.R.O. 251(I)/2026, >= 9 Feb 2026):
             - Gross Net-Billing: Zero 1:1 unit netting. All imported Peak and Off-Peak kWh
               are billed at full retail tariff + surcharges + 18% GST.
             - Exported kWh are credited separately at NAEPP = Rs 8.13/kWh.
          2. GRANDFATHERED_NET_METERING (S.R.O. 547(I)/2026, < 9 Feb 2026):
             - Retains 1:1 monthly unit netting against Off-Peak imported kWh.
             - Net surplus exported kWh beyond Off-Peak imports are valued at NAPPP = Rs 25.32/kWh.
             - Surcharges/taxes apply to net billed imported kWh (plus Peak imports, which are never
               offset 1:1 by daytime Off-Peak exports).
        """
        e_peak = _d(gross_peak_import_kwh)
        e_off = _d(gross_off_peak_import_kwh)
        e_exp = _d(gross_export_kwh)
        prev_cred = _round_pkr(_d(previous_credit_balance_pkr))

        if regime == ProsumerRegime2026.NET_BILLING_2026:
            net_peak_kwh = e_peak
            net_off_kwh = e_off
            surplus_exp_kwh = e_exp
            exp_rate = self.config.naepp_export_rate_pkr_per_kwh
        elif regime == ProsumerRegime2026.GRANDFATHERED_NET_METERING:
            net_peak_kwh = e_peak
            if e_exp >= e_off:
                net_off_kwh = _ZERO
                surplus_exp_kwh = e_exp - e_off
            else:
                net_off_kwh = e_off - e_exp
                surplus_exp_kwh = _ZERO
            exp_rate = self.config.nappp_grandfathered_rate_pkr_per_kwh
        else:
            raise ValueError(f"Unsupported prosumer settlement regime: {regime}")

        retail_bill = self.calculate_monthly_bill(
            category=ConsumerCategory2026.TOU_A1B,
            sanctioned_load_kw=sanctioned_load_kw,
            peak_kwh=net_peak_kwh,
            off_peak_kwh=net_off_kwh,
            fpa_reference_2m_prior_kwh=fpa_reference_2m_prior_kwh,
            include_electricity_duty=include_electricity_duty,
            is_atl_filer=is_atl_filer,
        )

        export_credit_pkr = _round_pkr(surplus_exp_kwh * exp_rate)
        total_available_credit_pkr = prev_cred + export_credit_pkr
        gross_bill_pkr = retail_bill.total_payable_pkr

        if total_available_credit_pkr >= gross_bill_pkr:
            net_payable_pkr = _ZERO
            closing_carryforward_pkr = _round_pkr(total_available_credit_pkr - gross_bill_pkr)
        else:
            net_payable_pkr = _round_pkr(gross_bill_pkr - total_available_credit_pkr)
            closing_carryforward_pkr = _ZERO

        return ProsumerMonthlySettlementDTO(
            regime=regime,
            gross_peak_import_kwh=e_peak,
            gross_off_peak_import_kwh=e_off,
            gross_export_kwh=e_exp,
            net_billed_peak_import_kwh=net_peak_kwh,
            net_billed_off_peak_import_kwh=net_off_kwh,
            net_surplus_export_kwh=surplus_exp_kwh,
            export_credit_rate_pkr_per_kwh=exp_rate,
            gross_retail_import_bill_pkr=gross_bill_pkr,
            export_credit_pkr=export_credit_pkr,
            previous_credit_balance_pkr=prev_cred,
            net_payable_after_credits_pkr=net_payable_pkr,
            closing_credit_carryforward_pkr=closing_carryforward_pkr,
            retail_bill_breakdown=retail_bill,
        )

    def marginal_value_of_exported_kwh(
        self,
        regime: ProsumerRegime2026,
        netting_headroom_kwh: Optional[float | Decimal] = None,
        export_rate_override_pkr_per_kwh: Optional[float | Decimal] = None,
        include_electricity_duty: bool = False,
    ) -> Decimal:
        """
        Marginal PKR value of ONE exported kWh for a given customer (nothing hard-coded per user):
          - export_rate_override_pkr_per_kwh (customer's own contract/portal figure) wins when given.
          - NET_BILLING_2026: NAEPP from the tariff config.
          - GRANDFATHERED_NET_METERING: while unmatched Off-Peak imports remain this month
            (netting_headroom_kwh > 0, or unknown/None) the exported unit cancels one Off-Peak import
            unit, so it is worth the all-in Off-Peak import rate; once headroom is exhausted the unit is
            surplus and is paid at NAPPP from the tariff config.
          - SINGLE_PHASE_SLAB_ZERO_EXPORT / NONE: 0.00 (export is not allowed / not metered).
        """
        if regime in (ProsumerRegime2026.SINGLE_PHASE_SLAB_ZERO_EXPORT, ProsumerRegime2026.NONE):
            return _ZERO
        if export_rate_override_pkr_per_kwh is not None:
            return _round_pkr(_d(export_rate_override_pkr_per_kwh))
        if regime == ProsumerRegime2026.NET_BILLING_2026:
            return self.config.naepp_export_rate_pkr_per_kwh
        _, off_all_in = self.get_all_in_tou_marginal_rates_pkr(
            include_electricity_duty=include_electricity_duty, include_fpa_marginal=True
        )
        if netting_headroom_kwh is None or _d(netting_headroom_kwh) > _ZERO:
            return off_all_in
        return self.config.nappp_grandfathered_rate_pkr_per_kwh

    def get_all_in_tou_marginal_rates_pkr(
        self,
        include_electricity_duty: bool = False,
        include_fpa_marginal: bool = True,
    ) -> Tuple[Decimal, Decimal]:
        """
        Returns (all_in_peak_rate_pkr, all_in_off_peak_rate_pkr) per kWh for ToU A-1(b),
        including QTA (0.5194), FC Surcharge (3.23), optional FPA (1.1086), optional 1.5% ED, and 18% GST.
        Matches Section 5.1 of the PDF report (Rs 60.31/kWh Peak & Rs 45.77/kWh Off-Peak without ED).
        """
        qta = self.config.qta_rate_pkr_per_kwh
        fc = self.config.tou_fc_surcharge_pkr_per_kwh
        fca = self.config.fca_rate_pkr_per_kwh if include_fpa_marginal else _ZERO
        gst_mult = Decimal("1") + self.config.gst_rate

        peak_base = self.config.tou_peak_rate_pkr_per_kwh
        off_base = self.config.tou_off_peak_rate_pkr_per_kwh

        if include_electricity_duty:
            ed_peak = self.config.electricity_duty_rate * (peak_base + qta + fca)
            ed_off = self.config.electricity_duty_rate * (off_base + qta + fca)
        else:
            ed_peak = _ZERO
            ed_off = _ZERO

        peak_all_in = _round_pkr((peak_base + qta + fc + fca + ed_peak) * gst_mult)
        off_all_in = _round_pkr((off_base + qta + fc + fca + ed_off) * gst_mult)
        return peak_all_in, off_all_in


# =====================================================================
# 3. CY 2026 Multi-Regime MILP Battery Dispatch Optimizer (CVXPY + HiGHS)
# =====================================================================

class Lesco2026BatteryDispatchOptimizer:
    """
    High-speed CVXPY + HiGHS MILP battery dispatch optimizer tailored to CY 2026 LESCO rules:
      1. Seasonal ToU Peak Windows (Dec-Feb 17:00-21:00, Mar-May 18:00-22:00,
         Jun-Aug 19:00-23:00, Sep-Nov 18:00-22:00).
      2. Regime 1 (NET_BILLING_2026): Gross Net-Billing where daytime export only earns
         NAEPP (Rs 8.13/kWh) while Peak imports cost ~Rs 60.31/kWh all-in -> prioritizes
         storing solar in battery to eliminate Peak imports (saving Rs 52.18/kWh net).
      3. Regime 2 (GRANDFATHERED_NET_METERING): 1:1 Off-Peak netting + Rs 25.32/kWh NAPPP ->
         covers the 4-hour seasonal Peak window (which cannot be offset 1:1 by Off-Peak export)
         while banking excess daytime solar 1:1 against Off-Peak loads.
      4. Regime 3 (SINGLE_PHASE_SLAB_ZERO_EXPORT): Enforces hard zero grid export
         (p_export == 0.0 kW), protects the 200-unit 6-month Protected threshold
         (default guardrail target <= 195 kWh/month), and shaves whole-bill landing-slab
         cliffs (100, 200, 300, 400, 500, 600, 700 kWh).
    """

    SLAB_BOUNDARIES_KWH: Tuple[float, ...] = (100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0)

    def __init__(
        self,
        tariff_engine: Optional[LescoCY2026TariffEngine] = None,
        bess: Optional[BESSConfig] = None,
        pv_capacity_kw: Optional[float] = None,
    ) -> None:
        self.tariff_engine = tariff_engine or LescoCY2026TariffEngine()
        self.bess = bess or BESSConfig.station_904a_residential()
        self.pv_capacity_kw = pv_capacity_kw  # None = no nameplate clipping (per-customer setting)
        self._dpp_cache: Dict[int, dict] = {}

    def _get_dpp_bundle(self, H: int) -> dict:
        """Builds and caches a parameterised DPP CVXPY problem for horizon length H."""
        if H in self._dpp_cache:
            return self._dpp_cache[H]

        # Parameters
        load_p = cp.Parameter(H, nonneg=True, name="load_p")
        solar_p = cp.Parameter(H, nonneg=True, name="solar_p")
        live_p = cp.Parameter(H, nonneg=True, name="live_p")
        outage_p = cp.Parameter(H, nonneg=True, name="outage_p")
        allow_exp_p = cp.Parameter(H, nonneg=True, name="allow_exp_p")
        peak_mask_p = cp.Parameter(H, nonneg=True, name="peak_mask_p")
        peak_solar_cap_p = cp.Parameter(H, nonneg=True, name="peak_solar_cap_p")
        peak_load_cap_p = cp.Parameter(H, nonneg=True, name="peak_load_cap_p")
        imp_price_p = cp.Parameter(H, nonneg=True, name="imp_price_p")
        exp_price_p = cp.Parameter(H, nonneg=True, name="exp_price_p")
        soc0_p = cp.Parameter(nonneg=True, name="soc0_p")
        headroom_p = cp.Parameter(nonneg=True, name="headroom_p")
        cliff_pen_p = cp.Parameter(nonneg=True, name="cliff_pen_p")
        bkp_cost_p = cp.Parameter(nonneg=True, name="bkp_cost_p")

        # Variables
        p_imp = cp.Variable(H, nonneg=True, name="p_imp")
        p_exp = cp.Variable(H, nonneg=True, name="p_exp")
        p_ch = cp.Variable(H, nonneg=True, name="p_ch")
        p_dis = cp.Variable(H, nonneg=True, name="p_dis")
        p_curt = cp.Variable(H, nonneg=True, name="p_curt")
        p_bkp = cp.Variable(H, nonneg=True, name="p_bkp")
        soc = cp.Variable(H + 1, name="soc")
        u_ch = cp.Variable(H, boolean=True, name="u_ch")
        s_cliff = cp.Variable(nonneg=True, name="s_cliff")

        M_imp = 50.0
        M_exp = 50.0
        wear_rate = float(self.bess.degradation_cost_pkr_per_kwh)
        terminal_soc_credit_rate = 12.0

        constraints = [
            solar_p + p_imp + p_dis + p_bkp == load_p + p_ch + p_exp + p_curt,
            soc[0] == soc0_p,
            soc[1:] == soc[:-1] + self.bess.charge_efficiency * p_ch - (1.0 / self.bess.discharge_efficiency) * p_dis,
            soc[1:] >= self.bess.min_soc_kwh,
            soc[1:] <= self.bess.max_soc_kwh,
            p_ch <= self.bess.max_charge_kw * u_ch,
            p_dis <= self.bess.max_discharge_kw * (1.0 - u_ch),
            p_imp <= M_imp * live_p,
            p_exp <= M_exp * allow_exp_p,
            p_bkp <= M_imp * outage_p,
            p_exp <= solar_p,
            p_ch <= peak_solar_cap_p,
            p_imp <= peak_load_cap_p,
            cp.sum(p_imp) - headroom_p <= s_cliff,
        ]

        objective = cp.Minimize(
            imp_price_p @ p_imp
            - exp_price_p @ p_exp
            + bkp_cost_p * cp.sum(p_bkp)
            + wear_rate * cp.sum(p_ch + p_dis)
            + cliff_pen_p * s_cliff
            + 0.05 * cp.sum(p_curt)
            - terminal_soc_credit_rate * (soc[H] - soc[0])
        )

        prob = cp.Problem(objective, constraints)
        bundle = {
            "prob": prob,
            "load_p": load_p,
            "solar_p": solar_p,
            "live_p": live_p,
            "outage_p": outage_p,
            "allow_exp_p": allow_exp_p,
            "peak_mask_p": peak_mask_p,
            "peak_solar_cap_p": peak_solar_cap_p,
            "peak_load_cap_p": peak_load_cap_p,
            "imp_price_p": imp_price_p,
            "exp_price_p": exp_price_p,
            "soc0_p": soc0_p,
            "headroom_p": headroom_p,
            "cliff_pen_p": cliff_pen_p,
            "bkp_cost_p": bkp_cost_p,
            "p_imp": p_imp,
            "p_exp": p_exp,
            "p_ch": p_ch,
            "p_dis": p_dis,
            "p_curt": p_curt,
            "p_bkp": p_bkp,
            "soc": soc,
            "s_cliff": s_cliff,
        }
        self._dpp_cache[H] = bundle
        return bundle

    @classmethod
    def get_active_slab_ceiling_kwh(
        cls,
        prior_month_to_date_import_kwh: float,
        is_protected_consumer: bool = True,
        protected_guardrail_kwh: float = 195.0,
    ) -> float:
        """
        Determines the active monthly cumulative grid-import ceiling (kWh) to defend:
          - For Protected consumers below the guardrail, defends `protected_guardrail_kwh`
            (default 195.0 kWh, giving a 5 kWh safety buffer below the 200 kWh 6-month cliff).
          - Otherwise defends the next whole-bill landing-slab boundary (100, 200, 300, ..., 700 kWh).
        """
        if is_protected_consumer and prior_month_to_date_import_kwh <= 200.0:
            if prior_month_to_date_import_kwh <= protected_guardrail_kwh:
                return float(protected_guardrail_kwh)
            return 200.0
        for bound in cls.SLAB_BOUNDARIES_KWH:
            if prior_month_to_date_import_kwh < bound:
                return float(bound)
        return float(prior_month_to_date_import_kwh + 100.0)

    def optimize_24h(
        self,
        load_kw: Sequence[float] | npt.ArrayLike,
        solar_kw: Sequence[float] | npt.ArrayLike,
        month: int,
        regime: ProsumerRegime2026 = ProsumerRegime2026.NET_BILLING_2026,
        outage_mask: Optional[Sequence[float] | npt.ArrayLike] = None,
        initial_soc_kwh: Optional[float] = None,
        prior_month_to_date_import_kwh: float = 0.0,
        is_protected_consumer: bool = True,
        protected_guardrail_kwh: float = 195.0,
        slab_ceiling_override_kwh: Optional[float] = None,
        include_electricity_duty: bool = False,
        backup_gen_cost_pkr_per_kwh: float = 95.0,
        export_rate_override_pkr_per_kwh: Optional[float] = None,
        netting_headroom_kwh: Optional[float] = None,
    ) -> Lesco2026DispatchResultDTO:
        """
        Solves the 24-hour MILP battery dispatch problem under the specified CY 2026 LESCO regime.
        Strictly enforces all physical laws:
          - Zero Nocturnal Solar Leakage
          - Anti-Islanding Blackout Isolation (p_grid_import == 0 and p_grid_export == 0 when outage == 1)
          - Post-Blackout Peak Recharge Suppression (no grid battery charging during seasonal Peak hours)
          - Mutual exclusivity of charging and discharging
        """
        t0 = time.perf_counter()
        H = len(load_kw)
        load_vec = np.asarray(load_kw, dtype=np.float64).reshape(H)
        solar_raw = np.asarray(solar_kw, dtype=np.float64).reshape(H)

        # Law 1: Zero nocturnal solar leakage (20:00-04:00 PKT or negative values)
        hours = np.arange(H, dtype=np.int64) % 24
        night_mask = (hours >= 20) | (hours <= 4)
        solar_vec = np.where(night_mask | (solar_raw <= 0.0), 0.0, (np.minimum(solar_raw, self.pv_capacity_kw) if self.pv_capacity_kw else solar_raw))

        if outage_mask is None:
            outage_vec = np.zeros(H, dtype=np.float64)
        else:
            outage_vec = (np.asarray(outage_mask, dtype=np.float64).reshape(H) > 0.5).astype(np.float64)
        live_vec = 1.0 - outage_vec

        seasonal_window = self.tariff_engine.get_seasonal_window(month)
        peak_mask = self.tariff_engine.build_24h_seasonal_peak_mask(month, start_hour=0, horizon=H)
        off_peak_mask = 1.0 - peak_mask

        soc0 = float(
            np.clip(
                initial_soc_kwh if initial_soc_kwh is not None else 0.50 * self.bess.capacity_kwh,
                self.bess.min_soc_kwh,
                self.bess.max_soc_kwh,
            )
        )

        # Hourly import & export price vectors (PKR/kWh)
        peak_all_in, off_all_in = self.tariff_engine.get_all_in_tou_marginal_rates_pkr(
            include_electricity_duty=include_electricity_duty,
            include_fpa_marginal=True,
        )

        export_value = self.tariff_engine.marginal_value_of_exported_kwh(
            regime,
            netting_headroom_kwh=netting_headroom_kwh,
            export_rate_override_pkr_per_kwh=export_rate_override_pkr_per_kwh,
            include_electricity_duty=include_electricity_duty,
        )

        if regime == ProsumerRegime2026.NET_BILLING_2026:
            import_price_vec = np.where(peak_mask > 0.5, float(peak_all_in), float(off_all_in))
            export_price_vec = np.full(H, float(export_value))
            allow_export = 1.0
            slab_ceiling: Optional[float] = None
            cliff_penalty_per_kwh = 0.0
        elif regime == ProsumerRegime2026.GRANDFATHERED_NET_METERING:
            import_price_vec = np.where(peak_mask > 0.5, float(peak_all_in), float(off_all_in))
            # Under 1:1 Off-Peak netting, exported units offset Off-Peak imports (valued above NAEPP,
            # at NAPPP/Off-Peak banking value, but strictly below Peak import rate so battery still
            # prioritizes covering the 4-hour seasonal Peak window).
            export_price_vec = np.full(H, float(export_value))
            allow_export = 1.0
            slab_ceiling = None
            cliff_penalty_per_kwh = 0.0
        elif regime == ProsumerRegime2026.SINGLE_PHASE_SLAB_ZERO_EXPORT:
            slab_ceiling = (
                float(slab_ceiling_override_kwh)
                if slab_ceiling_override_kwh is not None
                else self.get_active_slab_ceiling_kwh(
                    prior_month_to_date_import_kwh=prior_month_to_date_import_kwh,
                    is_protected_consumer=is_protected_consumer,
                    protected_guardrail_kwh=protected_guardrail_kwh,
                )
            )
            # Determine base marginal slab rate
            est_cat = (
                ConsumerCategory2026.PROTECTED
                if (is_protected_consumer and prior_month_to_date_import_kwh <= 200.0)
                else ConsumerCategory2026.UNPROTECTED
            )
            bracket = self.tariff_engine.get_slab_bracket(est_cat, max(prior_month_to_date_import_kwh, 1.0))
            base_var = float(bracket.variable_rate_pkr_per_kwh)
            cfg_ = self.tariff_engine.config
            all_in_slab = float(
                (
                    bracket.variable_rate_pkr_per_kwh
                    + bracket.fc_surcharge_pkr_per_kwh
                    + cfg_.qta_rate_pkr_per_kwh
                    + cfg_.fca_rate_pkr_per_kwh
                )
                * (Decimal("1") + cfg_.gst_rate)
            )
            # Slight evening preference so battery naturally covers evening household peaks
            import_price_vec = np.where(peak_mask > 0.5, all_in_slab + 1.50, all_in_slab)
            export_price_vec = np.zeros(H, dtype=np.float64)
            allow_export = 0.0
            # Step-function cliff penalty for crossing the 200-unit Protected guardrail or whole-bill slab boundary
            # Crossing 200 kWh costs ~Rs 4,000+ per month for 6 consecutive months; crossing 300->301 kWh jumps
            # the entire 300 kWh base bill by Rs 1,044.46 (+18% GST).
            cliff_penalty_per_kwh = 1200.0 if slab_ceiling <= 200.0 else 450.0
        else:
            import_price_vec = np.where(peak_mask > 0.5, float(peak_all_in), float(off_all_in))
            export_price_vec = np.zeros(H, dtype=np.float64)
            allow_export = 0.0
            slab_ceiling = None
            cliff_penalty_per_kwh = 0.0

        # Populate cached DPP Parameters & solve via HiGHS
        bundle = self._get_dpp_bundle(H)
        bundle["load_p"].value = load_vec
        bundle["solar_p"].value = solar_vec
        bundle["live_p"].value = live_vec
        bundle["outage_p"].value = outage_vec
        bundle["allow_exp_p"].value = live_vec * allow_export
        bundle["peak_mask_p"].value = peak_mask
        bundle["peak_solar_cap_p"].value = np.where(
            peak_mask > 0.5, solar_vec, float(self.bess.max_charge_kw)
        )
        bundle["peak_load_cap_p"].value = np.where(
            peak_mask > 0.5, load_vec, 50.0
        )
        bundle["imp_price_p"].value = import_price_vec
        bundle["exp_price_p"].value = export_price_vec
        bundle["soc0_p"].value = soc0
        if slab_ceiling is not None:
            bundle["headroom_p"].value = max(0.0, float(slab_ceiling) - float(prior_month_to_date_import_kwh))
            bundle["cliff_pen_p"].value = cliff_penalty_per_kwh
        else:
            bundle["headroom_p"].value = 1e6
            bundle["cliff_pen_p"].value = 0.0
        bundle["bkp_cost_p"].value = float(backup_gen_cost_pkr_per_kwh)

        wear_rate = float(self.bess.degradation_cost_pkr_per_kwh)
        prob = bundle["prob"]
        prob.solve(solver=cp.HIGHS, warm_start=True)
        solve_ms = (time.perf_counter() - t0) * 1000.0

        p_imp = bundle["p_imp"]
        p_exp = bundle["p_exp"]
        p_ch = bundle["p_ch"]
        p_dis = bundle["p_dis"]
        p_curt = bundle["p_curt"]
        p_bkp = bundle["p_bkp"]
        soc = bundle["soc"]
        s_cliff = bundle["s_cliff"]

        if prob.status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE) and prob.value is not None:
            imp_v = np.maximum(np.asarray(p_imp.value, dtype=np.float64), 0.0)
            exp_v = np.maximum(np.asarray(p_exp.value, dtype=np.float64), 0.0)
            ch_v = np.maximum(np.asarray(p_ch.value, dtype=np.float64), 0.0)
            dis_v = np.maximum(np.asarray(p_dis.value, dtype=np.float64), 0.0)
            curt_v = np.maximum(np.asarray(p_curt.value, dtype=np.float64), 0.0)
            bkp_v = np.maximum(np.asarray(p_bkp.value, dtype=np.float64), 0.0)
            soc_v = np.clip(np.asarray(soc.value, dtype=np.float64), self.bess.min_soc_kwh, self.bess.max_soc_kwh)
            cliff_v = max(float(s_cliff.value or 0.0), 0.0)
            status_str = str(prob.status)
        else:
            # Deterministic safe fallback
            imp_v = np.where(live_vec > 0.5, np.maximum(load_vec - solar_vec, 0.0), 0.0)
            exp_v = np.where((live_vec > 0.5) & (allow_export > 0.5), np.maximum(solar_vec - load_vec, 0.0), 0.0)
            ch_v = np.zeros(H, dtype=np.float64)
            dis_v = np.zeros(H, dtype=np.float64)
            curt_v = np.where(
                (outage_vec > 0.5) | (allow_export < 0.5),
                np.maximum(solar_vec - load_vec, 0.0),
                0.0,
            )
            bkp_v = np.where(outage_vec > 0.5, np.maximum(load_vec - solar_vec, 0.0), 0.0)
            soc_v = np.full(H + 1, soc0, dtype=np.float64)
            cliff_v = 0.0
            status_str = "FALLBACK"

        # Clean micro-numerical solver noise (< 1e-7)
        imp_v[imp_v < 1e-7] = 0.0
        exp_v[exp_v < 1e-7] = 0.0
        ch_v[ch_v < 1e-7] = 0.0
        dis_v[dis_v < 1e-7] = 0.0
        curt_v[curt_v < 1e-7] = 0.0
        bkp_v[bkp_v < 1e-7] = 0.0

        proj_mtd_import = float(prior_month_to_date_import_kwh + float(np.sum(imp_v)))
        guardrail_ok = proj_mtd_import <= 200.0 + 1e-6

        imp_cost_pkr = _round_pkr(_d(float(np.dot(import_price_vec, imp_v))))
        exp_rev_pkr = _round_pkr(_d(float(np.dot(export_price_vec, exp_v))))
        cliff_pen_pkr = _round_pkr(_d(cliff_penalty_per_kwh * cliff_v))
        wear_pkr = _round_pkr(_d(wear_rate * float(np.sum(ch_v + dis_v))))
        bkp_pkr = _round_pkr(_d(backup_gen_cost_pkr_per_kwh * float(np.sum(bkp_v))))
        net_cost_pkr = imp_cost_pkr - exp_rev_pkr + cliff_pen_pkr + wear_pkr + bkp_pkr

        # Counterfactual: same day, no battery, same tariff & export valuation
        deficit = np.maximum(load_vec - solar_vec, 0.0)
        surplus = np.maximum(solar_vec - load_vec, 0.0)
        base_imp = np.dot(import_price_vec, deficit * live_vec)
        base_exp = np.dot(export_price_vec, surplus * live_vec * allow_export)
        base_bkp = backup_gen_cost_pkr_per_kwh * float(np.sum(deficit * outage_vec))
        baseline_pkr = _round_pkr(_d(float(base_imp - base_exp + base_bkp)))
        savings_pkr = baseline_pkr - net_cost_pkr

        return Lesco2026DispatchResultDTO(
            regime=regime,
            season=seasonal_window.season,
            status=status_str,
            solve_time_ms=round(solve_ms, 3),
            p_grid_import_kw=_ro_vec(imp_v, H),
            p_grid_export_kw=_ro_vec(exp_v, H),
            p_ch_kw=_ro_vec(ch_v, H),
            p_dis_kw=_ro_vec(dis_v, H),
            p_curtail_kw=_ro_vec(curt_v, H),
            p_backup_kw=_ro_vec(bkp_v, H),
            soc_kwh=_ro_vec(soc_v, H + 1),
            is_peak_mask=peak_mask,
            initial_soc_kwh=float(soc_v[0]),
            terminal_soc_kwh=float(soc_v[-1]),
            prior_month_to_date_import_kwh=float(prior_month_to_date_import_kwh),
            projected_month_to_date_import_kwh=round(proj_mtd_import, 4),
            slab_ceiling_target_kwh=slab_ceiling,
            protected_200_guardrail_intact=guardrail_ok,
            import_energy_cost_pkr=imp_cost_pkr,
            export_revenue_credit_pkr=exp_rev_pkr,
            slab_cliff_penalty_pkr=cliff_pen_pkr,
            battery_wear_cost_pkr=wear_pkr,
            net_horizon_cost_pkr=net_cost_pkr,
            export_rate_used_pkr_per_kwh=_round_pkr(_d(float(export_value))),
            baseline_no_battery_cost_pkr=baseline_pkr,
            net_savings_pkr=savings_pkr,
        )

