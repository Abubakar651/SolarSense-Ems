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
