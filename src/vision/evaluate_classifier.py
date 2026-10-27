"""
SolarSense EMS — EfficientNet-B2 Panel Defect Evaluation & Accuracy Analyzer
Evaluates a trained model checkpoint on the holdout test split.
Outputs:
1. Overall Accuracy, Macro-F1, and Weighted-F1
2. Per-class Precision, Recall, and F1-score
3. Formatted 5x5 Confusion Matrix
4. Saves high-resolution confusion matrix visualization
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import torch
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from src.vision.dataloader import build_dataloaders
from src.vision.train_classifier import (
    DEFAULT_CHECKPOINT_PATH,
    HYBRID_ROOT,
    build_model,
)


def evaluate_model(
    checkpoint_path: Path = DEFAULT_CHECKPOINT_PATH,
    dataset_root: Path = HYBRID_ROOT,
    batch_size: int = 32,
    save_plot_path: Path | None = Path("docs/samples/panel_defect_confusion_matrix.png"),
) -> dict:
    checkpoint_path = Path(checkpoint_path)
    dataset_root = Path(dataset_root)

    if not checkpoint_path.exists():
        raise FileNotFoundError(
            f"Model checkpoint not found: {checkpoint_path}. Train the model first via src/vision/train_classifier.py"
        )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("=" * 70)
    print("SOLARSENSE EMS — PANEL DEFECT CLASSIFICATION EVALUATOR")
    print(f"Device:          {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")
    print(f"Checkpoint:      {checkpoint_path}")
    print(f"Dataset Root:    {dataset_root}")
    print("=" * 70)

    # 1. Load DataLoaders
    loaders = build_dataloaders(root=dataset_root, batch_size=batch_size)
    test_loader = loaders["test"]
    class_to_idx = test_loader.dataset.class_to_idx
    idx_to_class = {v: k for k, v in class_to_idx.items()}
    class_names = [idx_to_class[i] for i in range(len(class_to_idx))]

    # 2. Load Checkpoint
    checkpoint = torch.load(checkpoint_path, map_location=device)
    num_classes = len(class_to_idx)
    model = build_model(num_classes=num_classes, pretrained=False).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    print(f"\n[INFO] Loaded model trained for {checkpoint.get('epoch', '?')} epochs.")
    print(f"[INFO] Testing on {len(test_loader.dataset)} holdout images across {num_classes} classes: {class_names}")

    # 3. Inference
    y_true, y_pred, y_probs = [], [], []
    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            logits = model(images)
            probs = torch.softmax(logits, dim=1)
            preds = logits.argmax(dim=1)

            y_true.extend(labels.cpu().tolist())
            y_pred.extend(preds.cpu().tolist())
            y_probs.extend(probs.cpu().tolist())

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    # 4. Metrics
    acc = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    cm = confusion_matrix(y_true, y_pred)
    report = classification_report(
        y_true, y_pred, target_names=class_names, digits=4, zero_division=0
    )

    print("\n" + "=" * 70)
    print("HOLDOUT TEST SET ACCURACY & PERFORMANCE SCORECARD")
    print("=" * 70)
    print(f"Overall Accuracy:   {acc * 100:.2f}%  (Target: >= 94.0%)  {'[PASS]' if acc >= 0.94 else '[SUB-TARGET]'}")
    print(f"Macro-F1 Score:     {macro_f1:.4f}   (Target: >= 0.920)  {'[PASS]' if macro_f1 >= 0.92 else '[SUB-TARGET]'}")
    print(f"Weighted-F1 Score:  {weighted_f1:.4f}")
    print("\nDetailed Per-Class Performance:")
    print("-" * 70)
    print(report)

    print("5x5 Confusion Matrix:")
    print("-" * 70)
    header = f"{'True \\ Pred':<20}" + "".join(f"{c[:10]:>12}" for c in class_names)
    print(header)
    for i, row in enumerate(cm):
        row_str = f"{class_names[i]:<20}" + "".join(f"{val:>12}" for val in row)
        print(row_str)
    print("=" * 70)

    # 5. Optional Plot Saving
    if save_plot_path:
        try:
            import matplotlib.pyplot as plt

            save_plot_path = Path(save_plot_path)
            save_plot_path.parent.mkdir(parents=True, exist_ok=True)

            fig, ax = plt.subplots(figsize=(8, 6))
            im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
            ax.figure.colorbar(im, ax=ax)
            ax.set(
                xticks=np.arange(cm.shape[1]),
                yticks=np.arange(cm.shape[0]),
                xticklabels=class_names,
                yticklabels=class_names,
                ylabel="True Label",
                xlabel="Predicted Label",
                title=f"EfficientNet-B2 Panel Defect Confusion Matrix\nAccuracy: {acc*100:.2f}% | Macro-F1: {macro_f1:.4f}",
            )
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

            thresh = cm.max() / 2.0
            for i in range(cm.shape[0]):
                for j in range(cm.shape[1]):
                    ax.text(
                        j,
                        i,
                        format(cm[i, j], "d"),
                        ha="center",
                        va="center",
                        color="white" if cm[i, j] > thresh else "black",
                    )
            fig.tight_layout()
            fig.savefig(save_plot_path, dpi=200)
            plt.close(fig)
            print(f"[SUCCESS] Confusion matrix plot saved to: {save_plot_path}")
        except Exception as e:
            print(f"[NOTE] Could not save confusion matrix plot: {e}")

    return {
        "accuracy": acc,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "confusion_matrix": cm.tolist(),
        "report": report,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SolarSense EMS — Panel Defect Classifier Evaluator")
    parser.add_argument("--checkpoint", type=str, default=str(DEFAULT_CHECKPOINT_PATH), help="Path to .pth checkpoint")
    parser.add_argument("--root", type=str, default=str(HYBRID_ROOT), help="Path to ImageFolder dataset root")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size for DataLoader")
    parser.add_argument("--save-plot", type=str, default="docs/samples/panel_defect_confusion_matrix.png", help="Path to save confusion matrix plot")
    args = parser.parse_args()

    evaluate_model(
        checkpoint_path=Path(args.checkpoint),
        dataset_root=Path(args.root),
        batch_size=args.batch_size,
        save_plot_path=Path(args.save_plot) if args.save_plot else None,
    )
