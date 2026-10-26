"""
SolarSense EMS — High-Performance Residential Load Forecaster
=============================================================
Trains, evaluates, and serializes a dual-model LightGBM forecasting bundle
for residential electricity demand in Lahore / urban Pakistan:
1. `point_model`: Regressor with cost-weighted loss (sample_weight=2.0 on LESCO peak
   hours 18:00–22:00) for the MILP battery energy balance.
2. `p90_model`: Quantile regressor (alpha=0.90) providing an upper-bound
   conservative margin for peak-shaving and outage reserve planning.

Key Invariants:
1. Cross-Target Isolation: Uses only calendar, weather (temp, humidity), and strictly causal demand lags (t <= t0).
2. Non-Crossing Invariant: Enforces p90 >= point >= 0.0 kW.
3. Sub-millisecond 24h inference on contiguous NumPy arrays.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

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

DEFAULT_MODEL_PATH = Path("models/residential_load_lightgbm.joblib")
LEGACY_MODEL_PATH = Path("models/factory_load_lightgbm.joblib")


class ResidentialLoadForecaster:
    """
    Production-grade dual-model inference and training wrapper for Residential Demand.
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
    def load(cls, path: Union[str, Path] = DEFAULT_MODEL_PATH) -> ResidentialLoadForecaster:
        path = Path(path)
        if not path.exists() and path == DEFAULT_MODEL_PATH and LEGACY_MODEL_PATH.exists():
            path = LEGACY_MODEL_PATH
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
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "point_model": self.point_model,
                "p90_model": self.p90_model,
                "feature_names": self.feature_names,
                "metadata": self.metadata,
            },
            path,
            compress=3,
        )

    def predict_24h(self, feature_matrix: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Runs vectorized 24h point and P90 inference with non-crossing guarantee."""
        if self.point_model is None or self.p90_model is None:
            raise RuntimeError("Models must be trained or loaded before running inference.")
        
        X = np.asarray(feature_matrix, dtype=np.float64)
        point = np.maximum(self.point_model.predict(X, num_threads=1), 0.0)
        p90 = np.maximum(self.p90_model.predict(X, num_threads=1), 0.0)
        p90 = np.maximum(p90, point)  # Non-crossing invariant
        return point, p90


# Compatibility alias
FactoryLoadForecaster = ResidentialLoadForecaster


def train_residential_load_model(
    repo: Optional[EMSDataRepository] = None,
    save_path: Union[str, Path] = DEFAULT_MODEL_PATH,
    random_state: int = 42,
) -> Tuple[ResidentialLoadForecaster, Dict[str, float]]:
    """Trains point and P90 LightGBM regressors on residential electricity demand."""
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

    # Sample weights: 2.0x during LESCO residential peak hours
    sample_weights_train = np.ones_like(y_train)
    for i in range(len(y_train)):
        h = int(X_train[i, h_idx])
        m = int(X_train[i, m_idx])
        is_peak = h in policy.get_peak_hours_for_month(m)
        if is_peak:
            sample_weights_train[i] = 2.0

    # 1. Point Estimator
    point_model = lgb.LGBMRegressor(
        objective="regression",
        n_estimators=300,
        learning_rate=0.03,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=random_state,
        n_jobs=-1,
        verbose=-1,
    )
    point_model.fit(
        X_train,
        y_train,
        sample_weight=sample_weights_train,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(stopping_rounds=30, verbose=False)],
    )

    # 2. P90 Quantile Estimator
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
        n_jobs=-1,
        verbose=-1,
    )
    p90_model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(stopping_rounds=30, verbose=False)],
    )

    forecaster = ResidentialLoadForecaster(
        point_model=point_model,
        p90_model=p90_model,
        feature_names=feature_names,
        metadata={"trained_at": datetime.now(PKT_TZ).isoformat()},
    )

    forecaster.save(save_path)
    # Also save to legacy path for backward compatibility
    forecaster.save(LEGACY_MODEL_PATH)

    # Evaluate on test set
    y_pred, y_p90 = forecaster.predict_24h(X_test)
    metrics = {
        "mae_kw": float(mean_absolute_error(y_test, y_pred)),
        "rmse_kw": float(root_mean_squared_error(y_test, y_pred)),
        "r2": float(r2_score(y_test, y_pred)),
        "p90_coverage": float(np.mean(y_test <= y_p90)),
    }
    return forecaster, metrics


if __name__ == "__main__":
    print("=" * 60)
    print("SolarSense EMS — Training Residential Load Forecaster")
    print("=" * 60)
    forecaster, metrics = train_residential_load_model()
    print(f"  MAE  : {metrics['mae_kw']:.3f} kW")
    print(f"  RMSE : {metrics['rmse_kw']:.3f} kW")
    print(f"  R2   : {metrics['r2']:.3f}")
    print(f"  P90 Coverage: {metrics['p90_coverage']*100:.1f}%")
    print("✅ Residential Load Forecaster trained and saved.")
