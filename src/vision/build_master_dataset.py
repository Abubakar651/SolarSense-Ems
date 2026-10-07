"""
SolarSense EMS — Master Dataset Engineering & Preprocessing Pipeline
Performs file-by-file deep audit, two-stage deduplication (exact SHA-256 + perceptual dHash),
color/channel normalization (RGB), Lanczos 512x512 letterbox resizing, stratified splitting,
and master metadata CSV export.
"""

import os
import sys
import csv
import shutil
import random
import hashlib
from pathlib import Path
from collections import Counter
from PIL import Image

from image_hasher import compute_dhash, hamming_distance
from deep_inspector import safe_convert_to_rgb, letterbox_resize, inspect_single_image

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

RAW_ROOT = Path("data/raw/panel_images")
MASTER_ROOT = Path("data/processed/panel_images/solarsense_master_v1")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

TARGET_RESOLUTION = (512, 512)
JPEG_QUALITY = 95
DHASH_THRESHOLD = 2  # Hamming distance <= 2 indicates near-identical visual content


def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_bytes_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def determine_source_and_class(p: Path):
    parts = [part.lower() for part in p.relative_to(RAW_ROOT).parts]
    source_name = "alicjalena" if "alicjalena" in parts[0] else ("hemanthsai7" if "hemanthsai7" in parts[0] else "unknown")

    parent_name = p.parent.name.lower().strip()

    if "snow" in parent_name:
        return source_name, "snow_covered"
    elif "clean" in parent_name:
        return source_name, "clean"
    elif "dust" in parent_name:
        return source_name, "dusty"
    elif "bird" in parent_name:
        return source_name, "bird_drop"
    elif "electrical" in parent_name:
        return source_name, "electrical_damage"
    elif "physical" in parent_name:
        return source_name, "physical_damage"
    else:
        return source_name, "unknown"


