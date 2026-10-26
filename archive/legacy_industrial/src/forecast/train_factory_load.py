"""
SolarSense EMS — High-Performance Industrial Factory Load Forecaster
====================================================================
Trains, evaluates, and serializes a dual-model LightGBM forecasting bundle:
1. `point_model`: Regressor with cost-weighted loss (sample_weight=2.5 on LESCO peak
   hours and loads > 440 kW) for the MILP energy balance equality constraint.
2. `p90_model`: Quantile regressor (alpha=0.90) providing a conservative upper-bound
   envelope for the MILP 500 kW MDI peak-shaving constraint.

Key Invariants & Guarantees:
1. Cross-Target Isolation: Uses only calendar, shift, weather, and causal demand lags.
2. Non-Crossing Invariant: Enforces p90 >= point >= 0.0 kW across all hours.
3. Sub-Millisecond 24h Inference: Executed via num_threads=1 on contiguous NumPy arrays.
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

DEFAULT_MODEL_PATH = Path("models/factory_load_lightgbm.joblib")


class FactoryLoadForecaster:
    """
    Production-grade dual-model inference and training wrapper for Industrial Factory Load.
    """

    def __init__(
        self,
        point_model: Optional[lgb.LGBMRegressor] = None,
        p90_model: Optional[lgb.LGBMRegressor] = None,
        feature_names: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.point_model = point_model
        self.p90_model = p90_model
        self.feature_names = feature_names or []
        self.metadata = metadata or {}

    @classmethod
    def load(cls, path: Union[str, Path] = DEFAULT_MODEL_PATH) -> FactoryLoadForecaster:
        """Loads serialized dual estimator and feature schema from disk."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Model artifact not found at '{path}'")
        data = joblib.load(path)
        return cls(
            point_model=data["point_model"],
            p90_model=data["p90_model"],
            feature_names=data["feature_names"],
            metadata=data.get("metadata", {}),
        )

    def save(self, path: Union[str, Path] = DEFAULT_MODEL_PATH) -> None:
        """Serializes estimators and metadata via joblib."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "point_model": self.point_model,
                "p90_model": self.p90_model,
                "feature_names": self.feature_names,
                "metadata": self.metadata,
                "model_type": "Dual LightGBM Regressor (Factory Load: Point + P90)",
            },
            path,
        )

    def predict_24h(
        self,
        X_24: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Fast 24-hour dual-model inference pipeline (< 2.0 ms).
        
        Args:
            X_24: Contiguous 2D NumPy array of shape (24, n_features), dtype float64.
            
        Returns:
            Tuple of (point_kw, p90_kw), each a 1D contiguous array of shape (24,).
            Guarantees: p90_kw >= point_kw >= 0.0.
        """
        if self.point_model is None or self.p90_model is None:
            raise RuntimeError("Forecaster estimators have not been fitted or loaded")

        X_arr = np.ascontiguousarray(X_24, dtype=np.float64)

        # 1. Single-threaded prediction for both models
        raw_point = self.point_model.predict(X_arr, num_threads=1)
        raw_p90 = self.p90_model.predict(X_arr, num_threads=1)

        # 2. Non-crossing and non-negativity physical post-processing
        point_kw = np.maximum(raw_point, 0.0)
        p90_kw = np.maximum(raw_p90, point_kw)

        return (
            np.ascontiguousarray(point_kw, dtype=np.float64),
            np.ascontiguousarray(p90_kw, dtype=np.float64),
        )


