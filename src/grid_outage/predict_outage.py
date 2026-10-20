"""
SolarSense EMS — High-Performance Calibrated Grid Outage Risk Predictor
=======================================================================
Trains, calibrates, and serializes a probabilistic LightGBM classifier predicting
hourly grid outage probabilities P(outage) in [0.0, 1.0] for Lahore feeder circuits.

Key Invariants & Guarantees:
1. Platt Sigmoid Calibration: Trained base estimator on `train` partition; calibrated
   strictly on chronological `val` partition using 1D Logistic Regression on log-odds.
   Eliminates Isotonic step-function overfitting on sparse blackout clusters.
2. Cost-Optimal Decision Threshold: Calibrates operational trigger balancing 95 PKR/kWh
   diesel backup fuel cost against 22 PKR/kWh arbitrage opportunity cost.
3. Proper Scoring Rules: Evaluated on PR-AUC, ROC-AUC, and Brier Score.
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
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from src.data_engineering.feature_store import (
    EMSDataRepository,
    PKT_TZ,
)

DEFAULT_MODEL_PATH = Path("models/outage_classifier.joblib")


class OutageRiskPredictor:
    """
    Production-grade inference and training wrapper for Grid Blackout Risk Prediction.
    """

    def __init__(
        self,
        base_model: Optional[lgb.LGBMClassifier] = None,
        calibrator: Optional[LogisticRegression] = None,
        feature_names: Optional[List[str]] = None,
        optimal_threshold: float = 0.25,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.base_model = base_model
        self.calibrator = calibrator
        self.feature_names = feature_names or []
        self.optimal_threshold = optimal_threshold
        self.metadata = metadata or {}

    @classmethod
    def load(cls, path: Union[str, Path] = DEFAULT_MODEL_PATH) -> OutageRiskPredictor:
        """Loads serialized classifier, calibrator, and metadata from disk."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Model artifact not found at '{path}'")
        data = joblib.load(path)
        return cls(
            base_model=data["base_model"],
            calibrator=data["calibrator"],
            feature_names=data["feature_names"],
            optimal_threshold=data.get("optimal_threshold", 0.25),
            metadata=data.get("metadata", {}),
        )

    def save(self, path: Union[str, Path] = DEFAULT_MODEL_PATH) -> None:
        """Serializes predictor, calibrator, and metadata via joblib."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "base_model": self.base_model,
                "calibrator": self.calibrator,
                "feature_names": self.feature_names,
                "optimal_threshold": self.optimal_threshold,
                "metadata": self.metadata,
                "model_type": "Calibrated LightGBM (Platt Sigmoid Outage Classifier)",
            },
            path,
        )

    def predict_proba_24h(
        self,
        X_24: np.ndarray,
    ) -> np.ndarray:
        """
        Fast 24-hour calibrated probabilistic inference (< 1.5 ms).
        
        Args:
            X_24: Contiguous 2D NumPy array of shape (24, n_features), dtype float64.
            
        Returns:
            1D array of calibrated outage probabilities P(outage) in [0.0, 1.0], shape (24,).
        """
        if self.base_model is None or self.calibrator is None:
            raise RuntimeError("Predictor estimators have not been fitted or loaded")

        X_arr = np.ascontiguousarray(X_24, dtype=np.float64)

        # 1. Base uncalibrated prediction with single-threading
        raw_probs = self.base_model.predict_proba(X_arr, num_threads=1)[:, 1]
        clipped_raw = np.clip(raw_probs, 1e-6, 1.0 - 1e-6)

        # 2. Platt Sigmoid Calibration via learned Logistic Regression on log-odds
        log_odds = logit(clipped_raw).reshape(-1, 1)
        calibrated_probs = self.calibrator.predict_proba(log_odds)[:, 1]

        # 3. Probability bounds guarantee
        final_probs = np.clip(calibrated_probs, 0.0, 1.0)
        return np.ascontiguousarray(final_probs, dtype=np.float64)

    def is_reserve_triggered(self, prob_outage: float) -> bool:
        """Evaluates whether predicted risk breaches the cost-optimal battery reserve threshold."""
        return float(prob_outage) >= self.optimal_threshold


def train_outage_classifier(
    repo: Optional[EMSDataRepository] = None,
    save_path: Union[str, Path] = DEFAULT_MODEL_PATH,
    random_state: int = 42,
) -> Tuple[OutageRiskPredictor, Dict[str, float]]:
    """
    Trains and calibrates the Grid Outage Risk Predictor on historical telemetry.
    """
    if repo is None:
        repo = EMSDataRepository()

    splits = repo.get_ml_feature_matrix(task="outage", purge_hours=24)
    feature_names = list(splits.feature_names)

    X_train = splits.train_features.to_numpy().astype(np.float64)
    y_train = splits.train_target.astype(np.int8)
    X_val = splits.val_features.to_numpy().astype(np.float64)
    y_val = splits.val_target.astype(np.int8)
    X_test = splits.test_features.to_numpy().astype(np.float64)
    y_test = splits.test_target.astype(np.int8)

    pos_count = int(np.sum(y_train == 1))
    neg_count = int(np.sum(y_train == 0))
    scale_pos = neg_count / max(pos_count, 1)

    # 1. Base LightGBM Classifier with moderated positive weighting
    base_clf = lgb.LGBMClassifier(
        objective="binary",
        n_estimators=120,
        learning_rate=0.03,
        num_leaves=15,
        min_child_samples=5,
        scale_pos_weight=min(scale_pos, 25.0),
        random_state=random_state,
        n_jobs=4,
    )

    t0 = time.perf_counter()
    base_clf.fit(X_train, y_train)

    # 2. Platt Sigmoid Calibration strictly on chronological validation split
    raw_val_probs = np.clip(base_clf.predict_proba(X_val)[:, 1], 1e-6, 1.0 - 1e-6)
    val_log_odds = logit(raw_val_probs).reshape(-1, 1)

    calibrator = LogisticRegression(C=1.0, solver="lbfgs", random_state=random_state)
    calibrator.fit(val_log_odds, y_val)
    fit_duration_ms = (time.perf_counter() - t0) * 1000

    # 3. Cost-Optimal Decision Threshold Grid Search on Validation Split
    # Cost Model: False Negative = 95 PKR/kWh (diesel); False Positive = 22 PKR/kWh (lost arbitrage)
    val_calibrated_probs = calibrator.predict_proba(val_log_odds)[:, 1]
    candidate_thresholds = np.linspace(0.05, 0.60, 56)
    best_th = 0.25
    min_cost = float("inf")

    for th in candidate_thresholds:
        pred_bin = (val_calibrated_probs >= th).astype(int)
        fn = np.sum((pred_bin == 0) & (y_val == 1))
        fp = np.sum((pred_bin == 1) & (y_val == 0))
        cost = fn * 95.0 + fp * 22.0
        if cost < min_cost:
            min_cost = cost
            best_th = float(th)

    predictor = OutageRiskPredictor(
        base_model=base_clf,
        calibrator=calibrator,
        feature_names=feature_names,
        optimal_threshold=round(best_th, 4),
        metadata={
            "train_rows": splits.metadata["train_rows"],
            "val_rows": splits.metadata["val_rows"],
            "test_rows": splits.metadata["test_rows"],
            "trained_at": datetime.now(PKT_TZ).isoformat(),
            "fit_duration_ms": round(fit_duration_ms, 2),
        },
    )

    # 4. Evaluate on Holdout Test Partition
    raw_test_probs = np.clip(base_clf.predict_proba(X_test, num_threads=1)[:, 1], 1e-6, 1.0 - 1e-6)
    test_log_odds = logit(raw_test_probs).reshape(-1, 1)
    test_calibrated_probs = calibrator.predict_proba(test_log_odds)[:, 1]

    pr_auc = float(average_precision_score(y_test, test_calibrated_probs))
    roc_auc = float(roc_auc_score(y_test, test_calibrated_probs))
    brier = float(brier_score_loss(y_test, test_calibrated_probs))

    # Benchmark 24-hour inference latency
    X_24 = np.ascontiguousarray(X_test[:24, :], dtype=np.float64)
    latencies = []
    for _ in range(200):
        t_start = time.perf_counter()
        _ = predictor.predict_proba_24h(X_24)
        latencies.append((time.perf_counter() - t_start) * 1000)
    avg_latency_ms = sum(latencies) / len(latencies)

    metrics = {
        "pr_auc": round(pr_auc, 4),
        "roc_auc": round(roc_auc, 4),
        "brier_score": round(brier, 4),
        "optimal_threshold": round(best_th, 4),
        "avg_24h_inference_latency_ms": round(avg_latency_ms, 4),
    }
    predictor.metadata["metrics"] = metrics

    # Save artifact
    predictor.save(save_path)

    return predictor, metrics


if __name__ == "__main__":
    print("=" * 70)
    print("SolarSense EMS — Training Platt Calibrated Grid Outage Predictor")
    print("=" * 70)
    predictor, metrics = train_outage_classifier()
    print(f"Training completed. Model serialized to '{DEFAULT_MODEL_PATH}'")
    print(f"Holdout Test ROC-AUC:               {metrics['roc_auc']:.4f}")
    print(f"Holdout Test PR-AUC:                {metrics['pr_auc']:.4f}")
    print(f"Holdout Test Brier Score:           {metrics['brier_score']:.4f} (Closer to 0 is better)")
    print(f"Cost-Optimal Decision Threshold:    {metrics['optimal_threshold']:.4f}")
    print(f"24-Hour Inference Latency:          {metrics['avg_24h_inference_latency_ms']:.4f} ms (Budget: < 2.0 ms)")
    print("=" * 70)
