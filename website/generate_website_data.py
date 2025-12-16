#!/usr/bin/env python3
"""
Generate JSON data files for the website from CSV files.

This script processes the document info CSV to create
JSON files that can be consumed by the web frontend.
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path


def load_document_info_csv(csv_path):
    """Load document info CSV and group by agency."""
    documents_by_agency = defaultdict(list)
    agency_names = {}  # Map agency_id to agency_name
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            agency_id = row.get('agency_id', '').strip()
            agency_name = row.get('agency_name', '').strip()
            
            if not agency_id:
                continue
            
            # Track agency name for this ID
            if agency_id and agency_name:
                agency_names[agency_id] = agency_name
            
            document = {
                'date': row.get('date', ''),
                'agency_name': agency_name,
                'document_title': row.get('document_title', ''),
                'is_special_investigation': row.get('is_special_investigation', 'False').lower() in ('true', '1', 'yes'),
                'sha256': row.get('sha256', ''),
                'date_processed': row.get('date_processed', '')
            }
            documents_by_agency[agency_id].append(document)
    
    return documents_by_agency, agency_names


def generate_json_files(document_csv, output_dir):
    """Generate JSON files for the website."""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Load document info data
    print("Loading document info data...")
    documents_by_agency, agency_names = load_document_info_csv(document_csv)
    
    # Build agency list from document data
    print("Building agency list from documents...")
    agency_data = []
    
    for agency_id, documents in documents_by_agency.items():
        # Get agency name from the documents data
        agency_name = agency_names.get(agency_id, 'Unknown Agency')
        
        agency_info = {
            'agencyId': agency_id,
            'AgencyName': agency_name,
            'documents': documents,
            'total_reports': len(documents)
        }
        
        agency_data.append(agency_info)
    
    # Sort by agency name
    agency_data.sort(key=lambda x: x.get('AgencyName', ''))
    
    # Write full data file
    output_file = os.path.join(output_dir, 'agencies_data.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(agency_data, f, indent=2)
    print(f"Wrote full data to {output_file}")
    
    # Write summary file (without full documents list for faster loading)
    summary_data = []
    for agency in agency_data:
        summary = {
            'agencyId': agency['agencyId'],
            'AgencyName': agency['AgencyName'],
            'total_reports': agency['total_reports']
        }
        summary_data.append(summary)
    
    summary_file = os.path.join(output_dir, 'agencies_summary.json')
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2)
    print(f"Wrote summary to {summary_file}")
    
    print(f"\nProcessed {len(agency_data)} agencies")
    print(f"Total reports: {sum(a['total_reports'] for a in agency_data)}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate JSON data files for the website from document info CSV only"
    )
    parser.add_argument(
        "--document-csv",
        required=True,
        help="Path to document info CSV file"
    )
    parser.add_argument(
        "--output-dir",
        default="public/data",
        help="Output directory for JSON files"
    )
    
    args = parser.parse_args()
    
    # Validate input files
    if not os.path.exists(args.document_csv):
        print(f"Error: Document info CSV not found: {args.document_csv}")
        sys.exit(1)
    
    generate_json_files(
        args.document_csv,
        args.output_dir
    )


if __name__ == "__main__":
    main()
