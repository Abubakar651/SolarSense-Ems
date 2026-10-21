"""
Unit Tests for the SolarSense EMS EfficientNet-B2 Defect Classifier Trainer
==========================================================================
Runs one epoch on a tiny synthetic ImageFolder (no network, no real dataset) and validates:
1. Best checkpoint is written with the expected schema and class mapping.
2. The checkpoint reloads into build_model() and yields [B, num_classes] logits.
3. Returned metrics are valid ratios.
4. Missing split folders fail loudly.
"""

from pathlib import Path

import pytest
import torch
from PIL import Image

from src.vision.train_classifier import build_model, train_classifier

CLASSES = ("bird_drop", "clean", "dusty", "electrical_damage", "physical_damage")


@pytest.fixture(scope="module")
def synthetic_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Builds train/val/test folders with 2 solid-colour images per class."""
    root = tmp_path_factory.mktemp("hybrid")
    for split in ("train", "val", "test"):
        for class_idx, cls in enumerate(CLASSES):
            cls_dir = root / split / cls
            cls_dir.mkdir(parents=True)
            for i in range(2):
                colour = (class_idx * 50, i * 100, 128)
                Image.new("RGB", (32, 32), colour).save(cls_dir / f"{cls}_{i}.png")
    return root


@pytest.fixture(scope="module")
def trained(synthetic_root: Path, tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    save_path = tmp_path_factory.mktemp("models") / "efficientnet_b2_defects.pth"
    results = train_classifier(
        root=synthetic_root, save_path=save_path, epochs=1, batch_size=4, pretrained=False
    )
    return save_path, results


def test_checkpoint_saved_with_schema_and_class_mapping(trained: tuple[Path, dict]):
    save_path, _ = trained
    checkpoint = torch.load(save_path)
    assert {"model_state_dict", "class_to_idx", "arch", "image_size", "epoch", "val_metrics"} <= set(checkpoint)
    assert checkpoint["class_to_idx"] == {cls: i for i, cls in enumerate(CLASSES)}
    assert checkpoint["arch"] == "efficientnet_b2"
    assert checkpoint["image_size"] == 260


def test_checkpoint_reloads_and_predicts_all_classes(trained: tuple[Path, dict]):
    save_path, _ = trained
    checkpoint = torch.load(save_path)
    model = build_model(num_classes=len(CLASSES), pretrained=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    with torch.no_grad():
        logits = model(torch.randn(2, 3, 260, 260))
    assert logits.shape == (2, len(CLASSES))


def test_returned_metrics_are_valid_ratios(trained: tuple[Path, dict]):
    _, results = trained
    assert results["best_epoch"] == 1
    for split in ("val", "test"):
        assert 0.0 <= results[split]["accuracy"] <= 1.0
        assert 0.0 <= results[split]["macro_f1"] <= 1.0
        assert results[split]["loss"] >= 0.0


def test_missing_split_folder_raises(tmp_path: Path):
    (tmp_path / "train" / "clean").mkdir(parents=True)
    with pytest.raises(FileNotFoundError):
        train_classifier(root=tmp_path, save_path=tmp_path / "m.pth", epochs=1, pretrained=False)
