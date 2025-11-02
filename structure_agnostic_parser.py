#!/usr/bin/env python3
"""
Structure-agnostic SIR parser that ignores Roman numeral sections entirely.
Instead, searches for rule patterns anywhere in the document.
Also tracks duplicate rule mentions before deduplication.
"""

import re
import json

def extract_rules_agnostic(text):
    """
    Extract rules without relying on Roman numeral section structure.
    Searches entire document for both rule format patterns.

    Returns:
        - rule_codes: List of unique rule codes
        - descriptions: List of descriptions (aligned with rule_codes)
        - conclusions: List of conclusion texts (aligned with rule_codes)
        - violation_established: List of violation status (aligned with rule_codes)
        - duplicates: Dict mapping rule_code -> count of how many times it appeared
    """

    all_rules = []  # List of (rule_code, description, conclusion, violation_status) tuples

    # Method 1: Extract "APPLICABLE RULE" / "APPLICABLE POLICY" format (has conclusions)
    applicable_rules = _extract_applicable_format_agnostic(text)
    all_rules.extend(applicable_rules)

    # Method 2: Extract "Rule Code & [ABBREV] Rule 400.xxx" format (no conclusions)
    rule_code_rules = _extract_rule_code_format_agnostic(text)
    all_rules.extend(rule_code_rules)

    # Count duplicates before deduping
    duplicates = {}
    for rule_code, _, _, _ in all_rules:
        duplicates[rule_code] = duplicates.get(rule_code, 0) + 1

    # Deduplicate while preserving order
    seen = set()
    unique_rules = []
    unique_descriptions = []
    unique_conclusions = []
    unique_violations = []

    for rule_code, description, conclusion, violation in all_rules:
        if rule_code not in seen:
            seen.add(rule_code)
            unique_rules.append(rule_code)
            unique_descriptions.append(description)
            unique_conclusions.append(conclusion)
            unique_violations.append(violation)

    return unique_rules, unique_descriptions, unique_conclusions, unique_violations, duplicates


def _extract_applicable_format_agnostic(text):
    """
    Extract rules in 'APPLICABLE RULE' or 'APPLICABLE POLICY' format.
    Searches entire document, not just specific sections.
    Returns tuples of (rule_code, description, conclusion, violation_established)
    """
    indices = [m.start() for m in re.finditer(r"applicable (?:rule|policy)", text, re.IGNORECASE)]

    # For each APPLICABLE RULE, find the full section including conclusion
    rules = []
    for idx, start_pos in enumerate(indices):
        # Find end of this rule section (start of next APPLICABLE RULE, or far ahead)
        if idx + 1 < len(indices):
            end_pos = indices[idx + 1]
        else:
            end_pos = min(len(text), start_pos + 2000)

        section_text = text[start_pos:end_pos]

        # Extract rule code (look for pattern like "400.xxxx", "R 400.xxxx", or "FOM 722-03D")
        rule_code = None
        rule_match = re.search(r"(?:R\s+)?(\d{3}\.\d+)", section_text)
        if rule_match:
            rule_code = rule_match.group(1)
        else:
            # Try FOM format
            fom_match = re.search(r"FOM\s+(\d+-\d+[A-Z]?)", section_text, re.IGNORECASE)
            if fom_match:
                rule_code = "FOM " + fom_match.group(1)

        if not rule_code:
            continue

        # Extract description (from APPLICABLE RULE to ANALYSIS/CONCLUSION)
        desc_match = re.search(r'APPLICABLE (?:RULE|POLICY)(.*?)(?=ANALYSIS|CONCLUSION|$)', section_text, re.DOTALL | re.IGNORECASE)
        description = desc_match.group(1).strip() if desc_match else section_text[:200].strip()

        # Extract conclusion
        conclusion_match = re.search(r'CONCLUSION:\s*(.*?)(?=APPLICABLE|$)', section_text, re.DOTALL | re.IGNORECASE)
        if conclusion_match:
            conclusion = conclusion_match.group(1).strip()
        else:
            conclusion = "N/A"

        # Determine violation status from conclusion
        if conclusion == "N/A":
            violation_established = "N/A"
        elif "not" in conclusion.lower() and "established" in conclusion.lower():
            violation_established = "No"
        elif "established" in conclusion.lower():
            violation_established = "Yes"
        else:
            violation_established = "N/A"

        rules.append((rule_code, description, conclusion, violation_established))

    return rules


