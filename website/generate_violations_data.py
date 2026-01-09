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
            license_status = row.get('LicenseStatus', '').strip()
            facilities[license_number] = {
                'agency_id': row.get('agencyId', ''),
                'license_number': license_number,
                'agency_name': row.get('AgencyName', ''),
                'agency_type': row.get('AgencyType', ''),
                'county': row.get('County', ''),
                'city': row.get('City', ''),
                'license_status': license_status,
                'license_effective_date': row.get('LicenseEffectiveDate', ''),
                'license_expiration_date': row.get('LicenseExpirationDate', ''),
            }
    
    print(f"Loaded {len(facilities)} facility records")
    return facilities


def is_active_license(license_status: str) -> bool:
    """Check if a license status indicates an active license."""
    # Active statuses in the Michigan system
    active_statuses = {'Regular', 'Original', 'Inspected', '1st Provisional', '2nd Provisional'}
    return license_status in active_statuses


def get_years_active_bin(years_active: Optional[float]) -> str:
    """Categorize years active into bins for visualization."""
    if years_active is None:
        return "Unknown"
    
    if years_active < 1:
        return "<1 year"
    elif years_active < 2:
        return "1-2 years"
    elif years_active < 3:
        return "2-3 years"
    elif years_active < 5:
        return "3-5 years"
    elif years_active < 10:
        return "5-10 years"
    else:
        return "10+ years"


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


def load_document_info(csv_path: str) -> Tuple[List[Dict], Dict[str, str]]:
    """Load document info and return list of SIR documents and earliest doc dates per facility.
    
    Returns:
        Tuple of (list of SIR documents, dict mapping license_number to earliest_doc_date)
    """
    sir_documents = []
    earliest_doc_by_facility = {}  # license_number -> earliest date string (for years active calculation)
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            agency_id = row.get('agency_id', '').strip()
            date_str = row.get('date', '')
            
            # Track earliest document date for each facility
            if agency_id and date_str:
                parsed = parse_date(date_str)
                if parsed:
                    year, month = parsed
                    date_key = f"{year}-{month:02d}"
                    
                    if agency_id not in earliest_doc_by_facility:
                        earliest_doc_by_facility[agency_id] = date_key
                    elif date_key < earliest_doc_by_facility[agency_id]:
                        earliest_doc_by_facility[agency_id] = date_key
            
            # Only include Special Investigation Reports in the main list
            is_sir = row.get('is_special_investigation', 'False').lower() in ('true', '1', 'yes')
            if not is_sir:
                continue
            
            sir_documents.append({
                'agency_id': agency_id,
                'date': date_str,
                'agency_name': row.get('agency_name', ''),
                'document_title': row.get('document_title', ''),
                'sha256': row.get('sha256', ''),
                'date_processed': row.get('date_processed', '')
            })
    
    print(f"Loaded {len(sir_documents)} SIR documents")
    print(f"Found earliest document dates for {len(earliest_doc_by_facility)} facilities")
    return sir_documents, earliest_doc_by_facility


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


def normalize_region(region: str) -> str:
    """Normalize region names for consistent display."""
    if not region or region.strip().upper() in ('N/A', ''):
        return "Unknown"
    
    region = region.strip()
    
    # Map to standard region names
    region_map = {
        'NE': 'NE',
        'SE': 'SE',
        'SW': 'SW',
        'N': 'N',
        'S': 'S',
        'E': 'E',
        'W': 'W',
        'Mid': 'Mid',
        'Ingham': 'Mid',  # Ingham is in the mid region
    }
    
    return region_map.get(region, region)


def normalize_gender(gender: str) -> str:
    """Normalize gender served values for consistent display."""
    if not gender or gender.strip().upper() in ('N/A', '', 'CONTRACT ONLY'):
        return "Unknown"
    
    gender = gender.strip().lower()
    
    # Normalize variations
    if gender in ('male', 'males'):
        return "Male"
    elif gender in ('female', 'females') or 'girl' in gender:
        return "Female"
    elif gender in ('co-ed', 'coed'):
        return "Co-ed"
    else:
        return "Unknown"


