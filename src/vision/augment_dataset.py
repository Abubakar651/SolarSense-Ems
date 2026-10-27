"""
SolarSense EMS — Offline Dataset Augmentation & Balancing Engine
================================================================
Generates photometrically and geometrically augmented training images to:
1. Balance minority defect classes (bird_drop, electrical_damage, physical_damage)
2. Simulate realistic rooftop solar environmental stressors:
   - Solar noon glare and high saturation
   - Winter smog / haze (low contrast, diffuse lighting)
   - CCTV installation tilt angles (+/- 15 deg)
   - Thermal hot spot discoloration
   - High-frequency micro-contrast (revealing hairline cracks)
3. Output a balanced, augmented dataset: data/processed/panel_images/solarsense_augmented_v1
"""

import argparse
import random
import shutil
import sys
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_INPUT_ROOT = Path("data/processed/panel_images/solarsense_hybrid_v1")
DEFAULT_OUTPUT_ROOT = Path("data/processed/panel_images/solarsense_augmented_v1")
TARGET_TRAIN_PER_CLASS = 200


def apply_photometric_jitter(img: Image.Image) -> Image.Image:
    """Simulates harsh solar illumination, haze, and color temperature shifts."""
    # Brightness (0.75 - 1.30)
    b_factor = random.uniform(0.75, 1.30)
    img = ImageEnhance.Brightness(img).enhance(b_factor)

    # Contrast (0.80 - 1.30)
    c_factor = random.uniform(0.80, 1.30)
    img = ImageEnhance.Contrast(img).enhance(c_factor)

    # Color saturation (0.80 - 1.25)
    s_factor = random.uniform(0.80, 1.25)
    img = ImageEnhance.Color(img).enhance(s_factor)

    # Sharpness (0.90 - 1.40) to highlight crack and bird droppings edges
    sh_factor = random.uniform(0.90, 1.40)
    img = ImageEnhance.Sharpness(img).enhance(sh_factor)

    return img


def apply_geometric_transform(img: Image.Image) -> Image.Image:
    """Applies physics-preserving rotations and flips."""
    # Random horizontal or vertical flip
    if random.random() < 0.5:
        img = ImageOps.mirror(img)
    if random.random() < 0.5:
        img = ImageOps.flip(img)

    # Random subtle angle rotation (-15 to +15 deg)
    angle = random.uniform(-15.0, 15.0)
    img = img.rotate(angle, resample=Image.Resampling.BILINEAR, expand=False)

    return img


def generate_augmented_dataset(
    input_root: Path = DEFAULT_INPUT_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    target_per_class: int = TARGET_TRAIN_PER_CLASS,
    seed: int = 42,
) -> dict[str, int]:
    random.seed(seed)
    input_root = Path(input_root)
    output_root = Path(output_root)

    print("=" * 70)
    print("SOLARSENSE EMS — OFFLINE DATASET AUGMENTATION & BALANCING ENGINE")
    print(f"Input Dataset:      {input_root}")
    print(f"Output Dataset:     {output_root}")
    print(f"Target Train/Class: {target_per_class}")
    print("=" * 70)

    # Recreate output structure
    if output_root.exists():
        shutil.rmtree(output_root)

    counts = {}

    for split in ["train", "val", "test"]:
        in_split = input_root / split
        out_split = output_root / split
        out_split.mkdir(parents=True, exist_ok=True)

        if not in_split.exists():
            continue

        for class_dir in in_split.iterdir():
            if not class_dir.is_dir():
                continue

            out_class_dir = out_split / class_dir.name
            out_class_dir.mkdir(parents=True, exist_ok=True)

            images = sorted(list(class_dir.glob("*.jpg")) + list(class_dir.glob("*.png")))
            # Copy all original images first
            for img_p in images:
                shutil.copy2(img_p, out_class_dir / img_p.name)

            if split == "train":
                current_count = len(images)
                aug_idx = 0
                while current_count < target_per_class:
                    base_img_path = images[aug_idx % len(images)]
                    with Image.open(base_img_path) as img:
                        aug_img = img.convert("RGB")
                        aug_img = apply_geometric_transform(aug_img)
                        aug_img = apply_photometric_jitter(aug_img)

                        aug_name = f"{base_img_path.stem}_aug_{aug_idx:04d}.jpg"
                        aug_img.save(out_class_dir / aug_name, quality=95)

                    current_count += 1
                    aug_idx += 1

                counts[f"{split}/{class_dir.name}"] = current_count
                print(f"  [{split:<5}] {class_dir.name:<18}: {len(images):>3} original -> {current_count:>3} balanced")
            else:
                counts[f"{split}/{class_dir.name}"] = len(images)
                print(f"  [{split:<5}] {class_dir.name:<18}: {len(images):>3} pristine holdout (no augmentation)")

    print("=" * 70)
    print("[SUCCESS] Augmented dataset created successfully at:", output_root)
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SolarSense EMS — Offline Dataset Augmentation")
    parser.add_argument("--input", type=str, default=str(DEFAULT_INPUT_ROOT), help="Input dataset root")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_ROOT), help="Output dataset root")
    parser.add_argument("--target", type=int, default=TARGET_TRAIN_PER_CLASS, help="Target training images per class")
    args = parser.parse_args()

    generate_augmented_dataset(input_root=Path(args.input), output_root=Path(args.output), target_per_class=args.target)
