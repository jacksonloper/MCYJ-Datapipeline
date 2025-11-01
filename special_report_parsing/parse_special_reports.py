"""
Extract structured data from special investigation reports.

This script processes PDF text from a JSONL file (created by pdf_parsing/extract_pdf_text.py)
and extracts structured information about special investigations, violations, and rule codes.

The script uses the same extraction approach as the PdfScrape.ipynb notebook, but reads
from pre-extracted PDF text instead of parsing PDFs directly.

Outputs three CSV files:
- output.csv: Main information about each investigation
- violations.csv: Individual allegations and their investigations
- rules.csv: Rule codes and violations
"""

import json
import csv
import regex as re
import time
from datetime import datetime
from pathlib import Path


def extract(pattern, text, default="", flags=re.IGNORECASE):
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else default


def extract_admin_and_designee(text):
    # Pattern 1: Administrator before Licensee Designee
    match = re.search(r"Administrator:\s*(.*?)\s+Licensee Designee:\s*(.*?)(?:\n|$)", text, re.IGNORECASE | re.DOTALL)
    if match:
        # Return (designee, admin) - note the reversed order since pattern captures (admin, designee)
        return match.group(2).strip(), match.group(1).strip()

    # Pattern 2: Licensee Designee before Chief Administrator
    match = re.search(r"Licensee Designee:\s*(.*?)\s+Chief Administrator:\s*(.*?)(?:\n|$)", text, re.IGNORECASE | re.DOTALL)
    if match:
        # Return (designee, admin) - pattern captures in this order
        return match.group(1).strip(), match.group(2).strip()

    # Pattern 3: Licensee Designee before Administrator
    match = re.search(r"Licensee Designee:\s*(.*?)\s+Administrator:\s*(.*?)(?:\n|$)", text, re.IGNORECASE | re.DOTALL)
    if match:
        # Return (designee, admin) - pattern captures in this order
        return match.group(1).strip(), match.group(2).strip()

    return "", ""


def extract_address(text, label):
    pattern = rf"{label}:\s*(.*?)\n\s*([^\n]*MI\s+\d{{5}}(?:-\d{{4}})?)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return f"{match.group(1).strip()} {match.group(2).strip()}"
    return ""


def extract_final_report_date(text):
    match = re.search(
        r"\b(?:"
        r"(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}"
        r"|"
        r"\d{1,2}/\d{1,2}/\d{4}"
        r")\b",
        text
    )
    return match.group(0) if match else ""


def extract_methodology_start_date(text):
    # First try to extract Complaint Receipt Date
    match = re.search(r"Complaint Receipt Date:\s*(\d{2}/\d{2}/\d{4})", text)
    if match:
        return match.group(1)

    # Extract Methodology section
    methodology_match = re.search(r"(?i)\bII\.\s*METHODOLOGY\b(.*?)(?=\n\s*\n|III\.|lll\.|\Z)", text, re.DOTALL)
    if methodology_match:
        methodology_text = methodology_match.group(1)

        # Find all dates in M/D/YYYY or MM/DD/YYYY format
        date_strings = re.findall(r"\d{1,2}/\d{1,2}/\d{2,4}", methodology_text)
        parsed_dates = []

        for d in date_strings:
            try:
                parsed_date = datetime.strptime(d, "%m/%d/%Y")  # try 4-digit year
            except ValueError:
                try:
                    parsed_date = datetime.strptime(d, "%m/%d/%y")  # try 2-digit year
                except ValueError:
                    continue  # skip unrecognized formats
            parsed_dates.append(parsed_date)

        if parsed_dates:
            earliest_date = min(parsed_dates)
            return earliest_date.strftime("%m/%d/%Y")

    return ""


def extract_date_before_initiat(text):
    # Extract Methodology section
    methodology_match = re.search(
        r"(?i)\bMETHODOLOGY\b(.*?)(?=\n\s*\n|III\.|lll\.|\Z)",
        text,
        re.DOTALL
    )
    if methodology_match:
        methodology_text = methodology_match.group(1)

        # Look for date near "initiat" - within same line or next ~100 chars
        # This handles cases where "Investigation Initiation" is split across lines
        match = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4}).{0,100}?initiat", methodology_text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
    return ""


