#!/usr/bin/env python3
"""
Script to download all PDFs listed in a CSV by calling download_michigan_pdf
from `download_pdf.py` for each row.

Expected CSV headers:
generated_filename,agency_name,agency_id,FileExtension,CreatedDate,Title,ContentBodyId,Id,ContentDocumentId

Usage:
python download_all_pdfs.py --csv /path/to/file.csv --output-dir ./pdfs
"""
import csv
import os
import argparse
import time
from typing import Optional

# Import functions from download_pdf.py
try:
    from download_pdf import download_michigan_pdf
except Exception as e:
    raise SystemExit(f"Failed to import download_michigan_pdf from download_pdf.py: {e}")


def process_csv(csv_path: str, output_dir: str, skip_existing: bool = True, limit: Optional[int] = None, sleep_seconds: float = 0.0):
    """Read CSV and call download_michigan_pdf for each row.

    Parameters:
        csv_path: path to input CSV
        output_dir: directory where PDFs will be saved
        skip_existing: if True and generated_filename present, skip if file exists
        limit: optional max number of rows to process
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    os.makedirs(output_dir, exist_ok=True)

    processed = 0
    failed = 0

    with open(csv_path, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if limit is not None and processed >= limit:
                break

            # Extract required fields from the CSV header
            gen_filename = (row.get('generated_filename') or '').strip()
            agency_name = (row.get('agency_name') or '').strip()
            agency_id = (row.get('agency_id') or '').strip()
            file_ext = (row.get('FileExtension') or '').strip()
            created_date = (row.get('CreatedDate') or '').strip()
            title = (row.get('Title') or '').strip()
            content_body_id = (row.get('ContentBodyId') or '').strip()
            id_field = (row.get('Id') or '').strip()
            content_document_id = (row.get('ContentDocumentId') or '').strip()

            # The download function needs ContentDocumentId (document_id);
            # fill other args from CSV.
            if not content_document_id:
                print(f"Skipping row with missing ContentDocumentId: {row}")
                failed += 1
                continue

            # If a generated_filename is provided, optionally skip download when file exists
            if gen_filename:
                target_path = os.path.join(output_dir, gen_filename)
                if skip_existing and os.path.exists(target_path):
                    print(f"Skipping existing file: {target_path}")
                    processed += 1
                    continue

            try:
                print(f"Downloading document {content_document_id} (agency: {agency_name}, title: {title})")
                out_path = download_michigan_pdf(
                    document_id=content_document_id,
                    document_agency=agency_name if agency_name else None,
                    document_name=title if title else None,
                    document_date=created_date if created_date else None,
                    output_dir=output_dir
                )

                if out_path:
                    print(f"Saved to: {out_path}")
                else:
                    print(f"Download returned None for {content_document_id}")
                    failed += 1

            except Exception as e:
                print(f"Error downloading {content_document_id}: {e}")
                failed += 1

            processed += 1
            # Sleep between downloads if requested
            if sleep_seconds and sleep_seconds > 0:
                try:
                    print(f"Sleeping for {sleep_seconds} seconds...")
                    time.sleep(sleep_seconds)
                except KeyboardInterrupt:
                    print("Sleep interrupted by user.")
                    break

    print(f"Done. Processed: {processed}. Failures: {failed}.")
    return processed, failed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download PDFs listed in a CSV using download_michigan_pdf from download_pdf.py')
    parser.add_argument('--csv', required=True, help='Path to input CSV file')
    parser.add_argument('--output-dir', required=True, help='Directory to save downloaded PDFs')
    parser.add_argument('--no-skip', dest='skip_existing', action='store_false', help='Do not skip when generated_filename exists')
    parser.add_argument('--limit', type=int, default=None, help='Optional max number of rows to process')
    parser.add_argument('--sleep', dest='sleep_seconds', type=float, default=0.0, help='Seconds to sleep between downloads (float allowed)')

    args = parser.parse_args()

    process_csv(args.csv, args.output_dir, skip_existing=args.skip_existing, limit=args.limit, sleep_seconds=args.sleep_seconds)
