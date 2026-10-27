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


def should_include_file(file_path: Path) -> bool:
    """Evaluate whether a given file path meets inclusion criteria."""
    if not file_path.is_file():
        return False

    # Check for excluded directory parts
    for part in file_path.relative_to(REPO_ROOT).parts[:-1]:
        if part in EXCLUDE_DIRS:
            return False

    # Check filename rules
    name = file_path.name
    if name.startswith(".~lock") or name.startswith(".git"):
        return False
    if name in EXCLUDE_FILE_PATTERNS or name.startswith(".env"):
        return False
    if name.endswith(".zip") or name.endswith(".tar.gz") or name.endswith(".pyc"):
        return False

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
    print("\nReady for delivery to Argon for full architecture & data review!")


if __name__ == "__main__":
    build_audit_bundle()
