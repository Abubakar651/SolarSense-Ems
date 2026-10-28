"""
SolarSense EMS — Hybrid Multi-Scale Panel Defect Classifier (Dataset A, SolarSense Hybrid V1)
=============================================================================================
Combines three lightweight ImageNet-pretrained feature hierarchies at native 260x260 resolution:
1. EfficientNet-B2 (1408ch compound-scaled MBConv features)
2. DenseNet-121 (1024ch multi-scale concatenated dense block features)
3. MobileNetV3-Large (960ch squeeze-and-excitation hard-swish features)

Applies Spatial Power Multi-Pooling (GAP + GMP + GSP), RootSIFT signed square-root power-law
normalization, block-wise L2 normalization, and Mean-Centered Cosine Space normalization, followed
by a probability-calibrated Cosine Logistic + Exact RBF Support Vector Hybrid Tensor Head.
Saves the best validation Macro-F1 checkpoint to models/efficientnet_b2_defects.pth.
"""

import sys
from datetime import datetime
from pathlib import Path

# Add project root to sys.path for direct CLI execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, log_loss
from sklearn.preprocessing import normalize
from sklearn.svm import SVC
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets, models

from src.vision.dataloader import IMAGE_SIZE, build_dataloaders, build_transforms

HYBRID_ROOT = Path("data/processed/panel_images/solarsense_hybrid_v1")
AUGMENTED_ROOT = Path("data/processed/panel_images/solarsense_augmented_v1")
DEFAULT_DATASET_ROOT = HYBRID_ROOT if HYBRID_ROOT.exists() else AUGMENTED_ROOT
DEFAULT_CHECKPOINT_PATH = Path("models/efficientnet_b2_defects.pth")
FEATURE_CACHE_DIR = Path(
    "/home/bakar/.gemini/antigravity/brain/b89d1495-a8bc-4c28-8cb1-d72fdc345aeb/scratch/clean_hybrid_cache"
)
EPOCHS = 15
RANDOM_SEED = 42
MAX_SUPPORT_VECTORS = 512

STREAM_SPECS = (
    ("densenet121", 1024, 1.8),
    ("mobilenet_v3_large", 960, 1.8),
    ("efficientnet_b2", 1408, 1.0),
)


def _rootsift_block_normalize_torch(raw_3c: torch.Tensor, c_dim: int, mu: torch.Tensor) -> torch.Tensor:
    """Applies RootSIFT power-law transform, block-wise L2 norm (GAP, GMP, GSP), and mean-centered cosine norm."""
    g1 = raw_3c[:, :c_dim]
    g2 = raw_3c[:, c_dim : 2 * c_dim]
    g3 = raw_3c[:, 2 * c_dim :]

    g1 = F.normalize(torch.sign(g1) * torch.sqrt(torch.abs(g1) + 1e-8), p=2.0, dim=1)
    g2 = F.normalize(torch.sign(g2) * torch.sqrt(torch.abs(g2) + 1e-8), p=2.0, dim=1) * 0.6
    g3 = F.normalize(torch.sign(g3) * torch.sqrt(torch.abs(g3) + 1e-8), p=2.0, dim=1) * 0.6

    comb = torch.cat([g1, g2, g3], dim=1)
    return F.normalize(comb - mu, p=2.0, dim=1)


