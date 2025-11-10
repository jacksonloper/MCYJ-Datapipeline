#!/usr/bin/env python3
"""Check that all SHA256 hashes across all parquet files are unique."""

import sys
from pathlib import Path
import pandas as pd


def check_unique_hashes(parquet_dir: Path) -> tuple[bool, dict]:
    """
    Check if all SHA256 hashes across all parquet files are unique.

    Args:
        parquet_dir: Directory containing parquet files

    Returns:
        Tuple of (all_unique: bool, stats: dict)
    """
    parquet_files = sorted(parquet_dir.glob("*.parquet"))

    if not parquet_files:
        print(f"❌ No parquet files found in {parquet_dir}")
        return False, {}

    print(f"Found {len(parquet_files)} parquet file(s):")
    for f in parquet_files:
        print(f"  - {f.name}")
    print()

    # Collect all hashes
    all_hashes = []
    file_hash_counts = {}

    for parquet_file in parquet_files:
        df = pd.read_parquet(parquet_file)

        if 'sha256' not in df.columns:
            print(f"❌ File {parquet_file.name} does not have a 'sha256' column")
            return False, {}

        hashes = df['sha256'].tolist()
        all_hashes.extend(hashes)
        file_hash_counts[parquet_file.name] = len(hashes)
        print(f"  {parquet_file.name}: {len(hashes)} hashes")

    print()
    total_hashes = len(all_hashes)
    unique_hashes = len(set(all_hashes))

    stats = {
        'total_files': len(parquet_files),
        'total_hashes': total_hashes,
        'unique_hashes': unique_hashes,
        'file_hash_counts': file_hash_counts
    }

    print(f"Total hashes across all files: {total_hashes}")
    print(f"Unique hashes: {unique_hashes}")

    if total_hashes == unique_hashes:
        print("✅ All SHA256 hashes are unique!")
        return True, stats
    else:
        duplicates = total_hashes - unique_hashes
        print(f"❌ Found {duplicates} duplicate hash(es)!")

        # Find and report duplicates
        hash_counts = {}
        for h in all_hashes:
            hash_counts[h] = hash_counts.get(h, 0) + 1

        duplicate_hashes = {h: count for h, count in hash_counts.items() if count > 1}
        print(f"\nDuplicate hashes:")
        for hash_val, count in sorted(duplicate_hashes.items()):
            print(f"  {hash_val}: appears {count} times")

        return False, stats


def main():
    """Run the uniqueness check."""
    parquet_dir = Path(__file__).parent / "parquet_files"

    if not parquet_dir.exists():
        print(f"❌ Directory {parquet_dir} does not exist")
        sys.exit(1)

    all_unique, stats = check_unique_hashes(parquet_dir)

    if not all_unique:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
