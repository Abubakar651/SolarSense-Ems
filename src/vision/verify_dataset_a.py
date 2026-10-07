"""
SolarSense EMS — Protocol 1 Image Verification Suite (Dataset A)
Executes comprehensive integrity, resolution, duplicate hashing, split leakage,
and sample grid generation for solar panel image datasets.
"""

import os
import sys
import hashlib
from collections import Counter
from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt


def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_image_dataset(dataset_dir: Path, output_grid_path: Path = None):
    print(f"==================================================")
    print(f"SOLARSENSE EMS — PROTOCOL 1: DATASET A VERIFICATION")
    print(f"Target Directory: {dataset_dir}")
    print(f"==================================================")

    if not dataset_dir.exists():
        print(f"[ERROR] Directory not found: {dataset_dir}")
        return

    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
    all_files = [p for p in dataset_dir.rglob("*") if p.is_file() and p.suffix.lower() in image_extensions]

    if not all_files:
        print("[WARNING] No image files found in directory.")
        return

    print(f"Total image files discovered: {len(all_files)}")

    # 1. PIL Integrity Check & Resolution Analysis
    corrupt_files = []
    resolutions = []
    hashes = {}
    duplicates = []
    class_counts = Counter()
    split_counts = Counter()
    split_hashes = {}  # split_name -> set of hashes (for leakage check)

    for img_path in all_files:
        # Determine class and split from folder structure
        # Typical formats:
        # 1. dataset/split/class/img.jpg
        # 2. dataset/class/img.jpg
        rel_parts = img_path.relative_to(dataset_dir).parts
        if len(rel_parts) >= 3 and rel_parts[0].lower() in {"train", "val", "validation", "test"}:
            split_name = rel_parts[0].lower()
            class_name = rel_parts[1]
        elif len(rel_parts) >= 2:
            split_name = "default"
            class_name = rel_parts[0]
        else:
            split_name = "default"
            class_name = "unclassified"

        class_counts[class_name] += 1
        split_counts[split_name] += 1

        # PIL integrity check
        try:
            with Image.open(img_path) as im:
                im.verify()  # verify integrity
            with Image.open(img_path) as im:
                resolutions.append(im.size)  # (width, height)
        except Exception as e:
            corrupt_files.append((str(img_path), str(e)))
            continue

        # Hash check
        h = compute_sha256(img_path)
        if h in hashes:
            duplicates.append((str(img_path), hashes[h]))
        else:
            hashes[h] = str(img_path)

        if split_name != "default":
            split_hashes.setdefault(split_name, {})[h] = str(img_path)

    # 2. Integrity Summary
    print(f"\n--- 1. PIL INTEGRITY CHECK ---")
    if corrupt_files:
        print(f"[FAIL] Found {len(corrupt_files)} corrupt or truncated image(s):")
        for f, err in corrupt_files[:5]:
            print(f"  - {f}: {err}")
    else:
        print(f"[PASS] 100% of tested images ({len(all_files)}) opened cleanly without corruption.")

    # 3. Class Distribution & Balance
    print(f"\n--- 2. CLASS DISTRIBUTION & BALANCE ---")
    total_valid = len(all_files) - len(corrupt_files)
    underrepresented = []
    for cls, count in sorted(class_counts.items(), key=lambda x: -x[1]):
        pct = (count / total_valid) * 100
        flag = " [UNDERREPRESENTED <10%]" if pct < 10.0 else ""
        print(f"  • {cls:<20}: {count:>5} images ({pct:5.2f}%){flag}")
        if pct < 10.0:
            underrepresented.append(cls)

    if underrepresented:
        print(f"[WARNING] Classes with <10% representation: {', '.join(underrepresented)}")
    else:
        print(f"[PASS] All classes meet the >=10% representation threshold.")

    # 4. Split Distribution
    if len(split_counts) > 1 or "default" not in split_counts:
        print(f"\n--- 3. DATA SPLITS ---")
        for sp, count in split_counts.items():
            print(f"  • {sp:<15}: {count:>5} images")

    # 5. Duplicate Check
    print(f"\n--- 4. DUPLICATE CHECK (SHA256) ---")
    if duplicates:
        print(f"[WARNING] Found {len(duplicates)} duplicate image pair(s):")
        for dup, orig in duplicates[:5]:
            print(f"  - {Path(dup).name} matches {Path(orig).name}")
    else:
        print(f"[PASS] No duplicate images found (all SHA256 hashes unique).")

    # 6. Data Leakage Check
    if len(split_hashes) > 1:
        print(f"\n--- 5. DATA LEAKAGE ACROSS SPLITS ---")
        splits = list(split_hashes.keys())
        leakage_found = False
        for i in range(len(splits)):
            for j in range(i + 1, len(splits)):
                s1, s2 = splits[i], splits[j]
                overlap = set(split_hashes[s1].keys()) & set(split_hashes[s2].keys())
                if overlap:
                    leakage_found = True
                    print(f"[FAIL] Data leakage detected between {s1} and {s2}: {len(overlap)} shared images!")
        if not leakage_found:
            print(f"[PASS] Zero data leakage: No images overlap between train, val, and test splits.")

    # 7. Resolution Analysis
    if resolutions:
        widths, heights = zip(*resolutions)
        min_dim = (min(widths), min(heights))
        max_dim = (max(widths), max(heights))
        modal_dim = Counter(resolutions).most_common(1)[0]
        print(f"\n--- 6. RESOLUTION ANALYSIS ---")
        print(f"  • Minimum dimensions: {min_dim[0]} × {min_dim[1]} px")
        print(f"  • Maximum dimensions: {max_dim[0]} × {max_dim[1]} px")
        print(f"  • Modal dimensions  : {modal_dim[0][0]} × {modal_dim[0][1]} px ({modal_dim[1]} images)")

    # 8. Metadata CSV Audit
    meta_csv = dataset_dir / "metadata.csv"
    if meta_csv.exists():
        print(f"\n--- 7. METADATA AUDIT (metadata.csv) ---")
        import csv
        with open(meta_csv, "r") as f:
            reader = csv.DictReader(f)
            meta_rows = list(reader)
        print(f"  • Total recorded entries in metadata.csv: {len(meta_rows)}")
        missing_files = 0
        for r in meta_rows:
            p = dataset_dir / r["relative_path"]
            if not p.exists():
                missing_files += 1
        if missing_files == 0:
            print(f"[PASS] 100% of metadata.csv entries map to existing files on disk.")
        else:
            print(f"[FAIL] {missing_files} metadata entries are missing from disk!")

    # 9. Sample Grid Generation
    if output_grid_path:
        print(f"\n--- 8. GENERATING VERIFICATION GRID ---")
        generate_sample_grid(dataset_dir, class_counts.keys(), output_grid_path)


