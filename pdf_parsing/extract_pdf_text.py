#!/usr/bin/env python3
"""
Extract text from PDF files using pdfplumber and save to JSONL.

Each PDF is hashed using SHA256, and the output contains:
- sha256: SHA256 hash of the PDF file
- text: List of strings, one per page
- dateprocessed: ISO 8601 timestamp when the PDF was processed

The JSONL file is treated as append-only. PDFs that are already
processed (based on their SHA256 hash) are skipped.
"""
import argparse
import hashlib
import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Set

import pdfplumber


def calculate_sha256(file_path: str) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def load_processed_ids(jsonl_path: str) -> Set[str]:
    """Load set of already processed PDF IDs from JSONL file."""
    processed = set()
    if os.path.exists(jsonl_path):
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        processed.add(record["sha256"])
                    except (json.JSONDecodeError, KeyError):
                        continue
    return processed


def load_all_records(jsonl_path: str) -> Dict[str, dict]:
    """Load all records from JSONL file, indexed by sha256."""
    records = {}
    if os.path.exists(jsonl_path):
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        records[record["sha256"]] = record
                    except (json.JSONDecodeError, KeyError):
                        continue
    return records


def extract_text_from_pdf(pdf_path: str) -> list[str]:
    """Extract text from PDF, returning a list of strings (one per page)."""
    pages_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages_text.append(text)
    return pages_text