def _rootsift_block_normalize_np(
    X: np.ndarray, c_dim: int, mu: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """NumPy equivalent of RootSIFT + Block-Wise L2 + Mean-Centered Cosine Space normalization."""
    g1 = normalize(np.sign(X[:, :c_dim]) * np.sqrt(np.abs(X[:, :c_dim]) + 1e-8))
    g2 = normalize(np.sign(X[:, c_dim : 2 * c_dim]) * np.sqrt(np.abs(X[:, c_dim : 2 * c_dim]) + 1e-8)) * 0.6
    g3 = normalize(np.sign(X[:, 2 * c_dim :]) * np.sqrt(np.abs(X[:, 2 * c_dim :]) + 1e-8)) * 0.6
    comb = np.hstack([g1, g2, g3]).astype(np.float32)
    if mu is None:
        mu = comb.mean(axis=0, keepdims=True).astype(np.float32)
    z = normalize(comb - mu).astype(np.float32)
    return z, mu


class MultiBackboneSpatialFeatures(nn.Module):
    """Extracts 260x260 Spatial Power Multi-Pooling (GAP + GMP + GSP) features from 3 backbones."""

    def __init__(self, pretrained: bool = True):
        super().__init__()
        self.effnet = models.efficientnet_b2(
            weights=models.EfficientNet_B2_Weights.IMAGENET1K_V1 if pretrained else None
        ).features
        self.densenet = models.densenet121(
            weights=models.DenseNet121_Weights.DEFAULT if pretrained else None
        ).features
        self.mobilenet = models.mobilenet_v3_large(
            weights=models.MobileNet_V3_Large_Weights.DEFAULT if pretrained else None
        ).features

    @staticmethod
    def _spatial_multipool(fm: torch.Tensor) -> torch.Tensor:
        gap = fm.mean(dim=(2, 3))
        gmp = fm.amax(dim=(2, 3))
        gsp = torch.sqrt(fm.var(dim=(2, 3), unbiased=False) + 1e-6)
        return torch.cat([gap, gmp, gsp], dim=1)

    def forward_streams(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        fm_dense = F.relu(self.densenet(x))
        fm_mobile = self.mobilenet(x)
        fm_eff = self.effnet(x)
        return {
            "densenet121": self._spatial_multipool(fm_dense),
            "mobilenet_v3_large": self._spatial_multipool(fm_mobile),
            "efficientnet_b2": self._spatial_multipool(fm_eff),
        }

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        streams = self.forward_streams(x)
        return torch.cat([streams[name] for name, _, _ in STREAM_SPECS], dim=1)


class StreamCosineRBFHead(nn.Module):
    """Per-backbone hybrid classifier combining Cosine Logistic Regression and Exact OvO RBF-SVM in PyTorch."""

    def __init__(self, c_dim: int, num_classes: int, dropout: float = 0.3, max_sv: int = MAX_SUPPORT_VECTORS):
        super().__init__()
        self.c_dim = c_dim
        self.in_features = 3 * c_dim
        self.num_classes = num_classes
        self.max_sv = max_sv
        self.num_pairs = max(1, num_classes * (num_classes - 1) // 2)

        self.dropout = nn.Dropout(p=dropout)
        self.linear = nn.Linear(self.in_features, num_classes)

        self.register_buffer("feature_mean", torch.zeros(1, self.in_features))
        self.register_buffer("sv", torch.zeros(max_sv, self.in_features))
        self.register_buffer("ovo_proj", torch.zeros(max_sv, self.num_pairs))
        self.register_buffer("ovo_bias", torch.zeros(self.num_pairs))
        self.register_buffer("gamma", torch.ones(1))
        self.register_buffer("svm_weight", torch.zeros(1))
        self.register_buffer("df_temp", torch.tensor([1.10]))

        pairs = []
        for i in range(num_classes):
            for j in range(i + 1, num_classes):
                pairs.append((i, j))
        self.pairs = pairs

    def fit_from_numpy(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        c_lr: float = 0.40,
        c_svm: float = 1.15,
        w_svm: float = 0.32,
        df_temp: float = 1.10,
    ) -> None:
        z_tr, mu = _rootsift_block_normalize_np(X_train, self.c_dim)
        lr = LogisticRegression(C=c_lr, class_weight="balanced", max_iter=1000, random_state=RANDOM_SEED)
        lr.fit(z_tr, y_train)

        svm = SVC(C=c_svm, kernel="rbf", class_weight="balanced", random_state=RANDOM_SEED)
        svm.fit(z_tr, y_train)

        device = self.linear.weight.device
        with torch.no_grad():
            self.feature_mean.copy_(torch.tensor(mu, dtype=torch.float32, device=device))
            self.linear.weight.copy_(torch.tensor(lr.coef_, dtype=torch.float32, device=device))
            self.linear.bias.copy_(torch.tensor(lr.intercept_, dtype=torch.float32, device=device))

            sv_np = svm.support_vectors_.astype(np.float32)
            n_sv = min(sv_np.shape[0], self.max_sv)
            starts = np.cumsum([0] + list(svm.n_support_))
            proj_np = np.zeros((self.max_sv, self.num_pairs), dtype=np.float32)

            p_idx = 0
            for i in range(self.num_classes):
                for j in range(i + 1, self.num_classes):
                    s_i, e_i = min(starts[i], n_sv), min(starts[i + 1], n_sv)
                    s_j, e_j = min(starts[j], n_sv), min(starts[j + 1], n_sv)
                    if e_i > s_i:
                        proj_np[s_i:e_i, p_idx] = svm.dual_coef_[j - 1, starts[i] : starts[i] + (e_i - s_i)]
                    if e_j > s_j:
                        proj_np[s_j:e_j, p_idx] = svm.dual_coef_[i, starts[j] : starts[j] + (e_j - s_j)]
                    p_idx += 1

            self.sv.zero_()
            self.sv[:n_sv].copy_(torch.tensor(sv_np[:n_sv], dtype=torch.float32, device=device))
            self.ovo_proj.copy_(torch.tensor(proj_np, dtype=torch.float32, device=device))
            self.ovo_bias.copy_(torch.tensor(svm.intercept_, dtype=torch.float32, device=device))
            self.gamma.fill_(float(svm._gamma))
            self.svm_weight.fill_(float(w_svm))
            self.df_temp.fill_(float(df_temp))

    def _svm_ovr_probs(self, z: torch.Tensor) -> torch.Tensor:
        dist_sq = torch.cdist(z, self.sv, p=2.0).pow(2)
        k_mat = torch.exp(-self.gamma * dist_sq)
        dec_ovo = k_mat @ self.ovo_proj + self.ovo_bias

        bsz = z.shape[0]
        votes = torch.zeros((bsz, self.num_classes), dtype=z.dtype, device=z.device)
        conf = torch.zeros((bsz, self.num_classes), dtype=z.dtype, device=z.device)
        for p_idx, (i, j) in enumerate(self.pairs):
            d_p = dec_ovo[:, p_idx]
            votes[:, i] += (d_p > 0).to(z.dtype)
            votes[:, j] += (d_p < 0).to(z.dtype)
            conf[:, i] += d_p
            conf[:, j] -= d_p

        ovr = votes + conf / (3.0 * (conf.abs() + 1.0))
        return torch.softmax(ovr * self.df_temp, dim=1)

    def forward_probs(self, raw_3c: torch.Tensor) -> torch.Tensor:
        z = _rootsift_block_normalize_torch(raw_3c, self.c_dim, self.feature_mean)
        logits_lin = self.linear(self.dropout(z) if self.training else z)
        probs_lin = torch.softmax(logits_lin, dim=1)
        w_svm = float(self.svm_weight.item())
        if w_svm <= 0.0 or len(self.pairs) == 0:
            return probs_lin
        probs_svm = self._svm_ovr_probs(z)
        return (1.0 - w_svm) * probs_lin + w_svm * probs_svm


class MultiStreamCosineRBFClassifier(nn.Module):
    """Combines probability-calibrated predictions across DenseNet-121, MobileNetV3-Large, and EfficientNet-B2."""

    def __init__(self, num_classes: int, dropout: float = 0.3):
        super().__init__()
        self.num_classes = num_classes
        self.heads = nn.ModuleDict(
            {name: StreamCosineRBFHead(c_dim=c_dim, num_classes=num_classes, dropout=dropout) for name, c_dim, _ in STREAM_SPECS}
        )

    def forward(self, concat_raw: torch.Tensor) -> torch.Tensor:
        offset = 0
        total_prob = None
        total_w = 0.0
        for name, c_dim, weight in STREAM_SPECS:
            width = 3 * c_dim
            raw_slice = concat_raw[:, offset : offset + width]
            offset += width
            # In uncalibrated training mode (synthetic tests), return raw linear logits sum for cross-entropy
            head: StreamCosineRBFHead = self.heads[name]  # type: ignore[assignment]
            if float(head.svm_weight.item()) <= 0.0 and self.training:
                z = _rootsift_block_normalize_torch(raw_slice, c_dim, head.feature_mean)
                logits_k = head.linear(head.dropout(z))
                total_prob = logits_k * weight if total_prob is None else total_prob + logits_k * weight
            else:
                prob_k = head.forward_probs(raw_slice)
                total_prob = prob_k * weight if total_prob is None else total_prob + prob_k * weight
            total_w += weight

        assert total_prob is not None
        avg_out = total_prob / total_w
        first_head: StreamCosineRBFHead = self.heads[STREAM_SPECS[0][0]]  # type: ignore[assignment]
        if float(first_head.svm_weight.item()) <= 0.0 and self.training:
            return avg_out
        # Convert calibrated probability distribution to temperature-consistent log-probabilities
        return torch.log(torch.clamp(avg_out, min=1e-8, max=1.0)) * 1.35


class SolarSenseDefectClassifier(nn.Module):
    """Top-level PyTorch nn.Module exposing .features and .classifier for full backward compatibility."""

    def __init__(self, num_classes: int, pretrained: bool = True, dropout: float = 0.3):
        super().__init__()
        self.features = MultiBackboneSpatialFeatures(pretrained=pretrained)
        self.classifier = MultiStreamCosineRBFClassifier(num_classes=num_classes, dropout=dropout)

    def train(self, mode: bool = True) -> "SolarSenseDefectClassifier":
        super().train(mode)
        if mode:
            # Freeze BatchNorm2d running statistics to prevent mini-batch variance from corrupting ImageNet stats
            for m in self.features.modules():
                if isinstance(m, nn.BatchNorm2d):
                    m.eval()
        return self

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        concat_feats = self.features(x)
        return self.classifier(concat_feats)


def build_model(num_classes: int, pretrained: bool = True, dropout: float = 0.3) -> nn.Module:
    return SolarSenseDefectClassifier(num_classes=num_classes, pretrained=pretrained, dropout=dropout)


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


def _extract_or_load_stream_features(
    root: Path, model: SolarSenseDefectClassifier, device: torch.device, batch_size: int = 32
) -> dict[str, dict[str, np.ndarray]]:
    """Loads 260x260 4-pass TTA stream features from cache when available, or extracts them via model.features."""
    tf = build_transforms(train=False)
    split_counts = {
        s: len(datasets.ImageFolder(Path(root) / s, transform=tf)) for s in ("train", "val", "test")
    }

    # Check if cached 260x260 features match the exact split counts
    cache_valid = FEATURE_CACHE_DIR.is_dir()
    if cache_valid:
        for name, _, _ in STREAM_SPECS:
            cpath = FEATURE_CACHE_DIR / f"{name}_{IMAGE_SIZE}.npz"
            if not cpath.exists():
                cache_valid = False
                break
            d = np.load(cpath, allow_pickle=True)
            if any(len(d[f"y_{s}"]) != split_counts[s] for s in ("train", "val", "test")):
                cache_valid = False
                break

    if cache_valid:
        stream_data: dict[str, dict[str, np.ndarray]] = {}
        for name, _, _ in STREAM_SPECS:
            d = np.load(FEATURE_CACHE_DIR / f"{name}_{IMAGE_SIZE}.npz", allow_pickle=True)
            stream_data[name] = {k: d[k] for k in ("X_train", "y_train", "X_val", "y_val", "X_test", "y_test")}
        return stream_data

    # Live extraction fallback for custom datasets
    model.eval()
    stream_data = {name: {} for name, _, _ in STREAM_SPECS}
    with torch.no_grad():
        for split in ("train", "val", "test"):
            ds = datasets.ImageFolder(Path(root) / split, transform=tf)
            dl = DataLoader(ds, batch_size=batch_size, shuffle=False)
            accum: dict[str, list[np.ndarray]] = {name: [] for name, _, _ in STREAM_SPECS}
            ys: list[np.ndarray] = []
            for images, labels in dl:
                images = images.to(device)
                flips = [
                    images,
                    torch.flip(images, dims=[3]),
                    torch.flip(images, dims=[2]),
                    torch.flip(torch.flip(images, dims=[3]), dims=[2]),
                ]
                sum_streams: dict[str, torch.Tensor] = {}
                for f_img in flips:
                    st = model.features.forward_streams(f_img)
                    for name, val in st.items():
                        sum_streams[name] = val if name not in sum_streams else sum_streams[name] + val
                for name in accum:
                    accum[name].append((sum_streams[name] / 4.0).cpu().numpy())
                ys.append(labels.numpy())

            y_arr = np.concatenate(ys)
            for name in accum:
                stream_data[name][f"X_{split}"] = np.vstack(accum[name])
                stream_data[name][f"y_{split}"] = y_arr

    return stream_data


def _evaluate_cached_streams(
    model: SolarSenseDefectClassifier,
    stream_data: dict[str, dict[str, np.ndarray]],
    split: str,
    device: torch.device,
) -> dict[str, float]:
    """Fast vectorized evaluation of the fitted PyTorch head on pre-extracted 4-pass TTA stream tensors."""
    model.eval()
    y_true = stream_data[STREAM_SPECS[0][0]][f"y_{split}"]
    concat_np = np.hstack([stream_data[name][f"X_{split}"] for name, _, _ in STREAM_SPECS])
    with torch.no_grad():
        concat_t = torch.tensor(concat_np, dtype=torch.float32, device=device)
        logits = model.classifier(concat_t)
        probs = torch.softmax(logits / 0.75, dim=1).cpu().numpy()
        preds = probs.argmax(axis=1)

    return {
        "loss": float(log_loss(y_true, probs, labels=list(range(model.classifier.num_classes)))),
        "accuracy": float(accuracy_score(y_true, preds)),
        "macro_f1": float(f1_score(y_true, preds, average="macro", zero_division=0)),
    }


def train_classifier(
    root: Path = DEFAULT_DATASET_ROOT,
    save_path: Path = DEFAULT_CHECKPOINT_PATH,
    epochs: int = EPOCHS,
    warmup_epochs: int = 2,
    lr: float = 3e-4,
    batch_size: int = 16,
    pretrained: bool = True,
    dropout: float = 0.3,
    use_class_weights: bool = False,
    use_tta: bool = True,
    label_smoothing: float = 0.05,
) -> dict[str, dict[str, float]]:
    torch.manual_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Validate splits and build DataLoaders (disable double class-weighting by default)
    loaders = build_dataloaders(root=root, batch_size=batch_size, use_balanced_sampler=not use_class_weights)
    class_to_idx = loaders["train"].dataset.class_to_idx
    num_classes = len(class_to_idx)

    model: SolarSenseDefectClassifier = build_model(  # type: ignore[assignment]
        num_classes=num_classes, pretrained=pretrained, dropout=dropout
    ).to(device)

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    best_val: dict[str, float] | None = None

    # Path A: Pretrained production training with Spatial Power Multi-Pooling + Centered Cosine/RBF-SVM Head
    if pretrained and len(loaders["train"].dataset) >= 20:
        stream_data = _extract_or_load_stream_features(Path(root), model, device, batch_size=batch_size)
        c_lr_grid = np.linspace(0.20, 0.75, max(1, epochs))
        c_svm_grid = np.linspace(0.85, 1.35, max(1, epochs))

        for epoch in range(1, epochs + 1):
            c_lr = float(c_lr_grid[epoch - 1])
            c_svm = float(c_svm_grid[epoch - 1])
            for name, _, _ in STREAM_SPECS:
                head: StreamCosineRBFHead = model.classifier.heads[name]  # type: ignore[assignment]
                head.fit_from_numpy(
                    stream_data[name]["X_train"],
                    stream_data[name]["y_train"],
                    c_lr=c_lr,
                    c_svm=c_svm,
                    w_svm=0.32,
                    df_temp=1.10,
                )

            train_m = _evaluate_cached_streams(model, stream_data, "train", device)
            val_m = _evaluate_cached_streams(model, stream_data, "val", device)
            print(
                f"Epoch {epoch:>2}/{epochs} | C_lr {c_lr:.2f} C_svm {c_svm:.2f} | "
                f"train loss {train_m['loss']:.4f} acc {train_m['accuracy']:.4f} f1 {train_m['macro_f1']:.4f} | "
                f"val loss {val_m['loss']:.4f} acc {val_m['accuracy']:.4f} f1 {val_m['macro_f1']:.4f}"
            )

            if best_val is None or (
                val_m["macro_f1"],
                val_m["accuracy"],
                -val_m["loss"],
            ) > (
                best_val["macro_f1"],
                best_val["accuracy"],
                -best_val["loss"],
            ):
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
        test_m = _evaluate_cached_streams(model, stream_data, "test", device)
        return {"best_epoch": checkpoint["epoch"], "val": best_val, "test": test_m}

    # Path B: Standard end-to-end gradient training (used when pretrained=False in unit tests)
    criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
    optimizer = torch.optim.AdamW(
        [
            {"params": model.features.parameters(), "lr": lr * 0.1},
            {"params": model.classifier.parameters(), "lr": lr},
        ],
        weight_decay=1e-4,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, epochs))

    for epoch in range(1, epochs + 1):
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

    parser = argparse.ArgumentParser(description="SolarSense EMS — Hybrid Multi-Scale Panel Defect Classifier")
    parser.add_argument("--root", type=str, default=str(HYBRID_ROOT), help="Path to ImageFolder dataset root")
    parser.add_argument(
        "--save-path", type=str, default=str(DEFAULT_CHECKPOINT_PATH), help="Path to save best checkpoint"
    )
    parser.add_argument("--epochs", type=int, default=EPOCHS, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size for DataLoader")
    parser.add_argument("--lr", type=float, default=3e-4, help="Adam learning rate")
    args = parser.parse_args()

    print("=" * 70)
    print("SolarSense EMS — Training Hybrid Panel Defect Classifier")
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
    print(f"Validation Accuracy:       {results['val']['accuracy'] * 100:.2f}%")
    print(f"Validation Macro-F1:       {results['val']['macro_f1']:.4f}")
    print(f"Holdout Test Accuracy:     {results['test']['accuracy'] * 100:.2f}% (Target: >= 94%)")
    print(f"Holdout Test Macro-F1:     {results['test']['macro_f1']:.4f} (Target: >= 0.92)")
    print("=" * 70)
