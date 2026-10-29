"""
SolarSense EMS — FastAPI Pydantic V2 Request & Response Schemas
==============================================================
Type-safe API contracts for Next.js frontend and Phase 2 AI Agents.
Enforces strict validation, automatic OpenAPI schema generation,
and high-speed JSON serialization.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PresetDateItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    date: str
    label: str
    category: str
    description: str


class DateBoundsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    min_date: str
    max_date: str
    total_days: int
    total_hours: int
    preset_dates: List[PresetDateItem]


class SoilingStatusResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    date: str
    plant_capacity_kw: float
    total_panels: int
    panel_rating_w: float
    actual_generation_kwh: float
    expected_clean_kwh: float
    performance_ratio: float
    soiling_derate_pct: float
    daily_kwh_lost: float
    daily_revenue_lost_pkr: float
    days_since_last_wash: Optional[int] = None
    event_type: str
    days_until_next_rain: int
    projected_loss_before_rain_pkr: float
    wash_cost_pkr: float
    net_cleaning_benefit_pkr: float
    decision: str


class VisionSampleItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    sample_id: str
    ground_truth_class: str
    sample_path: str
    label: str


class VisionSamplesResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_samples: int
    classes: List[str]
    samples: List[VisionSampleItem]


class VisionInspectRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    sample_path: Optional[str] = Field(
        default="data/processed/panel_images/solarsense_master_v1/test/dusty/dusty_test_0001.jpg",
        description="Relative path to panel image inside data/processed/panel_images/",
    )
    base64_image: Optional[str] = Field(
        default=None,
        description="Optional base64-encoded RGB image payload (overrides sample_path if provided)",
    )
    use_tta: bool = Field(
        default=True,
        description="Enable 4-pass Test-Time Augmentation (TTA)",
    )
    days_until_rain: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Forecasted dry days until next rainfall for ROI calculation",
    )


class VisionInspectResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    condition: str
    confidence: float
    severity: str
    requires_cleaning: bool
    estimated_derate_pr: float
    all_probabilities: Dict[str, float]
    estimated_daily_kwh_lost: float
    estimated_daily_pkr_lost: float
    projected_loss_before_rain_pkr: float
    wash_cost_pkr: float
    recommended_action: str
    inference_time_ms: float


class AgentAdvisoryRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    date_str: str = Field(
        default="2026-09-23",
        description="Target date in YYYY-MM-DD format",
        examples=["2026-09-23"],
    )
    use_forecasts: bool = Field(
        default=False,
        description="True = ML forecasted vectors; False = ground truth",
    )
    days_until_rain: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Forecasted dry days until next rainfall",
    )
    defect_condition: Optional[str] = Field(
        default=None,
        description="Optional CV defect class override (clean, dusty, bird_drop, electrical_damage, physical_damage)",
    )


class AgentAdvisoryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    date: str
    station_id: str
    headline: str
    dispatch_arbitrage_brief: str
    blackout_resilience_brief: str
    soiling_maintenance_brief: str
    recommended_actions: List[str]
    key_metrics: Dict[str, float]
    generation_mode: str
    latency_ms: float


class SimulationWindowResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    date: str
    horizon_hours: int
    timestamps: List[str]
    hours: List[int]
    solar_generation_kw: List[float]
    factory_load_kw: List[float]
    net_power_kw: List[float]
    tariff_rates_pkr: List[float]
    tariff_windows: List[str]
    outage_flags: List[int]
    baseline_electricity_cost_pkr: float
    baseline_mdi_penalty_pkr: float
    total_baseline_cost_pkr: float
    ghi_wm2: List[float]
    temp_c: List[float]


class OptimizationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    date_str: str = Field(..., description="Target date in YYYY-MM-DD format", examples=["2025-07-17"])
    use_forecasts: bool = Field(default=False, description="True = ML forecasted vectors; False = ground truth")
    initial_soc_kwh: Optional[float] = Field(default=None, description="Optional battery initial SoC override (kWh)")
    mdi_high_water_kw: Optional[float] = Field(default=None, description="Optional monthly MDI ratchet override (kW)")
    off_peak_rate_pkr: Optional[float] = Field(default=None, description="Optional off-peak tariff override (PKR/kWh)")
    peak_rate_pkr: Optional[float] = Field(default=None, description="Optional peak tariff override (PKR/kWh)")
    diesel_cost_pkr: Optional[float] = Field(default=None, description="Optional diesel fuel cost override (PKR/kWh)")


class OptimizationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    window_start: str
    status: str
    solve_time_ms: float
    timestamps: List[str]
    solar_kw: List[float]
    factory_load_kw: List[float]
    p_grid_kw: List[float]
    p_export_kw: List[float] = Field(default_factory=list)
    p_diesel_kw: List[float]
    p_ch_kw: List[float]
    p_dis_kw: List[float]
    p_curtail_kw: List[float]
    soc_kwh: List[float]
    initial_soc_kwh: float
    terminal_soc_kwh: float
    prior_mdi_high_water_kw: float
    updated_mdi_high_water_kw: float
    baseline_energy_pkr: float
    baseline_diesel_pkr: float
    baseline_mdi_penalty_pkr: float
    baseline_total_pkr: float
    optimized_energy_pkr: float
    export_revenue_pkr: float = 0.0
    optimized_diesel_pkr: float
    optimized_mdi_penalty_pkr: float
    degradation_cost_pkr: float
    optimized_total_pkr: float
    net_savings_pkr: float
    savings_pct: float
    mdi_penalty_saved_pkr: float
    diesel_cost_saved_pkr: float


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    app_name: str
    version: str
    dataset_rows: int
    date_range_start: str
    date_range_end: str
    solver_warmed_up: bool


# =====================================================================
# CY 2026 LESCO Tariff / Prosumer Dispatch (v2) Contracts
# =====================================================================

class Lesco2026OptimizeRequest(BaseModel):
    """24h dispatch request under CY 2026 LESCO rules (default: grandfathered net-metering)."""
    model_config = ConfigDict(frozen=True)

    date_str: str = Field(..., description="Target date YYYY-MM-DD", examples=["2025-07-17"])
    regime: str = Field(
        default="GRANDFATHERED_NET_METERING",
        description="NET_BILLING_2026 | GRANDFATHERED_NET_METERING | SINGLE_PHASE_SLAB_ZERO_EXPORT",
    )
    use_forecasts: bool = False
    initial_soc_kwh: Optional[float] = Field(default=None, ge=0.0)
    prior_month_to_date_import_kwh: float = Field(default=0.0, ge=0.0)
    is_protected_consumer: bool = True
    protected_guardrail_kwh: float = Field(default=195.0, gt=0.0)
    include_electricity_duty: bool = False


class Lesco2026OptimizeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    regime: str
    season: str
    status: str
    solve_time_ms: float
    timestamps: List[str]
    solar_kw: List[float]
    load_kw: List[float]
    outage_flags: List[int]
    is_peak: List[int]
    p_grid_import_kw: List[float]
    p_grid_export_kw: List[float]
    p_ch_kw: List[float]
    p_dis_kw: List[float]
    p_curtail_kw: List[float]
    p_backup_kw: List[float]
    soc_kwh: List[float]
    initial_soc_kwh: float
    terminal_soc_kwh: float
    projected_month_to_date_import_kwh: float
    slab_ceiling_target_kwh: Optional[float]
    protected_200_guardrail_intact: bool
    import_energy_cost_pkr: str
    export_revenue_credit_pkr: str
    slab_cliff_penalty_pkr: str
    battery_wear_cost_pkr: str
    net_horizon_cost_pkr: str
    export_rate_used_pkr_per_kwh: str = "0.00"
    baseline_no_battery_cost_pkr: str = "0.00"
    net_savings_pkr: str = "0.00"


class BillEstimateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: str = Field(..., description="LIFELINE | PROTECTED | UNPROTECTED | TOU_A1B | PREPAID_A1C")
    sanctioned_load_kw: float = Field(..., gt=0.0)
    current_kwh: float = Field(default=0.0, ge=0.0)
    peak_kwh: float = Field(default=0.0, ge=0.0)
    off_peak_kwh: float = Field(default=0.0, ge=0.0)
    fpa_reference_2m_prior_kwh: float = Field(default=0.0, ge=0.0)
    include_electricity_duty: bool = False
    is_atl_filer: bool = True


class BillEstimateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: str
    slab_id: str
    current_total_kwh: str
    line_items: Dict[str, str]
    total_payable_pkr: str
    total_payable_rounded_rupee_pkr: str
    effective_all_in_rate_pkr_per_kwh: str


class PeakWindowResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    month: int
    season: str
    peak_start_hour: int
    peak_end_hour: int
    peak_hours: List[int]


class ProsumerCompareRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    sanctioned_load_kw: float = Field(default=10.0, gt=0.0)
    gross_peak_import_kwh: float = Field(..., ge=0.0)
    gross_off_peak_import_kwh: float = Field(..., ge=0.0)
    gross_export_kwh: float = Field(..., ge=0.0)
    fpa_reference_2m_prior_kwh: float = Field(default=0.0, ge=0.0)
    include_electricity_duty: bool = False
    is_atl_filer: bool = True


class ProsumerSettlementItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    regime: str
    net_billed_peak_import_kwh: str
    net_billed_off_peak_import_kwh: str
    net_surplus_export_kwh: str
    export_credit_rate_pkr_per_kwh: str
    gross_retail_import_bill_pkr: str
    export_credit_pkr: str
    net_payable_after_credits_pkr: str
    closing_credit_carryforward_pkr: str


class ProsumerCompareResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    grandfathered: ProsumerSettlementItem
    net_billing_2026: ProsumerSettlementItem
    grandfathered_advantage_pkr: str
