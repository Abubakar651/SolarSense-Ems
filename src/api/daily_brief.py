"""
Today's written brief for one site, worded from its live plan, its tariff and its dust model.

Every figure in the text is computed here from:
- the site's live plan for today (POST /api/v2/plan/today: its forecast, battery, reserve and array),
- the tariff engine's peak window and all-in rates for the user's regime (the rates the plan was priced at),
- the plan's forecast outage risk and the blackout hours already logged today,
- the site's dust model (src/api/site_soiling.py) and the Lahore rain forecast (src/api/rain_forecast.py).
Nothing describes the station's hardware unless it is the user's own. The text is a fixed template filled in
with those figures (generation_mode "deterministic_template"); no language model writes it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Protocol, Union

from src.api.insights import DatasetUnavailable, SiteSoilingOut
from src.api.rain_forecast import RainForecastOut, RainUnavailable
from src.api.schemas import DailyBriefResponse, LivePlanResponse
from src.api.site_soiling import WASH_HORIZON_DAYS, SoilingCollectingError
from src.api.user_site import UserSite
from src.forecast.live_forecast import WeatherUnavailable
from src.optimizer.lesco_2026_tariff_and_dispatch import LescoCY2026TariffEngine, ProsumerRegime2026
from src.soiling.live_model import MIN_FIT_DAYS, SoilingCollecting

GENERATION_MODE = "deterministic_template"


class SoilingSource(Protocol):
    async def soiling(self, site: UserSite, now: datetime) -> tuple[SiteSoilingOut, object]: ...


class RainSource(Protocol):
    async def forecast(self, today: date) -> RainForecastOut: ...


@dataclass(frozen=True, slots=True)
class DustUnavailable:
    """The dust model could not be worked out (no sunlight data, or the recorded model is missing)."""


Dust = Union[SiteSoilingOut, SoilingCollecting, DustUnavailable]


@dataclass(frozen=True, slots=True)
class TariffFacts:
    regime: ProsumerRegime2026
    peak_start_hour: int
    peak_end_hour: int
    # All-in ToU rates the plan was priced at; None on the single-phase slab tariff, which has no peak price.
    peak_rate_pkr: Optional[Decimal]
    off_peak_rate_pkr: Optional[Decimal]


def tariff_facts(
    engine: LescoCY2026TariffEngine, regime: ProsumerRegime2026, month: int, include_electricity_duty: bool
) -> TariffFacts:
    """The peak window for `month` and the import rates the dispatch optimizer uses for this regime."""
    window = engine.get_seasonal_window(month)
    if regime == ProsumerRegime2026.SINGLE_PHASE_SLAB_ZERO_EXPORT:
        peak, off_peak = None, None
    else:
        peak, off_peak = engine.get_all_in_tou_marginal_rates_pkr(
            include_electricity_duty=include_electricity_duty, include_fpa_marginal=True
        )
    return TariffFacts(regime, window.peak_start_hour, window.peak_end_hour, peak, off_peak)


async def site_dust(source: SoilingSource, site: UserSite, now: datetime) -> Dust:
    """The site's dust model, or why there is none today. The brief is still written without it."""
    try:
        soiling, _weather = await source.soiling(site, now)
    except SoilingCollectingError as exc:
        return exc.collecting
    except (WeatherUnavailable, DatasetUnavailable):
        return DustUnavailable()
    return soiling


async def rain_outlook(source: RainSource, today: date) -> Optional[RainForecastOut]:
    """The rain forecast, or None when it could not be fetched."""
    try:
        return await source.forecast(today)
    except RainUnavailable:
        return None


# ---------- wording ----------


def _kwh(value: float) -> str:
    return f"{value:.1f}"


def _pkr(value: float | Decimal) -> str:
    return f"{float(value):,.0f}"


def _rate(value: Decimal) -> str:
    return f"{float(value):,.2f}"


def _hour(hour: int) -> str:
    return f"{hour % 24:02d}:00"


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _window_sum(values: Sequence[float], start: int, end: int) -> float:
    return float(sum(values[start:end]))


@dataclass(frozen=True, slots=True)
class WashAdvice:
    days: int
    loss_pkr: float
    net_pkr: float

    @property
    def pays_off(self) -> bool:
        return self.net_pkr > 0.0


