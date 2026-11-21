"""
A site's tariff from its saved settings, priced through the CY 2026 tariff engine: the rates its logged energy
is valued at, and what its month's grid use is billed. Nothing here is a fixed rate; every figure comes from
the engine's configuration at the site's category, regime and options. Pure: the engine is passed in.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

import numpy as np

from src.api.user_site import UserSite
from src.optimizer.lesco_2026_tariff_and_dispatch import (
    ConsumerCategory2026,
    LescoCY2026TariffEngine,
    ProsumerRegime2026,
)

_PROSUMER_REGIMES = (ProsumerRegime2026.NET_BILLING_2026, ProsumerRegime2026.GRANDFATHERED_NET_METERING)
_SLAB_CATEGORIES = (ConsumerCategory2026.LIFELINE, ConsumerCategory2026.PROTECTED, ConsumerCategory2026.UNPROTECTED)


def _round_pkr(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True, slots=True)
class EnergyRates:
    """PKR per kWh, all-in (surcharges and GST included)."""

    # What a kWh of the site's own solar used at home saves: the import it avoids (solar hours are Off-Peak).
    self_consumed_pkr_per_kwh: Decimal
    # What the regime credits for a kWh sent to the grid (0 where export isn't allowed or metered).
    export_pkr_per_kwh: Decimal


@dataclass(frozen=True, slots=True)
class MonthFlows:
    """One month's metered energy (kWh) and the share of it that fell in the seasonal peak window."""

    import_kwh: float
    export_kwh: float
    load_kwh: float
    import_peak_share: float
    load_peak_share: float


@dataclass(frozen=True, slots=True)
class MonthCost:
    # The month's bill as metered (after the regime's export credits), and with the same usage all bought.
    cost_pkr: Decimal
    without_solar_pkr: Decimal


def _regime(site: UserSite) -> ProsumerRegime2026:
    return ProsumerRegime2026(site.prosumer_regime)


def _category(site: UserSite) -> ConsumerCategory2026:
    return ConsumerCategory2026(site.tariff_category)


def _off_peak_rate(engine: LescoCY2026TariffEngine, site: UserSite, month_import_kwh: float) -> Decimal:
    category = _category(site)
    if _regime(site) not in _PROSUMER_REGIMES and category in _SLAB_CATEGORIES:
        return engine.all_in_slab_rate_pkr(category, max(month_import_kwh, 1.0))
    if _regime(site) not in _PROSUMER_REGIMES and category == ConsumerCategory2026.PREPAID_A1C:
        cfg = engine.config
        return (
            cfg.prepaid_variable_rate_pkr_per_kwh
            + cfg.prepaid_fc_surcharge_pkr_per_kwh
            + cfg.qta_rate_pkr_per_kwh
            + cfg.fca_rate_pkr_per_kwh
        ) * (Decimal("1") + cfg.gst_rate)
    _, off_peak = engine.get_all_in_tou_marginal_rates_pkr(
        include_electricity_duty=site.include_electricity_duty, include_fpa_marginal=True
    )
    return off_peak


def export_credit_rate(
    engine: LescoCY2026TariffEngine, site: UserSite, station_export_override_pkr_per_kwh: float | None
) -> Decimal:
    """
    The regime's credit for an exported kWh: NAEPP under net-billing, NAPPP (or the station owner's contract
    rate) under grandfathered net-metering, 0 under zero-export. Exports that cancel Off-Peak imports 1:1 are
    worth more; month_cost settles that properly.
    """
    regime = _regime(site)
    cfg = engine.config
    if regime == ProsumerRegime2026.NET_BILLING_2026:
        return cfg.naepp_export_rate_pkr_per_kwh
    if regime == ProsumerRegime2026.GRANDFATHERED_NET_METERING:
        if site.is_station and station_export_override_pkr_per_kwh is not None:
            return _round_pkr(Decimal(str(station_export_override_pkr_per_kwh)))
        return cfg.nappp_grandfathered_rate_pkr_per_kwh
    return Decimal("0.00")


