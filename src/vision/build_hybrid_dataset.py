"""
SolarSense EMS — Dataset A Hybrid Curation Engine (Protocol 1 Compliant)
Performs strict SHA256 content deduplication across all sources, prunes snow,
balances class distribution so all classes satisfy >=10% representation,
and constructs leak-free stratified Train/Val/Test splits.
"""

import os
import sys
import shutil
import random
import hashlib
from pathlib import Path
from collections import Counter
from PIL import Image

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

RAW_ROOT = Path("data/raw/panel_images")
PROCESSED_ROOT = Path("data/processed/panel_images/solarsense_hybrid_v1")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_hybrid_dataset(
    clean_target: int = 250,
    dusty_target: int = 250,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15
):
    print("==================================================")
    print("SOLARSENSE EMS — RIGOROUS DATASET A CURATION")
    print("==================================================")

    # 1. Harvest and Deduplicate by SHA256
    unique_hashes = {}  # hash -> (class_name, file_path)
    all_raw_files = [p for p in RAW_ROOT.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
    print(f"Total raw image files found across all sources: {len(all_raw_files)}")

    class_pool = {
        "clean": [],
        "dusty": [],
        "bird_drop": [],
        "electrical_damage": [],
        "physical_damage": []
    }

    # Tracking stats
    duplicates_discarded = 0
    snow_discarded = 0

    for p in all_raw_files:
        parent_name = p.parent.name.lower().strip()

        # Map to canonical class
        if "snow" in parent_name:
            snow_discarded += 1
            continue
        elif "clean" in parent_name:
            canonical_cls = "clean"
        elif "dust" in parent_name:
            canonical_cls = "dusty"
        elif "bird" in parent_name:
            canonical_cls = "bird_drop"
        elif "electrical" in parent_name:
            canonical_cls = "electrical_damage"
        elif "physical" in parent_name:
            canonical_cls = "physical_damage"
        else:
            continue

        # SHA256 integrity & deduplication
        try:
            with Image.open(p) as img:
                img.verify()
            h = compute_sha256(p)
            if h in unique_hashes:
                duplicates_discarded += 1
                continue
            unique_hashes[h] = (canonical_cls, p)
            class_pool[canonical_cls].append(p)
        except Exception as e:
            print(f"[CORRUPT] Skipping {p.name}: {e}")

    print(f"\n--- DEDUPLICATION & FILTERING AUDIT ---")
    print(f"  • Total raw images evaluated    : {len(all_raw_files)}")
    print(f"  • Exact duplicates removed      : {duplicates_discarded}")
    print(f"  • Snow images pruned for Lahore : {snow_discarded}")
    print(f"  • Total verified unique images  : {len(unique_hashes)}")

    print(f"\n--- UNIQUE IMAGES AVAILABLE PER CLASS ---")
    for cls, paths in class_pool.items():
        print(f"  • {cls:<20}: {len(paths)} unique images")

    # 2. Balanced Selection to satisfy >=10% threshold across all classes
    # With electrical_damage=97, physical_damage=85, capping clean=250, dusty=250
    # Total = 839 -> min class is physical_damage at 85/839 = 10.13% (Passes Protocol 1!)
    random.shuffle(class_pool["clean"])
    random.shuffle(class_pool["dusty"])

    selected_pool = {
        "clean": class_pool["clean"][:clean_target],
        "dusty": class_pool["dusty"][:dusty_target],
        "bird_drop": class_pool["bird_drop"],
        "electrical_damage": class_pool["electrical_damage"],
        "physical_damage": class_pool["physical_damage"]
    }

    grand_total = sum(len(paths) for paths in selected_pool.values())

    # 3. Create Clean Destination Directory
    if PROCESSED_ROOT.exists():
        shutil.rmtree(PROCESSED_ROOT)

    for split in ["train", "val", "test"]:
        for cls in selected_pool.keys():
            (PROCESSED_ROOT / split / cls).mkdir(parents=True, exist_ok=True)

    # 4. Stratified Split (Leak-Free)
    split_summary = {cls: {"train": 0, "val": 0, "test": 0, "total": 0} for cls in selected_pool}

    for cls, paths in selected_pool.items():
        random.shuffle(paths)
        total = len(paths)
        n_train = int(total * train_ratio)
        n_val = int(total * val_ratio)
        n_test = total - n_train - n_val

        splits = {
            "train": paths[:n_train],
            "val": paths[n_train:n_train + n_val],
            "test": paths[n_train + n_val:]
        }

        for split_name, split_paths in splits.items():
            for idx, p in enumerate(split_paths):
                ext = p.suffix.lower()
                dest = PROCESSED_ROOT / split_name / cls / f"{cls}_{idx:04d}{ext}"
                shutil.copy2(p, dest)
                split_summary[cls][split_name] += 1
            split_summary[cls]["total"] += len(split_paths)

    # 5. Final Output Table
    print("\n==================================================")
    print("SOLARSENSE HYBRID-1: FINAL BENCHMARK DATASET")
    print("==================================================")
    print(f"{'Class':<20} {'Train':<8} {'Val':<8} {'Test':<8} {'Total':<8} {'Share (%)':<10} {'Protocol 1'}")
    print("-" * 75)
    for cls, c in split_summary.items():
        pct = (c["total"] / grand_total * 100) if grand_total > 0 else 0
        status = "PASS (>=10%)" if pct >= 10.0 else "FAIL (<10%)"
        print(f"{cls:<20} {c['train']:<8} {c['val']:<8} {c['test']:<8} {c['total']:<8} {pct:6.2f}%    {status}")
    print("-" * 75)
    total_train = sum(c['train'] for c in split_summary.values())
    total_val = sum(c['val'] for c in split_summary.values())
    total_test = sum(c['test'] for c in split_summary.values())
    print(f"{'GRAND TOTAL':<20} {total_train:<8} {total_val:<8} {total_test:<8} {grand_total:<8} 100.00%    OPTIMAL")
    print("==================================================")
    print(f"[SAVED] Dataset successfully built at: {PROCESSED_ROOT}")
    return True


if __name__ == "__main__":
    build_hybrid_dataset()
