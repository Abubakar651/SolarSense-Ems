"""
SolarSense EMS — EfficientNet-B2 Panel Defect Classifier (Dataset A, SolarSense Hybrid V1)
Fine-tunes an ImageNet-pretrained EfficientNet-B2 on the train/val/test ImageFolder layout
written by build_hybrid_dataset.py, using cross-entropy, Adam and cosine LR decay.
Keeps the epoch with the best validation macro-F1 and saves it to models/efficientnet_b2_defects.pth.
"""

import sys
from datetime import datetime
from pathlib import Path

# Add project root to sys.path for direct CLI execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch
from sklearn.metrics import f1_score
from torch import nn
from torch.utils.data import DataLoader
from torchvision.models import EfficientNet_B2_Weights, efficientnet_b2

from src.vision.dataloader import IMAGE_SIZE, build_dataloaders

HYBRID_ROOT = Path("data/processed/panel_images/solarsense_hybrid_v1")
DEFAULT_CHECKPOINT_PATH = Path("models/efficientnet_b2_defects.pth")
EPOCHS = 15
RANDOM_SEED = 42


def build_model(num_classes: int, pretrained: bool = True) -> nn.Module:
    weights = EfficientNet_B2_Weights.IMAGENET1K_V1 if pretrained else None
    model = efficientnet_b2(weights=weights)
    # Swap only the 1000-class ImageNet head; the whole backbone is fine-tuned
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model


def run_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    optimizer: torch.optim.Optimizer | None = None,
) -> dict[str, float]:
    """Trains for one pass when given an optimizer, otherwise evaluates."""
    is_train = optimizer is not None
    model.train(is_train)
    total_loss, y_true, y_pred = 0.0, [], []

    with torch.set_grad_enabled(is_train):
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            logits = model(images)
            loss = criterion(logits, labels)
            if is_train:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            total_loss += loss.item() * labels.size(0)
            y_true += labels.tolist()
            y_pred += logits.argmax(dim=1).tolist()

    correct = sum(t == p for t, p in zip(y_true, y_pred))
    return {
        "loss": total_loss / len(y_true),
        "accuracy": correct / len(y_true),
        # Macro-F1 weights the small damage classes equally with clean/dusty
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
    }


def train_classifier(
    root: Path = HYBRID_ROOT,
    save_path: Path = DEFAULT_CHECKPOINT_PATH,
    epochs: int = EPOCHS,
    lr: float = 3e-4,
    batch_size: int = 16,
    pretrained: bool = True,
) -> dict[str, dict[str, float]]:
    torch.manual_seed(RANDOM_SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    loaders = build_dataloaders(root=root, batch_size=batch_size)
    class_to_idx = loaders["train"].dataset.class_to_idx

    model = build_model(num_classes=len(class_to_idx), pretrained=pretrained).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    best_val: dict[str, float] | None = None

    for epoch in range(1, epochs + 1):
        current_lr = optimizer.param_groups[0]["lr"]
        train_m = run_epoch(model, loaders["train"], criterion, device, optimizer)
        val_m = run_epoch(model, loaders["val"], criterion, device)
        scheduler.step()
        print(
            f"Epoch {epoch:>2}/{epochs} | lr {current_lr:.2e} | "
            f"train loss {train_m['loss']:.4f} acc {train_m['accuracy']:.4f} f1 {train_m['macro_f1']:.4f} | "
            f"val loss {val_m['loss']:.4f} acc {val_m['accuracy']:.4f} f1 {val_m['macro_f1']:.4f}"
        )

        # Classes are imbalanced (clean/dusty ~3x each damage class), so select on macro-F1
        if best_val is None or val_m["macro_f1"] > best_val["macro_f1"]:
            best_val = val_m
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "class_to_idx": class_to_idx,
                    "arch": "efficientnet_b2",
                    "image_size": IMAGE_SIZE,
                    "epoch": epoch,
                    "val_metrics": val_m,
                    "trained_at": datetime.now().isoformat(),
                },
                save_path,
            )

    checkpoint = torch.load(save_path, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])
    test_m = run_epoch(model, loaders["test"], criterion, device)
    return {"best_epoch": checkpoint["epoch"], "val": best_val, "test": test_m}


if __name__ == "__main__":
    print("=" * 70)
    print("SolarSense EMS — Training EfficientNet-B2 Panel Defect Classifier")
    print("=" * 70)
    results = train_classifier()
    print("-" * 70)
    print(f"Best checkpoint (epoch {results['best_epoch']}) saved to '{DEFAULT_CHECKPOINT_PATH}'")
    print(f"Validation Macro-F1:       {results['val']['macro_f1']:.4f}")
    print(f"Holdout Test Accuracy:     {results['test']['accuracy'] * 100:.2f}% (Target: >= 94%)")
    print(f"Holdout Test Macro-F1:     {results['test']['macro_f1']:.4f} (Target: >= 0.92)")
    print("=" * 70)
