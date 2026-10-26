"""
repair_master_dataset.py
========================
SolarSense EMS — Forensic data repair & weather-anchored PV reconstruction

Reference array : 12 x 585 W = 7.02 kWp  (hard AC/DC ceiling for any hourly PV kW)
Reference BESS  : 5.12 kWh LiFePO4 (its charge/discharge is what contaminated the PV channel)

Pipeline (idempotent — safe to re-run, safe to call from build_master_feature_store.py)
---------------------------------------------------------------------------------
STEP 1  Fix "phantom solar" in the 5-min telemetry (goodwe_lahore_5min.csv)
        The legacy channel was `max(0, active_power_kw)`. `active_power_kw` is the inverter's
        AC output, so every kW of battery discharge at night (self-consumption, or islanded
        during a LESCO blackout) was logged as solar generation. Inverter power conservation:
            pv_true_kw = where(ghi > 0, clip(active_power_kw - battery_power_kw, 0, 7.02), 0)
        (battery_power_kw > 0 = discharge, < 0 = charge.)
        The old channel is preserved as `solar_power_kw_legacy`; `solar_power_kw` is replaced.

STEP 2  Weather-anchored transfer model (LightGBM) trained on the measured days only:
        Open-Meteo weather + solar geometry + soiling state  ->  true hourly PV kWh.
        Validated with leave-one-contiguous-block-out CV (whole measured weeks held out), against
        a GHI-proportional baseline. Cross-target isolation: no load / outage / battery features.

STEP 3  Reconstruct all 464 days and anchor each day to the portal's daily total
        (goodwe_lahore_daily_raw.csv `generation_kwh`). The model supplies the hourly *shape*;
        the daily integral is forced to equal the real log, respecting the 7.02 kW hourly cap.

Outputs
-------
  data/processed/solar_timeseries/goodwe_lahore_5min.csv                  (repaired in place)
  data/processed/solar_timeseries/goodwe_lahore_hourly.csv                (solar cols repaired in place)
  data/processed/solar_timeseries/goodwe_lahore_hourly_reconstructed.csv  (464 x 24 rows, new)
"""

from __future__ import annotations

import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import lightgbm as lgb
import numpy as np
import polars as pl

BASE = Path(__file__).resolve().parents[2]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from src.data_engineering.feature_store import TariffPolicy  # noqa: E402

# ──────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────
ARRAY_KWP = 12 * 0.585            # 7.02 kWp
STEP_H = 5.0 / 60.0               # 5-min sample -> hours
LAT, LON = 31.5204, 74.3587
TZ = "Asia/Karachi"
KNOWN_WASH_DATE = date(2026, 9, 23)
RAIN_CLEAN_MM = 2.5               # daily rain that is assumed to wash the array
SOILING_CAP_DAYS = 90

PATH_5MIN = BASE / "data/processed/solar_timeseries/goodwe_lahore_5min.csv"
PATH_HOURLY = BASE / "data/processed/solar_timeseries/goodwe_lahore_hourly.csv"
PATH_RECON = BASE / "data/processed/solar_timeseries/goodwe_lahore_hourly_reconstructed.csv"
PATH_WEATHER = BASE / "data/processed/weather/lahore_historical_weather_hourly.csv"
PATH_DAILY = BASE / "data/raw/solar_timeseries/goodwe_lahore/goodwe_lahore_daily_raw.csv"

DT_FMT = "%Y-%m-%d %H:%M:%S"

FEATURES = [
    "ghi_wm2", "ghi_next_wm2", "dni_wm2", "dhi_wm2", "temp_c", "wind_ms",
    "humidity_pct", "rain_mm", "solar_elevation_deg", "solar_zenith_deg",
    "solar_azimuth_deg", "days_since_clean",
]
MONOTONE = [1 if f == "ghi_wm2" else 0 for f in FEATURES]


# ══════════════════════════════════════════════════════
# STEP 1 — Phantom-solar repair (pure numpy kernel + IO wrapper)
# ══════════════════════════════════════════════════════
def compute_pv_true_kw(
    active_power_kw: np.ndarray,
    battery_power_kw: np.ndarray,
    ghi_wm2: np.ndarray,
    cap_kw: float = ARRAY_KWP,
) -> np.ndarray:
    """Inverter power conservation: PV = AC output - battery discharge (+ battery charge)."""
    pv = np.clip(active_power_kw - battery_power_kw, 0.0, cap_kw)
    return np.where(ghi_wm2 > 0.0, pv, 0.0).astype(np.float64)


