"""
SolarSense EMS — PyTorch DataLoaders for Dataset A (SolarSense Master V1)
Reads the train/val/test ImageFolder layout written by build_master_dataset.py,
resizes to 260x260 (EfficientNet-B2 native input), applies random flips on the
train split only, and normalizes with ImageNet statistics.
"""

from pathlib import Path

import torch
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import datasets, transforms

MASTER_ROOT = Path("data/processed/panel_images/solarsense_master_v1")
IMAGE_SIZE = 260
SPLITS = ("train", "val", "test")

# ImageNet statistics, matching the pretrained backbone weights
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def build_transforms(train: bool) -> transforms.Compose:
    steps = [transforms.Resize((IMAGE_SIZE, IMAGE_SIZE))]
    if train:
        # Solar panel defects are invariant to flips and subtle rotation/angles.
        # ColorJitter and RandomErasing simulate harsh Lahore sunlight, dust haze, and partial sensor occlusions.
        steps += [
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.5),
            transforms.RandomRotation(degrees=15),
            transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.03),
            transforms.RandomAffine(degrees=10, translate=(0.04, 0.04), scale=(0.95, 1.05)),
        ]
    steps += [transforms.ToTensor(), transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD)]
    if train:
        steps.append(transforms.RandomErasing(p=0.2, scale=(0.02, 0.15), value="random"))
    return transforms.Compose(steps)


def build_dataloaders(
    root: Path = MASTER_ROOT,
    batch_size: int = 32,
    num_workers: int = 0,
    use_balanced_sampler: bool = True,
) -> dict[str, DataLoader]:
    loaders = {}
    for split in SPLITS:
        split_dir = Path(root) / split
        if not split_dir.is_dir():
            raise FileNotFoundError(
                f"Missing split folder: {split_dir}. Run src/vision/build_master_dataset.py first."
            )
        is_train = split == "train"
        dataset = datasets.ImageFolder(split_dir, transform=build_transforms(train=is_train))
        # ImageFolder indexes classes per folder, so a missing class would silently shift labels
        if not is_train and dataset.class_to_idx != loaders["train"].dataset.class_to_idx:
            raise ValueError(
                f"Class folders in {split_dir} do not match train: "
                f"{sorted(dataset.class_to_idx)} vs {sorted(loaders['train'].dataset.class_to_idx)}"
            )

        sampler = None
        shuffle = is_train
        if is_train and use_balanced_sampler and hasattr(dataset, "samples") and len(dataset.samples) > 0:
            targets = [s[1] for s in dataset.samples]
            counts = torch.bincount(torch.tensor(targets), minlength=len(dataset.classes)).float()
            class_weights = 1.0 / torch.clamp(counts, min=1.0)
            sample_weights = class_weights[targets]
            sampler = WeightedRandomSampler(
                weights=sample_weights,
                num_samples=len(sample_weights),
                replacement=True,
            )
            shuffle = False  # Mutually exclusive with sampler in PyTorch

        loaders[split] = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=shuffle,
            sampler=sampler,
            num_workers=num_workers,
        )
    return loaders


if __name__ == "__main__":
    loaders = build_dataloaders()
    print(f"Classes: {loaders['train'].dataset.class_to_idx}")
    for split, loader in loaders.items():
        print(f"  • {split:<5}: {len(loader.dataset)} images")

    images, labels = next(iter(loaders["train"]))
    print(f"Batch shape: {tuple(images.shape)}, labels: {tuple(labels.shape)}")
    print(f"Per-channel mean: {images.mean(dim=(0, 2, 3)).tolist()}")
    print(f"Per-channel std : {images.std(dim=(0, 2, 3)).tolist()}")