def format_time(seconds: float) -> str:
    """Format time in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def process_directory(pdf_dir: str, output_jsonl: str) -> None:
    """Process all PDFs in directory and append results to JSONL."""
    pdf_dir_path = Path(pdf_dir)

    if not pdf_dir_path.exists():
        print(f"Error: Directory '{pdf_dir}' does not exist", file=sys.stderr)
        sys.exit(1)

    if not pdf_dir_path.is_dir():
        print(f"Error: '{pdf_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    # Load already processed IDs
    processed_ids = load_processed_ids(output_jsonl)
    print(f"Found {len(processed_ids)} already processed PDFs")

    # Find all PDF files
    pdf_files = list(pdf_dir_path.glob("*.pdf")) + list(pdf_dir_path.glob("*.PDF"))
    print(f"Found {len(pdf_files)} PDF files in directory")

    # Count how many need processing
    to_process_count = len(pdf_files) - len(processed_ids)
    print(f"Estimated {to_process_count} PDFs to process\n")

    # Create output directory if it doesn't exist
    output_path = Path(output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Open output file in append mode
    with open(output_jsonl, "a", encoding="utf-8") as out_f:
        processed_count = 0
        skipped_count = 0
        error_count = 0
        start_time = time.time()

        for idx, pdf_path in enumerate(sorted(pdf_files), 1):
            try:
                # Calculate SHA256 hash
                pdf_hash = calculate_sha256(str(pdf_path))

                # Skip if already processed
                if pdf_hash in processed_ids:
                    print(f"[{idx}/{len(pdf_files)}] Skipping (already processed): {pdf_path.name}")
                    skipped_count += 1
                    continue

                # Extract text
                print(f"[{idx}/{len(pdf_files)}] Processing: {pdf_path.name}")
                pages_text = extract_text_from_pdf(str(pdf_path))

                # Create record with timestamp
                record = {
                    "sha256": pdf_hash,
                    "text": pages_text,
                    "dateprocessed": datetime.now().isoformat()
                }

                # Append to JSONL
                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                out_f.flush()  # Ensure it's written immediately

                processed_count += 1

                # Calculate time estimates
                elapsed_time = time.time() - start_time
                avg_time_per_pdf = elapsed_time / processed_count
                remaining = to_process_count - processed_count
                estimated_remaining = avg_time_per_pdf * remaining

                elapsed_str = format_time(elapsed_time)
                remaining_str = format_time(estimated_remaining)

                print(f"  -> Processed {len(pages_text)} pages")
                print(f"  -> Time: {elapsed_str} elapsed, ~{remaining_str} remaining (est.)\n")

            except Exception as e:
                print(f"Error processing {pdf_path.name}: {e}", file=sys.stderr)
                error_count += 1
                continue

    print(f"\nSummary:")
    print(f"  Processed: {processed_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Errors: {error_count}")


def spot_check(pdf_dir: str, output_jsonl: str, num_checks: int) -> None:
    """Spot check existing records by re-extracting and comparing."""
    pdf_dir_path = Path(pdf_dir)

    if not pdf_dir_path.exists():
        print(f"Error: Directory '{pdf_dir}' does not exist", file=sys.stderr)
        sys.exit(1)

    if not pdf_dir_path.is_dir():
        print(f"Error: '{pdf_dir}' is not a directory", file=sys.stderr)
        sys.exit(1)

    # Load all existing records
    print(f"Loading existing records from {output_jsonl}...")
    records = load_all_records(output_jsonl)
    print(f"Loaded {len(records)} existing records")

    if len(records) == 0:
        print("No records to spot check!")
        return

    # Find all PDF files
    pdf_files = list(pdf_dir_path.glob("*.pdf")) + list(pdf_dir_path.glob("*.PDF"))

    # Filter to only PDFs we have records for
    pdf_files_with_records = []
    for pdf_path in pdf_files:
        try:
            pdf_hash = calculate_sha256(str(pdf_path))
            if pdf_hash in records:
                pdf_files_with_records.append((pdf_path, pdf_hash))
        except Exception:
            continue

    if len(pdf_files_with_records) == 0:
        print("No PDFs found that match existing records!")
        return

    # Sample up to num_checks PDFs
    sample_size = min(num_checks, len(pdf_files_with_records))
    sample = random.sample(pdf_files_with_records, sample_size)

    print(f"\nSpot checking {sample_size} PDFs...\n")

    passed = 0
    failed = 0

    for pdf_path, pdf_hash in sample:
        try:
            print(f"Checking: {pdf_path.name}")

            # Re-extract text
            pages_text = extract_text_from_pdf(str(pdf_path))

            # Get existing record
            existing_record = records[pdf_hash]
            existing_text = existing_record["text"]

            # Compare
            if pages_text == existing_text:
                print(f"  ✓ PASS - {len(pages_text)} pages match")
                passed += 1
            else:
                print(f"  ✗ FAIL - Text mismatch!")
                print(f"    Expected {len(existing_text)} pages, got {len(pages_text)} pages")
                if len(pages_text) == len(existing_text):
                    # Same number of pages, check which pages differ
                    for i, (old, new) in enumerate(zip(existing_text, pages_text)):
                        if old != new:
                            print(f"    Page {i+1} differs")
                failed += 1

        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            failed += 1

        print()

    print(f"\nSpot Check Summary:")
    print(f"  Passed: {passed}/{sample_size}")
    print(f"  Failed: {failed}/{sample_size}")

    if failed == 0:
        print("\n✓ All spot checks passed!")
    else:
        print(f"\n✗ {failed} spot check(s) failed")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract text from PDFs and save to JSONL"
    )
    parser.add_argument(
        "--pdf-dir",
        required=True,
        help="Directory containing PDF files to process"
    )
    parser.add_argument(
        "-o", "--output",
        default="pdf_parsing/pdfs_as_text.jsonl",
        help="Output JSONL file (default: pdf_parsing/pdfs_as_text.jsonl)"
    )
    parser.add_argument(
        "--spot-check",
        type=int,
        metavar="N",
        help="Spot check N random PDFs by re-extracting and comparing with existing records"
    )

    args = parser.parse_args()

    if args.spot_check is not None:
        spot_check(args.pdf_dir, args.output, args.spot_check)
    else:
        process_directory(args.pdf_dir, args.output)


if __name__ == "__main__":
    main()
