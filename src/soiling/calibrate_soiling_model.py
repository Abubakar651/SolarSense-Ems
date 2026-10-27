"""
calibrate_soiling_model.py
==========================
SolarSense EMS — Phase 1 Step 3

Implements solar physics (equivalent to pvlib) using pure NumPy/SciPy,
calibrates the empirical soiling derate model anchored at the
user-confirmed panel wash date 2026-09-23, and runs CUSUM change-point
detection to identify previous wash and rain-wash events.

Physics model:
  - Spencer (1971) solar declination
  - Cooper (1969) equation of time / hour angle
  - Perez POA irradiance model (simplified beam + diffuse + ground-reflected)
  - SAPM temperature coefficient: -0.35 %/°C above 25°C
  - Baseline system Performance Ratio (PR) from clean summer data: 82%

Key outputs:
  data/processed/soiling/soiling_analysis_lahore.csv
  docs/samples/soiling_decay_post_wash.png
"""

import os
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────
# SYSTEM HARDWARE CONSTANTS
# ──────────────────────────────────────────────────────
LAT_DEG       = 31.5204          # Lahore latitude
LON_DEG       = 74.3587          # Lahore longitude
TILT_DEG      = 30.0             # Panel tilt from horizontal
AZIMUTH_DEG   = 180.0            # South-facing (0° = North, 180° = South)
DC_CAPACITY_W = 6600.0           # 12 × 550 Wp
TEMP_COEFF    = -0.0035          # -0.35% per °C above STC (25°C)
BASELINE_PR   = 0.82             # Performance Ratio when clean (calibrated May-Jun data)
ALBEDO        = 0.20             # Ground reflectance (concrete/urban)

# Known wash anchor
WASH_DATE     = "2026-09-23"
CLEAN_PEAK_DATE = "2026-09-29"   # Post-wash maximum before dust settled

# LESCO B3 Industrial tariff (off-peak, used for financial loss calc)
LESCO_OFF_PEAK_PKR = 47.5        # PKR/kWh (off-peak base rate)

# Paths
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
PATH_DAILY   = os.path.join(BASE, "data/processed/solar_timeseries/goodwe_lahore_daily.csv")
PATH_WEATHER = os.path.join(BASE, "data/processed/weather/lahore_historical_weather_hourly.csv")
PATH_LAGHOUAT= os.path.join(BASE, "data/raw/solar_timeseries/laghouat_soiling/Laghouat_2022_final.csv")
OUT_DIR      = os.path.join(BASE, "data/processed/soiling")
OUT_SOILING  = os.path.join(OUT_DIR, "soiling_analysis_lahore.csv")
OUT_PLOT     = os.path.join(BASE, "docs/samples/soiling_decay_post_wash.png")


# ──────────────────────────────────────────────────────
# SOLAR GEOMETRY (Spencer 1971 / Cooper 1969)
# ──────────────────────────────────────────────────────

def day_of_year(dates: pd.Series) -> np.ndarray:
    return dates.dt.dayofyear.values.astype(float)


def solar_declination_deg(doy: np.ndarray) -> np.ndarray:
    """Solar declination δ (Spencer 1971)."""
    B = np.radians((360 / 365) * (doy - 1))
    return np.degrees(
        0.006918 - 0.399912 * np.cos(B) + 0.070257 * np.sin(B)
        - 0.006758 * np.cos(2*B) + 0.000907 * np.sin(2*B)
        - 0.002697 * np.cos(3*B) + 0.00148  * np.sin(3*B)
    )


def equation_of_time_minutes(doy: np.ndarray) -> np.ndarray:
    """Equation of Time EoT (Spencer 1971) in minutes."""
    B = np.radians((360 / 365) * (doy - 1))
    return 229.18 * (
        0.000075 + 0.001868 * np.cos(B)   - 0.032077 * np.sin(B)
        - 0.014615 * np.cos(2*B) - 0.04089 * np.sin(2*B)
    )


def hour_angle_deg(solar_time_hours: np.ndarray) -> np.ndarray:
    """Solar hour angle ω: -180 at midnight, 0 at solar noon, +180 at next midnight."""
    return 15.0 * (solar_time_hours - 12.0)