def repair_5min_telemetry(f5: pl.DataFrame, wx: pl.DataFrame) -> Tuple[pl.DataFrame, Dict[str, float]]:
    """Returns the repaired 5-min frame (with `ghi_wm2` helper col dropped) and forensic stats."""
    keep = [c for c in f5.columns if c not in ("pv_true_kw", "ghi_wm2", "hts")]
    f5 = f5.select(keep)
    if "solar_power_kw_legacy" not in f5.columns:      # preserve the original, only once
        f5 = f5.with_columns(pl.col("solar_power_kw").alias("solar_power_kw_legacy"))

    lut = wx.select(pl.col("timestamp").alias("hts"), "ghi_wm2")
    max_wx_ts = wx["timestamp"].max()

    # Split telemetry into in-spine (weather-aligned) and post-spine (recent/current day)
    f5_in = f5.filter(pl.col("timestamp") <= max_wx_ts)
    f5_out = f5.filter(pl.col("timestamp") > max_wx_ts)

    j = (
        f5_in.with_columns(pl.col("timestamp").dt.truncate("1h").alias("hts"))
        .join(lut, on="hts", how="left")
        .sort("timestamp")
    )

    ghi = j["ghi_wm2"].to_numpy()
    pv = compute_pv_true_kw(j["active_power_kw"].to_numpy(), j["battery_power_kw"].to_numpy(), ghi)
    legacy = np.clip(j["solar_power_kw_legacy"].to_numpy(), 0.0, None)
    bat = j["battery_power_kw"].to_numpy()
    night = ghi <= 0.0

    stats = {
        "rows": float(j.height),
        "night_rows": float(night.sum()),
        "legacy_phantom_rows": float(((legacy > 0) & night).sum()),
        "legacy_phantom_kwh": float(legacy[night].sum() * STEP_H),
        "legacy_phantom_blackout_rows": float(((legacy > 0) & night & (bat > 0.5)).sum()),
        "legacy_total_kwh": float(legacy.sum() * STEP_H),
        "true_total_kwh": float(pv.sum() * STEP_H),
        "true_night_max_kw": float(pv[night].max()) if night.any() else 0.0,
        "true_peak_kw": float(pv.max()),
    }
    j = j.with_columns(
        pl.Series("pv_true_kw", pv),
        pl.Series("solar_power_kw", pv),
    ).drop(["hts", "ghi_wm2"])

    if not f5_out.is_empty():
        out_hours = f5_out["timestamp"].dt.hour().to_numpy()
        out_daytime = (out_hours >= 6) & (out_hours <= 18)
        out_pv = np.clip(f5_out["active_power_kw"].to_numpy() - f5_out["battery_power_kw"].to_numpy(), 0.0, ARRAY_KWP)
        out_pv = np.where(out_daytime, out_pv, 0.0)
        f5_out_fixed = f5_out.with_columns(
            pl.Series("pv_true_kw", out_pv),
            pl.Series("solar_power_kw", out_pv),
        )
        j = pl.concat([j, f5_out_fixed]).sort("timestamp")

    return j, stats


def measured_hourly(f5_fixed: pl.DataFrame) -> pl.DataFrame:
    """Integrate repaired 5-min PV kW -> hourly kWh (Riemann sum) + hourly peak kW."""
    return (
        f5_fixed.with_columns(pl.col("timestamp").dt.truncate("1h").alias("hts"))
        .group_by("hts")
        .agg(
            (pl.col("pv_true_kw").sum() * STEP_H).alias("solar_energy_kwh"),
            pl.col("pv_true_kw").max().alias("solar_peak_kw"),
        )
        .rename({"hts": "timestamp"})
        .sort("timestamp")
    )


def update_hourly_csv(meas: pl.DataFrame, path: Path = PATH_HOURLY) -> int:
    hr = pl.read_csv(path, try_parse_dates=True)
    cols = hr.columns
    hr = hr.drop(["solar_energy_kwh", "solar_peak_kw"]).join(meas, on="timestamp", how="left").select(cols)
    hr.write_csv(path, datetime_format=DT_FMT)
    return hr.height


