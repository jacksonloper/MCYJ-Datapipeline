# Remaining Mismatch Analysis After Parser Rewrite

## Summary

After rewriting the parser, allegation/rule mismatches reduced from **469 (43%)** to **77 (7%)**.

Analyzed the remaining 77 mismatches to understand root causes.

## Categories of Remaining Mismatches

### 1. FOM Format (~1.2% of all SIRs)
**Example:** SHA256 ecea03a1d22844c9...

**Issue:**
- Documents use "FOM" (Field Operations Manual) format instead of Rule 400.xxx
- Format: "FOM 722-03D" instead of "R 400.12404"
- Current parser pattern looks for `\d{3}\.\d+` (3 digits, dot, digits)
- FOM format uses dash: `\d+-\d+[A-Z]?` (digits, dash, digits, optional letter)

**Impact:**
- ~21 SIRs out of 1,708 (1.2%)
- Parser extracts 0 rules when it should extract multiple

**Solution:**
Update `_extract_applicable_rule_format()` to also match FOM pattern:
```python
rule_match = re.search(r"(?:R\s+)?(\d{3}\.\d+|FOM\s+\d+-\d+[A-Z]?)", text[i:e])
```

### 2. Legitimate Multiple Rules per Allegation
**Example:** SHA256 81f8c85b18909108... (1 allegation, 3 rules)

**Not a Bug:**
- Single allegation about "unwarranted prone restraint"
- Violates 3 different restraint rules: 400.4160, 400.4159, 400.4161
- This is legitimate - one allegation can violate multiple rules

**Impact:**
- Unknown percentage of remaining mismatches
- These are NOT parser errors

### 3. Legitimate Fewer Rules than Allegations
**Hypothesis:**
- Some allegations may not have associated rule violations
- Allegations found "Not Established" may not have rules listed
- Multiple allegations may share the same rule

**Impact:**
- Unknown percentage
- Need more investigation to confirm

### 4. Unknown/Other
**Examples:**
- SHA256 adbbf0431a816c7d... (4 allegations, 2 rules)
- SHA256 da708626667f6a29... (1 allegation, 0 rules - likely FOM)

**Need Investigation:**
- Some may be additional format variations
- Some may be legitimate mismatches
- Some may be parser bugs we haven't identified

## Format Distribution Across Full Dataset

Based on analysis of 1,708 SIRs:

| Format | Count | Percentage | Parser Support |
|--------|-------|------------|----------------|
| Rule Code & <ABBREV> Rule 400.xxx | 1,181 | 69.1% | ✓ Fixed |
| APPLICABLE RULE with 400.xxx | 467 | 27.3% | ✓ Supported |
| Other/No rules | 39 | 2.3% | Various issues |
| APPLICABLE RULE with FOM | 21 | 1.2% | ✗ Not supported |

## Recommendations

### High Priority
1. **Add FOM format support** (~1.2% of SIRs)
   - Update regex pattern in `_extract_applicable_rule_format()`
   - Test against FOM test cases

### Medium Priority
2. **Document legitimate mismatch scenarios**
   - Create guidance for users on why allegation ≠ rule count
   - Add metadata field indicating "legitimate mismatch" vs "parser issue"

### Low Priority
3. **Investigate remaining edge cases**
   - Manually review sample of remaining 77 mismatches
   - Identify any additional format variations
   - Document patterns for future improvements

## Test Cases Added

Added 4 new test cases to `testcases.csv`:
- ecea03a1d22844c9... - FOM format (0 rules extracted, should be 4)
- 81f8c85b18909108... - Legitimate: 1 allegation violating 3 rules
- adbbf0431a816c7d... - Needs investigation: 4 allegations, 2 rules
- da708626667f6a29... - Likely FOM format: 1 allegation, 0 rules

Total test cases: 18
