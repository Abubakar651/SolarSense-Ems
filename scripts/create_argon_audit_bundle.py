#!/usr/bin/env python3
"""
Dynamic Codebase & Data Archiver for Argon Review.
Discovers and bundles core source code, test suites, configs, processed datasets,
and Argon audit packs into a clean, portable zip archive: solarsense_argon_audit_bundle.zip.
"""

from collections import Counter
import os
from pathlib import Path
import sys
import zipfile

# Set up paths relative to repository root
REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ZIP_NAME = "solarsense_argon_audit_bundle.zip"
OUTPUT_ZIP_PATH = REPO_ROOT / OUTPUT_ZIP_NAME

# Allowed file extensions for code, config, documentation, and audited datasets
ALLOWED_EXTENSIONS = {
    ".py",
    ".json",
    ".md",
    ".toml",
    ".csv",
    ".xlsx",
    ".yaml",
    ".yml",
    ".parquet",
    ".ini",
    ".txt",
    ".ipynb",   # Jupyter EDA notebooks (including industrial load & MDI)
    ".joblib",  # Trained ML forecasters (including factory_load_lightgbm)
    ".docx",    # Specifications and audit documentation
}

# Directories and folders to exclude completely
EXCLUDE_DIRS = {
    ".venv",
    "venv",
    "env",
    "node_modules",
    ".git",
    "__pycache__",
    ".pytest_cache",
    "build",
    "dist",
    ".eggs",
    "logs",
    ".system_generated",
    ".gemini",
    "scratch",
    ".cache",
    "panel_images",  # Exclude heavy raw imagery (300+ MB)
    "backups",       # Exclude local raw backups
}

# Files or prefix patterns to exclude (e.g. secret files, lock files, archives)
EXCLUDE_FILE_PATTERNS = {
    ".env",
    ".DS_Store",
    "Thumbs.db",
}

# Specific high-value documentation and diagram assets to include
EXPLICIT_INCLUDE_FILES = {
    "docs/SolarSense_Industrial_EMS.pptx",
    "docs/samples/load_and_mdi_spikes.png",
}


def should_include_file(file_path: Path) -> bool:
    """Evaluate whether a given file path meets inclusion criteria."""
    if not file_path.is_file():
        return False

    rel_path = file_path.relative_to(REPO_ROOT)
    rel_str = str(rel_path)

    # Check for excluded directory parts
    for part in rel_path.parts[:-1]:
        if part in EXCLUDE_DIRS:
            return False

    # Check filename rules
    name = file_path.name
    if name.startswith(".~lock") or name.startswith(".git") or name.startswith(".thunderbird"):
        return False
    if name in EXCLUDE_FILE_PATTERNS or name.startswith(".env"):
        return False
    if name.endswith(".zip") or name.endswith(".tar.gz") or name.endswith(".eml") or name.endswith(".pyc"):
        return False

    # Check explicit includes (e.g., industrial slide deck & MDI charts)
    if rel_str in EXPLICIT_INCLUDE_FILES:
        return True

    # Extension check
    return file_path.suffix.lower() in ALLOWED_EXTENSIONS