def extract_allegation_investigation_analysis_conclusion(text):
    # 1. Find "Methodology"
    methodology_start = re.search(r"\bmethodology\b", text, re.IGNORECASE)
    if not methodology_start:
        return [], [], [], []

    # 2. Cut text from "Methodology" onward
    remaining_text = text[methodology_start.end():]

    # 3. Stop at "IV." (section marker), if it exists
    stop_match = re.search(r"\bIV\.\b", remaining_text)
    if stop_match:
        remaining_text = remaining_text[:stop_match.start()]

    # 4. Find all matches between "allegation" or "additional findings" and "investigation"
    allegations = []
    investigations = []
    analyses = []
    conclusions = []

    while True:
        try:
            # allegation
            pattern = r"(?:ALLEGATION|ADDITIONAL FINDINGS)(.*?)(?=(INVESTIGATION){e<2})"
            match = re.search(pattern, remaining_text, re.DOTALL)
            if not match:
                pattern = r"(?:Allegation|Additional Findings)(.*?)(?=(Investigation){e<2})"
                match = re.search(pattern, remaining_text, re.DOTALL)
                if not match:
                    break
            allegation = match.group(1).replace("\n", " ").replace("\r", " ").strip()

            remaining_text = remaining_text[match.end():]

            match = re.search(r"(?:INVESTIGATION){e<2}[:\s]*(.*?)(?=(APPLICABLE){e<2})", remaining_text, flags=re.DOTALL)
            if not match:
                match = re.search(r"(?:Investigation){e<2}[:\s]*(.*?)(?=(Analysis){e<2})", remaining_text, flags=re.DOTALL)
                if not match:
                    match = re.search(r"(?:Investigation){e<2}[:\s]*(.*?)(?=(Conclusion){e<2})", remaining_text, flags=re.DOTALL | re.IGNORECASE)
            investigation = match.group(1).replace("\n", " ").replace("\r", " ").strip()

            remaining_text = remaining_text[match.end():]

            # analysis
            match = re.search(r"(?:ANALYSIS){e<2}[:\s]*(.*?)(?=(CONCLUSION){e<2})", remaining_text, flags=re.DOTALL)
            if not match:
                match = re.search(r"(?:Analysis){e<2}[:\s]*(.*?)(?=(Conclusion){e<2})", remaining_text, flags=re.DOTALL)
                if not match:
                    match = re.search(r"(?:ANALYSIS){e<2}[:\s]*(.*?)(?=(VIOLATION){e<2})", remaining_text, flags=re.DOTALL | re.IGNORECASE)
            try:
                analysis = match.group(1).replace("\n", " ").replace("\r", " ").strip()
                remaining_text = remaining_text[match.end():]
            except:
                analysis = ""

            # conclusion
            match = re.search(r"(?:CONCLUSION){e<2}[:\s]*(.*?(ESTABLISHED){e<2})", remaining_text, flags=re.DOTALL | re.IGNORECASE)
            if not match:
                match = re.search(r"((?:VIOLATION){e<2}[:\s]*.*?(ESTABLISHED){e<2})", remaining_text, flags=re.DOTALL | re.IGNORECASE)
                if not match:
                    match = re.search(r"(?:CONCLUSION){e<2}[:\s]*(.*?(VIOLATION){e<2})", remaining_text, flags=re.DOTALL | re.IGNORECASE)
            conclusion = match.group(1).replace("\n", " ").replace("\r", " ").strip()

            remaining_text = remaining_text[match.end():]

            allegations.append(re.sub(r"^[^a-zA-Z0-9]+", "", allegation))
            investigations.append(re.sub(r"^[^a-zA-Z0-9]+", "", investigation))
            analyses.append(re.sub(r"^[^a-zA-Z0-9]+", "", analysis))
            conclusions.append(re.sub(r"^[^a-zA-Z0-9]+", "", conclusion))
        except:
            break

    return allegations, investigations, analyses, conclusions


