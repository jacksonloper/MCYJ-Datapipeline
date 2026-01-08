#!/usr/bin/env python3
"""
Generate JSON data files for the violations analytics page.

This script processes document info, facility information, and violation levels
to create aggregated violation statistics by:
- Date (year/month)
- Facility type
- Age group (normalized)
"""

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple


def normalize_age_group(age_str: str) -> Optional[str]:
    """
    Normalize inconsistent age group strings to a standard format.
    
    Examples of inputs:
    - "11-17", "11 - 17", "11- 17", "11 -17"
    - "10 - 17", "10-17"
    - "N/A", "", "Contract Only"
    
    Returns normalized format like "11-17" or None for invalid/unknown.
    """
    if not age_str or age_str.strip().upper() in ('N/A', 'CONTRACT ONLY', ''):
        return None
    
    # Remove extra spaces and normalize
    age_str = age_str.strip()
    
    # Handle range patterns like "11-17", "11 - 17", "8- 17", "10 - 17"
    match = re.match(r'(\d+)\s*-\s*(\d+)', age_str)
    if match:
        min_age = int(match.group(1))
        max_age = int(match.group(2))
        return f"{min_age}-{max_age}"
    
    # If it's just a single number (rare case)
    if age_str.isdigit():
        return age_str
    
    return None


def parse_date(date_str: str) -> Optional[Tuple[int, int]]:
    """
    Parse a date string and return (year, month) tuple.
    
    Handles various formats like:
    - "04/28/2022"
    - "February 21, 2023"
    - "5/14/2021"
    - "NA 01/19-02/18/2022"
    - "Special Investigation Intake Date: March 3, 2025"
    """
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    # Try various date formats
    formats = [
        '%m/%d/%Y',      # 04/28/2022
        '%B %d, %Y',     # February 21, 2023
        '%B %d,%Y',      # February 21,2023
        '%Y-%m-%d',      # 2022-04-28
    ]
    
    # First, try to extract a date from complex strings
    # Look for patterns like "March 3, 2025" or "04/28/2022"
    
    # Pattern for "Month Day, Year"
    month_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s*(\d{4})'
    match = re.search(month_pattern, date_str)
    if match:
        month_name, day, year = match.groups()
        try:
            dt = datetime.strptime(f"{month_name} {day}, {year}", '%B %d, %Y')
            return (dt.year, dt.month)
        except ValueError:
            pass
    
    # Pattern for MM/DD/YYYY
    mm_dd_yyyy = r'(\d{1,2})/(\d{1,2})/(\d{4})'
    match = re.search(mm_dd_yyyy, date_str)
    if match:
        month, day, year = match.groups()
        try:
            return (int(year), int(month))
        except ValueError:
            pass
    
    # Try standard parsing
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return (dt.year, dt.month)
        except ValueError:
            continue
    
    return None


def load_facility_annotations(csv_path: str) -> Dict[str, Dict]:
    """Load facility annotations (MCYJ_annotations.csv) and create lookup by LicenseNumber."""
    annotations = {}
    
    if not os.path.exists(csv_path):
        print(f"Warning: Facility annotations file not found: {csv_path}")
        return annotations
    
    def get_field(row: Dict, name: str) -> str:
        """Get field from row, handling columns with trailing spaces in names."""
        # Try exact match first, then with trailing space
        return row.get(name, row.get(name + ' ', '')).strip()
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            license_number = get_field(row, 'LicenseNumber')
            if not license_number:
                continue
            
            annotations[license_number] = {
                'facility_name': get_field(row, 'Facility Name'),
                'county': get_field(row, 'County'),
                'region': get_field(row, 'Region'),
                'agency_type': get_field(row, 'Agency Type'),
                'capacity': get_field(row, 'Capacity'),
                'genders_served': get_field(row, 'Genders Served'),
                'ages_served': get_field(row, 'Ages Served'),
                'ages_served_normalized': normalize_age_group(get_field(row, 'Ages Served')),
                'shelter_services': get_field(row, 'Shelter / Respite / Crisis Stabilization Services'),
                'specialization': get_field(row, 'Specialization (substance use, CSC, acute)')
            }
    
    print(f"Loaded {len(annotations)} facility annotations")
    return annotations


