"""
Bridge / compatibility stub: re-exports ResidentialLoadForecaster as FactoryLoadForecaster.
Original industrial factory load training script is archived at:
  archive/legacy_industrial/src/forecast/train_factory_load.py
"""

from src.forecast.train_residential_load import (
    ResidentialLoadForecaster as FactoryLoadForecaster,
    ResidentialLoadForecaster,
    train_residential_load_model as train_factory_load_model,
    DEFAULT_MODEL_PATH,
    LEGACY_MODEL_PATH,
)

__all__ = [
    "FactoryLoadForecaster",
    "ResidentialLoadForecaster",
    "train_factory_load_model",
    "DEFAULT_MODEL_PATH",
    "LEGACY_MODEL_PATH",
]