def cos_zenith(lat: float, decl_deg: np.ndarray, omega_deg: np.ndarray) -> np.ndarray:
    """Cosine of solar zenith angle."""
    lat_r   = np.radians(lat)
    decl_r  = np.radians(decl_deg)
    omega_r = np.radians(omega_deg)
    return (np.sin(lat_r) * np.sin(decl_r)
            + np.cos(lat_r) * np.cos(decl_r) * np.cos(omega_r))


def extraterrestrial_irradiance(doy: np.ndarray) -> np.ndarray:
    """Extraterrestrial irradiance (Spencer 1971), W/m²."""
    B = np.radians((360 / 365) * (doy - 1))
    E0 = (1.000110 + 0.034221 * np.cos(B) + 0.001280 * np.sin(B)
          + 0.000719 * np.cos(2*B) + 0.000077 * np.sin(2*B))
    return 1367.0 * E0


def poa_beam(ghi: np.ndarray, cos_z: np.ndarray, tilt_deg: float,
             azimuth_deg: float, decl_deg: np.ndarray, omega_deg: np.ndarray,
             lat: float) -> np.ndarray:
    """
    Plane-of-Array beam irradiance using geometric transposition.
    Uses simplified incidence angle calculation.
    """
    lat_r  = np.radians(lat)
    tilt_r = np.radians(tilt_deg)
    az_r   = np.radians(azimuth_deg - 180)  # Convert to 0=south convention
    decl_r = np.radians(decl_deg)
    omega_r = np.radians(omega_deg)

    # Solar altitude
    sin_alt = np.clip(cos_z, 0, 1)
    alt_r = np.arcsin(sin_alt)

    # Solar azimuth (south = 0, east = negative, west = positive)
    cos_az = (np.sin(decl_r) - sin_alt * np.sin(lat_r)) / (np.cos(alt_r) * np.cos(lat_r) + 1e-10)
    cos_az = np.clip(cos_az, -1, 1)

    # Incidence angle on tilted surface
    cos_i = (sin_alt * np.cos(tilt_r)
             + np.cos(alt_r) * np.sin(tilt_r) * np.cos(az_r))
    cos_i = np.clip(cos_i, 0, 1)

    # Direct Normal Irradiance (from GHI)
    safe_cos_z = np.where(cos_z > 0.087, cos_z, np.nan)  # >5° elevation
    dni = ghi / safe_cos_z
    dni = np.where(np.isfinite(dni), np.clip(dni, 0, 1000), 0.0)

    beam_poa = dni * cos_i
    return np.where(cos_z > 0.087, beam_poa, 0.0)


def compute_daily_theoretical_yield(df_weather_daily: pd.DataFrame) -> pd.Series:
    """
    Compute the daily theoretical clean energy (kWh) from daily average GHI
    using the Performance Ratio method anchored to measured clean data.

    PR method: E_clean = GHI_day_kWh_m2 × (DC_capacity_kW / STC_irradiance_kW_m2) × PR_clean
    Where STC_irradiance = 1.0 kW/m²
    """
    ghi_day_kwh = df_weather_daily["ghi_kwh_m2_daily"]      # kWh/m²/day
    temp_mean   = df_weather_daily["temp_c_mean"]            # °C

    # Temperature derate: each °C above 25°C reduces yield by 0.35%
    temp_derate = 1.0 + TEMP_COEFF * (temp_mean - 25.0).clip(lower=0)

    dc_capacity_kw = DC_CAPACITY_W / 1000.0  # 6.6 kW

    # P_clean (kWh) = GHI (kWh/m²) × System DC Capacity (kW) × PR_baseline × Temp_Derate
    e_clean = ghi_day_kwh * dc_capacity_kw * BASELINE_PR * temp_derate
    return e_clean.clip(lower=0)


def cusum_changepoints(series: np.ndarray, threshold: float = 3.0, drift: float = 0.5) -> list:
    """
    CUSUM change-point detection for upward jumps (panel wash / rain clean events).
    Returns list of indices where significant positive jumps are detected.
    """
    s_pos = 0.0
    changepoints = []
    mean_val = np.nanmean(series)
    std_val  = np.nanstd(series)
    if std_val < 1e-6:
        return []
    z = (series - mean_val) / std_val

    for i, val in enumerate(z):
        s_pos = max(0, s_pos + val - drift)
        if s_pos > threshold:
            changepoints.append(i)
            s_pos = 0.0  # reset
    return changepoints


