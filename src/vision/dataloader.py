"""
SolarSense EMS — PyTorch DataLoaders for Dataset A (SolarSense Master V1)
Reads the train/val/test ImageFolder layout written by build_master_dataset.py,
resizes to 260x260 (EfficientNet-B2 native input), applies random flips on the
train split only, and normalizes with ImageNet statistics.
"""

from pathlib import Path

from torch.utils.data import DataLoader
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
        # Panel defects look the same in any orientation, so both flips are label-safe.
        # Photometric jitter and slight affine perturbation simulate solar glare and CCTV angle shifts.
        steps += [
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1),
            transforms.RandomAffine(degrees=10, translate=(0.04, 0.04), scale=(0.96, 1.04)),
        ]
    steps += [transforms.ToTensor(), transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD)]
    return transforms.Compose(steps)



def build_dataloaders(
    root: Path = MASTER_ROOT,
    batch_size: int = 32,
    num_workers: int = 0
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
        loaders[split] = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=is_train,
            num_workers=num_workers
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
