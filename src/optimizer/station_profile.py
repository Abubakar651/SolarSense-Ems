"""
Per-customer prosumer profile (nothing about a specific house is hard-coded in solver/API code).
Loaded once at API startup; individual requests may override any field.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.optimizer.lesco_2026_tariff_and_dispatch import ProsumerRegime2026

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PROFILE_PATH = PROJECT_ROOT / "docs" / "station_profile_lhr_res_01.json"


@dataclass(frozen=True, slots=True)
class StationProfile:
    station_id: str
    regime: ProsumerRegime2026
    sanctioned_load_kw: float
    pv_capacity_kw: Optional[float]
    is_atl_filer: bool
    include_electricity_duty: bool
    is_protected_consumer: bool
    protected_guardrail_kwh: float
    export_rate_override_pkr_per_kwh: Optional[float]


def load_station_profile(path: Path = DEFAULT_PROFILE_PATH) -> StationProfile:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    override = raw.get("export_rate_override_pkr_per_kwh")
    pv = raw.get("pv_capacity_kw")
    return StationProfile(
        station_id=str(raw["station_id"]),
        regime=ProsumerRegime2026(raw["regime"]),
        sanctioned_load_kw=float(raw["sanctioned_load_kw"]),
        pv_capacity_kw=float(pv) if pv is not None else None,
        is_atl_filer=bool(raw["is_atl_filer"]),
        include_electricity_duty=bool(raw["include_electricity_duty"]),
        is_protected_consumer=bool(raw["is_protected_consumer"]),
        protected_guardrail_kwh=float(raw["protected_guardrail_kwh"]),
        export_rate_override_pkr_per_kwh=float(override) if override is not None else None,
    )
