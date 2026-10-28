"""
SolarSense EMS — FastAPI Pydantic V2 Request & Response Schemas
==============================================================
Type-safe API contracts for Next.js frontend and Phase 2 AI Agents.
Enforces strict validation, automatic OpenAPI schema generation,
and high-speed JSON serialization.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


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