def generate_sample_grid(dataset_dir: Path, classes, output_path: Path):
    import matplotlib
    matplotlib.use('Agg')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Include all valid non-snow classes (up to 5 classes, 3 samples each = 15 images)
    selected_classes = [c for c in classes if c.lower() not in {"snow-covered", "snow", "unclassified"}]

    samples = []
    labels = []
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    for cls in selected_classes:
        cls_images = [p for p in dataset_dir.rglob("*") if p.is_file() and p.suffix.lower() in image_extensions and p.parent.name == cls]
        for p in cls_images[:3]:
            try:
                img = Image.open(p).convert("RGB")
                samples.append(img)
                labels.append(f"{cls}\n({img.width}x{img.height})")
            except Exception:
                pass

    if not samples:
        print("[WARNING] Could not load sample images for grid.")
        return

    n_images = len(samples)
    cols = 3
    rows = (n_images + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(12, 3.8 * rows))
    if hasattr(axes, "flatten"):
        axes = axes.flatten()
    elif not isinstance(axes, (list, tuple)):
        axes = [axes]

    for i in range(len(axes)):
        if i < n_images:
            axes[i].imshow(samples[i])
            axes[i].set_title(labels[i], fontsize=10, pad=4)
        axes[i].axis("off")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[SAVED] Sample grid saved to: {output_path}")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw/panel_images")
    grid_out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("docs/samples/dataset_A_grid.png")
    verify_image_dataset(target, grid_out)