def get_rule_codes(text):
    """
    Extract rule codes and descriptions from SIR documents.

    Handles two document structures:
    - Structure A: Rules in Section III with "Rule Code & <ABBREV> Rule 400.xxx" format
    - Structure B: Rules in Section II with "APPLICABLE RULE" format
    """

    # Detect document structure
    # Structure B: Has "II. METHODOLOGY" AND does NOT have "III. INVESTIGATION"
    # Structure A: Has "III. INVESTIGATION" OR has "II. ALLEGATION(S)" (most common)

    has_section_III_investigation = bool(re.search(r'\bIII\.\s+INVESTIGATION', text, re.IGNORECASE))
    section_II_match = re.search(r'\bII\.\s+([A-Z]+)', text)
    has_section_II_methodology = section_II_match and section_II_match.group(1).startswith('METHODOLOGY')

    # Structure B is only when we have II. METHODOLOGY but NO III. INVESTIGATION
    is_structure_B = has_section_II_methodology and not has_section_III_investigation

    # Extract the correct section based on structure
    if is_structure_B:
        # Structure B: Extract Section II (between "II." and "III.")
        section_match = re.search(r"(?:II|ll)(.*?)(?:III|lll|\Z)", text, flags=re.DOTALL)
    else:
        # Structure A: Extract Section III (between "III" and "IV")
        section_match = re.search(r"(?:III|lll)(.*?)(?:IV|lV|\Z)", text, flags=re.DOTALL)

    if not section_match:
        return [], []

    section_text = section_match.group(1).strip()

    # Check which format is used
    if "applicable rule" in section_text.lower() or "applicable policy" in section_text.lower():
        # APPLICABLE RULE/POLICY format (Structure B)
        return _extract_applicable_rule_format(section_text)
    else:
        # Rule Code format (Structure A)
        return _extract_rule_code_format(section_text)


def _extract_applicable_rule_format(text):
    """Extract rules in 'APPLICABLE RULE' or 'APPLICABLE POLICY' format."""
    indices = [m.start() for m in re.finditer(r"applicable (?:rule|policy)", text, re.IGNORECASE)]

    # Find end of each rule section (typically "analysis" or "conclusion")
    end_indices = []
    for i in indices:
        # Try to find "analysis" or "conclusion" after this index
        analysis_match = re.search(r"analysis|conclusion", text[i:], re.IGNORECASE)
        if analysis_match:
            end_indices.append(i + analysis_match.start())
        else:
            # If not found, try "anaylsis" (common typo)
            typo_match = re.search(r"anaylsis", text[i:], re.IGNORECASE)
            if typo_match:
                end_indices.append(i + typo_match.start())
            else:
                # Default to 500 chars if no delimiter found
                end_indices.append(i + 500)

    rule_codes = []
    descriptions = []
    for i, e in zip(indices, end_indices):
        # Extract rule code (look for pattern like "400.xxxx", "R 400.xxxx", or "FOM 722-03D")
        # Try Rule 400.xxx format first
        rule_match = re.search(r"(?:R\s+)?(\d{3}\.\d+)", text[i:e])
        if rule_match:
            rule_codes.append(rule_match.group(1))
            descriptions.append(text[i:e].strip())
        else:
            # Try FOM format
            fom_match = re.search(r"FOM\s+(\d+-\d+[A-Z]?)", text[i:e], re.IGNORECASE)
            if fom_match:
                rule_codes.append("FOM " + fom_match.group(1))
                descriptions.append(text[i:e].strip())

    return rule_codes, descriptions


def _extract_rule_code_format(text):
    """Extract rules in 'Rule Code & <ABBREV> Rule 400.xxx' format."""

    # Use regex pattern to match actual rule codes, not column headers
    # Pattern matches: "Rule Code [& ][ABBREV ](Rule|R) 400.xxxx"
    # But NOT: "Rule Code Placement", "Rule Code Sufficiency of staff", etc.

    # Pattern explanation:
    # - "Rule Code" literal text
    # - \s+ one or more spaces
    # - (?:&\s+)? optional ampersand and spaces
    # - (?:[A-Z]{2,4}\s+)? optional 2-4 letter abbreviation (CCI, CPA, COF, etc.)
    # - (?:Rule|R) either "Rule" or "R"
    # - \s+ spaces
    # - (\d{3}\.\d+) the actual rule number (captured)

    pattern = r"Rule Code\s+(?:&\s+)?(?:[A-Z]{2,4}\s+)?(?:Rule|R)\s+(\d{3}\.\d+)"

    matches = list(re.finditer(pattern, text))

    if not matches:
        # Fallback: try simpler pattern for edge cases
        # This matches "R 400.xxxx" without "Rule Code" prefix
        pattern_fallback = r"\bR\s+(\d{3}\.\d+)"
        matches = list(re.finditer(pattern_fallback, text))

    rule_codes = []
    descriptions = []

    for match in matches:
        rule_code = match.group(1)
        start_idx = match.start()

        # Find end of this rule section (look for "Violation" or next rule)
        remaining_text = text[start_idx:]
        end_match = re.search(r"Violation|Rule Code", remaining_text[20:])  # Skip first 20 chars

        if end_match:
            end_idx = start_idx + 20 + end_match.start()
        else:
            end_idx = min(start_idx + 500, len(text))

        rule_codes.append(rule_code)
        descriptions.append(text[start_idx:end_idx].strip())

    return rule_codes, descriptions


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