# ══════════════════════════════════════════════════════
# STEP 2 — Features + transfer model
# ══════════════════════════════════════════════════════
def days_since_clean_event(daily_rain_mm: np.ndarray, wash_mask: np.ndarray,
                           rain_clean_mm: float = RAIN_CLEAN_MM, cap: int = SOILING_CAP_DAYS) -> np.ndarray:
    """
    Days since the array was last cleaned by a known wash or a washing rain (>= rain_clean_mm/day).
    The wash history before 2026-09-23 is unknown, so rain is the only physical reset available;
    before the first reset the clock starts at the beginning of the record. Vectorised.
    """
    idx = np.arange(daily_rain_mm.size)
    event = (daily_rain_mm >= rain_clean_mm) | wash_mask
    last = np.maximum.accumulate(np.where(event, idx, -1))
    return np.minimum(np.where(last >= 0, idx - last, idx + 1), cap).astype(np.float64)


def solar_geometry(ts: pl.Series) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Apparent elevation / zenith / azimuth at the middle of each hour (pvlib, PKT, no DST)."""
    import pandas as pd  # pvlib's API is pandas-only; confined to this bridge
    import pvlib

    idx = pd.DatetimeIndex(ts.to_numpy()).tz_localize(TZ) + pd.Timedelta(minutes=30)
    sp = pvlib.solarposition.get_solarposition(idx, LAT, LON)
    return (sp["apparent_elevation"].to_numpy(), sp["zenith"].to_numpy(), sp["azimuth"].to_numpy())


def load_weather(path: Path = PATH_WEATHER) -> pl.DataFrame:
    wx = pl.read_csv(path, try_parse_dates=True).sort("timestamp").with_columns(
        pl.col("humidity_pct").cast(pl.Float64)
    )
    step = wx["timestamp"].diff().drop_nulls().dt.total_seconds().unique().to_list()
    if step != [3600] or wx.height % 24 != 0:
        raise ValueError(f"Weather spine must be a gap-free hourly series of whole days (steps={step})")
    return wx


def build_feature_frame(wx: pl.DataFrame) -> pl.DataFrame:
    elev, zen, azi = solar_geometry(wx["timestamp"])
    ghi = wx["ghi_wm2"].to_numpy()
    wx = wx.with_columns(pl.col("timestamp").dt.date().alias("date"))

    daily = wx.group_by("date", maintain_order=True).agg(pl.col("rain_mm").sum().alias("rain_day"))
    dates = daily["date"].to_numpy().astype("datetime64[D]")
    dsc = days_since_clean_event(
        daily["rain_day"].to_numpy(), dates == np.datetime64(KNOWN_WASH_DATE)
    )
    daily = daily.with_columns(pl.Series("days_since_clean", dsc)).select("date", "days_since_clean")

    return (
        wx.with_columns(
            pl.Series("ghi_next_wm2", np.append(ghi[1:], ghi[-1])),   # Open-Meteo GHI is hour-ending
            pl.Series("solar_elevation_deg", elev),
            pl.Series("solar_zenith_deg", zen),
            pl.Series("solar_azimuth_deg", azi),
        )
        .join(daily, on="date", how="left")
        .sort("timestamp")
    )


def make_model() -> lgb.LGBMRegressor:
    return lgb.LGBMRegressor(
        objective="regression", n_estimators=400, learning_rate=0.03, num_leaves=8,
        min_child_samples=8, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
        reg_lambda=2.0, monotone_constraints=MONOTONE, random_state=42,
        deterministic=True, force_row_wise=True, verbose=-1,
    )


def _err(y: np.ndarray, p: np.ndarray) -> Dict[str, float]:
    if y.size == 0:
        return {"mae": float("nan"), "rmse": float("nan"), "r2": float("nan"), "n": 0}
    d = p - y
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return {
        "mae": float(np.abs(d).mean()),
        "rmse": float(np.sqrt((d ** 2).mean())),
        "r2": float(1.0 - (d ** 2).sum() / ss_tot) if ss_tot > 0 else float("nan"),
        "n": int(y.size),
    }


def block_ids(day_values: np.ndarray) -> np.ndarray:
    """Contiguous-date blocks (a gap of >1 day starts a new block) for leave-one-block-out CV."""
    d = np.unique(day_values.astype("datetime64[D]"))
    block_of_day = np.concatenate([[0], np.cumsum(np.diff(d).astype(np.int64) > 1)])
    return block_of_day[np.searchsorted(d, day_values.astype("datetime64[D]"))]


def train_transfer_model(train: pl.DataFrame) -> Tuple[lgb.LGBMRegressor, Dict[str, Any]]:
    """`train` = daytime rows of measured days with columns FEATURES + `y_kwh` + `date`."""
    X = train.select(FEATURES).to_numpy()
    y = train["y_kwh"].to_numpy()
    ghi = train["ghi_wm2"].to_numpy()
    dates = train["date"].to_numpy().astype("datetime64[D]")
    blocks = block_ids(dates)
    months = train["timestamp"].dt.month().to_numpy()

    oof = np.full(y.size, np.nan)
    base = np.full(y.size, np.nan)
    for b in np.unique(blocks):
        te = blocks == b
        m = make_model().fit(X[~te], y[~te])
        oof[te] = np.clip(m.predict(X[te]), 0.0, ARRAY_KWP)
        k = float((y[~te] * ghi[~te]).sum() / (ghi[~te] ** 2).sum())   # through-origin GHI baseline
        base[te] = np.clip(k * ghi[te], 0.0, ARRAY_KWP)

    hours = train["timestamp"].dt.hour().to_numpy()
    policy = TariffPolicy()
    peak_table = np.zeros((13, 24), dtype=bool)          # [month, hour] -> in LESCO seasonal peak window
    for mo in range(1, 13):                              # 12 iterations over calendar months, not rows
        peak_table[mo, list(policy.get_peak_hours_for_month(mo))] = True
    peak_mask = peak_table[months, hours]

    day_idx = np.unique(dates, return_inverse=True)[1]
    day_true = np.bincount(day_idx, weights=y)
    day_pred = np.bincount(day_idx, weights=oof)
    day_base = np.bincount(day_idx, weights=base)
    ok = day_true > 1.0

    # Shape-only skill: rescale each held-out day's predicted curve to the TRUE daily total,
    # exactly what STEP 3 does in production (daily energy is anchored, only the shape is modelled).
    def _anchored(p: np.ndarray, day_p: np.ndarray) -> np.ndarray:
        f = np.divide(day_true, day_p, out=np.zeros_like(day_p), where=day_p > 0)
        return np.clip(p * f[day_idx], 0.0, ARRAY_KWP)

    oof_anch, base_anch = _anchored(oof, day_pred), _anchored(base, day_base)

    cv = {
        "n_rows": int(y.size), "n_days": int(np.unique(dates).size), "n_blocks": int(np.unique(blocks).size),
        "model": _err(y, oof), "baseline": _err(y, base),
        "model_anchored": _err(y, oof_anch), "baseline_anchored": _err(y, base_anch),
        "model_peak_window": _err(y[peak_mask], oof[peak_mask]),
        "model_anchored_peak_window": _err(y[peak_mask], oof_anch[peak_mask]),
        "daily_mape_model_pct": float(np.mean(np.abs(day_pred[ok] - day_true[ok]) / day_true[ok]) * 100),
        "daily_mape_baseline_pct": float(np.mean(np.abs(day_base[ok] - day_true[ok]) / day_true[ok]) * 100),
    }
    final = make_model().fit(X, y)
    final.set_params(n_jobs=1)
    return final, cv


def benchmark_inference(model: lgb.LGBMRegressor, X24: np.ndarray, reps: int = 200) -> float:
    model.predict(X24)
    t0 = time.perf_counter()
    for _ in range(reps):
        model.predict(X24)
    return (time.perf_counter() - t0) / reps * 1000.0


# ══════════════════════════════════════════════════════
# STEP 3 — Daily-total anchoring
# ══════════════════════════════════════════════════════
def anchor_to_daily_totals(base: np.ndarray, target_kwh: np.ndarray, cap_kw: float = ARRAY_KWP,
                           fallback_shape: Optional[np.ndarray] = None,
                           max_iter: int = 50) -> Tuple[np.ndarray, np.ndarray]:
    """
    Scale each row of `base` (n_days, 24) so it integrates to `target_kwh` while no hour exceeds
    `cap_kw`. Hours that hit the cap shed their excess to the remaining sunlit hours (water-filling).
    Zero-target days are forced to zero (the portal logged no generation). Fully vectorised.
    Returns (anchored, scale) where scale = target / sum(base) (NaN if base is all zero).
    """
    base = np.asarray(base, dtype=np.float64)
    target = np.asarray(target_kwh, dtype=np.float64)
    shape = base.copy()
    if fallback_shape is not None:
        empty = (shape.sum(axis=1) <= 0.0) & (target > 0.0)
        shape[empty] = fallback_shape[empty]

    s = shape.sum(axis=1)
    scale = np.divide(target, s, out=np.full_like(s, np.nan), where=s > 0)
    out = shape * np.nan_to_num(scale, nan=0.0)[:, None]
    lit = shape > 0.0

    for _ in range(max_iter):
        excess = np.clip(out - cap_kw, 0.0, None).sum(axis=1)
        if excess.max(initial=0.0) <= 1e-12:
            break
        out = np.minimum(out, cap_kw)
        free = lit & (out < cap_kw - 1e-12)
        w = np.where(free, shape, 0.0)
        ws = w.sum(axis=1)
        out = out + np.divide(w, ws[:, None], out=np.zeros_like(w), where=ws[:, None] > 0) * excess[:, None]
    return out, scale


# ══════════════════════════════════════════════════════
# ORCHESTRATION
# ══════════════════════════════════════════════════════
def reconstruct_all_days(feats: pl.DataFrame, meas: pl.DataFrame, daily: pl.DataFrame,
                         model: lgb.LGBMRegressor) -> Tuple[pl.DataFrame, Dict[str, float]]:
    n = feats.height
    n_days = n // 24
    ts = feats["timestamp"]
    if not np.array_equal(ts.dt.hour().to_numpy()[:24], np.arange(24)):
        raise ValueError("Spine must start at 00:00")

    ghi = feats["ghi_wm2"].to_numpy()
    pred = np.clip(model.predict(feats.select(FEATURES).to_numpy()), 0.0, ARRAY_KWP)
    pred = np.where(ghi > 0.0, pred, 0.0)

    j = feats.select("timestamp").join(meas, on="timestamp", how="left")
    meas_kwh = j["solar_energy_kwh"].to_numpy().reshape(n_days, 24)
    meas_peak = j["solar_peak_kw"].to_numpy().reshape(n_days, 24)
    is_meas_day = ~np.isnan(meas_kwh).any(axis=1)

    pred_m = pred.reshape(n_days, 24)
    base = np.where(is_meas_day[:, None], np.nan_to_num(meas_kwh, nan=0.0), pred_m)   # shape source
    ghi_m = ghi.reshape(n_days, 24)

    dates = feats["date"].to_numpy().reshape(n_days, 24)[:, 0]
    tgt_df = pl.DataFrame({"date": dates}).join(
        daily.select("date", pl.col("generation_kwh")), on="date", how="left"
    )
    if tgt_df["generation_kwh"].null_count():
        raise ValueError("Daily raw log does not cover every day of the weather spine")
    target = tgt_df["generation_kwh"].to_numpy()

    anchored, scale = anchor_to_daily_totals(base, target, ARRAY_KWP, fallback_shape=np.where(ghi_m > 0, ghi_m, 0.0))
    anchored = np.where(ghi_m > 0.0, anchored, 0.0)

    sc = np.nan_to_num(scale, nan=0.0)[:, None]
    peak = np.where(is_meas_day[:, None], np.clip(np.nan_to_num(meas_peak, nan=0.0) * sc, 0.0, ARRAY_KWP), np.nan)
    peak = np.where(np.isnan(peak), np.nan, np.maximum(peak, anchored))

    recon = pl.DataFrame({
        "timestamp": ts,
        "date": feats["date"],
        "solar_energy_kwh": anchored.reshape(-1),
        "solar_peak_kw": peak.reshape(-1),
        "solar_source": np.repeat(np.where(is_meas_day, "measured_5min", "reconstructed"), 24),
        "model_pred_kwh": pred,
        "anchor_scale": np.repeat(scale, 24),
    })

    day_sum = anchored.sum(axis=1)
    rec_days = ~is_meas_day & (target > 0)
    stats = {
        "n_days": float(n_days),
        "n_measured_days": float(is_meas_day.sum()),
        "n_reconstructed_days": float((~is_meas_day).sum()),
        "max_abs_daily_err_kwh": float(np.abs(day_sum - target).max()),
        "zero_target_days": float((target == 0).sum()),
        "scale_median_reconstructed": float(np.nanmedian(scale[rec_days])),
        "scale_p05_reconstructed": float(np.nanpercentile(scale[rec_days], 5)),
        "scale_p95_reconstructed": float(np.nanpercentile(scale[rec_days], 95)),
        "scale_median_measured": float(np.nanmedian(scale[is_meas_day & (target > 0)])),
        "scale_min_measured": float(np.nanmin(scale[is_meas_day & (target > 0)])),
        "scale_max_measured": float(np.nanmax(scale[is_meas_day & (target > 0)])),
        "max_hourly_kw": float(anchored.max()),
        "observed_max_hourly_kw": float(np.nanmax(meas_kwh)),
        "recon_days_above_observed_max": float((anchored[~is_meas_day].max(axis=1) > np.nanmax(meas_kwh)).sum()),
        "night_solar_max_kw": float(anchored[ghi_m <= 0].max(initial=0.0)),
        "total_recon_kwh": float(day_sum.sum()),
        "total_portal_kwh": float(target.sum()),
    }
    return recon, stats


def verify_master(csv_path: Path) -> Dict[str, float]:
    """Post-build physics/consistency audit of master_ems_timeseries.csv."""
    m = pl.read_csv(csv_path, try_parse_dates=True).with_columns(
        pl.col("solar_energy_kwh").cast(pl.Float64, strict=False)
    )
    solar = m["solar_energy_kwh"]
    ghi = m["ghi_wm2"].cast(pl.Float64)
    day = m.group_by("date").agg(
        pl.col("solar_energy_kwh").sum().alias("s"), pl.col("generation_kwh_daily").first().alias("g")
    )
    return {
        "rows": float(m.height),
        "solar_nulls": float(solar.null_count()),
        "night_rows_with_solar": float(((ghi <= 0) & (solar > 0)).sum()),
        "max_hourly_kw": float(solar.max()),
        "max_abs_daily_err_kwh": float((day["s"] - day["g"]).abs().max()),
        "total_solar_kwh": float(solar.sum()),
    }


def _print_report(p1: Dict[str, float], cv: Dict[str, Any], lat_ms: float, p3: Dict[str, float]) -> None:
    bar = "═" * 66
    print(f"\n{bar}\n  STEP 1 — PHANTOM SOLAR REPAIR (5-min telemetry)\n{bar}")
    print(f"  5-min rows                          : {int(p1['rows']):,}  (night rows: {int(p1['night_rows']):,})")
    print(f"  Legacy phantom rows (solar>0 @ GHI=0): {int(p1['legacy_phantom_rows']):,}"
          f"  of which battery>0.5 kW (blackout): {int(p1['legacy_phantom_blackout_rows']):,}")
    print(f"  Legacy phantom energy               : {p1['legacy_phantom_kwh']:.2f} kWh")
    print(f"  Telemetry PV total  legacy -> true  : {p1['legacy_total_kwh']:.1f} -> {p1['true_total_kwh']:.1f} kWh")
    print(f"  Repaired night max / array peak     : {p1['true_night_max_kw']:.3f} kW / {p1['true_peak_kw']:.2f} kW (cap {ARRAY_KWP:.2f})")

    m, b, pk = cv["model"], cv["baseline"], cv["model_peak_window"]
    ma, ba, pka = cv["model_anchored"], cv["baseline_anchored"], cv["model_anchored_peak_window"]
    print(f"\n{bar}\n  STEP 2 — TRANSFER MODEL (leave-one-block-out CV, {cv['n_blocks']} blocks / {cv['n_days']} days)\n{bar}")
    print(f"  Held-out daytime hours (n={cv['n_rows']})")
    print(f"  {'':32s}{'MAE kW':>9s}{'RMSE kW':>10s}{'R2':>8s}{'daily MAPE':>13s}")
    print(f"  {'LightGBM  raw':32s}{m['mae']:9.3f}{m['rmse']:10.3f}{m['r2']:8.3f}{cv['daily_mape_model_pct']:12.1f}%")
    print(f"  {'GHI-proportional  raw':32s}{b['mae']:9.3f}{b['rmse']:10.3f}{b['r2']:8.3f}{cv['daily_mape_baseline_pct']:12.1f}%")
    print(f"  {'LightGBM  anchored (production)':32s}{ma['mae']:9.3f}{ma['rmse']:10.3f}{ma['r2']:8.3f}{'0.0':>12s}%")
    print(f"  {'GHI-proportional  anchored':32s}{ba['mae']:9.3f}{ba['rmse']:10.3f}{ba['r2']:8.3f}{'0.0':>12s}%")
    print(f"  LESCO peak-window MAE (daytime rows in peak hours, n={pk['n']}): raw {pk['mae']:.3f} kW | anchored {pka['mae']:.3f} kW")
    print(f"  24h inference latency (24 rows)     : {lat_ms:.3f} ms  (budget 10 ms)")

    print(f"\n{bar}\n  STEP 3 — DAILY-TOTAL ANCHORING\n{bar}")
    print(f"  Days: {int(p3['n_days'])} = {int(p3['n_measured_days'])} measured + {int(p3['n_reconstructed_days'])} reconstructed"
          f"   (zero-generation days in portal log: {int(p3['zero_target_days'])})")
    print(f"  Max |daily integral - portal log|   : {p3['max_abs_daily_err_kwh']:.2e} kWh")
    print(f"  Anchor scale, reconstructed days    : median {p3['scale_median_reconstructed']:.2f}"
          f"  (p05 {p3['scale_p05_reconstructed']:.2f} / p95 {p3['scale_p95_reconstructed']:.2f})")
    print(f"  Anchor scale, measured days         : median {p3['scale_median_measured']:.2f}"
          f"  (min {p3['scale_min_measured']:.2f} / max {p3['scale_max_measured']:.2f})")
    print(f"  Max hourly kW / night solar max     : {p3['max_hourly_kw']:.3f} kW / {p3['night_solar_max_kw']:.3f} kW")
    print(f"  Max hourly kWh ever MEASURED        : {p3['observed_max_hourly_kw']:.3f} kW -> reconstructed days exceeding it: {int(p3['recon_days_above_observed_max'])}")
    print(f"  Total reconstructed vs portal       : {p3['total_recon_kwh']:.1f} vs {p3['total_portal_kwh']:.1f} kWh")


def run_repair(verbose: bool = True) -> Dict[str, Any]:
    wx = load_weather()
    f5 = pl.read_csv(PATH_5MIN, try_parse_dates=True)
    daily = pl.read_csv(PATH_DAILY, try_parse_dates=True)

    # STEP 1
    f5_fixed, p1 = repair_5min_telemetry(f5, wx)
    f5_fixed.write_csv(PATH_5MIN, datetime_format=DT_FMT)
    meas = measured_hourly(f5_fixed)
    update_hourly_csv(meas)

    # STEP 2
    feats = build_feature_frame(wx)
    zero_days = daily.filter(pl.col("generation_kwh") <= 0.0)["date"]
    train = (
        feats.join(meas.select("timestamp", pl.col("solar_energy_kwh").alias("y_kwh")), on="timestamp", how="inner")
        .filter((pl.col("ghi_wm2") > 0) & ~pl.col("date").is_in(zero_days.implode()))   # offline/fault days excluded
    )
    model, cv = train_transfer_model(train)
    lat_ms = benchmark_inference(model, feats.select(FEATURES).to_numpy()[12 * 24:13 * 24])

    # STEP 3
    recon, p3 = reconstruct_all_days(feats, meas, daily, model)
    recon.write_csv(PATH_RECON, datetime_format=DT_FMT)

    if verbose:
        _print_report(p1, cv, lat_ms, p3)
    return {"step1": p1, "cv": cv, "latency_ms": lat_ms, "step3": p3}


def main() -> None:
    print("=" * 66)
    print("SolarSense EMS — Forensic Repair & Weather-Anchored Reconstruction")
    print("=" * 66)
    run_repair(verbose=True)


if __name__ == "__main__":
    main()