def energy_rates(
    engine: LescoCY2026TariffEngine,
    site: UserSite,
    month_import_kwh: float,
    station_export_override_pkr_per_kwh: float | None,
) -> EnergyRates:
    """The site's rates; a slab tariff's rate depends on the month's imports so far (its landing slab)."""
    return EnergyRates(
        self_consumed_pkr_per_kwh=_round_pkr(_off_peak_rate(engine, site, month_import_kwh)),
        export_pkr_per_kwh=export_credit_rate(engine, site, station_export_override_pkr_per_kwh),
    )


def _split(kwh: float, peak_share: float) -> tuple[Decimal, Decimal]:
    peak = Decimal(str(round(kwh * peak_share, 4)))
    return peak, Decimal(str(round(kwh, 4))) - peak


def month_cost(engine: LescoCY2026TariffEngine, site: UserSite, flows: MonthFlows) -> MonthCost:
    """
    The month's LESCO bill (fixed charges and taxes included) for what was metered, and for the same usage
    bought entirely from the grid. Prosumers settle through the regime's netting and export credit; every
    other site is billed its imports on its own category, and its exports earn nothing.
    """
    regime = _regime(site)
    load_peak, load_off = _split(flows.load_kwh, flows.load_peak_share)
    if regime in _PROSUMER_REGIMES:
        imp_peak, imp_off = _split(flows.import_kwh, flows.import_peak_share)
        settled = engine.calculate_prosumer_settlement(
            regime=regime,
            sanctioned_load_kw=site.sanctioned_load_kw,
            gross_peak_import_kwh=imp_peak,
            gross_off_peak_import_kwh=imp_off,
            gross_export_kwh=Decimal(str(round(flows.export_kwh, 4))),
            include_electricity_duty=site.include_electricity_duty,
            is_atl_filer=site.is_atl_filer,
        )
        cost = settled.net_payable_after_credits_pkr
        category = ConsumerCategory2026.TOU_A1B
    else:
        category = _category(site)
        imp_peak, imp_off = _split(flows.import_kwh, flows.import_peak_share)
        cost = engine.calculate_monthly_bill(
            category=category,
            sanctioned_load_kw=site.sanctioned_load_kw,
            current_kwh=imp_peak + imp_off,
            peak_kwh=imp_peak,
            off_peak_kwh=imp_off,
            include_electricity_duty=site.include_electricity_duty,
            is_atl_filer=site.is_atl_filer,
        ).total_payable_pkr
    without = engine.calculate_monthly_bill(
        category=category,
        sanctioned_load_kw=site.sanctioned_load_kw,
        current_kwh=load_peak + load_off,
        peak_kwh=load_peak,
        off_peak_kwh=load_off,
        include_electricity_duty=site.include_electricity_duty,
        is_atl_filer=site.is_atl_filer,
    ).total_payable_pkr
    return MonthCost(cost_pkr=_round_pkr(cost), without_solar_pkr=_round_pkr(without))


def peak_shares(
    engine: LescoCY2026TariffEngine,
    month: int,
    hours: Sequence[int],
    import_kw: Sequence[float],
    load_kw: Sequence[float],
) -> tuple[float, float]:
    """
    Shares of the month's import and load that fell in its seasonal peak window, from hourly rows of that
    month (hour of day, mean kW = kWh). With no hourly rows everything counts as Off-Peak.
    """
    window = engine.get_seasonal_window(month)
    hour = np.asarray(hours, dtype=np.int64)
    in_peak = (hour >= window.peak_start_hour) & (hour < window.peak_end_hour)

    def share(values: Sequence[float]) -> float:
        kw = np.asarray(values, dtype=np.float64)
        total = float(kw.sum())
        return float(kw[in_peak].sum()) / total if total > 0.0 else 0.0

    return share(import_kw), share(load_kw)
