#!/usr/bin/env python3
"""
Analyze Roman numeral section structures across all SIR documents.
Identifies structural variants to understand document diversity.
"""

import json
import re
from collections import Counter, defaultdict

def extract_roman_numeral_structure(text):
    """
    Extract Roman numeral sections and their headings.
    Returns a tuple of section headings like ('I. IDENTIFYING INFORMATION', 'II. ALLEGATION', ...)
    """
    # Find all Roman numeral sections at the start of lines
    # Pattern: I., II., III., IV., V., etc. followed by heading text
    # Include parentheses, hyphens, and other common punctuation in headings
    pattern = r'^\s*([IVX]+)\.\s+([A-Z][A-Z\s\(\)\-/]+?)(?:\s*$|\n)'

    matches = re.findall(pattern, text, re.MULTILINE)

    sections = []
    for roman, heading in matches:
        # Clean up the heading (remove extra spaces, trailing words that might be content)
        heading = heading.strip()
        # Take only first few words if very long
        words = heading.split()
        if len(words) > 4:
            heading = ' '.join(words[:4])
        sections.append(f"{roman}. {heading}")

    return tuple(sections)

def normalize_structure(sections):
    """
    Normalize section headings to group similar structures.
    E.g., 'II. ALLEGATION' and 'II. ALLEGATIONS' -> 'II. ALLEGATION(S)'
    """
    normalized = []
    for section in sections:
        s = section
        # Normalize ALLEGATION vs ALLEGATIONS
        s = re.sub(r'ALLEGATION\(?S?\)?', 'ALLEGATION(S)', s, flags=re.IGNORECASE)
        # Normalize RECOMMENDATION vs RECOMMENDATIONS
        s = re.sub(r'RECOMMENDATION\(?S?\)?', 'RECOMMENDATION(S)', s, flags=re.IGNORECASE)
        normalized.append(s)
    return tuple(normalized)

def main():
    print("Analyzing document structures across all SIRs...")
    print("=" * 80)
    print()

    structures = []
    structure_to_sha = defaultdict(list)

    with open('/home/user/MCYJ-Datapipeline/pdf_parsing/pdfs_as_text.jsonl') as f:
        for line in f:
            record = json.loads(line)
            text = '\n'.join(record['text'])

            # Only analyze SIR documents
            if 'SPECIAL INVESTIGATION REPORT' not in text:
                continue

            sha_prefix = record['sha256'][:16]
            structure = extract_roman_numeral_structure(text)

            if structure:
                normalized = normalize_structure(structure)
                structures.append(normalized)
                structure_to_sha[normalized].append(sha_prefix)

    # Count structure frequencies
    structure_counts = Counter(structures)

    print(f"Total SIR documents analyzed: {len(structures)}")
    print(f"Unique structures found: {len(structure_counts)}")
    print()
    print("=" * 80)
    print("STRUCTURE FREQUENCY ANALYSIS")
    print("=" * 80)
    print()

    # Sort by frequency (descending)
    for structure, count in structure_counts.most_common(20):
        pct = 100 * count / len(structures)
        print(f"{count:4d} ({pct:5.1f}%)  {' -> '.join(structure)}")

        # Show example SHA for less common structures
        if count <= 10:
            example_sha = structure_to_sha[structure][0]
            print(f"          Example: {example_sha}...")
        print()

    # Show remaining structures if there are many
    if len(structure_counts) > 20:
        print(f"\n... and {len(structure_counts) - 20} more rare structures")

    print()
    print("=" * 80)
    print("SECTION III VARIANTS")
    print("=" * 80)
    print()

    # Analyze what Section III is called
    section_iii_variants = Counter()
    for structure in structures:
        for section in structure:
            if section.startswith('III.'):
                section_iii_variants[section] += 1

    for variant, count in section_iii_variants.most_common():
        pct = 100 * count / len(structures)
        print(f"{count:4d} ({pct:5.1f}%)  {variant}")

    print()
    print("=" * 80)
    print("UNUSUAL STRUCTURES (fewer than 1%)")
    print("=" * 80)
    print()

    threshold = len(structures) * 0.01
    unusual = [(s, c, structure_to_sha[s]) for s, c in structure_counts.items() if c < threshold]

    for structure, count, shas in sorted(unusual, key=lambda x: -x[1]):
        pct = 100 * count / len(structures)
        print(f"\n{count:4d} ({pct:5.1f}%)  {' -> '.join(structure)}")
        print(f"Example SHA: {shas[0]}...")

if __name__ == '__main__':
    main()
