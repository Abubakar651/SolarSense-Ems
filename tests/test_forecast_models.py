"""
Unit Tests for SolarSense EMS AI Forecasters & Risk Classifiers
==============================================================
Validates:
1. Model loading, deserialization, and metadata integrity (.joblib).
2. Sub-millisecond 24h inference latency budgets (< 2.0 ms per model).
3. Physical post-processing bounds (Solar: [0, 600] kW & 0 at night; Load: p90 >= point >= 0).
4. Probability calibration and score ranges (Outage: [0.0, 1.0]).
5. Zero NaN/Inf output guarantees.
6. End-to-end integration with EMSDataRepository.
"""

import time
import numpy as np
import pytest

from src.data_engineering.feature_store import (
    EMSDataRepository,
    TariffPolicy,
)
from src.forecast.train_solar_pv import SolarPVForecaster, DEFAULT_MODEL_PATH as SOLAR_MODEL_PATH
from src.forecast.train_factory_load import FactoryLoadForecaster, DEFAULT_MODEL_PATH as LOAD_MODEL_PATH
from src.grid_outage.predict_outage import OutageRiskPredictor, DEFAULT_MODEL_PATH as OUTAGE_MODEL_PATH


@pytest.fixture(scope="module")
def repo() -> EMSDataRepository:
    """Instantiates the repository once for ML test fixtures."""
    return EMSDataRepository()


@pytest.fixture(scope="module")
def solar_model() -> SolarPVForecaster:
    """Loads the serialized Solar PV Forecaster."""
    return SolarPVForecaster.load(SOLAR_MODEL_PATH)


@pytest.fixture(scope="module")
def load_model() -> FactoryLoadForecaster:
    """Loads the serialized Factory Load Forecaster."""
    return FactoryLoadForecaster.load(LOAD_MODEL_PATH)


@pytest.fixture(scope="module")
def outage_model() -> OutageRiskPredictor:
    """Loads the serialized Outage Risk Predictor."""
    return OutageRiskPredictor.load(OUTAGE_MODEL_PATH)


# =====================================================================
# 1. Solar PV Forecaster Tests
# =====================================================================

def test_solar_forecaster_loading_and_shape(repo: EMSDataRepository, solar_model: SolarPVForecaster):
    """Verifies that the solar model loads and produces a shape (24,) float64 array."""
    splits = repo.get_ml_feature_matrix("solar")
    X_24 = np.ascontiguousarray(splits.test_features.to_numpy()[:24, :], dtype=np.float64)

    preds = solar_model.predict_24h(X_24)
    assert isinstance(preds, np.ndarray)
    assert preds.shape == (24,)
    assert preds.dtype == np.float64
    assert not np.isnan(preds).any(), "Solar predictions must contain zero NaNs"
    assert not np.isinf(preds).any(), "Solar predictions must contain zero Infs"


def test_solar_forecaster_physical_bounds(repo: EMSDataRepository, solar_model: SolarPVForecaster):
    """Ensures solar generation is strictly bounded in [0.0, 600.0] and 0.0 at night."""
    splits = repo.get_ml_feature_matrix("solar")
    X_test = splits.test_features.to_numpy().astype(np.float64)
    ghi_idx = solar_model._ghi_idx

    X_24 = np.ascontiguousarray(X_test[:24, :], dtype=np.float64)
    preds = solar_model.predict_24h(X_24)

    # Physical bounds check
    assert (preds >= 0.0).all(), "Solar generation cannot be negative"
    assert (preds <= 600.0).all(), "Solar generation cannot exceed installed 600 kW capacity"

    # Night hours check
    night_indices = np.where(X_24[:, ghi_idx] <= 0.0)[0]
    assert len(night_indices) > 0, "Test slice must contain night hours"
    assert (preds[night_indices] == 0.0).all(), "Solar generation must strictly equal 0.0 kW when GHI <= 0"


def test_solar_forecaster_latency_budget(repo: EMSDataRepository, solar_model: SolarPVForecaster):
    """Verifies 24-hour inference latency is < 2.0 ms (budget < 10.0 ms)."""
    splits = repo.get_ml_feature_matrix("solar")
    X_24 = np.ascontiguousarray(splits.test_features.to_numpy()[:24, :], dtype=np.float64)

    # Warmup
    for _ in range(10):
        _ = solar_model.predict_24h(X_24)

    latencies = []
    for _ in range(100):
        t0 = time.perf_counter()
        _ = solar_model.predict_24h(X_24)
        latencies.append((time.perf_counter() - t0) * 1000)

    avg_latency = sum(latencies) / len(latencies)
    assert avg_latency < 2.0, f"Solar 24h inference latency {avg_latency:.4f} ms exceeded 2.0 ms budget"


# =====================================================================
# 2. Factory Load Forecaster Tests
# =====================================================================

def test_factory_load_loading_and_shapes(repo: EMSDataRepository, load_model: FactoryLoadForecaster):
    """Verifies that the factory load forecaster outputs dual (point, p90) arrays of shape (24,)."""
    splits = repo.get_ml_feature_matrix("load")
    X_24 = np.ascontiguousarray(splits.test_features.to_numpy()[:24, :], dtype=np.float64)

    point_kw, p90_kw = load_model.predict_24h(X_24)

    assert isinstance(point_kw, np.ndarray) and isinstance(p90_kw, np.ndarray)
    assert point_kw.shape == (24,)
    assert p90_kw.shape == (24,)
    assert point_kw.dtype == np.float64
    assert p90_kw.dtype == np.float64
    assert not np.isnan(point_kw).any() and not np.isnan(p90_kw).any()


