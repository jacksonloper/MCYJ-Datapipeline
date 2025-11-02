#!/usr/bin/env python3
"""
Check if duplicate rule mentions have consistent violation statuses.
"""

import json
import sys
import re

sys.path.insert(0, '/home/user/MCYJ-Datapipeline')

def extract_all_rules_with_status(text):
    """
    Extract ALL rule mentions (before deduplication) with their violation statuses.
    Returns list of (rule_code, conclusion, violation_status) tuples.
    """
    all_rules = []

    # Extract from APPLICABLE RULE/POLICY sections
    indices = [m.start() for m in re.finditer(r"applicable (?:rule|policy)", text, re.IGNORECASE)]

    for idx, start_pos in enumerate(indices):
        # Find end of this rule section
        if idx + 1 < len(indices):
            end_pos = indices[idx + 1]
        else:
            end_pos = min(len(text), start_pos + 2000)

        section_text = text[start_pos:end_pos]

        # Extract rule code
        rule_code = None
        rule_match = re.search(r"(?:R\s+)?(\d{3}\.\d+)", section_text)
        if rule_match:
            rule_code = rule_match.group(1)
        else:
            fom_match = re.search(r"FOM\s+(\d+-\d+[A-Z]?)", section_text, re.IGNORECASE)
            if fom_match:
                rule_code = "FOM " + fom_match.group(1)

        if not rule_code:
            continue

        # Extract conclusion
        conclusion_match = re.search(r'CONCLUSION:\s*(.*?)(?=APPLICABLE|$)', section_text, re.DOTALL | re.IGNORECASE)
        if conclusion_match:
            conclusion = conclusion_match.group(1).strip()[:100]  # First 100 chars
        else:
            conclusion = "N/A"

        # Determine violation status
        if conclusion == "N/A":
            violation_established = "N/A"
        elif "not" in conclusion.lower() and "established" in conclusion.lower():
            violation_established = "No"
        elif "established" in conclusion.lower():
            violation_established = "Yes"
        else:
            violation_established = "N/A"

        all_rules.append((rule_code, conclusion, violation_established))

    return all_rules


def check_consistency():
    """Check for inconsistent violation statuses in duplicate rules."""

    print("Checking for inconsistent violation statuses in duplicate rules...")
    print("=" * 80)
    print()

    inconsistent_docs = []
    total_docs_with_dups = 0
    total_docs = 0

    with open('/home/user/MCYJ-Datapipeline/pdf_parsing/pdfs_as_text.jsonl') as f:
        for line in f:
            record = json.loads(line)
            text = '\n'.join(record['text'])

            if 'SPECIAL INVESTIGATION REPORT' not in text:
                continue

            total_docs += 1

            # Extract all rules with their statuses
            all_rules = extract_all_rules_with_status(text)

            # Group by rule code
            rule_statuses = {}
            for rule_code, conclusion, status in all_rules:
                if rule_code not in rule_statuses:
                    rule_statuses[rule_code] = []
                rule_statuses[rule_code].append((conclusion, status))

            # Check for duplicates with inconsistent statuses
            has_duplicates = False
            inconsistencies = []

            for rule_code, statuses in rule_statuses.items():
                if len(statuses) > 1:
                    has_duplicates = True

                    # Check if all statuses are the same
                    unique_statuses = set(s[1] for s in statuses)
                    if len(unique_statuses) > 1:
                        inconsistencies.append({
                            'rule': rule_code,
                            'statuses': statuses
                        })

            if has_duplicates:
                total_docs_with_dups += 1

            if inconsistencies:
                inconsistent_docs.append({
                    'sha256': record['sha256'][:16],
                    'inconsistencies': inconsistencies
                })

                # Show first 5 examples
                if len(inconsistent_docs) <= 5:
                    sha = record['sha256'][:16]
                    print(f"INCONSISTENCY FOUND: {sha}...")
                    for inc in inconsistencies:
                        print(f"  Rule: {inc['rule']}")
                        for i, (concl, status) in enumerate(inc['statuses'], 1):
                            print(f"    Mention {i}: Violation={status} - {concl}")
                    print()

    print("=" * 80)
    print("RESULTS:")
    print("=" * 80)
    print(f"Total SIRs analyzed: {total_docs}")
    print(f"Documents with duplicate rules: {total_docs_with_dups} ({100*total_docs_with_dups/total_docs:.1f}%)")
    print(f"Documents with INCONSISTENT violation statuses: {len(inconsistent_docs)} ({100*len(inconsistent_docs)/total_docs:.1f}%)")
    print()

    if len(inconsistent_docs) > 5:
        print(f"Showing first 5 examples above. Total: {len(inconsistent_docs)}")
        print()
        print("Additional cases:")
        for doc in inconsistent_docs[5:10]:
            sha = doc['sha256']
            rule_count = len(doc['inconsistencies'])
            print(f"  {sha}... - {rule_count} rule(s) with inconsistent statuses")

if __name__ == '__main__':
    check_consistency()