def wash_advice(soiling: SiteSoilingOut, rain: Optional[RainForecastOut]) -> WashAdvice:
    """Dust cost until washing rain (at most the wash horizon) against one wash; same sum as the Panels screen."""
    until_rain = rain.days_until_rain if rain is not None else None
    days = min(until_rain if until_rain is not None else WASH_HORIZON_DAYS, WASH_HORIZON_DAYS)
    loss = soiling.daily_loss_kwh * soiling.tariff_pkr_per_kwh * days
    return WashAdvice(days=days, loss_pkr=loss, net_pkr=loss - soiling.wash_cost_pkr)


def _rain_sentence(rain: Optional[RainForecastOut], days: int) -> str:
    if rain is None:
        return f"The rain forecast isn't available, so this counts the next {_plural(days, 'day')}."
    if rain.days_until_rain is None:
        return f"No rain heavy enough to wash the panels is forecast in the next {_plural(rain.horizon_days, 'day')}."
    if rain.days_until_rain == 0:
        return f"Rain of {rain.threshold_mm:g} mm or more, enough to wash the panels, is forecast today."
    return (
        f"Rain of {rain.threshold_mm:g} mm or more, enough to wash the panels, is forecast in "
        f"{_plural(rain.days_until_rain, 'day')}."
    )


def _dust_text(dust: Dust, rain: Optional[RainForecastOut]) -> tuple[str, Optional[str], Optional[WashAdvice]]:
    """(brief, recommended action or None, wash advice or None)."""
    if isinstance(dust, DustUnavailable):
        return "The dust estimate isn't available right now: the sunlight data for your area couldn't be fetched.", None, None
    if isinstance(dust, SoilingCollecting):
        if dust.clean is None:
            return (
                "No wash is on record and no rain has washed your panels recently, so there is no dust estimate yet. "
                f"It starts {_plural(MIN_FIT_DAYS, 'full day')} of inverter readings after your next wash.",
                'After your next panel wash, tap "I washed the panels today" on the Panels screen.',
                None,
            )
        cleaned = "Rain washed your panels" if dust.clean.kind == "rain" else "Your panels were washed"
        return (
            f"{cleaned} on {dust.clean.day.isoformat()}. The dust estimate needs "
            f"{_plural(MIN_FIT_DAYS, 'full day')} of inverter readings after that; {dust.fit_days} so far.",
            None,
            None,
        )

    advice = wash_advice(dust, rain)
    cleaned = "rain washed the panels" if dust.clean_event == "rain" else "the panels were washed"
    measured = (
        "measured from your own inverter log"
        if dust.source == "live"
        else f"from the recorded dust model, which runs to {dust.as_of}"
    )
    brief = (
        f"Dust costs about {dust.daily_loss_kwh:.2f} kWh a day since {cleaned} on {dust.wash_date} ({measured}), "
        f"worth PKR {dust.tariff_pkr_per_kwh:,.2f} per kWh on your tariff. {_rain_sentence(rain, advice.days)} "
        f"Over the next {_plural(advice.days, 'day')} dust costs PKR {_pkr(advice.loss_pkr)} against "
        f"PKR {_pkr(dust.wash_cost_pkr)} for a wash."
    )
    if advice.pays_off:
        action = f"Book a panel wash: it saves PKR {_pkr(advice.net_pkr)} more than it costs over the next {_plural(advice.days, 'day')}."
    else:
        action = "Hold off washing the panels: the dust costs less than a wash before the next rain."
    return brief, action, advice


