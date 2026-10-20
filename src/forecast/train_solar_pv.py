"""
SolarSense EMS — High-Performance LightGBM Solar PV Generation Forecaster
=========================================================================
Trains, evaluates, and serializes a production-grade LightGBM regressor predicting
hourly solar PV generation (kW) from weather telemetry and causal historical lags.

Key Invariants & Guarantees:
1. Physical Zero at Night: Generation strictly forced to 0.0 kW when GHI <= 0.
2. Capacity Clipping: Predictions bounded to [0.0, 600.0] kW (installed capacity).
3. Causal Boundary: All features known at or before t <= t0 (24h purge gap).
4. Sub-Millisecond 24h Inference: Executed via num_threads=1 on contiguous NumPy arrays.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Add project root to sys.path for direct CLI execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib
import lightgbm as lgb
import numpy as np
import polars as pl
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error

from src.data_engineering.feature_store import (
    EMSDataRepository,
    TariffPolicy,
    PKT_TZ,
)

DEFAULT_MODEL_PATH = Path("models/solar_pv_lightgbm.joblib")


class SolarPVForecaster:
    """
    Production-grade inference and training wrapper for Solar PV generation.
    """

    def __init__(
        self,
        model: Optional[lgb.LGBMRegressor] = None,
        feature_names: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.model = model
        self.feature_names = feature_names or []
        self.metadata = metadata or {}
        self._ghi_idx: int = (
            self.feature_names.index("ghi_wm2") if "ghi_wm2" in self.feature_names else 0
        )

    @classmethod
    def load(cls, path: Union[str, Path] = DEFAULT_MODEL_PATH) -> SolarPVForecaster:
        """Loads serialized estimator and feature schema from disk."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Model artifact not found at '{path}'")
        data = joblib.load(path)
        return cls(
            model=data["model"],
            feature_names=data["feature_names"],
            metadata=data.get("metadata", {}),
        )

    def save(self, path: Union[str, Path] = DEFAULT_MODEL_PATH) -> None:
        """Serializes estimator and metadata via joblib."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "model": self.model,
                "feature_names": self.feature_names,
                "metadata": self.metadata,
                "model_type": "LightGBM Regressor (Solar PV)",
            },
            path,
        )

    def predict_24h(
        self,
        X_24: np.ndarray,
        ghi_24: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Fast 24-hour inference pipeline adhering to Section 2 latency budgets (< 2.0 ms).
        
        Args:
            X_24: Contiguous 2D NumPy array of shape (24, n_features), dtype float64.
            ghi_24: Optional 1D vector of GHI values of shape (24,). If omitted,
                    extracted from X_24[:, ghi_idx].
        """
        if self.model is None:
            raise RuntimeError("Forecaster has not been fitted or loaded")

        # 1. Single-threaded inference to eliminate OpenMP thread synchronization overhead
        X_arr = np.ascontiguousarray(X_24, dtype=np.float64)
        raw_preds = self.model.predict(X_arr, num_threads=1)

        # 2. Extract GHI vector for physical zero enforcement
        if ghi_24 is None:
            ghi_vec = X_arr[:, self._ghi_idx]
        else:
            ghi_vec = np.asarray(ghi_24, dtype=np.float64)

        # 3. Physical bounds clipping: [0.0, 600.0] kW and strict 0.0 at night (GHI <= 0)
        clipped_preds = np.clip(raw_preds, 0.0, 600.0)
        final_preds = np.where(ghi_vec <= 0.0, 0.0, clipped_preds)

        return np.ascontiguousarray(final_preds, dtype=np.float64)


