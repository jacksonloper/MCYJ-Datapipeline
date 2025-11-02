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
        - duplicates: Dict mapping rule_code -> count of how many times it appeared
    """

    all_rules = []  # List of (rule_code, description) tuples

    # Method 1: Extract "APPLICABLE RULE" / "APPLICABLE POLICY" format
    applicable_rules = _extract_applicable_format_agnostic(text)
    all_rules.extend(applicable_rules)

    # Method 2: Extract "Rule Code & [ABBREV] Rule 400.xxx" format
    rule_code_rules = _extract_rule_code_format_agnostic(text)
    all_rules.extend(rule_code_rules)

    # Count duplicates before deduping
    duplicates = {}
    for rule_code, _ in all_rules:
        duplicates[rule_code] = duplicates.get(rule_code, 0) + 1

    # Deduplicate while preserving order
    seen = set()
    unique_rules = []
    unique_descriptions = []

    for rule_code, description in all_rules:
        if rule_code not in seen:
            seen.add(rule_code)
            unique_rules.append(rule_code)
            unique_descriptions.append(description)

    return unique_rules, unique_descriptions, duplicates


def _extract_applicable_format_agnostic(text):
    """
    Extract rules in 'APPLICABLE RULE' or 'APPLICABLE POLICY' format.
    Searches entire document, not just specific sections.
    """
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

    rules = []
    for i, e in zip(indices, end_indices):
        # Extract rule code (look for pattern like "400.xxxx", "R 400.xxxx", or "FOM 722-03D")
        # Try Rule 400.xxx format first
        rule_match = re.search(r"(?:R\s+)?(\d{3}\.\d+)", text[i:e])
        if rule_match:
            rules.append((rule_match.group(1), text[i:e].strip()))
        else:
            # Try FOM format
            fom_match = re.search(r"FOM\s+(\d+-\d+[A-Z]?)", text[i:e], re.IGNORECASE)
            if fom_match:
                rules.append(("FOM " + fom_match.group(1), text[i:e].strip()))

    return rules


def _extract_rule_code_format_agnostic(text):
    """
    Extract rules in 'Rule Code & <ABBREV> Rule 400.xxx' format.
    Searches entire document, not just specific sections.
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
        rules.append((rule_code, description))

    # Fallback: try simpler pattern for edge cases
    if not rules:
        pattern_fallback = r"\bR\s+(\d{3}\.\d+)"
        matches_fallback = list(re.finditer(pattern_fallback, text))
        for match in matches_fallback:
            rule_code = match.group(1)
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 200)
            description = text[start:end].strip()
            rules.append((rule_code, description))

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
            agnostic_rules, _, duplicates = extract_rules_agnostic(text)

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