def train_factory_load_model(
    repo: Optional[EMSDataRepository] = None,
    save_path: Union[str, Path] = DEFAULT_MODEL_PATH,
    random_state: int = 42,
) -> Tuple[FactoryLoadForecaster, Dict[str, float]]:
    """
    Trains the Dual LightGBM Factory Load Forecaster with cost-weighted point model
    and 90th percentile quantile upper-bound model.
    """
    if repo is None:
        repo = EMSDataRepository()

    splits = repo.get_ml_feature_matrix(task="load", purge_hours=24)
    feature_names = list(splits.feature_names)
    policy = TariffPolicy()

    X_train = splits.train_features.to_numpy().astype(np.float64)
    y_train = splits.train_target.astype(np.float64)
    X_val = splits.val_features.to_numpy().astype(np.float64)
    y_val = splits.val_target.astype(np.float64)
    X_test = splits.test_features.to_numpy().astype(np.float64)
    y_test = splits.test_target.astype(np.float64)

    h_idx = feature_names.index("hour")
    m_idx = feature_names.index("month")

    # Sample weights for point model: 2.5x on LESCO peak hours or near-ceiling loads (> 440 kW)
    sample_weights_train = np.ones_like(y_train)
    for i in range(len(y_train)):
        h = int(X_train[i, h_idx])
        m = int(X_train[i, m_idx])
        is_peak = h in policy.get_peak_hours_for_month(m)
        if is_peak or y_train[i] > 440.0:
            sample_weights_train[i] = 2.5

    # 1. Point Estimator (Mean / Energy Balance)
    point_model = lgb.LGBMRegressor(
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

    t0_fit = time.perf_counter()
    point_model.fit(
        X_train,
        y_train,
        sample_weight=sample_weights_train,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(stopping_rounds=30, verbose=False)],
    )

    # 2. P90 Estimator (Quantile Upper Bound for 500 kW MDI Shaving)
    p90_model = lgb.LGBMRegressor(
        objective="quantile",
        alpha=0.90,
        n_estimators=300,
        learning_rate=0.03,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=random_state,
        n_jobs=4,
    )
    p90_model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(stopping_rounds=30, verbose=False)],
    )
    fit_duration_ms = (time.perf_counter() - t0_fit) * 1000

    forecaster = FactoryLoadForecaster(
        point_model=point_model,
        p90_model=p90_model,
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
    raw_point_test = forecaster.point_model.predict(X_test, num_threads=1)
    raw_p90_test = forecaster.p90_model.predict(X_test, num_threads=1)

    point_test = np.maximum(raw_point_test, 0.0)
    p90_test = np.maximum(raw_p90_test, point_test)

    r2 = float(r2_score(y_test, point_test))
    mae = float(mean_absolute_error(y_test, point_test))
    rmse = float(root_mean_squared_error(y_test, point_test))

    # Persistence baseline (lag_24h)
    lag_24h_idx = feature_names.index("lag_24h")
    baseline_preds = X_test[:, lag_24h_idx]
    baseline_mae = float(mean_absolute_error(y_test, baseline_preds))

    # LESCO peak window evaluation
    peak_mask = np.array([
        int(h) in policy.get_peak_hours_for_month(int(m))
        for h, m in zip(X_test[:, h_idx], X_test[:, m_idx])
    ])
    peak_window_mae = (
        float(mean_absolute_error(y_test[peak_mask], point_test[peak_mask]))
        if np.any(peak_mask)
        else 0.0
    )

    # P90 empirical coverage (% of test actuals <= p90 forecast)
    p90_coverage = float(np.mean(y_test <= p90_test))

    # Benchmark 24-hour dual inference latency
    X_24 = np.ascontiguousarray(X_test[:24, :], dtype=np.float64)
    latencies = []
    for _ in range(200):
        t_start = time.perf_counter()
        _ = forecaster.predict_24h(X_24)
        latencies.append((time.perf_counter() - t_start) * 1000)
    avg_latency_ms = sum(latencies) / len(latencies)

    metrics = {
        "point_r2": round(r2, 4),
        "point_mae_kw": round(mae, 4),
        "point_rmse_kw": round(rmse, 4),
        "peak_window_mae_kw": round(peak_window_mae, 4),
        "baseline_mae_kw": round(baseline_mae, 4),
        "p90_coverage_pct": round(p90_coverage * 100.0, 2),
        "avg_24h_dual_inference_latency_ms": round(avg_latency_ms, 4),
    }
    forecaster.metadata["metrics"] = metrics

    # Save artifact
    forecaster.save(save_path)

    return forecaster, metrics


if __name__ == "__main__":
    print("=" * 70)
    print("SolarSense EMS — Training Dual LightGBM Factory Load Forecaster")
    print("=" * 70)
    forecaster, metrics = train_factory_load_model()
    print(f"Training completed. Model serialized to '{DEFAULT_MODEL_PATH}'")
    print(f"Holdout Point Test R²:              {metrics['point_r2']:.4f}")
    print(f"Holdout Point Test MAE:             {metrics['point_mae_kw']:.4f} kW")
    print(f"Holdout Point Test RMSE:            {metrics['point_rmse_kw']:.4f} kW")
    print(f"LESCO Peak-Window MAE:              {metrics['peak_window_mae_kw']:.4f} kW")
    print(f"P90 Quantile Empirical Coverage:    {metrics['p90_coverage_pct']:.2f}% (Target: ~90.0%)")
    print(f"24-Hour Dual Inference Latency:     {metrics['avg_24h_dual_inference_latency_ms']:.4f} ms (Budget: < 2.0 ms)")
    print("=" * 70)