def _extract_rule_code_format_agnostic(text):
    """
    Extract rules in 'Rule Code & <ABBREV> Rule 400.xxx' format.
    Searches entire document, not just specific sections.
    Returns tuples of (rule_code, description, conclusion, violation_established)
    Note: This format doesn't have per-rule conclusions, so those are "N/A"
    """

    # Use regex pattern to match actual rule codes, not column headers
    # Pattern matches: "Rule Code [& ][ABBREV ](Rule|R) 400.xxxx"
    # But NOT: "Rule Code Placement", "Rule Code Sufficiency of staff", etc.

    pattern = r"Rule Code\s+(?:&\s+)?(?:[A-Z]{2,4}\s+)?(?:Rule|R)\s+(\d{3}\.\d+)"
    matches = list(re.finditer(pattern, text))

    rules = []
    for match in matches:
        rule_code = match.group(1)
        # Get some context around the match
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 200)
        description = text[start:end].strip()
        # Rule Code format doesn't have per-rule conclusions
        rules.append((rule_code, description, "N/A", "N/A"))

    # Fallback: try simpler pattern for edge cases
    if not rules:
        pattern_fallback = r"\bR\s+(\d{3}\.\d+)"
        matches_fallback = list(re.finditer(pattern_fallback, text))
        for match in matches_fallback:
            rule_code = match.group(1)
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 200)
            description = text[start:end].strip()
            rules.append((rule_code, description, "N/A", "N/A"))

    return rules


def test_agnostic_parser():
    """
    Test the structure-agnostic parser against all SIRs.
    Compare with current section-based parser.
    """
    import sys
    sys.path.insert(0, '/home/user/MCYJ-Datapipeline')
    from special_report_parsing.parse_special_reports import get_rule_codes

    print("Testing structure-agnostic parser vs current parser")
    print("=" * 80)
    print()

    matches = 0
    differences = 0
    total = 0

    agnostic_better = 0
    current_better = 0
    duplicate_cases = 0

    with open('/home/user/MCYJ-Datapipeline/pdf_parsing/pdfs_as_text.jsonl') as f:
        for line in f:
            record = json.loads(line)
            text = '\n'.join(record['text'])

            if 'SPECIAL INVESTIGATION REPORT' not in text:
                continue

            total += 1

            # Current parser
            current_rules, _ = get_rule_codes(text)

            # New agnostic parser
            agnostic_rules, _, _, _, duplicates = extract_rules_agnostic(text)

            # Check for duplicates
            has_duplicates = any(count > 1 for count in duplicates.values())
            if has_duplicates:
                duplicate_cases += 1

            # Compare results
            current_set = set(current_rules)
            agnostic_set = set(agnostic_rules)

            if current_set == agnostic_set:
                matches += 1
            else:
                differences += 1

                # Who found more rules?
                if len(agnostic_set) > len(current_set):
                    agnostic_better += 1
                elif len(current_set) > len(agnostic_set):
                    current_better += 1

                # Show first few examples of differences
                if differences <= 5:
                    sha = record['sha256'][:16]
                    print(f"Difference #{differences}: {sha}...")
                    print(f"  Current:  {len(current_rules)} rules: {current_rules}")
                    print(f"  Agnostic: {len(agnostic_rules)} rules: {agnostic_rules}")
                    if has_duplicates:
                        print(f"  Duplicates: {[(k, v) for k, v in duplicates.items() if v > 1]}")
                    print()

    print("=" * 80)
    print("RESULTS:")
    print("=" * 80)
    print(f"Total SIRs tested: {total}")
    print(f"Exact matches: {matches} ({100*matches/total:.1f}%)")
    print(f"Differences: {differences} ({100*differences/total:.1f}%)")
    print()
    print(f"Cases with duplicate rule mentions: {duplicate_cases} ({100*duplicate_cases/total:.1f}%)")
    print()
    print("When different:")
    print(f"  Agnostic found more rules: {agnostic_better}")
    print(f"  Current found more rules: {current_better}")
    print(f"  Same count, different rules: {differences - agnostic_better - current_better}")


if __name__ == '__main__':
    test_agnostic_parser()