def load_facility_info(csv_path: str) -> Dict[str, Dict]:
    """Load facility information and create lookup by LicenseNumber.
    
    Note: The documents and violation_levels CSVs use LicenseNumber as the agency_id,
    not the Salesforce-style agencyId. So we key this lookup by LicenseNumber.
    """
    facilities = {}
    
    if not os.path.exists(csv_path):
        print(f"Warning: Facility info file not found: {csv_path}")
        return facilities
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            license_number = row.get('LicenseNumber', '').strip()
            if not license_number:
                continue
            
            # Key by LicenseNumber since that's what document_info and violation_levels use
            facilities[license_number] = {
                'agency_id': row.get('agencyId', ''),
                'license_number': license_number,
                'agency_name': row.get('AgencyName', ''),
                'agency_type': row.get('AgencyType', ''),
                'county': row.get('County', ''),
                'city': row.get('City', '')
            }
    
    print(f"Loaded {len(facilities)} facility records")
    return facilities


def load_violation_levels(csv_path: str) -> Dict[str, Dict]:
    """Load SIR violation levels and create lookup by SHA256."""
    levels = {}
    
    if not os.path.exists(csv_path):
        print(f"Warning: Violation levels file not found: {csv_path}")
        return levels
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sha256 = row.get('sha256', '').strip()
            if not sha256:
                continue
            
            levels[sha256] = {
                'agency_id': row.get('agency_id', ''),
                'agency_name': row.get('agency_name', ''),
                'date': row.get('date', ''),
                'level': row.get('level', ''),
                'justification': row.get('justification', ''),
                'keywords': row.get('keywords', '')
            }
    
    print(f"Loaded {len(levels)} violation level records")
    return levels


def load_document_info(csv_path: str) -> List[Dict]:
    """Load document info and return list of SIR documents."""
    documents = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Only include Special Investigation Reports
            is_sir = row.get('is_special_investigation', 'False').lower() in ('true', '1', 'yes')
            if not is_sir:
                continue
            
            documents.append({
                'agency_id': row.get('agency_id', '').strip(),
                'date': row.get('date', ''),
                'agency_name': row.get('agency_name', ''),
                'document_title': row.get('document_title', ''),
                'sha256': row.get('sha256', ''),
                'date_processed': row.get('date_processed', '')
            })
    
    print(f"Loaded {len(documents)} SIR documents")
    return documents


def categorize_age_group(normalized_age: Optional[str]) -> str:
    """
    Categorize normalized age ranges into broader groups for visualization.
    
    Categories:
    - "Young Children (≤10)": facilities serving only children 10 and under
    - "Adolescents (11+)": facilities serving only children 11 and older
    - "Mixed Ages": facilities serving both younger children and adolescents
    - "Unknown": no age information available
    """
    if not normalized_age:
        return "Unknown"
    
    # Parse the range
    match = re.match(r'(\d+)-(\d+)', normalized_age)
    if not match:
        return "Unknown"
    
    min_age = int(match.group(1))
    max_age = int(match.group(2))
    
    # Categorize based on age range into broad groups
    # These are simplified categories for visualization purposes
    if max_age <= 10:
        return "Young Children (≤10)"
    elif min_age >= 11:
        return "Adolescents (11+)"
    elif min_age <= 10 and max_age >= 11:
        return "Mixed Ages"
    else:
        return "Other"