def parse_capacity(capacity_str: str) -> Optional[int]:
    """Parse capacity string to integer, returning None for invalid/unknown values."""
    if not capacity_str:
        return None
    
    capacity_str = capacity_str.strip()
    
    # Handle N/A and other non-numeric values
    if capacity_str.upper() in ('N/A', '', 'PRIVATE', 'CONTRACT ONLY'):
        return None
    
    # Try to parse as integer
    try:
        capacity = int(capacity_str)
        return capacity if capacity > 0 else None
    except ValueError:
        return None


def get_capacity_bin(capacity: Optional[int]) -> str:
    """Categorize capacity into histogram bins."""
    if capacity is None:
        return "Unknown"
    
    if capacity <= 10:
        return "1-10"
    elif capacity <= 20:
        return "11-20"
    elif capacity <= 30:
        return "21-30"
    elif capacity <= 50:
        return "31-50"
    elif capacity <= 100:
        return "51-100"
    else:
        return "100+"


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


def calculate_years_active(earliest_doc_date: Optional[str], reference_year: int = 2025) -> Optional[float]:
    """Calculate years active from earliest document date to reference year.
    
    Args:
        earliest_doc_date: Date string in YYYY-MM format
        reference_year: Year to calculate up to (default 2025, current year)
    
    Returns:
        Number of years active, or None if date is invalid
    """
    if not earliest_doc_date:
        return None
    
    try:
        parts = earliest_doc_date.split('-')
        if len(parts) >= 2:
            start_year = int(parts[0])
            start_month = int(parts[1])
            # Calculate years as decimal (roughly)
            years = (reference_year - start_year) + (12 - start_month) / 12.0
            return max(0, years)
    except (ValueError, IndexError):
        pass
    
    return None