def parse_single_record(record: dict) -> dict:
    """
    Parse a single JSONL record and return structured data.

    This is used by both the batch processor and the debug viewer.

    Returns:
        dict with keys:
            - basic_info: dict of basic investigation information
            - allegations: list of dicts with allegation data
            - rules: list of dicts with rule data
            - text: full text
            - mismatch: bool indicating if allegation/rule counts don't match
    """
    filename = record.get('filename', record['sha256'])
    text = "\n".join(record['text'])

    # Extract basic info
    designee, admin = extract_admin_and_designee(text)

    basic_info = {
        "File Name": filename,
        "SHA256": record['sha256'],
        "License #": extract(r"License #:\s*([A-Z]+\d+)", text),
        "Investigation #": extract(r"Investigation\s*#\s*:?\s*([0-9A-Z]+)", text, flags=re.DOTALL | re.IGNORECASE)
            or extract(r"SI\s*#\s*:?\s*([0-9A-Z]+)", text, flags=re.DOTALL | re.IGNORECASE)
            or extract(r"SIR\s*#\s*:?\s*([0-9A-Z]+)", text, flags=re.DOTALL | re.IGNORECASE)
            or extract(r"Investigation\s*Number\s*:?\s*([0-9A-Z]+)", text, flags=re.DOTALL | re.IGNORECASE)
            or extract(r"SI\s*Number\s*:?\s*([0-9A-Z]+)", text, flags=re.DOTALL | re.IGNORECASE)
            or extract(r"SIR\s*Number\s*:?\s*([0-9A-Z]+)", text, flags=re.DOTALL | re.IGNORECASE)
            or "",  # Removed overly broad fallback that matched "INVESTIGATION REPORT"
        "Final Report Date": extract_final_report_date(text),
        "Administrator": admin,
        "Licensee Designee": designee,
        "Facility Name": extract(r"Name of Facility:\s*(.*?)\n", text) or extract(r"Agency Name:\s*(.*?)\n", text) or extract(r"Name of Agency:\s*(.*?)\n", text),
        "Capacity": extract(r"Capacity:\s*(\d+)", text),
        "Complaint Receipt Date": extract_methodology_start_date(text),
        "Investigation Initiation Date": extract_date_before_initiat(text),
        "Effective Date": extract(r"Effective Date:\s*(\d{1,2}/\d{1,2}/\d{2,4})", text),
        "Expiration Date": extract(r"Expiration Date:\s*(\d{1,2}/\d{1,2}/\d{2,4})", text),
        "Facility Address": extract_address(text, "Facility Address") or extract_address(text, "Agency Address"),
        "Facility Telephone #": extract(r"Facility Telephone #:\s*(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})", text),
        "License Status": extract(r"License Status:\s*(\w+)", text).lower(),
        "Licensee Address": extract_address(text, "Licensee Address") or extract_address(text, "LicenseeAddress"),
        "Licensee Name": extract(r"Licensee Name:\s*(.*?)\n", text) or extract(r"Licensee Group Organization:\s*(.*?)\n", text) or extract(r"LicenseeName:\s*(.*?)\n", text),
        "Licensee Telephone #": extract(r"Licensee Telephone #:\s*(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})", text) or extract(r"LicenseeTelephone #:\s*(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})", text),
        "Original Issuance Date": extract(r"Original Issuance Date:\s*(\d{1,2}/\d{1,2}/\d{2,4})", text),
        "Program Type": extract(r"Program Type:\s*(.*?)\n", text),
        "Recommendation": extract(r"RECOMMENDATION\s*(?!\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b)(.*?)(?=_{2,}|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b)", text, flags=re.DOTALL).replace("\n", " ")
    }

    # Extract allegations
    allegations, investigations, analyses, conclusions = extract_allegation_investigation_analysis_conclusion(text)

    allegations_data = []
    for i, (alleg, invest, analysis, concl) in enumerate(zip(allegations, investigations, analyses, conclusions), 1):
        allegations_data.append({
            "number": i,
            "allegation": alleg,
            "investigation": invest,
            "analysis": analysis,
            "conclusion": concl,
            "violation_established": "No" if "not" in concl.lower() else "Yes"
        })

    # Extract rules
    rule_codes, descriptions = get_rule_codes(text)

    rules_data = []
    for i, (code, desc) in enumerate(zip(rule_codes, descriptions), 1):
        # Get corresponding conclusion if available
        concl = conclusions[i-1] if i <= len(conclusions) else "N/A"
        rules_data.append({
            "number": i,
            "rule_code": code,
            "description": desc,
            "conclusion": concl,
            "violation_established": "No" if "not" in concl.lower() else "Yes" if concl != "N/A" else "N/A"
        })

    return {
        "basic_info": basic_info,
        "text": text,
        "allegations": allegations_data,
        "rules": rules_data,
        "mismatch": len(allegations_data) != len(rules_data)
    }