def compose_brief(
    site: UserSite,
    plan: LivePlanResponse,
    tariff: TariffFacts,
    dust: Dust,
    rain: Optional[RainForecastOut],
) -> DailyBriefResponse:
    start, end = tariff.peak_start_hour, tariff.peak_end_hour
    window = f"{_hour(start)}–{_hour(end)}"
    name = site.name.strip() or "Your home"

    solar = float(sum(plan.solar_kw))
    load = float(sum(plan.load_kw))
    grid = float(sum(plan.p_grid_import_kw))
    exported = float(sum(plan.p_grid_export_kw))
    peak_load = _window_sum(plan.load_kw, start, end)
    peak_grid = _window_sum(plan.p_grid_import_kw, start, end)
    peak_battery = _window_sum(plan.p_dis_kw, start, end)
    export_rate = Decimal(plan.export_rate_used_pkr_per_kwh)
    export_credit = Decimal(plan.export_revenue_credit_pkr)
    savings = Decimal(plan.net_savings_pkr)
    reserve_pct = round(plan.reserve_floor_kwh / plan.battery_capacity_kwh * 100.0)
    logged_outage_hours = int(sum(plan.outage_flags))
    risk = max(plan.outage_prob) if plan.outage_prob else 0.0
    risk_hour = plan.outage_prob.index(risk) if plan.outage_prob else 0

    cover_pct = round(min(1.0, peak_battery / peak_load) * 100.0) if peak_load > 0.0 else None
    slab = tariff.peak_rate_pkr is None or tariff.off_peak_rate_pkr is None
    period = "evening" if slab else "peak-hour"

    # ---- savings and peak hours ----
    dispatch = (
        f"Today's forecast for your {plan.pv_kwp:g} kWp array is {_kwh(solar)} kWh of solar against "
        f"{_kwh(load)} kWh of home use. "
    )
    if tariff.peak_rate_pkr is not None and tariff.off_peak_rate_pkr is not None:
        dispatch += (
            f"Peak hours are {window}, when grid power costs PKR {_rate(tariff.peak_rate_pkr)}/kWh against "
            f"PKR {_rate(tariff.off_peak_rate_pkr)}/kWh the rest of the day (all-in). "
        )
    else:
        ceiling = (
            f"; the plan keeps this month's grid use under {plan.slab_ceiling_target_kwh:.0f} kWh"
            if plan.slab_ceiling_target_kwh is not None
            else ""
        )
        dispatch += f"Your single-phase slab tariff has no peak price{ceiling}. "
    dispatch += (
        f"Your home is expected to use {_kwh(peak_load)} kWh from {window}; your {plan.battery_capacity_kwh:g} kWh "
        f"battery supplies {_kwh(peak_battery)} kWh of it and the grid {_kwh(peak_grid)} kWh. "
        f"The plan buys {_kwh(grid)} kWh from the grid today"
    )
    if exported > 0.0 and export_rate > 0:
        dispatch += (
            f" and sends {_kwh(exported)} kWh to it at PKR {_rate(export_rate)}/kWh "
            f"(PKR {_pkr(export_credit)} credit)"
        )
    dispatch += "."
    if export_rate == 0:
        dispatch += " Exports earn nothing on your tariff."
    dispatch += f" The plan saves PKR {_pkr(savings)} against running without the battery."

    # ---- outages ----
    if logged_outage_hours > 0:
        blackout = (
            f"Your inverter has logged {_plural(logged_outage_hours, 'hour')} without grid power today; the plan "
            "runs those hours on solar and battery only and sends nothing to the grid."
        )
    else:
        blackout = "Your inverter has logged no blackout today so far."
    risk_pct = round(risk * 100.0)
    if risk_pct >= 1:
        blackout += f" The highest forecast outage risk today is {risk_pct}% around {_hour(risk_hour)}."
    else:
        blackout += " The forecast outage risk stays under 1% all day."
    blackout += f" {reserve_pct}% of the battery ({plan.reserve_floor_kwh:.2f} kWh) stays reserved for outages."

    # ---- dust ----
    soiling_brief, dust_action, advice = _dust_text(dust, rain)

    # ---- headline and actions ----
    headline = f"{name}: "
    if cover_pct is not None:
        headline += f"the battery covers {cover_pct}% of your {window} {period} use"
    else:
        headline += f"no {period} use is forecast for {window}"
    headline += f" and today's plan saves PKR {_pkr(savings)}"
    if advice is not None:
        headline += "; a panel wash pays for itself" if advice.pays_off else "; the panels can wait for a wash"
    headline += "."

    actions = [
        f"Let the battery charge from solar before {_hour(start)} so it covers {window}.",
        f"Keep the {reserve_pct}% outage reserve ({plan.reserve_floor_kwh:.2f} kWh) untouched.",
    ]
    if dust_action is not None:
        actions.append(dust_action)

    return DailyBriefResponse(
        date=plan.date,
        site_name=name,
        headline=headline,
        dispatch_arbitrage_brief=dispatch,
        blackout_resilience_brief=blackout,
        soiling_maintenance_brief=soiling_brief,
        recommended_actions=actions,
        key_metrics={
            "solar_generation_kwh": round(solar, 2),
            "household_load_kwh": round(load, 2),
            "grid_import_kwh": round(grid, 2),
            "net_metering_export_kwh": round(exported, 2),
            "export_revenue_pkr": float(export_credit),
            "peak_battery_discharge_kwh": round(peak_battery, 2),
            "outage_hours": float(logged_outage_hours),
            "net_savings_pkr": float(savings),
            "soiling_loss_kwh": dust.daily_loss_kwh if isinstance(dust, SiteSoilingOut) else None,
            "net_cleaning_benefit_pkr": round(advice.net_pkr, 2) if advice is not None else None,
        },
        generation_mode=GENERATION_MODE,
    )