def build_audit_bundle() -> None:
    """Dynamically scan repository, build the zip archive, and verify contents."""
    print("=" * 80)
    print("   SOLARSENSE EMS — DYNAMIC CODEBASE & DATA ARCHIVER FOR ARGON REVIEW")
    print("=" * 80)
    print(f"Scanning workspace root: {REPO_ROOT}")

    matched_files = []
    category_counts = Counter()
    total_uncompressed_bytes = 0

    for path in sorted(REPO_ROOT.rglob("*")):
        if should_include_file(path):
            rel_path = path.relative_to(REPO_ROOT)
            matched_files.append((path, rel_path))
            total_uncompressed_bytes += path.stat().st_size

            top_folder = rel_path.parts[0] if len(rel_path.parts) > 1 else "[root]"
            category_counts[top_folder] += 1

    print(f"\nDiscovered {len(matched_files)} matching files across the repository:")
    for category, count in sorted(category_counts.items()):
        print(f"  • {category:<25s}: {count:3d} files")

    # Build the zip bundle
    print(f"\nCreating compressed archive: {OUTPUT_ZIP_PATH} ...")
    if OUTPUT_ZIP_PATH.exists():
        OUTPUT_ZIP_PATH.unlink()

    with zipfile.ZipFile(
        OUTPUT_ZIP_PATH,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zf:
        for abs_path, rel_path in matched_files:
            zf.write(abs_path, arcname=str(rel_path))

    # Verification of the generated archive
    compressed_size_bytes = OUTPUT_ZIP_PATH.stat().st_size
    uncompressed_mb = total_uncompressed_bytes / (1024 * 1024)
    compressed_mb = compressed_size_bytes / (1024 * 1024)
    compression_ratio = (
        (1.0 - (compressed_size_bytes / total_uncompressed_bytes)) * 100
        if total_uncompressed_bytes > 0
        else 0.0
    )

    # Integrity verification
    with zipfile.ZipFile(OUTPUT_ZIP_PATH, mode="r") as zf:
        bad_file = zf.testzip()
        if bad_file:
            print(f"\n[ERROR] Corrupted file found in archive: {bad_file}", file=sys.stderr)
            sys.exit(1)
        archive_file_count = len(zf.namelist())

    print("\n" + "=" * 80)
    print("   ARCHIVE VERIFICATION REPORT")
    print("=" * 80)
    print(f"  • Archive Name:        {OUTPUT_ZIP_NAME}")
    print(f"  • Destination Path:    {OUTPUT_ZIP_PATH}")
    print(f"  • Total Files Packed:  {archive_file_count} files")
    print(f"  • Uncompressed Size:   {uncompressed_mb:.2f} MB")
    print(f"  • Compressed Size:     {compressed_mb:.2f} MB")
    print(f"  • Space Saved:         {compression_ratio:.1f}%")
    print(f"  • Archive Integrity:   100% OK (testzip passed, 0 CRC errors)")
    print("=" * 80)

    # 4. Deep Industrial Microgrid Verification Scan
    print("\n" + "=" * 80)
    print("   DEEP INDUSTRIAL MICROGRID COVERAGE VERIFICATION")
    print("=" * 80)
    with zipfile.ZipFile(OUTPUT_ZIP_PATH, mode="r") as zf:
        packed_names = set(zf.namelist())

    industrial_checklist = [
        ("Raw Factory Load Dataset", "archive/legacy_industrial/data/factory_load/lahore_industrial_load_hourly.csv"),
        ("Master Parquet (with factory_load_kw)", "data/processed/master_ems_timeseries.parquet"),
        ("Master CSV (with diesel & MDI columns)", "data/processed/master_ems_timeseries.csv"),
        ("Argon Audit Pack Master Timeseries", "data/argon_audit_pack/master_ems_timeseries.csv"),
        ("LESCO B3 Industrial Tariff Schedule", "data/processed/tariffs/lesco_tariff_schedule.json"),
        ("Factory Load ML Model (.joblib)", "models/factory_load_lightgbm.joblib"),
        ("Outage Classifier ML Model (.joblib)", "models/outage_classifier.joblib"),
        ("Solar PV Forecaster ML Model (.joblib)", "models/solar_pv_lightgbm.joblib"),
        ("Residential Forecaster ML Model (.joblib)", "models/residential_load_lightgbm.joblib"),
        ("Factory Load EDA Notebook (.ipynb)", "archive/legacy_industrial/notebooks/01_industrial_load_eda.ipynb"),
        ("Industrial Load & MDI Notebook (.ipynb)", "archive/legacy_industrial/notebooks/01_industrial_load_and_mdi_eda.ipynb"),
        ("Factory Load Feature Pipeline (src)", "src/forecast/train_factory_load.py"),
        ("Legacy Factory Load Pipeline", "archive/legacy_industrial/src/data_engineering/build_factory_load.py"),
        ("Legacy Factory Forecaster Script", "archive/legacy_industrial/src/forecast/train_factory_load.py"),
        ("Industrial EDA Test Suite", "archive/legacy_industrial/tests/test_eda_notebook.py"),
        ("Industrial MILP Optimizer Formulation", "src/optimizer/milp_solver.py"),
        ("Industrial Tariff Engine", "src/optimizer/tariff_engine.py"),
        ("Industrial Feature Store Engine", "src/data_engineering/feature_store.py"),
        ("Industrial Master Slide Deck (.pptx)", "docs/SolarSense_Industrial_EMS.pptx"),
        ("Sprint Plan & Industrial Architecture (.docx)", "docs/WEEK_4_5_SPRINT_PLAN_AND_AUDIT.docx"),
        ("MDI Peak Spike Visual Analysis (.png)", "docs/samples/load_and_mdi_spikes.png"),
        ("Argon Review Prompt Document", "docs/ARGON_AUDIT_PROMPT.md"),
    ]

    all_industrial_passed = True
    for label, rel_file in industrial_checklist:
        present = rel_file in packed_names
        status_str = "[VERIFIED PACKED]" if present else "[MISSING]"
        if not present:
            all_industrial_passed = False
        print(f"  {status_str:<20s} • {label} -> {rel_file}")

    print("-" * 80)
    if all_industrial_passed:
        print("  100% OF INDUSTRIAL MICROGRID ASSETS CONFIRMED PRESENT IN THE AUDIT BUNDLE!")
    else:
        print("  WARNING: Some industrial assets were not packed.")
    print("=" * 80)
    print("\nReady for delivery to Argon for full architecture & data review!")


if __name__ == "__main__":
    build_audit_bundle()
