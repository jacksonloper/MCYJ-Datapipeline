# Section III Format Variations in Special Investigation Reports

## Investigation Summary

Analyzed 200 Special Investigation Reports to understand Section III formatting inconsistencies.

## Format Distribution

Based on 200 SIR sample:

| Format Type | Count | % | Description |
|-------------|-------|---|-------------|
| Rule Code & <ABBREV> Rule | 172 | 86.0% | Standard format: "Rule Code & CCI Rule 400.4109" |
| Column Headers + Rule | 12 | 6.0% | Has headers like "Rule Code Placement" before actual rule |
| Rule Code & Rule | 9 | 4.5% | Missing abbreviation: "Rule Code & Rule 400.4131" |
| Other formats | 4 | 2.0% | Various non-standard formats |
| Rule Code <ABBREV> Rule | 3 | 1.5% | No ampersand: "Rule Code CCI Rule 400.4118" |

## Key Findings

### 1. Column Header Problem (6% of reports)
**Impact:** Causes duplicate rule extraction

Reports have column headers that contain "Rule Code" followed by descriptive text:
- "Rule Code Placement"
- "Rule Code Sufficiency of staff"
- "Rule Code Resident restraint"
- "Rule Code Program"
- "Rule Code Non-Compliance Type"

These appear BEFORE the actual rule code line, causing the parser to match both:
```
Rule Code Placement        <- Column header (incorrectly matched)
Title
Rule Code & CPA Rule 400.12404  <- Actual rule (correctly matched)
```

Result: Rule 400.12404 extracted twice, creating allegation/rule mismatch.

### 2. Format Variations (7.5% of reports)
Several non-standard formats exist:

**Missing Abbreviation (4.5%):**
```
Rule Code & Rule 400.4131
```
Instead of: `Rule Code & CCI Rule 400.4131`

**No Ampersand (1.5%):**
```
Rule Code CCI Rule 400.4118
```
Instead of: `Rule Code & CCI Rule 400.4118`

**'R' prefix instead of 'Rule' (2%):**
```
Rule Code & R 400.4109
```
Instead of: `Rule Code & CCI Rule 400.4109`

**No 'Rule Code' at all (rare):**
```
R 400.12214 Compliance with 1975 PA 238.
```

## Impact on Parsing

**Current Problem:**
- Parser searches for all instances of text "Rule Code"
- In 6% of reports, this matches BOTH column headers AND actual rules
- Results in ~43% of SIRs (469/1089) having allegation/rule count mismatches

**Root Cause:**
Line 206 in `parse_special_reports.py`:
```python
start_tag = "Rule Code"
```

This simple string search is too broad and catches column headers.

## Recommendations

Parser needs to:
1. Distinguish between column headers and actual rule codes
2. Handle multiple format variations:
   - With/without ampersand
   - With/without abbreviation (CCI, CPA, COF, etc.)
   - With "Rule" or "R" prefix
3. Use regex pattern matching instead of simple string search

Example improved pattern:
```python
# Match actual rule codes, not headers
r"Rule Code\s+(?:&\s+)?(?:[A-Z]{2,4}\s+)?(?:Rule|R)\s+400\.\d+"
```

This would match:
- ✓ "Rule Code & CCI Rule 400.4109"
- ✓ "Rule Code & Rule 400.4131"
- ✓ "Rule Code CCI Rule 400.4118"
- ✓ "Rule Code & R 400.4109"
- ✗ "Rule Code Placement" (header)
- ✗ "Rule Code Sufficiency of staff" (header)
