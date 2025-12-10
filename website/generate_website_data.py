#!/usr/bin/env python3
"""
Generate JSON data files for the website from CSV files.

This script processes the violations CSV and agency CSV to create
JSON files that can be consumed by the web frontend.
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path


def load_violations_csv(csv_path):
    """Load violations CSV and group by agency."""
    violations_by_agency = defaultdict(list)
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            agency_id = row.get('agency_id', '').strip()
            if not agency_id:
                continue
                
            violation = {
                'date': row.get('date', ''),
                'agency_name': row.get('agency_name', ''),
                'violations_list': row.get('violations_list', ''),
                'num_violations': int(row.get('num_violations', 0)),
                'sha256': row.get('sha256', ''),
                'date_processed': row.get('date_processed', '')
            }
            violations_by_agency[agency_id].append(violation)
    
    return violations_by_agency


def load_agency_csv(csv_path):
    """Load agency CSV."""
    agencies = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            agencies.append({
                'agencyId': row.get('agencyId', ''),
                'AgencyName': row.get('AgencyName', ''),
                'AgencyType': row.get('AgencyType', ''),
                'Address': row.get('Address', ''),
                'City': row.get('City', ''),
                'County': row.get('County', ''),
                'ZipCode': row.get('ZipCode', ''),
                'Phone': row.get('Phone', ''),
                'LicenseNumber': row.get('LicenseNumber', ''),
                'LicenseStatus': row.get('LicenseStatus', ''),
                'LicenseEffectiveDate': row.get('LicenseEffectiveDate', ''),
                'LicenseExpirationDate': row.get('LicenseExpirationDate', ''),
                'LicenseeGroupOrganizationName': row.get('LicenseeGroupOrganizationName', '')
            })
    
    return agencies


def load_documents_csv(csv_path):
    """Load documents CSV and group by agency."""
    documents_by_agency = defaultdict(list)
    
    if not os.path.exists(csv_path):
        print(f"Warning: Documents CSV not found at {csv_path}, skipping documents")
        return documents_by_agency
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            agency_name = row.get('agency_name', '').strip()
            agency_id = row.get('agency_id', '').strip()
            
            if not agency_id:
                continue
                
            document = {
                'agency_name': agency_name,
                'FileExtension': row.get('FileExtension', ''),
                'CreatedDate': row.get('CreatedDate', ''),
                'Title': row.get('Title', ''),
                'ContentBodyId': row.get('ContentBodyId', ''),
                'Id': row.get('Id', ''),
                'ContentDocumentId': row.get('ContentDocumentId', '')
            }
            documents_by_agency[agency_id].append(document)
    
    return documents_by_agency


def generate_json_files(violations_csv, agency_csv, documents_csv, output_dir):
    """Generate JSON files for the website."""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Load data
    print("Loading violations data...")
    violations_by_agency = load_violations_csv(violations_csv)
    
    print("Loading agency data...")
    agencies = load_agency_csv(agency_csv)
    
    print("Loading documents data...")
    documents_by_agency = load_documents_csv(documents_csv)
    
    # Combine data
    print("Combining data...")
    agency_data = []
    
    for agency in agencies:
        agency_id = agency['agencyId']
        
        # Get violations for this agency
        violations = violations_by_agency.get(agency_id, [])
        
        # Get documents for this agency
        documents = documents_by_agency.get(agency_id, [])
        
        # Count violations
        total_violations = sum(v['num_violations'] for v in violations)
        
        agency_info = {
            **agency,
            'violations': violations,
            'documents': documents,
            'total_violations': total_violations,
            'total_documents': len(documents),
            'total_reports': len(violations)
        }
        
        agency_data.append(agency_info)
    
    # Sort by agency name
    agency_data.sort(key=lambda x: x.get('AgencyName', ''))
    
    # Write full data file
    output_file = os.path.join(output_dir, 'agencies_data.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(agency_data, f, indent=2)
    print(f"Wrote full data to {output_file}")
    
    # Write summary file (without full violations and documents lists for faster loading)
    summary_data = []
    for agency in agency_data:
        summary = {
            'agencyId': agency['agencyId'],
            'AgencyName': agency['AgencyName'],
            'AgencyType': agency['AgencyType'],
            'City': agency['City'],
            'County': agency['County'],
            'LicenseStatus': agency['LicenseStatus'],
            'total_violations': agency['total_violations'],
            'total_documents': agency['total_documents'],
            'total_reports': agency['total_reports']
        }
        summary_data.append(summary)
    
    summary_file = os.path.join(output_dir, 'agencies_summary.json')
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2)
    print(f"Wrote summary to {summary_file}")
    
    print(f"\nProcessed {len(agency_data)} agencies")
    print(f"Total violations: {sum(a['total_violations'] for a in agency_data)}")
    print(f"Total documents: {sum(a['total_documents'] for a in agency_data)}")
    print(f"Total reports: {sum(a['total_reports'] for a in agency_data)}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate JSON data files for the website"
    )
    parser.add_argument(
        "--violations-csv",
        required=True,
        help="Path to violations CSV file"
    )
    parser.add_argument(
        "--agency-csv",
        required=True,
        help="Path to agency info CSV file"
    )
    parser.add_argument(
        "--documents-csv",
        default="",
        help="Path to combined documents CSV file (optional)"
    )
    parser.add_argument(
        "--output-dir",
        default="public/data",
        help="Output directory for JSON files"
    )
    
    args = parser.parse_args()
    
    # Validate input files
    if not os.path.exists(args.violations_csv):
        print(f"Error: Violations CSV not found: {args.violations_csv}")
        sys.exit(1)
    
    if not os.path.exists(args.agency_csv):
        print(f"Error: Agency CSV not found: {args.agency_csv}")
        sys.exit(1)
    
    generate_json_files(
        args.violations_csv,
        args.agency_csv,
        args.documents_csv,
        args.output_dir
    )


if __name__ == "__main__":
    main()
