# Special Investigation Report Parser - Design Overview

## Purpose

This parser extracts structured data from Michigan DHHS Special Investigation Report (SIR) PDFs that have been converted to text. SIRs document investigations into alleged violations at licensed child welfare facilities.

## Major Parsing Challenges

### 1. Structural Inconsistency Across Documents

**Challenge**: Documents use 18 different structural variants with Roman numeral sections.

**Two dominant structures (91.2% of documents):**

**Structure A (63.6%)**: Embedded allegations
```
I. IDENTIFYING INFORMATION
   └─ Allegations embedded as table fields
II. METHODOLOGY
III. INVESTIGATION
    └─ Rules cited here
IV. RECOMMENDATION
```

**Structure B (27.6%)**: Dedicated allegation section
```
I. IDENTIFYING INFORMATION
II. ALLEGATION(S)
    └─ Full section for allegations
III. METHODOLOGY
    └─ Rules cited here (nested INVESTIGATION subsection)
IV. RECOMMENDATION
```

**Other variants (8.8%)**:
- Missing sections (skip II, start at III)
- Misnumbered sections (duplicate "II", jump to "VI")
- Different section names (III. METHODOLOGY vs III. INVESTIGATION)

**Solution**: **Structure-agnostic approach** - Don't rely on Roman numeral sections. Search entire document for content patterns instead.

---

### 2. Section Boundary Detection Bugs

**The "HIV/AIDS" Bug**

**Problem**: Pattern `(?:IV|lV|\Z)` to detect Section IV matched "**IV**" inside "H**IV**/AIDS child"

**Impact**:
- Section extraction terminated prematurely at "HIV/AIDS" text
- Example: SHA 9a054a7f447ba913 should extract 19,906 chars → only extracted 2,355 chars
- Result: **0 rules extracted instead of 4**

**Solution**: Structure-agnostic parser doesn't rely on section boundaries.

---

### 3. Multiple Rule Citation Formats

**Challenge**: Rules cited in 2+ different formats within same corpus.

**Format 1: "Rule Code" format (63.6% of documents)**
```
Rule Code & CCI Rule 400.4126 Staff to resident ratio
```

Variants:
- `Rule Code & CCI Rule 400.xxx`
- `Rule Code & R 400.xxx` (capital R)
- `R 400.xxx` (no "Rule Code" prefix)

**Format 2: "APPLICABLE RULE" format (35.2% of documents)**
```
APPLICABLE RULE
R 400.4126 Staff to resident ratio.
(3) The ratio formula shall correspond...
ANALYSIS: The facility is found in noncompliance...
CONCLUSION: VIOLATION ESTABLISHED
```

**Format 3: FOM format (4.2% of documents)**
```
APPLICABLE POLICY
FOM 722-03D Placement Change
CONCLUSION: VIOLATION NOT ESTABLISHED
```

FOM = Field Operations Manual (casework policies, not facility regulations)

**Solution**: Search for all formats in parallel, combine results.

---

### 4. Column Header Duplication

**Problem**: Table column headers match rule extraction patterns.

**Example**:
```
Rule Code    Placement      <-- Column header (not a rule)
-------------
Rule Code & CCI Rule 400.4126  <-- Actual rule
```

Simple text search for "Rule Code" finds both → extracts duplicate rules.

**Impact**: Affected 6% of documents, causing duplicate rule extraction.

**Solution**: Require full pattern match:
```regex
Rule Code\s+(?:&\s+)?(?:[A-Z]{2,4}\s+)?(?:Rule|R)\s+(\d{3}\.\d+)
```

This matches "Rule Code & CCI Rule 400.4126" but NOT "Rule Code Placement".

---

### 5. Violation Status Extraction

**The Index-Matching Bug**

**Problem**: Old parser matched conclusions to rules by index position.

```python
# Old approach (WRONG)
conclusions = extract_from_allegations()  # Gets 1 conclusion
rules = extract_rules()  # Gets 3 rules
for i, rule in enumerate(rules):
    conclusion = conclusions[i] if i < len(conclusions) else "N/A"
```

**Impact**: When 1 allegation violates 3 rules:
- Rule 0 gets conclusion[0] ✓
- Rule 1 gets conclusion[1] → doesn't exist → "N/A" ✗
- Rule 2 gets conclusion[2] → doesn't exist → "N/A" ✗

**Example (SHA 81f8c85b18909108)**:
- Document has 3 separate "CONCLUSION:" sections, one per rule
- Old parser showed rules 2 & 3 as "N/A" (wrong!)
- Actual: Rule 2 = "REPEAT VIOLATION ESTABLISHED", Rule 3 = "REPEAT VIOLATION ESTABLISHED"

**Solution**: Extract CONCLUSION directly from each APPLICABLE RULE section.
```python
# New approach (CORRECT)
for each APPLICABLE RULE section:
    rule_code = extract_from_section()
    conclusion = extract_from_section()  # Same section!
    violation = determine_status(conclusion)
```

---

### 6. Conclusion Extraction Text Bleed

**Problem**: Conclusion extraction included too much text.

**Example**:
```
CONCLUSION: VIOLATION ESTABLISHED
ADDITIONAL FINDINGS:
During this investigation staff are not checking on youth...
```

Old regex: `r'CONCLUSION:\s*(.*?)(?=APPLICABLE|$)'` captured entire block.

Check: `if "not" in conclusion.lower()` → found "**not** checking" in ADDITIONAL FINDINGS

Result: **Incorrectly determined as "No" instead of "Yes"**

