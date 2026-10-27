"""
Unit Tests for SolarSense EMS CCTV Panel Monitor
=================================================
Validates:
1. CCTVPanelMonitor initialization and model reloading.
2. PIL image defect prediction dictionary schema & probability bounds.
3. OpenCV frame processing and HUD banner annotation.
4. Missing checkpoint error handling.
"""

from pathlib import Path
import numpy as np
import pytest
from PIL import Image

torch = pytest.importorskip("torch")
cv2 = pytest.importorskip("cv2")

from src.vision.cctv_panel_monitor import CCTVPanelMonitor, DERATE_COEFFICIENTS
from src.vision.train_classifier import DEFAULT_CHECKPOINT_PATH


@pytest.fixture(scope="module")
def monitor():
    if not DEFAULT_CHECKPOINT_PATH.exists():
        pytest.skip(f"Model checkpoint not found at {DEFAULT_CHECKPOINT_PATH}")
    return CCTVPanelMonitor(checkpoint_path=DEFAULT_CHECKPOINT_PATH)


def test_monitor_initialization(monitor):
    assert monitor.model is not None
    assert len(monitor.class_to_idx) == 5
    assert "clean" in monitor.class_to_idx
    assert "dusty" in monitor.class_to_idx


def test_predict_synthetic_pil_image(monitor):
    img = Image.new("RGB", (260, 260), (128, 128, 128))
    diag = monitor.predict_pil_image(img, use_tta=True)

    assert "condition" in diag
    assert diag["condition"] in monitor.class_to_idx
    assert 0.0 <= diag["confidence"] <= 1.0
    assert isinstance(diag["requires_cleaning"], bool)
    assert diag["severity"] in {"NONE", "MEDIUM", "HIGH", "CRITICAL", "EMERGENCY"}
    assert 0.0 <= diag["estimated_derate_pr"] <= 1.0
    assert len(diag["all_probabilities"]) == 5


def test_process_frame_overlay(monitor):
    frame = np.full((480, 640, 3), 128, dtype=np.uint8)
    diag, annotated = monitor.process_frame(frame, draw_overlay=True)

    assert annotated.shape == (480, 640, 3)
    assert isinstance(diag, dict)
    assert diag["condition"] in monitor.class_to_idx


def test_missing_checkpoint_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        CCTVPanelMonitor(checkpoint_path=tmp_path / "non_existent.pth")