def simplify_facility_type(agency_type: str) -> str:
    """Simplify facility types for cleaner visualization."""
    if not agency_type:
        return "Unknown"
    
    agency_type = agency_type.strip()
    
    # Map detailed types to simpler categories
    if 'Child Placing Agency' in agency_type:
        if 'Private' in agency_type:
            return "Child Placing Agency (Private)"
        elif 'MDHHS' in agency_type:
            return "Child Placing Agency (MDHHS)"
        elif 'Government' in agency_type:
            return "Child Placing Agency (Government)"
        return "Child Placing Agency"
    elif 'Child Caring Institution' in agency_type:
        if 'Private' in agency_type:
            return "Child Caring Institution (Private)"
        elif 'MDHHS' in agency_type:
            return "Child Caring Institution (MDHHS)"
        elif 'Government' in agency_type or 'Non-MDHHS' in agency_type:
            return "Child Caring Institution (Government)"
        elif 'Therapeutic' in agency_type:
            return "Therapeutic Group Home"
        return "Child Caring Institution"
    elif 'Court Operated' in agency_type:
        return "Court Operated Facility"
    elif 'Therapeutic' in agency_type.lower():
        return "Therapeutic Group Home"
    
    return agency_type


def generate_violations_data(
    document_csv: str,
    facility_info_csv: str,
    facility_annotations_csv: str,
    violation_levels_csv: str,
    output_dir: str
):
    """Generate violations analytics data."""
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Load all data
    documents = load_document_info(document_csv)
    facilities = load_facility_info(facility_info_csv)
    annotations = load_facility_annotations(facility_annotations_csv)
    violation_levels = load_violation_levels(violation_levels_csv)
    
    # Aggregation containers
    violations_by_date = defaultdict(lambda: {'total': 0, 'low': 0, 'moderate': 0, 'severe': 0})
    violations_by_facility_type = defaultdict(lambda: {'total': 0, 'low': 0, 'moderate': 0, 'severe': 0})
    violations_by_age_group = defaultdict(lambda: {'total': 0, 'low': 0, 'moderate': 0, 'severe': 0})
    violations_by_year = defaultdict(lambda: {'total': 0, 'low': 0, 'moderate': 0, 'severe': 0})
    
    # Per-facility age data for granular visualization
    # Key: license_number, Value: {facility_name, min_age, max_age, total, low, moderate, severe}
    violations_by_facility_age = defaultdict(lambda: {
        'facility_name': '',
        'min_age': None,
        'max_age': None,
        'total': 0,
        'low': 0,
        'moderate': 0,
        'severe': 0
    })
    
    # Track unique violations (some documents may be duplicated)
    processed_sha256 = set()
    
    for doc in documents:
        sha256 = doc['sha256']
        
        # Skip if already processed
        if sha256 in processed_sha256:
            continue
        processed_sha256.add(sha256)
        
        agency_id = doc['agency_id']
        
        # Get violation level info
        vl_info = violation_levels.get(sha256, {})
        level = vl_info.get('level', '').lower()
        
        # Only count documents with substantiated violations (have a level)
        if not level or level not in ('low', 'moderate', 'severe'):
            continue
        
        # Parse date
        date_str = doc['date'] or vl_info.get('date', '')
        parsed_date = parse_date(date_str)
        
        # Get facility info - agency_id from documents is actually the LicenseNumber
        license_number = agency_id  # agency_id in document_info is the LicenseNumber
        facility = facilities.get(license_number, {})
        
        # Get annotation info
        annotation = annotations.get(license_number, {})
        
        # Determine facility type - prefer annotation, fall back to facility_information
        facility_type = annotation.get('agency_type', '') or facility.get('agency_type', '')
        simplified_type = simplify_facility_type(facility_type)
        
        # Determine age group
        ages_normalized = annotation.get('ages_served_normalized')
        age_category = categorize_age_group(ages_normalized)
        
        # Aggregate by date (month)
        if parsed_date:
            year, month = parsed_date
            date_key = f"{year}-{month:02d}"
            violations_by_date[date_key]['total'] += 1
            violations_by_date[date_key][level] += 1
            
            # Also aggregate by year
            violations_by_year[str(year)]['total'] += 1
            violations_by_year[str(year)][level] += 1
        
        # Aggregate by facility type
        violations_by_facility_type[simplified_type]['total'] += 1
        violations_by_facility_type[simplified_type][level] += 1
        
        # Aggregate by age group
        violations_by_age_group[age_category]['total'] += 1
        violations_by_age_group[age_category][level] += 1
        
        # Aggregate by facility with age range for granular visualization
        if ages_normalized:
            match = re.match(r'(\d+)-(\d+)', ages_normalized)
            if match:
                min_age = int(match.group(1))
                max_age = int(match.group(2))
                facility_name = annotation.get('facility_name', '') or facility.get('agency_name', '') or license_number
                
                fac_data = violations_by_facility_age[license_number]
                fac_data['facility_name'] = facility_name
                fac_data['min_age'] = min_age
                fac_data['max_age'] = max_age
                fac_data['total'] += 1
                fac_data[level] += 1
    
    # Convert to sorted lists for JSON output
    def dict_to_sorted_list(d: dict, key_name: str = 'key') -> list:
        """Convert defaultdict to sorted list of dicts."""
        result = []
        for key, counts in sorted(d.items()):
            entry = {key_name: key}
            entry.update(counts)
            result.append(entry)
        return result
    
    # Convert facility age data to sorted list (sorted by min_age, then by total violations)
    def facility_age_to_list(d: dict) -> list:
        """Convert facility age data to list sorted by starting age."""
        result = []
        for license_num, data in d.items():
            if data['min_age'] is not None and data['max_age'] is not None:
                entry = {
                    'license_number': license_num,
                    'facility_name': data['facility_name'],
                    'min_age': data['min_age'],
                    'max_age': data['max_age'],
                    'total': data['total'],
                    'low': data['low'],
                    'moderate': data['moderate'],
                    'severe': data['severe']
                }
                result.append(entry)
        # Sort by min_age, then by max_age
        result.sort(key=lambda x: (x['min_age'], x['max_age']))
        return result
    
    # Prepare output data
    output_data = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_documents_processed': len(processed_sha256),
            'total_violations_with_level': sum(v['total'] for v in violations_by_date.values())
        },
        'by_month': dict_to_sorted_list(violations_by_date, 'month'),
        'by_year': dict_to_sorted_list(violations_by_year, 'year'),
        'by_facility_type': dict_to_sorted_list(violations_by_facility_type, 'facility_type'),
        'by_age_group': dict_to_sorted_list(violations_by_age_group, 'age_group'),
        'by_facility_age': facility_age_to_list(violations_by_facility_age)
    }
    
    # Write output
    output_file = os.path.join(output_dir, 'violations_data.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nWrote violations data to {output_file}")
    print(f"Total violations with severity level: {output_data['metadata']['total_violations_with_level']}")
    print(f"Date range: {output_data['by_month'][0]['month'] if output_data['by_month'] else 'N/A'} to {output_data['by_month'][-1]['month'] if output_data['by_month'] else 'N/A'}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate violations analytics data for the website"
    )
    parser.add_argument(
        "--document-csv",
        required=True,
        help="Path to document info CSV file"
    )
    parser.add_argument(
        "--facility-info-csv",
        required=True,
        help="Path to facility information CSV file"
    )
    parser.add_argument(
        "--facility-annotations-csv",
        required=True,
        help="Path to facility annotations CSV file (MCYJ_annotations.csv)"
    )
    parser.add_argument(
        "--violation-levels-csv",
        required=True,
        help="Path to SIR violation levels CSV file"
    )
    parser.add_argument(
        "--output-dir",
        default="public/data",
        help="Output directory for JSON files"
    )
    
    args = parser.parse_args()
    
    # Validate input files
    for csv_path, name in [
        (args.document_csv, 'Document info'),
        (args.facility_info_csv, 'Facility info'),
        (args.violation_levels_csv, 'Violation levels')
    ]:
        if not os.path.exists(csv_path):
            print(f"Error: {name} CSV not found: {csv_path}")
            sys.exit(1)
    
    generate_violations_data(
        args.document_csv,
        args.facility_info_csv,
        args.facility_annotations_csv,
        args.violation_levels_csv,
        args.output_dir
    )


if __name__ == "__main__":
    main()
