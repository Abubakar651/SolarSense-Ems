"""
One site's history for the Savings, Reports and Outage screens (Panels: src/api/site_soiling.py).

The station site (UserSite.is_station) gets the recorded dataset followed by whatever its own log adds
after the dataset ends. Every other site gets only its own logged samples, so no tenant ever sees another
site's data. Pure: samples and dates come from the caller.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import polars as pl

from src.api import insights
from src.api.insights import EnergyHistoryOut, EnergyRatesOut, MonthCostOut, OutageHistoryOut
from src.api.site_tariff import MonthFlows, energy_rates, month_cost, peak_shares
from src.api.telemetry_history import daily_energy, hourly_energy, monthly_energy, outage_events
from src.api.user_site import UserSite
from src.data_engineering.feature_store import PKT_TZ
from src.forecast.live_forecast import TelemetrySample
from src.optimizer.lesco_2026_tariff_and_dispatch import LescoCY2026TariffEngine


def _local_days(samples: Sequence[TelemetrySample]) -> list[str]:
    return sorted({s.recorded_at.astimezone(PKT_TZ).date().isoformat() for s in samples})


def energy_for_site(site: UserSite, samples: Sequence[TelemetrySample], today: date) -> EnergyHistoryOut:
    logged = daily_energy(samples, before=today)
    logged_through = logged[-1].date if logged else None
    if not site.is_station:
        return EnergyHistoryOut(
            daily=logged,
            monthly=monthly_energy(logged)[-insights.METER_MONTHS :],
            monthly_history=monthly_energy(logged)[-insights.METER_HISTORY_MONTHS :],
            metered_through=logged_through,
            logged_through=logged_through,
            logged_days=len(logged),
        )

    recorded = insights.energy_history()
    cutoff = recorded.metered_through or ""
    new_days = [d for d in logged if d.date > cutoff]
    last_month = recorded.monthly[-1].month if recorded.monthly else ""
    new_months = [m for m in monthly_energy(new_days) if m.month > last_month]
    return EnergyHistoryOut(
        daily=[*recorded.daily, *new_days],
        monthly=[*recorded.monthly, *new_months][-insights.METER_MONTHS :],
        monthly_history=[*recorded.monthly_history, *new_months][-insights.METER_HISTORY_MONTHS :],
        metered_through=max(filter(None, (recorded.metered_through, logged_through))),
        recorded_through=recorded.metered_through,
        logged_through=logged_through,
        logged_days=len(logged),
        hourly_through=recorded.daily[-1].date if recorded.daily else None,
    )


def _month_hours(site: UserSite, history: EnergyHistoryOut, samples: Sequence[TelemetrySample], month: str) -> pl.DataFrame:
    """The month's hourly rows (hour, load_kw, import_kw): recorded for the station's recorded months, else logged."""
    if site.is_station and month <= (history.recorded_through or "")[:7]:
        recorded = insights.recorded_hourly_flows()
        return recorded.filter(pl.col("date").str.starts_with(month)).select(
            "hour", pl.col("residential_load_kw").alias("load_kw"), pl.col("grid_import_kw").alias("import_kw")
        )
    logged = hourly_energy(samples)
    return logged.filter(pl.col("date").dt.strftime("%Y-%m") == month).select(
        pl.col("hour").dt.hour().alias("hour"), "load_kw", "import_kw"
    )


def with_tariff(
    history: EnergyHistoryOut,
    site: UserSite,
    samples: Sequence[TelemetrySample],
    engine: LescoCY2026TariffEngine,
    station_export_override_pkr_per_kwh: float | None,
) -> EnergyHistoryOut:
    """
    The history with the site's tariff rates and its latest month's bill from the tariff engine, at the site's
    saved category, regime and options. The month's peak share comes from its hourly rows.
    """
    if not history.monthly:
        return history
    latest = history.monthly[-1]
    hours = _month_hours(site, history, samples, latest.month)
    import_share, load_share = peak_shares(
        engine, int(latest.month[5:7]), hours["hour"].to_list(), hours["import_kw"].to_list(), hours["load_kw"].to_list()
    )
    rates = energy_rates(engine, site, latest.purchased_kwh, station_export_override_pkr_per_kwh)
    cost = month_cost(
        engine,
        site,
        MonthFlows(
            import_kwh=latest.purchased_kwh,
            export_kwh=latest.sold_kwh,
            load_kwh=latest.load_kwh,
            import_peak_share=import_share,
            load_peak_share=load_share,
        ),
    )
    return history.model_copy(
        update={
            "rates": EnergyRatesOut(
                self_consumed_pkr_per_kwh=str(rates.self_consumed_pkr_per_kwh),
                export_pkr_per_kwh=str(rates.export_pkr_per_kwh),
            ),
            "current_month": MonthCostOut(
                month=latest.month, cost_pkr=str(cost.cost_pkr), without_solar_pkr=str(cost.without_solar_pkr)
            ),
        }
    )


def outages_for_site(site: UserSite, samples: Sequence[TelemetrySample]) -> OutageHistoryOut:
    logged = outage_events(samples)
    days = _local_days(samples)
    logged_through = days[-1] if days else None
    if not site.is_station:
        return OutageHistoryOut(
            period_start=days[0] if days else None,
            period_end=logged_through,
            events=logged,
            logged_through=logged_through,
            logged_days=len(days),
        )

    recorded = insights.outage_history()
    cutoff = recorded.period_end or ""
    return OutageHistoryOut(
        period_start=recorded.period_start,
        period_end=max(filter(None, (recorded.period_end, logged_through))),
        events=[*recorded.events, *(e for e in logged if e.date > cutoff)],
        recorded_through=recorded.period_end,
        logged_through=logged_through,
        logged_days=len(days),
    )