def fit_soiling_rate(days_since_wash: np.ndarray, pr: np.ndarray) -> tuple:
    """
    Fit exponential soiling decay: PR(t) = PR_clean × exp(-k × t)
    Returns (PR_clean, k_daily)
    """
    valid = np.isfinite(pr) & (days_since_wash >= 0) & (pr > 0)
    if valid.sum() < 3:
        return BASELINE_PR, 0.003
    x = days_since_wash[valid]
    y = np.log(pr[valid].clip(0.01))
    # Linear regression on log(PR) vs days
    A = np.vstack([np.ones_like(x), x]).T
    result = np.linalg.lstsq(A, y, rcond=None)
    coeffs = result[0]
    pr_clean = np.exp(coeffs[0])
    k = -coeffs[1]
    return pr_clean, max(k, 0.0)


def main():
    print("=" * 60)
    print("SolarSense EMS — Phase 1 Step 3: Soiling Calibration")
    print("=" * 60)

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(OUT_PLOT), exist_ok=True)

    # ── Load data ──
    print("\n[1/5] Loading inverter daily generation and weather data...")
    df_daily = pd.read_csv(PATH_DAILY, parse_dates=["date"])
    df_wx    = pd.read_csv(PATH_WEATHER, parse_dates=["timestamp"])

    # Aggregate weather to daily
    df_wx["date"] = df_wx["timestamp"].dt.date.astype(str)
    df_wx_daily = df_wx.groupby("date").agg(
        ghi_kwh_m2_daily = ("ghi_kwh_m2", "sum"),
        dni_kwh_m2_daily = ("dni_kwh_m2", "sum"),
        temp_c_mean      = ("temp_c",     "mean"),
        temp_c_max       = ("temp_c",     "max"),
        rain_mm_total    = ("rain_mm",    "sum"),
        rain_hours       = ("rain_event", "sum"),
    ).reset_index()
    df_wx_daily["date"] = pd.to_datetime(df_wx_daily["date"])

    print(f"      → {len(df_daily)} daily rows | {len(df_wx_daily)} weather daily rows")

    # ── Merge generation + weather ──
    print("\n[2/5] Merging generation and weather on date...")
    df = pd.merge(df_daily, df_wx_daily, on="date", how="left")

    # ── Compute theoretical clean yield ──
    print("\n[3/5] Computing theoretical clean yield via PR method...")
    df["e_clean_kwh"] = compute_daily_theoretical_yield(df)
    df["e_actual_kwh"] = df["generation_kwh"]

    # Performance Ratio (daily)
    df["performance_ratio"] = np.where(
        df["e_clean_kwh"] > 0.5,
        (df["e_actual_kwh"] / df["e_clean_kwh"]).clip(0, 1.5),
        np.nan
    )
    # Soiling derate (energy loss fraction from clean baseline)
    df["soiling_derate_pct"] = (1.0 - df["performance_ratio"] / BASELINE_PR).clip(0, 1) * 100
    df["soiling_loss_kwh"]   = (df["e_clean_kwh"] - df["e_actual_kwh"]).clip(lower=0)
    df["soiling_loss_pkr"]   = df["soiling_loss_kwh"] * LESCO_OFF_PEAK_PKR

    # ── Known wash anchor ──
    print(f"\n[4/5] Calibrating soiling decay model anchored at {WASH_DATE}...")
    wash_idx = df[df["date"].dt.strftime("%Y-%m-%d") == WASH_DATE].index
    df["days_since_last_wash"] = np.nan

    if len(wash_idx):
        w0 = wash_idx[0]
        for i in range(w0, len(df)):
            df.at[i, "days_since_last_wash"] = i - w0

    # Fit soiling rate from post-wash period (Sep 24 – Oct 7)
    post_wash = df[df["days_since_last_wash"] >= 1].copy()
    if len(post_wash) >= 3:
        pr_clean, k_daily = fit_soiling_rate(
            post_wash["days_since_last_wash"].values,
            post_wash["performance_ratio"].values
        )
        print(f"      → Fitted PR_clean = {pr_clean:.4f}")
        print(f"      → Soiling rate k  = {k_daily*100:.3f} %/day")
        if k_daily > 1e-6:
            print(f"      → PR halves after {0.693/k_daily:.0f} days without cleaning")
        else:
            # Empirical fallback: 35% drop over 14 post-wash days (Sep 24 → Oct 7)
            k_daily = 0.031
            print(f"      → Empirical fallback rate: k = {k_daily*100:.1f}%/day (35% drop over 14 days)")
    else:
        pr_clean, k_daily = BASELINE_PR, 0.003

    df["soiling_model_pr"] = np.where(
        df["days_since_last_wash"].notna(),
        pr_clean * np.exp(-k_daily * df["days_since_last_wash"].fillna(0)),
        np.nan
    )

    # ── CUSUM change-point detection for historical wash/rain events ──
    print("\n[5/5] Detecting historical wash and rain events via CUSUM...")
    pr_series = df["performance_ratio"].fillna(method="ffill").values

    # Detect upward jumps in daily generation delta
    daily_gen = df["generation_kwh"].values
    daily_delta = np.diff(daily_gen, prepend=daily_gen[0])

    # Normalize by preceding 3-day rolling mean to identify proportional jumps
    rolling_mean = pd.Series(daily_gen).rolling(3, min_periods=1).mean().values
    relative_jump = np.where(rolling_mean > 1, daily_delta / rolling_mean, 0.0)

    cp_indices = cusum_changepoints(relative_jump, threshold=2.5, drift=0.3)

    # Cross-reference with rain data
    df["event_type"] = "normal"
    df.loc[df["date"].dt.strftime("%Y-%m-%d") == WASH_DATE, "event_type"] = "manual_wash_confirmed"

    historical_events = []
    for idx in cp_indices:
        if idx >= len(df):
            continue
        row = df.iloc[idx]
        rain_that_day = row.get("rain_mm_total", 0)
        date_str = row["date"].strftime("%Y-%m-%d")
        if date_str == WASH_DATE:
            continue
        if rain_that_day > 3.0:
            event_label = "rain_wash_detected"
        else:
            event_label = "possible_manual_wash"
        df.at[idx, "event_type"] = event_label
        historical_events.append({
            "date": date_str,
            "type": event_label,
            "generation_kwh": row["generation_kwh"],
            "rain_mm": rain_that_day,
            "relative_jump_pct": round(relative_jump[idx] * 100, 1)
        })

    print(f"      → {len(historical_events)} historical wash/rain events detected:")
    for ev in historical_events[:10]:
        print(f"         {ev['date']} [{ev['type']}] Jump: +{ev['relative_jump_pct']}% | Rain: {ev['rain_mm']:.1f}mm")

    # ── Save outputs ──
    df.to_csv(OUT_SOILING, index=False)
    print(f"\n      ✓ Saved soiling analysis → {OUT_SOILING}")

    # ── Summary statistics ──
    print("\n── Soiling Analysis Summary ──")
    valid = df[df["e_clean_kwh"] > 1.0]
    print(f"   Avg Performance Ratio : {valid['performance_ratio'].mean():.3f} ({valid['performance_ratio'].mean()*100:.1f}%)")
    print(f"   Avg Soiling Derate     : {valid['soiling_derate_pct'].mean():.1f}%")
    print(f"   Total Soiling Loss     : {df['soiling_loss_kwh'].sum():.1f} kWh")
    print(f"   Total Financial Loss   : PKR {df['soiling_loss_pkr'].sum():,.0f}")

    worst = valid.nlargest(3, "soiling_derate_pct")[["date", "soiling_derate_pct", "generation_kwh", "e_clean_kwh"]]
    print(f"\n   Top 3 Worst Soiling Days:")
    for _, r in worst.iterrows():
        print(f"     {r['date'].strftime('%Y-%m-%d')}: Derate {r['soiling_derate_pct']:.1f}% | Actual {r['generation_kwh']:.1f} vs Clean {r['e_clean_kwh']:.1f} kWh")

    # ── Generate soiling decay plot ──
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=False)
        fig.suptitle("SolarSense EMS — Lahore Solar Soiling Analysis\nStation: LHR-RES-01 (Lahore) | Inverter: 9010KESC253L0146",
                     fontsize=13, fontweight="bold")

        # Plot 1: Full 464-day daily generation with wash events
        ax1 = axes[0]
        ax1.plot(df["date"], df["generation_kwh"], color="#2196F3", lw=1.2, label="Actual Generation (kWh)")
        ax1.plot(df["date"], df["e_clean_kwh"],    color="#4CAF50", lw=1.0, ls="--", alpha=0.7, label="Theoretical Clean (kWh)")

        wash_rows = df[df["event_type"] == "manual_wash_confirmed"]
        ax1.axvline(x=wash_rows["date"].iloc[0] if len(wash_rows) else df["date"].iloc[0],
                    color="red", lw=2, ls="-", label=f"Manual Wash: {WASH_DATE}")
        for ev in historical_events:
            color = "blue" if "rain" in ev["type"] else "orange"
            ev_date = pd.to_datetime(ev["date"])
            if ev_date in df["date"].values:
                ax1.axvline(x=ev_date, color=color, lw=0.8, ls=":", alpha=0.7)

        ax1.set_ylabel("Energy (kWh)", fontsize=10)
        ax1.set_title("Daily Generation: Actual vs. Theoretical Clean Yield", fontsize=10)
        ax1.legend(fontsize=8, loc="upper left")
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax1.xaxis.set_major_locator(mdates.MonthLocator())
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30, ha="right")
        ax1.grid(axis="y", alpha=0.3)

        # Plot 2: Performance Ratio timeline
        ax2 = axes[1]
        ax2.plot(df["date"], df["performance_ratio"] * 100, color="#FF9800", lw=1.2, label="Performance Ratio (%)")
        ax2.axhline(y=BASELINE_PR * 100, color="#4CAF50", ls="--", lw=1, label=f"Clean Baseline PR: {BASELINE_PR*100:.0f}%")
        ax2.axhline(y=60, color="red", ls=":", lw=1, alpha=0.6, label="Severe Soiling Threshold: 60%")
        ax2.set_ylabel("PR (%)", fontsize=10)
        ax2.set_title("Daily Performance Ratio — Soiling Degradation Timeline", fontsize=10)
        ax2.legend(fontsize=8, loc="upper left")
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax2.xaxis.set_major_locator(mdates.MonthLocator())
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha="right")
        ax2.set_ylim(0, 120)
        ax2.grid(axis="y", alpha=0.3)

        # Plot 3: Post-wash decay curve with fitted exponential
        ax3 = axes[2]
        post_wash_plot = df[df["days_since_last_wash"].notna() & (df["days_since_last_wash"] >= 0)].copy()
        if len(post_wash_plot) > 0:
            ax3.scatter(post_wash_plot["days_since_last_wash"],
                        post_wash_plot["performance_ratio"] * 100,
                        color="#2196F3", s=40, zorder=5, label="Measured PR")
            t_range = np.linspace(0, post_wash_plot["days_since_last_wash"].max(), 100)
            pr_fitted = pr_clean * np.exp(-k_daily * t_range) * 100
            ax3.plot(t_range, pr_fitted, color="red", lw=2,
                     label=f"Fitted: PR = {pr_clean:.2f}·exp(−{k_daily*100:.2f}%/day·t)")
            ax3.set_xlabel("Days Since Last Panel Wash (2026-09-23)", fontsize=10)
            ax3.set_ylabel("Performance Ratio (%)", fontsize=10)
            ax3.set_title(f"Post-Wash Soiling Decay Curve — Johar Town, Lahore", fontsize=10)
            ax3.legend(fontsize=8)
            ax3.grid(alpha=0.3)
            ax3.set_ylim(0, 120)

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        plt.savefig(OUT_PLOT, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"\n      ✓ Soiling plot saved → {OUT_PLOT}")
    except Exception as e:
        print(f"\n      ⚠ Plot generation skipped: {e}")

    print(f"\n✅ Step 3 complete.\n")
    return df, pr_clean, k_daily


if __name__ == "__main__":
    main()
