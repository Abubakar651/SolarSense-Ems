"""
Sizes a user's plan from their own site: their battery, backup reserve and array, not the station's.

The forecasters learned the station's 7.02 kWp array, so forecast solar is scaled to the user's kWp.
The dispatch optimizer compiles its battery limits into the solver problem, so there is one optimizer
per (battery, array) pair, built on first use and kept in a small LRU pool.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass, replace
import threading

import numpy as np
import numpy.typing as npt

from src.forecast.live_forecast import TelemetrySample
from src.forecast.train_solar_pv import RESIDENTIAL_ARRAY_KWP
from src.optimizer.lesco_2026_tariff_and_dispatch import (
    Lesco2026BatteryDispatchOptimizer,
    LescoCY2026TariffEngine,
)
from src.optimizer.milp_solver import BESSConfig

_STATION_BATTERY = BESSConfig.station_residential()
# Sites don't record their battery's power rating; assume the station pack's C-rate (5.0 kW on 5.12 kWh).
_STATION_C_RATE = _STATION_BATTERY.max_charge_kw / _STATION_BATTERY.capacity_kwh


@dataclass(frozen=True, slots=True)
class SiteSizes:
    pv_kwp: float
    battery_kwh: float
    # The user's "keep at least X% for outages" setting (15-100, enforced by the sites table).
    reserve_pct: int


def battery_for(sizes: SiteSizes) -> BESSConfig:
    """The station battery's chemistry and costs at the user's capacity, power and reserve floor."""
    power_kw = sizes.battery_kwh * _STATION_C_RATE
    return replace(
        _STATION_BATTERY,
        capacity_kwh=sizes.battery_kwh,
        max_charge_kw=power_kw,
        max_discharge_kw=power_kw,
        min_soc_pct=sizes.reserve_pct / 100.0,
    )


def scale_solar(station_solar_kw: npt.NDArray[np.float64], pv_kwp: float) -> npt.NDArray[np.float64]:
    """Forecast output of the user's array: the station forecast scaled by array size (zero stays zero)."""
    scaled = np.ascontiguousarray(station_solar_kw * (pv_kwp / RESIDENTIAL_ARRAY_KWP), dtype=np.float64)
    scaled.setflags(write=False)
    return scaled


def to_station_scale(samples: Sequence[TelemetrySample], pv_kwp: float) -> list[TelemetrySample]:
    """The site's logged solar as the station's array would have produced it (the forecasters' scale)."""
    factor = RESIDENTIAL_ARRAY_KWP / pv_kwp
    return [replace(s, pv_power_w=s.pv_power_w * factor) for s in samples]


class OptimizerPool:
    """One dispatch optimizer per (battery, array) pair, least recently used evicted past `max_size`."""

    def __init__(self, tariff_engine: LescoCY2026TariffEngine, max_size: int = 64) -> None:
        self._engine = tariff_engine
        self._max_size = max_size
        self._pool: OrderedDict[tuple[BESSConfig, float], Lesco2026BatteryDispatchOptimizer] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, sizes: SiteSizes) -> Lesco2026BatteryDispatchOptimizer:
        key = (battery_for(sizes), sizes.pv_kwp)
        with self._lock:
            optimizer = self._pool.get(key)
            if optimizer is not None:
                self._pool.move_to_end(key)
                return optimizer
            optimizer = Lesco2026BatteryDispatchOptimizer(
                tariff_engine=self._engine, bess=key[0], pv_capacity_kw=sizes.pv_kwp
            )
            self._pool[key] = optimizer
            if len(self._pool) > self._max_size:
                self._pool.popitem(last=False)
            return optimizer