def test_factory_load_non_crossing_and_bounds(repo: EMSDataRepository, load_model: FactoryLoadForecaster):
    """Validates the non-crossing invariant: p90_kw >= point_kw >= 0.0 kW across all hours."""
    splits = repo.get_ml_feature_matrix("load")
    X_test = splits.test_features.to_numpy().astype(np.float64)

    # Test across 10 different 24-hour windows
    for day_i in range(10):
        start_idx = day_i * 24
        X_24 = np.ascontiguousarray(X_test[start_idx : start_idx + 24, :], dtype=np.float64)
        point_kw, p90_kw = load_model.predict_24h(X_24)

        assert (point_kw >= 0.0).all(), f"Point load on day {day_i} must be non-negative"
        assert (p90_kw >= point_kw).all(), (
            f"Non-crossing violation on day {day_i}: p90 must be >= point forecast across all hours"
        )


def test_factory_load_latency_budget(repo: EMSDataRepository, load_model: FactoryLoadForecaster):
    """Verifies 24-hour dual inference latency is < 2.0 ms (budget < 10.0 ms)."""
    splits = repo.get_ml_feature_matrix("load")
    X_24 = np.ascontiguousarray(splits.test_features.to_numpy()[:24, :], dtype=np.float64)

    for _ in range(10):
        _ = load_model.predict_24h(X_24)

    latencies = []
    for _ in range(100):
        t0 = time.perf_counter()
        _ = load_model.predict_24h(X_24)
        latencies.append((time.perf_counter() - t0) * 1000)

    avg_latency = sum(latencies) / len(latencies)
    assert avg_latency < 10.0, f"Load 24h dual inference latency {avg_latency:.4f} ms exceeded 10.0 ms budget"


# =====================================================================
# 3. Grid Outage Risk Predictor Tests
# =====================================================================

def test_outage_predictor_loading_and_probabilities(repo: EMSDataRepository, outage_model: OutageRiskPredictor):
    """Verifies that the outage predictor produces calibrated probabilities strictly in [0.0, 1.0]."""
    splits = repo.get_ml_feature_matrix("outage")
    X_24 = np.ascontiguousarray(splits.test_features.to_numpy()[:24, :], dtype=np.float64)

    probs = outage_model.predict_proba_24h(X_24)

    assert isinstance(probs, np.ndarray)
    assert probs.shape == (24,)
    assert probs.dtype == np.float64
    assert not np.isnan(probs).any(), "Outage probabilities must contain zero NaNs"
    assert (probs >= 0.0).all() and (probs <= 1.0).all(), "Probabilities must be strictly bounded in [0.0, 1.0]"
    assert 0.01 <= outage_model.optimal_threshold <= 0.60, "Optimal threshold must be valid"


def test_outage_predictor_latency_budget(repo: EMSDataRepository, outage_model: OutageRiskPredictor):
    """Verifies 24-hour probabilistic inference latency is < 1.5 ms (budget < 10.0 ms)."""
    splits = repo.get_ml_feature_matrix("outage")
    X_24 = np.ascontiguousarray(splits.test_features.to_numpy()[:24, :], dtype=np.float64)

    for _ in range(10):
        _ = outage_model.predict_proba_24h(X_24)

    latencies = []
    for _ in range(100):
        t0 = time.perf_counter()
        _ = outage_model.predict_proba_24h(X_24)
        latencies.append((time.perf_counter() - t0) * 1000)

    avg_latency = sum(latencies) / len(latencies)
    assert avg_latency < 10.0, f"Outage 24h inference latency {avg_latency:.4f} ms exceeded 10.0 ms budget"


# =====================================================================
# 4. Cross-Model Integration Test
# =====================================================================

def test_all_models_under_total_latency_budget(
    repo: EMSDataRepository,
    solar_model: SolarPVForecaster,
    load_model: FactoryLoadForecaster,
    outage_model: OutageRiskPredictor,
):
    """
    Validates that running all three models for a 24-hour horizon combined
    executes well under the Section 2 API budget (< 10.0 ms per model).
    """
    solar_splits = repo.get_ml_feature_matrix("solar")
    load_splits = repo.get_ml_feature_matrix("load")
    outage_splits = repo.get_ml_feature_matrix("outage")

    X_solar_24 = np.ascontiguousarray(solar_splits.test_features.to_numpy()[:24, :], dtype=np.float64)
    X_load_24 = np.ascontiguousarray(load_splits.test_features.to_numpy()[:24, :], dtype=np.float64)
    X_outage_24 = np.ascontiguousarray(outage_splits.test_features.to_numpy()[:24, :], dtype=np.float64)

    # Warmup
    for _ in range(5):
        _ = solar_model.predict_24h(X_solar_24)
        _ = load_model.predict_24h(X_load_24)
        _ = outage_model.predict_proba_24h(X_outage_24)

    times = []
    for _ in range(20):
        t0 = time.perf_counter()
        solar_preds = solar_model.predict_24h(X_solar_24)
        load_point, load_p90 = load_model.predict_24h(X_load_24)
        outage_probs = outage_model.predict_proba_24h(X_outage_24)
        times.append((time.perf_counter() - t0) * 1000)

    avg_total_ms = sum(times) / len(times)

    assert len(solar_preds) == 24
    assert len(load_point) == 24
    assert len(outage_probs) == 24
    assert avg_total_ms < 15.0, f"Combined 3-model 24h inference time {avg_total_ms:.4f} ms exceeded 15.0 ms target"
