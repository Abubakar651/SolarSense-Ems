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

AUGMENTED_ROOT = Path("data/processed/panel_images/solarsense_augmented_v1")
HYBRID_ROOT = Path("data/processed/panel_images/solarsense_hybrid_v1")
DEFAULT_DATASET_ROOT = AUGMENTED_ROOT if AUGMENTED_ROOT.exists() else HYBRID_ROOT
DEFAULT_CHECKPOINT_PATH = Path("models/efficientnet_b2_defects.pth")
EPOCHS = 15
RANDOM_SEED = 42


def build_model(num_classes: int, pretrained: bool = True, dropout: float = 0.4) -> nn.Module:
    weights = EfficientNet_B2_Weights.IMAGENET1K_V1 if pretrained else None
    model = efficientnet_b2(weights=weights)
    in_features = model.classifier[1].in_features
    # Upgraded classifier head with dropout regularization to combat overfitting on small datasets
    model.classifier = nn.Sequential(
        nn.Dropout(p=dropout),
        nn.Linear(in_features, num_classes)
    )
    return model


def run_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    optimizer: torch.optim.Optimizer | None = None,
    use_tta: bool = False,
) -> dict[str, float]:
    """Trains for one pass when given an optimizer, otherwise evaluates with optional Test-Time Augmentation."""
    is_train = optimizer is not None
    model.train(is_train)
    total_loss, y_true, y_pred = 0.0, [], []

    with torch.set_grad_enabled(is_train):
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            if is_train or not use_tta:
                logits = model(images)
            else:
                # 4-pass Test-Time Augmentation (original, horizontal flip, vertical flip, 180-deg flip)
                l1 = model(images)
                l2 = model(torch.flip(images, dims=[3]))
                l3 = model(torch.flip(images, dims=[2]))
                l4 = model(torch.flip(torch.flip(images, dims=[3]), dims=[2]))
                logits = (l1 + l2 + l3 + l4) / 4.0

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
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
    }


def train_classifier(
    root: Path = DEFAULT_DATASET_ROOT,
    save_path: Path = DEFAULT_CHECKPOINT_PATH,
    epochs: int = EPOCHS,
    warmup_epochs: int = 2,
    lr: float = 3e-4,
    batch_size: int = 16,
    pretrained: bool = True,
    dropout: float = 0.4,
    use_class_weights: bool = True,
    use_tta: bool = True,
    label_smoothing: float = 0.08,
) -> dict[str, dict[str, float]]:
    torch.manual_seed(RANDOM_SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    loaders = build_dataloaders(root=root, batch_size=batch_size)
    class_to_idx = loaders["train"].dataset.class_to_idx
    num_classes = len(class_to_idx)

    model = build_model(num_classes=num_classes, pretrained=pretrained, dropout=dropout).to(device)

    # Class-weighted cross entropy with label smoothing to prevent overconfidence and under-representation
    if use_class_weights and hasattr(loaders["train"].dataset, "samples"):
        train_targets = [s[1] for s in loaders["train"].dataset.samples]
        counts = torch.bincount(torch.tensor(train_targets), minlength=num_classes).float()
        counts = torch.clamp(counts, min=1.0)
        weights = len(train_targets) / (num_classes * counts)
        criterion = nn.CrossEntropyLoss(weight=weights.to(device), label_smoothing=label_smoothing)
    else:
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

    # Differential learning rate with AdamW: head learns faster, pretrained backbone fine-tunes gently
    optimizer = torch.optim.AdamW(
        [
            {"params": model.features.parameters(), "lr": lr * 0.1},
            {"params": model.classifier.parameters(), "lr": lr},
        ],
        weight_decay=1e-4,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    best_val: dict[str, float] | None = None

    for epoch in range(1, epochs + 1):
        # Warmup phase: freeze backbone feature layers to prevent noisy early gradients from corrupting ImageNet weights
        if epoch <= warmup_epochs:
            for p in model.features.parameters():
                p.requires_grad = False
        else:
            for p in model.features.parameters():
                p.requires_grad = True

        current_lr = optimizer.param_groups[1]["lr"]
        train_m = run_epoch(model, loaders["train"], criterion, device, optimizer)
        val_m = run_epoch(model, loaders["val"], criterion, device, use_tta=use_tta)
        scheduler.step()
        print(
            f"Epoch {epoch:>2}/{epochs} | lr {current_lr:.2e} | "
            f"train loss {train_m['loss']:.4f} acc {train_m['accuracy']:.4f} f1 {train_m['macro_f1']:.4f} | "
            f"val loss {val_m['loss']:.4f} acc {val_m['accuracy']:.4f} f1 {val_m['macro_f1']:.4f}"
        )

        # Classes are imbalanced, so select checkpoint on validation macro-F1
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
    test_m = run_epoch(model, loaders["test"], criterion, device, use_tta=use_tta)
    return {"best_epoch": checkpoint["epoch"], "val": best_val, "test": test_m}



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SolarSense EMS — EfficientNet-B2 Panel Defect Classifier")
    parser.add_argument("--root", type=str, default=str(HYBRID_ROOT), help="Path to ImageFolder dataset root")
    parser.add_argument("--save-path", type=str, default=str(DEFAULT_CHECKPOINT_PATH), help="Path to save best checkpoint")
    parser.add_argument("--epochs", type=int, default=EPOCHS, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size for DataLoader")
    parser.add_argument("--lr", type=float, default=3e-4, help="Adam learning rate")
    args = parser.parse_args()

    print("=" * 70)
    print("SolarSense EMS — Training EfficientNet-B2 Panel Defect Classifier")
    print(f"Dataset Root:    {args.root}")
    print(f"Checkpoint Path: {args.save_path}")
    print(f"Epochs: {args.epochs} | Batch Size: {args.batch_size} | Learning Rate: {args.lr}")
    print("=" * 70)
    results = train_classifier(
        root=Path(args.root),
        save_path=Path(args.save_path),
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
    )
    print("-" * 70)
    print(f"Best checkpoint (epoch {results['best_epoch']}) saved to '{args.save_path}'")
    print(f"Validation Macro-F1:       {results['val']['macro_f1']:.4f}")
    print(f"Holdout Test Accuracy:     {results['test']['accuracy'] * 100:.2f}% (Target: >= 94%)")
    print(f"Holdout Test Macro-F1:     {results['test']['macro_f1']:.4f} (Target: >= 0.92)")
    print("=" * 70)