def generate_violations_data(
    document_csv: str,
    facility_info_csv: str,
    facility_annotations_csv: str,
    violation_levels_csv: str,
    output_dir: str
):
    """Generate violations analytics data.
    
    FILTERING: Only facilities with currently active licenses are included.
    This ensures comparisons are meaningful - inactive facilities may have 
    stopped operating years ago and should not be compared to currently 
    active facilities.
    
    NORMALIZATION: When "normalize by capacity" is checked, we divide by
    (capacity × years_active) to account for both facility size and how
    long it has been operating. Years active is estimated from the earliest
    document we have for that facility.
    """
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Load all data - documents now returns (sir_documents, earliest_doc_dates)
    documents, earliest_doc_by_facility = load_document_info(document_csv)
    facilities = load_facility_info(facility_info_csv)
    annotations = load_facility_annotations(facility_annotations_csv)
    violation_levels = load_violation_levels(violation_levels_csv)
    
    # Determine which facilities have active licenses
    active_license_numbers = set()
    inactive_count = 0
    for license_number, fac_info in facilities.items():
        if is_active_license(fac_info.get('license_status', '')):
            active_license_numbers.add(license_number)
        else:
            inactive_count += 1
    
    print(f"Found {len(active_license_numbers)} facilities with active licenses, {inactive_count} inactive")
    
    # Aggregation containers - now with capacity_years tracking for normalization
    # capacity_years = sum of (capacity × years_active) for each facility
    violations_by_date = defaultdict(lambda: {'total': 0, 'low': 0, 'moderate': 0, 'severe': 0})
    violations_by_facility_type = defaultdict(lambda: {'total': 0, 'low': 0, 'moderate': 0, 'severe': 0, 'capacity': 0, 'capacity_years': 0.0})
    violations_by_region = defaultdict(lambda: {'total': 0, 'low': 0, 'moderate': 0, 'severe': 0, 'capacity': 0, 'capacity_years': 0.0})
    violations_by_gender = defaultdict(lambda: {'total': 0, 'low': 0, 'moderate': 0, 'severe': 0, 'capacity': 0, 'capacity_years': 0.0})
    violations_by_capacity = defaultdict(lambda: {'total': 0, 'low': 0, 'moderate': 0, 'severe': 0, 'capacity': 0, 'capacity_years': 0.0})
    violations_by_year = defaultdict(lambda: {'total': 0, 'low': 0, 'moderate': 0, 'severe': 0})
    violations_by_years_active = defaultdict(lambda: {'total': 0, 'low': 0, 'moderate': 0, 'severe': 0})
    
    # Track facilities we've seen for each bin (to avoid double-counting capacity)
    facilities_by_type = defaultdict(set)
    facilities_by_region = defaultdict(set)
    facilities_by_gender = defaultdict(set)
    facilities_by_capacity_bin = defaultdict(set)
    facilities_by_years_active_bin = defaultdict(set)
    
    # Per-year data for year range filtering
    # Structure: {year: {grouping_type: {group_key: {counts}}}}
    violations_by_year_grouped = defaultdict(lambda: {
        'facility_type': defaultdict(lambda: {'total': 0, 'low': 0, 'moderate': 0, 'severe': 0, 'capacity': 0, 'capacity_years': 0.0}),
        'region': defaultdict(lambda: {'total': 0, 'low': 0, 'moderate': 0, 'severe': 0, 'capacity': 0, 'capacity_years': 0.0}),
        'gender': defaultdict(lambda: {'total': 0, 'low': 0, 'moderate': 0, 'severe': 0, 'capacity': 0, 'capacity_years': 0.0}),
        'capacity_bin': defaultdict(lambda: {'total': 0, 'low': 0, 'moderate': 0, 'severe': 0, 'capacity': 0, 'capacity_years': 0.0}),
        'years_active_bin': defaultdict(lambda: {'total': 0, 'low': 0, 'moderate': 0, 'severe': 0}),
    })
    
    # Track facilities per year for facility counts
    facilities_per_year = defaultdict(lambda: {
        'facility_type': defaultdict(set),
        'region': defaultdict(set),
        'gender': defaultdict(set),
        'capacity_bin': defaultdict(set),
        'years_active_bin': defaultdict(set),
    })
    
    # Track capacity per year per grouping (to avoid double-counting)
    capacity_tracked_per_year = defaultdict(lambda: {
        'facility_type': defaultdict(set),
        'region': defaultdict(set),
        'gender': defaultdict(set),
        'capacity_bin': defaultdict(set),
    })
    
    # Track unique violations (some documents may be duplicated)
    processed_sha256 = set()
    
    # Track skipped violations for reporting
    skipped_inactive = 0
    skipped_unknown_facility = 0
    
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
        
        # Get facility info - agency_id from documents is actually the LicenseNumber
        license_number = agency_id  # agency_id in document_info is the LicenseNumber
        facility = facilities.get(license_number, {})
        
        # Filter: Only include facilities with active licenses
        # Facilities not in our records are considered inactive/unknown and excluded
        if license_number not in active_license_numbers:
            skipped_inactive += 1
            continue
        
        # Parse date
        date_str = doc['date'] or vl_info.get('date', '')
        parsed_date = parse_date(date_str)
        
        # Get annotation info
        annotation = annotations.get(license_number, {})
        
        # Determine facility type - prefer annotation, fall back to facility_information
        facility_type = annotation.get('agency_type', '') or facility.get('agency_type', '')
        simplified_type = simplify_facility_type(facility_type)
        
        # Determine region
        region = normalize_region(annotation.get('region', ''))
        
        # Determine gender served
        gender = normalize_gender(annotation.get('genders_served', ''))
        
        # Determine capacity
        capacity = parse_capacity(annotation.get('capacity', ''))
        capacity_bin = get_capacity_bin(capacity)
        
        # Calculate years active from earliest document
        earliest_doc = earliest_doc_by_facility.get(license_number)
        years_active = calculate_years_active(earliest_doc)
        years_active_bin = get_years_active_bin(years_active)
        
        # Calculate capacity_years (capacity × years_active) for normalization
        capacity_years = None
        if capacity is not None and years_active is not None:
            capacity_years = capacity * years_active
        
        # Aggregate by date (month)
        year_str = None
        if parsed_date:
            year, month = parsed_date
            year_str = str(year)
            date_key = f"{year}-{month:02d}"
            violations_by_date[date_key]['total'] += 1
            violations_by_date[date_key][level] += 1
            
            # Also aggregate by year
            violations_by_year[year_str]['total'] += 1
            violations_by_year[year_str][level] += 1
            
            # Aggregate by years active bin
            violations_by_years_active[years_active_bin]['total'] += 1
            violations_by_years_active[years_active_bin][level] += 1
            if license_number not in facilities_by_years_active_bin[years_active_bin]:
                facilities_by_years_active_bin[years_active_bin].add(license_number)
            
            # Per-year grouped data for year range filtering
            violations_by_year_grouped[year_str]['facility_type'][simplified_type]['total'] += 1
            violations_by_year_grouped[year_str]['facility_type'][simplified_type][level] += 1
            violations_by_year_grouped[year_str]['region'][region]['total'] += 1
            violations_by_year_grouped[year_str]['region'][region][level] += 1
            violations_by_year_grouped[year_str]['gender'][gender]['total'] += 1
            violations_by_year_grouped[year_str]['gender'][gender][level] += 1
            violations_by_year_grouped[year_str]['capacity_bin'][capacity_bin]['total'] += 1
            violations_by_year_grouped[year_str]['capacity_bin'][capacity_bin][level] += 1
            violations_by_year_grouped[year_str]['years_active_bin'][years_active_bin]['total'] += 1
            violations_by_year_grouped[year_str]['years_active_bin'][years_active_bin][level] += 1
            
            # Track facilities per year (for facility counts)
            facilities_per_year[year_str]['facility_type'][simplified_type].add(license_number)
            facilities_per_year[year_str]['region'][region].add(license_number)
            facilities_per_year[year_str]['gender'][gender].add(license_number)
            facilities_per_year[year_str]['capacity_bin'][capacity_bin].add(license_number)
            facilities_per_year[year_str]['years_active_bin'][years_active_bin].add(license_number)
            
            # Track capacity and capacity_years per year per grouping
            if capacity is not None:
                if license_number not in capacity_tracked_per_year[year_str]['facility_type'][simplified_type]:
                    violations_by_year_grouped[year_str]['facility_type'][simplified_type]['capacity'] += capacity
                    if capacity_years is not None:
                        violations_by_year_grouped[year_str]['facility_type'][simplified_type]['capacity_years'] += capacity_years
                    capacity_tracked_per_year[year_str]['facility_type'][simplified_type].add(license_number)
                if license_number not in capacity_tracked_per_year[year_str]['region'][region]:
                    violations_by_year_grouped[year_str]['region'][region]['capacity'] += capacity
                    if capacity_years is not None:
                        violations_by_year_grouped[year_str]['region'][region]['capacity_years'] += capacity_years
                    capacity_tracked_per_year[year_str]['region'][region].add(license_number)
                if license_number not in capacity_tracked_per_year[year_str]['gender'][gender]:
                    violations_by_year_grouped[year_str]['gender'][gender]['capacity'] += capacity
                    if capacity_years is not None:
                        violations_by_year_grouped[year_str]['gender'][gender]['capacity_years'] += capacity_years
                    capacity_tracked_per_year[year_str]['gender'][gender].add(license_number)
                if license_number not in capacity_tracked_per_year[year_str]['capacity_bin'][capacity_bin]:
                    violations_by_year_grouped[year_str]['capacity_bin'][capacity_bin]['capacity'] += capacity
                    if capacity_years is not None:
                        violations_by_year_grouped[year_str]['capacity_bin'][capacity_bin]['capacity_years'] += capacity_years
                    capacity_tracked_per_year[year_str]['capacity_bin'][capacity_bin].add(license_number)
        
        # Aggregate by facility type
        violations_by_facility_type[simplified_type]['total'] += 1
        violations_by_facility_type[simplified_type][level] += 1
        if license_number not in facilities_by_type[simplified_type]:
            if capacity is not None:
                violations_by_facility_type[simplified_type]['capacity'] += capacity
            if capacity_years is not None:
                violations_by_facility_type[simplified_type]['capacity_years'] += capacity_years
            facilities_by_type[simplified_type].add(license_number)
        
        # Aggregate by region
        violations_by_region[region]['total'] += 1
        violations_by_region[region][level] += 1
        if license_number not in facilities_by_region[region]:
            if capacity is not None:
                violations_by_region[region]['capacity'] += capacity
            if capacity_years is not None:
                violations_by_region[region]['capacity_years'] += capacity_years
            facilities_by_region[region].add(license_number)
        
        # Aggregate by gender
        violations_by_gender[gender]['total'] += 1
        violations_by_gender[gender][level] += 1
        if license_number not in facilities_by_gender[gender]:
            if capacity is not None:
                violations_by_gender[gender]['capacity'] += capacity
            if capacity_years is not None:
                violations_by_gender[gender]['capacity_years'] += capacity_years
            facilities_by_gender[gender].add(license_number)
        
        # Aggregate by capacity bin
        violations_by_capacity[capacity_bin]['total'] += 1
        violations_by_capacity[capacity_bin][level] += 1
        if license_number not in facilities_by_capacity_bin[capacity_bin]:
            if capacity is not None:
                violations_by_capacity[capacity_bin]['capacity'] += capacity
            if capacity_years is not None:
                violations_by_capacity[capacity_bin]['capacity_years'] += capacity_years
            facilities_by_capacity_bin[capacity_bin].add(license_number)
    
    print(f"Skipped {skipped_inactive} violations from facilities with inactive licenses")
    
    # Convert to sorted lists for JSON output
    def dict_to_sorted_list(d: dict, key_name: str = 'key') -> list:
        """Convert defaultdict to sorted list of dicts."""
        result = []
        for key, counts in sorted(d.items()):
            entry = {key_name: key}
            entry.update(counts)
            result.append(entry)
        return result
    
    # Custom sort for capacity bins
    def capacity_bin_sort_key(item):
        """Sort capacity bins in logical order."""
        order = {'1-10': 0, '11-20': 1, '21-30': 2, '31-50': 3, '51-100': 4, '100+': 5, 'Unknown': 6}
        return order.get(item['capacity_bin'], 99)
    
    # Custom sort for years active bins
    def years_active_bin_sort_key(item):
        """Sort years active bins in logical order."""
        order = {'<1 year': 0, '1-2 years': 1, '2-3 years': 2, '3-5 years': 3, '5-10 years': 4, '10+ years': 5, 'Unknown': 6}
        return order.get(item['years_active_bin'], 99)
    
    capacity_list = dict_to_sorted_list(violations_by_capacity, 'capacity_bin')
    capacity_list.sort(key=capacity_bin_sort_key)
    
    years_active_list = dict_to_sorted_list(violations_by_years_active, 'years_active_bin')
    years_active_list.sort(key=years_active_bin_sort_key)
    
    # Process per-year grouped data
    per_year_data = {}
    for year_str in sorted(violations_by_year_grouped.keys()):
        year_data = violations_by_year_grouped[year_str]
        per_year_data[year_str] = {
            'facility_type': dict_to_sorted_list(year_data['facility_type'], 'facility_type'),
            'region': dict_to_sorted_list(year_data['region'], 'region'),
            'gender': dict_to_sorted_list(year_data['gender'], 'gender'),
            'capacity_bin': sorted(
                [{'capacity_bin': k, **dict(v)} for k, v in year_data['capacity_bin'].items()],
                key=lambda x: {'1-10': 0, '11-20': 1, '21-30': 2, '31-50': 3, '51-100': 4, '100+': 5, 'Unknown': 6}.get(x['capacity_bin'], 99)
            ),
            'years_active_bin': sorted(
                [{'years_active_bin': k, **dict(v)} for k, v in year_data['years_active_bin'].items()],
                key=lambda x: {'<1 year': 0, '1-2 years': 1, '2-3 years': 2, '3-5 years': 3, '5-10 years': 4, '10+ years': 5, 'Unknown': 6}.get(x['years_active_bin'], 99)
            ),
        }
    
    # Process facility counts per year
    facility_counts_per_year = {}
    for year_str in sorted(facilities_per_year.keys()):
        year_facilities = facilities_per_year[year_str]
        facility_counts_per_year[year_str] = {
            'facility_type': [{'facility_type': k, 'count': len(v)} for k, v in sorted(year_facilities['facility_type'].items())],
            'region': [{'region': k, 'count': len(v)} for k, v in sorted(year_facilities['region'].items())],
            'gender': [{'gender': k, 'count': len(v)} for k, v in sorted(year_facilities['gender'].items())],
            'capacity_bin': sorted(
                [{'capacity_bin': k, 'count': len(v)} for k, v in year_facilities['capacity_bin'].items()],
                key=lambda x: {'1-10': 0, '11-20': 1, '21-30': 2, '31-50': 3, '51-100': 4, '100+': 5, 'Unknown': 6}.get(x['capacity_bin'], 99)
            ),
            'years_active_bin': sorted(
                [{'years_active_bin': k, 'count': len(v)} for k, v in year_facilities['years_active_bin'].items()],
                key=lambda x: {'<1 year': 0, '1-2 years': 1, '2-3 years': 2, '3-5 years': 3, '5-10 years': 4, '10+ years': 5, 'Unknown': 6}.get(x['years_active_bin'], 99)
            ),
        }
    
    # Prepare output data
    output_data = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_documents_processed': len(processed_sha256),
            'total_violations_with_level': sum(v['total'] for v in violations_by_date.values()),
            'skipped_inactive_facilities': skipped_inactive,
            'active_facility_count': len(active_license_numbers),
            'year_range': {
                'min': min(violations_by_year.keys()) if violations_by_year else None,
                'max': max(violations_by_year.keys()) if violations_by_year else None,
            },
            'methodology': {
                'filtering': 'Only facilities with confirmed active licenses (Regular, Original, Inspected, 1st/2nd Provisional) are included. Facilities not in our license database or with inactive/unknown license status are excluded.',
                'years_active_estimation': 'Years active is estimated from the earliest document we have for each facility. This is an approximation - actual facility opening dates may differ.',
                'capacity_normalization': 'When normalizing by capacity, values are divided by (capacity × years_active) to account for both facility size and operating duration.',
                'caveats': [
                    'Capacity may have changed over time - we use current capacity for all calculations.',
                    'Years active is estimated from document history, not actual licensing records.',
                    'Some facilities may have documents predating our records.',
                    'Facilities with unknown license status are treated as inactive and excluded.'
                ]
            }
        },
        'by_year': dict_to_sorted_list(violations_by_year, 'year'),
        'by_facility_type': dict_to_sorted_list(violations_by_facility_type, 'facility_type'),
        'by_region': dict_to_sorted_list(violations_by_region, 'region'),
        'by_gender': dict_to_sorted_list(violations_by_gender, 'gender'),
        'by_capacity': capacity_list,
        'by_years_active': years_active_list,
        'per_year': per_year_data,
        'facility_counts_per_year': facility_counts_per_year,
    }
    
    # Write output
    output_file = os.path.join(output_dir, 'violations_data.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nWrote violations data to {output_file}")
    print(f"Total violations with severity level: {output_data['metadata']['total_violations_with_level']}")
    print(f"Year range: {output_data['by_year'][0]['year'] if output_data['by_year'] else 'N/A'} to {output_data['by_year'][-1]['year'] if output_data['by_year'] else 'N/A'}")


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