def run_pipeline(
    clean_target: int = 210,
    dusty_target: int = 210,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15
):
    print("==================================================")
    print("SOLARSENSE EMS — MASTER DATASET PREPROCESSING")
    print(f"Target Output: {MASTER_ROOT}")
    print(f"Standardized Resolution: {TARGET_RESOLUTION[0]}x{TARGET_RESOLUTION[1]} px")
    print("==================================================")

    all_raw_files = [p for p in RAW_ROOT.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
    print(f"Discovered {len(all_raw_files)} raw files across all source folders.")

    # Tracking metrics
    audit_stats = {
        "total_scanned": len(all_raw_files),
        "corrupt": 0,
        "degenerate": 0,
        "snow_pruned": 0,
        "exact_duplicates": 0,
        "perceptual_duplicates": 0,
        "accepted": 0,
        "modes_converted": Counter()
    }

    seen_sha256 = set()
    accepted_by_class = {
        "clean": [],
        "dusty": [],
        "bird_drop": [],
        "electrical_damage": [],
        "physical_damage": []
    }

    # Global perceptual hashes for near-duplicate rejection across all classes
    global_dhashes = []

    print("\n[PHASE 1] Deep file-by-file audit & two-stage deduplication...")
    for idx, p in enumerate(all_raw_files, 1):
        if idx % 1000 == 0 or idx == len(all_raw_files):
            print(f"  Processed {idx}/{len(all_raw_files)} files...")

        source_name, canonical_class = determine_source_and_class(p)

        # 1. Prune climate-irrelevant classes
        if canonical_class == "snow_covered":
            audit_stats["snow_pruned"] += 1
            continue
        if canonical_class not in accepted_by_class:
            continue

        # 2. Deep File Inspection
        info = inspect_single_image(p)
        if not info["valid"]:
            audit_stats["corrupt"] += 1
            continue
        if info["degenerate"]:
            audit_stats["degenerate"] += 1
            continue

        # 3. Stage 1 Deduplication: Exact SHA256
        sha = compute_sha256(p)
        if sha in seen_sha256:
            audit_stats["exact_duplicates"] += 1
            continue

        # 4. Stage 2 Deduplication: Perceptual dHash (Global across all classes)
        try:
            with Image.open(p) as raw_img:
                rgb_img = safe_convert_to_rgb(raw_img)
                d_hash = compute_dhash(rgb_img)
        except Exception:
            audit_stats["corrupt"] += 1
            continue

        # Compare with all accepted images globally
        is_near_dup = False
        for existing_hash in global_dhashes:
            if hamming_distance(d_hash, existing_hash) <= DHASH_THRESHOLD:
                is_near_dup = True
                break

        if is_near_dup:
            audit_stats["perceptual_duplicates"] += 1
            continue

        # Accept image
        seen_sha256.add(sha)
        global_dhashes.append(d_hash)
        audit_stats["modes_converted"][info["mode"]] += 1

        accepted_by_class[canonical_class].append({
            "path": p,
            "source": source_name,
            "orig_info": info,
            "orig_sha256": sha,
            "dhash": f"{d_hash:016x}"
        })

    print("\n--- PHASE 1 SUMMARY REPORT ---")
    print(f"  • Total files scanned            : {audit_stats['total_scanned']}")
    print(f"  • Corrupt files discarded        : {audit_stats['corrupt']}")
    print(f"  • Degenerate / blank discarded   : {audit_stats['degenerate']}")
    print(f"  • Snow images pruned (Lahore)    : {audit_stats['snow_pruned']}")
    print(f"  • Exact byte duplicates removed  : {audit_stats['exact_duplicates']}")
    print(f"  • Perceptual near-duplicates cut : {audit_stats['perceptual_duplicates']}")
    print(f"  • Unique high-quality pool       : {sum(len(v) for v in accepted_by_class.values())}")
    print(f"  • Color modes normalized to RGB  : {dict(audit_stats['modes_converted'])}")

    print("\n--- UNIQUE IMAGES AVAILABLE PER CLASS ---")
    for cls, items in accepted_by_class.items():
        print(f"  • {cls:<20}: {len(items)} images")

    # [PHASE 2] Class Balancing & Stratification
    print("\n[PHASE 2] Class balancing & stratified partitioning...")
    random.shuffle(accepted_by_class["clean"])
    random.shuffle(accepted_by_class["dusty"])

    balanced_pool = {
        "clean": accepted_by_class["clean"][:clean_target],
        "dusty": accepted_by_class["dusty"][:dusty_target],
        "bird_drop": accepted_by_class["bird_drop"],
        "electrical_damage": accepted_by_class["electrical_damage"],
        "physical_damage": accepted_by_class["physical_damage"]
    }

    # Initialize destination folders
    if MASTER_ROOT.exists():
        shutil.rmtree(MASTER_ROOT)

    for split in ["train", "val", "test"]:
        for cls in balanced_pool.keys():
            (MASTER_ROOT / split / cls).mkdir(parents=True, exist_ok=True)

    metadata_rows = []
    split_counts = {cls: {"train": 0, "val": 0, "test": 0, "total": 0} for cls in balanced_pool}

    print("\n[PHASE 3] Geometry standardization (512x512 Lanczos) & metadata logging...")
    for cls, items in balanced_pool.items():
        random.shuffle(items)
        total = len(items)
        n_train = int(total * train_ratio)
        n_val = int(total * val_ratio)
        n_test = total - n_train - n_val

        splits = {
            "train": items[:n_train],
            "val": items[n_train:n_train + n_val],
            "test": items[n_train + n_val:]
        }

        for split_name, split_items in splits.items():
            for idx, item in enumerate(split_items, 1):
                image_id = f"{cls}_{split_name}_{idx:04d}"
                out_filename = f"{image_id}.jpg"
                dest_path = MASTER_ROOT / split_name / cls / out_filename
                rel_path = f"{split_name}/{cls}/{out_filename}"

                # Standardize image
                with Image.open(item["path"]) as raw_img:
                    rgb_img = safe_convert_to_rgb(raw_img)
                    standardized_img = letterbox_resize(rgb_img, TARGET_RESOLUTION)
                    standardized_img.save(dest_path, "JPEG", quality=JPEG_QUALITY, optimize=True)

                # Processed image checksum & inspection
                processed_sha256 = compute_sha256(dest_path)
                processed_info = inspect_single_image(dest_path)

                metadata_rows.append({
                    "image_id": image_id,
                    "class": cls,
                    "split": split_name,
                    "filename": out_filename,
                    "relative_path": rel_path,
                    "source_dataset": item["source"],
                    "original_filename": item["path"].name,
                    "original_width": item["orig_info"]["width"],
                    "original_height": item["orig_info"]["height"],
                    "original_aspect_ratio": item["orig_info"]["aspect_ratio"],
                    "original_mode": item["orig_info"]["mode"],
                    "processed_width": TARGET_RESOLUTION[0],
                    "processed_height": TARGET_RESOLUTION[1],
                    "mean_brightness": processed_info["brightness"],
                    "contrast_std": processed_info["contrast"],
                    "processed_sha256": processed_sha256,
                    "dhash_hex": item["dhash"]
                })

                split_counts[cls][split_name] += 1
            split_counts[cls]["total"] += len(split_items)

    # Write Master Metadata CSV
    csv_path = MASTER_ROOT / "metadata.csv"
    fieldnames = [
        "image_id", "class", "split", "filename", "relative_path",
        "source_dataset", "original_filename", "original_width", "original_height",
        "original_aspect_ratio", "original_mode", "processed_width", "processed_height",
        "mean_brightness", "contrast_std", "processed_sha256", "dhash_hex"
    ]

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(metadata_rows)

    print(f"\n[METADATA] Master metadata CSV exported: {csv_path} ({len(metadata_rows)} rows)")

    # Print Final Verification Table
    grand_total = sum(c["total"] for c in split_counts.values())
    print("\n==================================================")
    print("SOLARSENSE MASTER DATASET (V1): FINAL DISTRIBUTION")
    print("==================================================")
    print(f"{'Class':<20} {'Train':<8} {'Val':<8} {'Test':<8} {'Total':<8} {'Share (%)':<10} {'Protocol 1'}")
    print("-" * 75)
    for cls, c in split_counts.items():
        pct = (c["total"] / grand_total * 100) if grand_total > 0 else 0
        status = "PASS (>=10%)" if pct >= 10.0 else "FAIL (<10%)"
        print(f"{cls:<20} {c['train']:<8} {c['val']:<8} {c['test']:<8} {c['total']:<8} {pct:6.2f}%    {status}")
    print("-" * 75)
    tot_tr = sum(c['train'] for c in split_counts.values())
    tot_va = sum(c['val'] for c in split_counts.values())
    tot_te = sum(c['test'] for c in split_counts.values())
    print(f"{'GRAND TOTAL':<20} {tot_tr:<8} {tot_va:<8} {tot_te:<8} {grand_total:<8} 100.00%    OPTIMAL")
    print("==================================================")
    return True


if __name__ == "__main__":
    run_pipeline()