def train_solar_pv_model(
    repo: Optional[EMSDataRepository] = None,
    save_path: Union[str, Path] = DEFAULT_MODEL_PATH,
    random_state: int = 42,
) -> Tuple[SolarPVForecaster, Dict[str, float]]:
    """
    Trains the LightGBM Solar PV Forecaster on historical data with 24-hour purge gap.
    """
    if repo is None:
        repo = EMSDataRepository()

    splits = repo.get_ml_feature_matrix(task="solar", purge_hours=24)
    feature_names = list(splits.feature_names)

    X_train = splits.train_features.to_numpy().astype(np.float64)
    y_train = splits.train_target.astype(np.float64)
    X_val = splits.val_features.to_numpy().astype(np.float64)
    y_val = splits.val_target.astype(np.float64)
    X_test = splits.test_features.to_numpy().astype(np.float64)
    y_test = splits.test_target.astype(np.float64)

    ghi_idx = feature_names.index("ghi_wm2")

    # Hyperparameters tuned for solar diurnal curves and weather transients
    model = lgb.LGBMRegressor(
        objective="regression",
        n_estimators=300,
        learning_rate=0.03,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=random_state,
        n_jobs=4,
    )

    t0 = time.perf_counter()
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(stopping_rounds=30, verbose=False)],
    )
    fit_duration_ms = (time.perf_counter() - t0) * 1000

    forecaster = SolarPVForecaster(
        model=model,
        feature_names=feature_names,
        metadata={
            "train_rows": splits.metadata["train_rows"],
            "val_rows": splits.metadata["val_rows"],
            "test_rows": splits.metadata["test_rows"],
            "trained_at": datetime.now(PKT_TZ).isoformat(),
            "fit_duration_ms": round(fit_duration_ms, 2),
        },
    )

    # Evaluate on holdout test partition
    raw_test_preds = forecaster.model.predict(X_test, num_threads=1)
    test_preds = np.clip(raw_test_preds, 0.0, 600.0)
    test_preds = np.where(X_test[:, ghi_idx] <= 0.0, 0.0, test_preds)

    r2 = float(r2_score(y_test, test_preds))
    mae = float(mean_absolute_error(y_test, test_preds))
    rmse = float(root_mean_squared_error(y_test, test_preds))

    # Persistence baseline (lag_24h)
    lag_24h_idx = feature_names.index("lag_24h")
    baseline_preds = X_test[:, lag_24h_idx]
    baseline_mae = float(mean_absolute_error(y_test, baseline_preds))

    # LESCO seasonal peak window evaluation
    policy = TariffPolicy()
    h_idx = feature_names.index("hour")
    m_idx = feature_names.index("month")
    peak_mask = np.array([
        int(h) in policy.get_peak_hours_for_month(int(m))
        for h, m in zip(X_test[:, h_idx], X_test[:, m_idx])
    ])
    peak_window_mae = (
        float(mean_absolute_error(y_test[peak_mask], test_preds[peak_mask]))
        if np.any(peak_mask)
        else 0.0
    )

    # Benchmark 24-hour inference latency
    X_24 = np.ascontiguousarray(X_test[:24, :], dtype=np.float64)
    latencies = []
    for _ in range(200):
        t_start = time.perf_counter()
        _ = forecaster.predict_24h(X_24)
        latencies.append((time.perf_counter() - t_start) * 1000)
    avg_latency_ms = sum(latencies) / len(latencies)

    metrics = {
        "r2": round(r2, 4),
        "mae_kw": round(mae, 4),
        "rmse_kw": round(rmse, 4),
        "peak_window_mae_kw": round(peak_window_mae, 4),
        "baseline_mae_kw": round(baseline_mae, 4),
        "avg_24h_inference_latency_ms": round(avg_latency_ms, 4),
    }
    forecaster.metadata["metrics"] = metrics

    # Save artifact
    forecaster.save(save_path)

    return forecaster, metrics


if __name__ == "__main__":
    print("=" * 70)
    print("SolarSense EMS — Training LightGBM Solar PV Generation Forecaster")
    print("=" * 70)
    forecaster, metrics = train_solar_pv_model()
    print(f"Training completed. Model serialized to '{DEFAULT_MODEL_PATH}'")
    print(f"Holdout Test R² Score:              {metrics['r2']:.4f} (Target: >= 0.90)")
    print(f"Holdout Test MAE:                   {metrics['mae_kw']:.4f} kW")
    print(f"Holdout Test RMSE:                  {metrics['rmse_kw']:.4f} kW")
    print(f"LESCO Peak-Window MAE:              {metrics['peak_window_mae_kw']:.4f} kW")
    print(f"Persistence Baseline MAE:           {metrics['baseline_mae_kw']:.4f} kW")
    print(f"24-Hour Inference Latency:          {metrics['avg_24h_inference_latency_ms']:.4f} ms (Budget: < 2.0 ms)")
    print("=" * 70)