**Solution**: Stop at section markers:
```python
r'CONCLUSION:\s*(.*?)(?=ADDITIONAL FINDINGS|APPLICABLE|ALLEGATION|$)'
```

Now extracts clean text: just "VIOLATION ESTABLISHED"

**Impact**: Fixed 7 false "status conflicts" (26% of apparent conflicts were parser bugs)

---

### 7. Duplicate Rules with Conflicting Statuses

**Challenge**: Same rule cited multiple times with different violation statuses.

**Why this happens**:
- Different subsections of same rule (e.g., subsection (3) violated, subsection (4) not violated)
- Different contexts (adequate during day, inadequate at night)
- Initial allegation vs additional findings

**Example (SHA ecea03a1d22844c9)**:
```
APPLICABLE POLICY
FOM 722-03D Placement Change
CONCLUSION: VIOLATION NOT ESTABLISHED

[Later in document]

APPLICABLE POLICY
FOM 722-03D Placement Change
CONCLUSION: VIOLATION ESTABLISHED
```

**Frequency**: 1.17% of documents (20 out of 1,708 SIRs) have true conflicts

**Solution**:
- Track all violation statuses before deduplication
- Detect conflicts: same rule_code with both "Yes" and "No"
- Flag in output: `has_status_conflict: true`
- Preserve duplicate_count to show how many times rule was mentioned

---

## Parser Design Decisions

### Structure-Agnostic Approach

**Don't rely on:**
- ✗ Roman numeral section numbers
- ✗ Section boundary detection
- ✗ Specific section names ("INVESTIGATION" vs "METHODOLOGY")
- ✗ Index-based matching between allegations and rules

**Do rely on:**
- ✓ Content patterns ("APPLICABLE RULE", "Rule Code &")
- ✓ Direct extraction from context (conclusion from same section as rule)
- ✓ Explicit duplicate tracking
- ✓ Conflict detection cross-checking

### Output Schema

For each rule:
```python
{
    "rule_code": "400.4160",  # or "FOM 722-03D"
    "description": "...",  # Rule text
    "conclusion": "VIOLATION ESTABLISHED",  # Extracted directly
    "violation_established": "Yes",  # Yes/No/N/A
    "duplicate_count": 2,  # How many times mentioned
    "has_status_conflict": False  # Conflicting Yes/No across mentions
}
```

### Pattern Matching Strategy

**Step 1**: Extract from "APPLICABLE RULE/POLICY" sections (highest quality)
- Includes conclusion text
- Works for both Rule 400.xxx and FOM formats
- ~35% of documents

**Step 2**: Extract from "Rule Code &" format
- No per-rule conclusions
- Multiple format variants (R vs Rule, different abbreviations)
- ~64% of documents

**Step 3**: Deduplicate while tracking conflicts
- Count duplicates before dedup
- Check for conflicting violation statuses
- Flag conflicts in output

---

## Test Coverage

**21 test cases** covering:

**Structural variants (3)**:
- Structure A (embedded allegations)
- Structure B (dedicated II. ALLEGATION section)
- Structure C (III. METHODOLOGY variant)

**Format variants (6)**:
- FOM format
- Different "Rule Code" patterns
- "R" prefix variations

**Critical bugs (2)**:
- HIV/AIDS section boundary bug
- Conclusion extraction text bleed

**Conflict detection (4)**:
- 2-mention conflicts
- 5-mention conflicts with high duplicate count
- False conflicts from parser bugs

**Edge cases (6)**:
- Column header duplication
- Missing fields
- Baseline correct cases

---

## Accuracy Metrics

**Overall parsing**:
- 1,708 SIRs successfully parsed
- 0 parsing errors
- 33% have duplicate rule mentions (tracked)
- 1.17% have violation status conflicts (flagged)

**Improvements from structure-agnostic approach**:
- HIV/AIDS bug: 0 rules → 4 rules (100% improvement on affected docs)
- Index-based bug: Fixed 271 documents (15.9%) with wrong violation statuses
- False conflicts: Reduced from 27 → 20 (eliminated 26% false positives)

**Remaining mismatches** (allegation count ≠ rule count): 20.3%
- These are expected: one allegation can violate multiple rules, vice versa
- Higher rate than old parser (15.9%) because old parser had bugs that coincidentally made counts match
- More accurate is better, even if counts don't match

---

## Key Insights

1. **Document formats are highly inconsistent** - Any parser relying on rigid structure will fail on edge cases

2. **Text patterns are more reliable than structure** - Content markers ("APPLICABLE RULE", "CONCLUSION:") appear consistently even when structure varies

3. **Context matters more than position** - Extracting conclusion from the same section as the rule is more accurate than index-matching

4. **Duplicates contain information** - Tracking duplicate counts and conflicts reveals important nuances (same rule violated in different contexts)

5. **Bugs can create false patterns** - The 7 "conflicts" caused by conclusion extraction bug looked like data inconsistencies but were actually parser errors

---

## Recommended Practices

For maintaining/extending this parser:

1. **Add test cases first** - When encountering a new edge case, add it to testcases.csv before fixing

2. **Use structure-agnostic patterns** - Don't add logic that depends on section numbers or specific document structure

3. **Extract in context** - When adding new fields, extract them from the same text chunk, not by index-matching

4. **Track and validate** - Use duplicate_count and has_status_conflict patterns for other extracted fields

5. **Test on full corpus** - Changes should be tested on all 1,708 SIRs, not just test cases

6. **Document format variations** - When finding new patterns, add examples to test cases and update this doc