def process_jsonl(input_jsonl: Path, output_dir: Path):
    """Process JSONL file and create three CSV outputs."""

    info_rows = []
    violation_rows = []
    rule_rows = []

    collected_investigations = set()

    # Count total lines first for progress tracking
    print("Counting total records...")
    with open(input_jsonl, 'r', encoding='utf-8') as f:
        total_records = sum(1 for _ in f)
    print(f"Found {total_records} total records\n")

    # Counters
    processed_count = 0
    skipped_count = 0
    duplicate_count = 0
    error_count = 0
    start_time = time.time()

    # Read JSONL file
    with open(input_jsonl, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                record = json.loads(line)

                # Get the filename from the record (if available) or use sha256
                filename = record.get('filename', record['sha256'])

                # Join all text pages
                text = "\n".join(record['text'])

                # Extract info
                designee, admin = extract_admin_and_designee(text)
                row = {
                    "File Name": filename,
                    "License #": extract(r"License #:\s*([A-Z]+\d+)", text),
                    "Investigation #": extract(r"Investigation\s*#\s*:?\s*([0-9A-Z]+)", text, flags=re.DOTALL | re.IGNORECASE)
                        or extract(r"SI\s*#\s*:?\s*([0-9A-Z]+)", text, flags=re.DOTALL | re.IGNORECASE)
                        or extract(r"SIR\s*#\s*:?\s*([0-9A-Z]+)", text, flags=re.DOTALL | re.IGNORECASE)
                        or extract(r"Investigation\s*Number\s*:?\s*([0-9A-Z]+)", text, flags=re.DOTALL | re.IGNORECASE)
                        or extract(r"SI\s*Number\s*:?\s*([0-9A-Z]+)", text, flags=re.DOTALL | re.IGNORECASE)
                        or extract(r"SIR\s*Number\s*:?\s*([0-9A-Z]+)", text, flags=re.DOTALL | re.IGNORECASE)
                        or extract(r"Investigation\s*:?\s*([0-9A-Z]+)", text, flags=re.DOTALL | re.IGNORECASE),
                    "Final Report Date": extract_final_report_date(text),
                    "Administrator": admin,
                    "Capacity": extract(r"Capacity:\s*(\d+)", text),
                    "Complaint Receipt Date": extract_methodology_start_date(text),
                    "Investigation Initiation Date": extract_date_before_initiat(text),
                    "Effective Date": extract(r"Effective Date:\s*(\d{1,2}/\d{1,2}/\d{2,4})", text),
                    "Expiration Date": extract(r"Expiration Date:\s*(\d{1,2}/\d{1,2}/\d{2,4})", text),
                    "Facility Address": extract_address(text, "Facility Address") or extract_address(text, "Agency Address"),
                    "Facility Telephone #": extract(r"Facility Telephone #:\s*(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})", text),
                    "License Status": extract(r"License Status:\s*(\w+)", text).lower(),
                    "Licensee Address": extract_address(text, "Licensee Address") or extract_address(text, "LicenseeAddress"),
                    "Licensee Designee": designee,
                    "Licensee Name": extract(r"Licensee Name:\s*(.*?)\n", text) or extract(r"Licensee Group Organization:\s*(.*?)\n", text) or extract(r"LicenseeName:\s*(.*?)\n", text),
                    "Licensee Telephone #": extract(r"Licensee Telephone #:\s*(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})", text) or extract(r"LicenseeTelephone #:\s*(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})", text),
                    "Facility Name": extract(r"Name of Facility:\s*(.*?)\n", text) or extract(r"Agency Name:\s*(.*?)\n", text) or extract(r"Name of Agency:\s*(.*?)\n", text),
                    "Original Issuance Date": extract(r"Original Issuance Date:\s*(\d{1,2}/\d{1,2}/\d{2,4})", text),
                    "Program Type": extract(r"Program Type:\s*(.*?)\n", text),
                    "Recommendation": extract(r"RECOMMENDATION\s*(?!\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b)(.*?)(?=_{2,}|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b)", text, flags=re.DOTALL).replace("\n", " ")
                }

                # Skip if not a special investigation report (no investigation number found)
                if row["Investigation #"] == "":
                    skipped_count += 1
                    if line_num % 100 == 0:  # Progress update every 100 records
                        print(f"[{line_num}/{total_records}] Processed: {processed_count}, Skipped (non-SIR): {skipped_count}, Duplicates: {duplicate_count}, Errors: {error_count}")
                    continue

                # Skip duplicates
                if row["Investigation #"] in collected_investigations:
                    duplicate_count += 1
                    if line_num % 100 == 0:
                        print(f"[{line_num}/{total_records}] Processed: {processed_count}, Skipped (non-SIR): {skipped_count}, Duplicates: {duplicate_count}, Errors: {error_count}")
                    continue

                collected_investigations.add(row["Investigation #"])
                print(f"[{line_num}/{total_records}] Processing: {row['Investigation #']}")

                if row["Investigation Initiation Date"] == "":
                    row["Investigation Initiation Date"] = row["Complaint Receipt Date"]

                # Allegations and investigations
                allegations, investigations, analyses, conclusions = extract_allegation_investigation_analysis_conclusion(text)
                row["Number of Allegations"] = len(allegations)
                info_rows.append(row)

                for allegation, investigation, analysis, conclusion in zip(allegations, investigations, analyses, conclusions):
                    vrow = {
                        "File Name": filename,
                        "Allegation": allegation,
                        "Investigation": investigation,
                        "Analysis": analysis,
                        "Conclusion": conclusion,
                        "Violation Established": "No" if "not" in conclusion.lower() else "Yes"
                    }
                    violation_rows.append(vrow)

                # Rule codes
                rule_codes, descriptions = get_rule_codes(text)
                for rule_code, description, conclusion in zip(rule_codes, descriptions, conclusions):
                    rrow = {
                        "File Name": filename,
                        "Rule": str(rule_code),
                        "Description": description,
                        "Conclusion": conclusion,
                        "Violation Established": "No" if "not" in conclusion.lower() else "Yes"
                    }
                    rule_rows.append(rrow)

                processed_count += 1

                # Show time estimate
                if processed_count > 0:
                    elapsed_time = time.time() - start_time
                    avg_time_per_record = elapsed_time / processed_count
                    remaining_estimate = avg_time_per_record * (total_records - line_num)
                    elapsed_str = format_time(elapsed_time)
                    remaining_str = format_time(remaining_estimate)
                    print(f"  -> {len(allegations)} allegations, {len(rule_codes)} rules | Time: {elapsed_str} elapsed, ~{remaining_str} remaining")

            except Exception as e:
                print(f"[{line_num}/{total_records}] Error: {e}")
                error_count += 1
                continue

    # Print summary
    print(f"\n{'='*60}")
    print("Summary:")
    print(f"  Total records: {total_records}")
    print(f"  Processed (SIR): {processed_count}")
    print(f"  Skipped (non-SIR): {skipped_count}")
    print(f"  Duplicates: {duplicate_count}")
    print(f"  Errors: {error_count}")
    print(f"{'='*60}\n")

    # Write CSV files
    output_dir.mkdir(parents=True, exist_ok=True)

    if info_rows:
        output_csv = output_dir / "output.csv"
        with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=info_rows[0].keys())
            writer.writeheader()
            writer.writerows(info_rows)
        print(f"✅ Extracted info from {len(info_rows)} special investigation reports")
        print(f"   Saved to: {output_csv}")

    if violation_rows:
        violations_csv = output_dir / "violations.csv"
        with open(violations_csv, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=violation_rows[0].keys())
            writer.writeheader()
            writer.writerows(violation_rows)
        print(f"✅ Extracted {len(violation_rows)} allegations")
        print(f"   Saved to: {violations_csv}")

    if rule_rows:
        rules_csv = output_dir / "rules.csv"
        with open(rules_csv, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rule_rows[0].keys())
            writer.writeheader()
            writer.writerows(rule_rows)
        print(f"✅ Extracted {len(rule_rows)} rule codes")
        print(f"   Saved to: {rules_csv}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Parse special investigation reports from JSONL")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("pdf_parsing/pdfs_as_text.jsonl"),
        help="Input JSONL file (default: pdf_parsing/pdfs_as_text.jsonl)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("special_report_parsing"),
        help="Output directory for CSV files (default: special_report_parsing)"
    )

    args = parser.parse_args()

    process_jsonl(args.input, args.output_dir)


if __name__ == "__main__":
    main()
