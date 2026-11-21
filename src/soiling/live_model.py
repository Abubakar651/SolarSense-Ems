"""
Live per-site dust (soiling) model from a site's own logged solar output and modelled sunlight.

After a clean event (a recorded panel wash, or a day with washing rain) the panels are clean. Each complete
logged day after it has a performance ratio, PR_d = solar kWh_d / (GHI_d kWh/m2 * array kWp). The clean PR
is the median of the first CLEAN_BASELINE_DAYS such days; the soiling ratio of every day is its PR over the
clean PR, and an exponential daily loss rate k is fitted to those ratios (least squares on the log ratio,
k >= 0). The model is PR(t) = PR(0) * exp(-k * t), t in days since the clean event. Until MIN_FIT_DAYS days
exist after the clean event the site is "collecting".

The station's calibrated rate (src/soiling/calibrate_soiling_model.py) is deliberately not used as a prior:
it was fitted to one roof's 14 days after one wash, and dust rates differ by roof, tilt and street, so a
borrowed rate would present another site's dust as this site's. The model waits for the site's own days.

Pure NumPy over plain values; the database, the weather API and the clock stay with the caller.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal

import numpy as np
import numpy.typing as npt

from src.data_engineering.repair_master_dataset import RAIN_CLEAN_MM

FloatVec = npt.NDArray[np.float64]

CleanKind = Literal["wash", "rain"]

# Days after the clean event whose PR sets the clean baseline (median, robust to one odd day).
CLEAN_BASELINE_DAYS = 2
# Fewer days than this after the clean event can't separate a trend from day-to-day noise.
MIN_FIT_DAYS = 3
# Below this daily GHI (thick fog, overcast monsoon days) the PR is dominated by diffuse light and
# measurement noise, not dust; a clear Lahore day is 3.5-7 kWh/m2.
MIN_GHI_KWH_M2 = 1.0
# A dusty day can look up to 5% better than the baseline through weather alone; anything more is noise.
MAX_RATIO = 1.05


@dataclass(frozen=True, slots=True)
class CleanEvent:
    day: date
    kind: CleanKind


@dataclass(frozen=True, slots=True)
class SoilingFit:
    clean: CleanEvent
    # PR at the clean event: the clean baseline brought back to day 0 along the fitted curve.
    clean_pr: float
    # k in ratio(t) = exp(-k t): the fraction of output lost per day, compounding.
    loss_rate_per_day: float
    # Last day the fit used.
    as_of: date
    # Modelled PR for each day from the clean event (day 0) to as_of; write-locked.
    model_pr: FloatVec
    # Days after the clean event the fit used.
    fit_days: int
    # Daily GHI of as_of (kWh/m2), the fallback for today's expected output.
    last_ghi_kwh_m2: float

    def ratio_on(self, day: date) -> float:
        """Modelled soiling ratio (1 = clean) on `day`."""
        return float(np.exp(-self.loss_rate_per_day * max(0, (day - self.clean.day).days)))


@dataclass(frozen=True, slots=True)
class SoilingCollecting:
    # None when no wash was recorded and no washing rain fell in the weather window.
    clean: CleanEvent | None
    fit_days: int


def latest_clean_event(
    washes: Sequence[date], weather_days: Sequence[date], rain_mm: Sequence[float], today: date
) -> CleanEvent | None:
    """
    The latest wash (up to today) or day with at least RAIN_CLEAN_MM of rain (before today: today's total
    is still partly a forecast). A wash and a washing rain on the same day count as the wash.
    """
    wash = max((d for d in washes if d <= today), default=None)
    rain = max(
        (d for d, mm in zip(weather_days, rain_mm) if d < today and np.isfinite(mm) and mm >= RAIN_CLEAN_MM),
        default=None,
    )
    if wash is not None and (rain is None or wash >= rain):
        return CleanEvent(wash, "wash")
    return CleanEvent(rain, "rain") if rain is not None else None


def fit_soiling(
    clean: CleanEvent,
    days: Sequence[date],
    solar_kwh: Sequence[float],
    ghi_kwh_m2: Sequence[float],
    pv_kwp: float,
) -> SoilingFit | SoilingCollecting:
    """
    Fits the loss rate to the complete logged days after `clean`. `days`, `solar_kwh` and `ghi_kwh_m2` are
    aligned (NaN GHI = no modelled sunlight for that day). Days without enough sunlight or without any solar
    output (an inverter that was off is not dust) are skipped.
    """
    t = np.array([(d - clean.day).days for d in days], dtype=np.float64)
    solar = np.asarray(solar_kwh, dtype=np.float64)
    ghi = np.asarray(ghi_kwh_m2, dtype=np.float64)
    usable = (t > 0) & np.isfinite(ghi) & (ghi >= MIN_GHI_KWH_M2) & (solar > 0.0)
    order = np.argsort(t[usable], kind="stable")
    t, solar, ghi = t[usable][order], solar[usable][order], ghi[usable][order]
    if t.size < MIN_FIT_DAYS or pv_kwp <= 0.0:
        return SoilingCollecting(clean, int(t.size))

    pr = solar / (ghi * pv_kwp)
    baseline_pr = float(np.median(pr[:CLEAN_BASELINE_DAYS]))
    baseline_t = float(np.mean(t[:CLEAN_BASELINE_DAYS]))
    log_ratio = np.log(np.minimum(pr / baseline_pr, MAX_RATIO))
    # Least squares through the baseline (ratio 1 there): log r = -k (t - baseline_t). Anchoring at the
    # baseline days rather than at the clean event keeps k unbiased; the dust already gathered by the
    # baseline days is then added back to give the PR at the clean event itself.
    x = t - baseline_t
    k = max(0.0, float(-(x @ log_ratio) / (x @ x))) if x @ x > 0.0 else 0.0
    clean_pr = baseline_pr * float(np.exp(k * baseline_t))

    as_of_t = int(t[-1])
    model_pr = clean_pr * np.exp(-k * np.arange(as_of_t + 1, dtype=np.float64))
    model_pr.setflags(write=False)
    as_of = date.fromordinal(clean.day.toordinal() + as_of_t)
    return SoilingFit(
        clean=clean,
        clean_pr=clean_pr,
        loss_rate_per_day=k,
        as_of=as_of,
        model_pr=model_pr,
        fit_days=int(t.size),
        last_ghi_kwh_m2=float(ghi[-1]),
    )


def daily_loss_kwh(fit: SoilingFit, today: date, ghi_today_kwh_m2: float | None, pv_kwp: float) -> float:
    """
    Energy dust costs today: today's clean expected output (clean PR x GHI x kWp, from today's sunlight
    forecast, or the last fitted day's when there is none) times the modelled loss fraction today.
    """
    ghi = ghi_today_kwh_m2 if ghi_today_kwh_m2 is not None and np.isfinite(ghi_today_kwh_m2) else fit.last_ghi_kwh_m2
    expected_kwh = fit.clean_pr * ghi * pv_kwp
    return expected_kwh * (1.0 - fit.ratio_on(today))
