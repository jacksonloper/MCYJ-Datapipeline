# Section Structure Variations in Special Investigation Reports

## Investigation Summary

Analyzed 300+ Special Investigation Reports to document section header inconsistencies.

## Key Findings

### Two Completely Different Document Structures

#### Structure A: Standard (Most Common ~97%)
```
I. IDENTIFYING INFORMATION
II. ALLEGATION(S) / ALLEGATIONS / ALLEGATION
III. METHODOLOGY
IV. RECOMMENDATION
```

Within Section III (METHODOLOGY), contains subsections like:
- Rule Code & CCI Rule 400.xxxx
- Allegation
- Investigation
- Analysis
- Conclusion

#### Structure B: Alternate (~3%)
```
I. IDENTIFYING INFORMATION
II. METHODOLOGY
III. RECOMMENDATION
```

Within Section II (METHODOLOGY), contains:
- Contact log with dates
- ALLEGATION:
- INVESTIGATION:
- APPLICABLE RULE (instead of "Rule Code")
- CONCLUSION:

**Example:** SHA256 b918cea3f07452e9...

### Section II Variations (in Structure A)

Found multiple text variations for the same section:
- "II. ALLEGATION(S)" (most common)
- "II. ALLEGATIONS"
- "II. ALLEGATION"
- "II. ALLEGATION:"
- "II. ALLEGATION(S):"

Note: Some documents have "II. METHODOLOGY" but these are **Structure B** documents with completely different format.

### Roman Numeral Inconsistencies

Found rare cases with:
- Lowercase "lll" instead of "III"
- Arabic numerals "3" or "4" instead of "III" or "IV"

However, these are very rare (< 1%).

## Impact on Parsing

### Critical Issues

1. **get_rule_codes() assumes Section III contains rules**
   - Line 197: `match = re.search(r"(?:III|lll)(.*)", text, flags=re.DOTALL)`
   - Searches for text AFTER "III"
   - In Structure B, "III" is RECOMMENDATION section, not METHODOLOGY
   - The rules are in Section II, so they're missed

2. **"APPLICABLE RULE" vs "Rule Code" patterns**
   - Structure A uses: "Rule Code & CCI Rule 400.xxxx"
   - Structure B uses: "APPLICABLE RULE" followed by rule text
   - Parser checks for "applicable rule" but only AFTER finding "III"
   - In Structure B, "applicable rule" is in Section II, before "III"

3. **Section delimiter assumptions**
   - Parser uses "IV." to delimit end of Section III
   - In Structure B, uses "III." to delimit end of Section II
   - This works, but the rule extraction logic fails

### Example Structure B Document

SHA256: b918cea3f07452e9...
- Investigation #: 2022C0420017
- Has 3 allegations (correctly extracted)
- Has 0 rules extracted (WRONG - should have ~3 rules)
- Uses "APPLICABLE RULE" format in Section II
- No "III. INVESTIGATION" section exists

## Recommendations

1. **Detect document structure early**
   - Check if "II. METHODOLOGY" exists
   - If yes → Structure B, search for rules in Section II
   - If no → Structure A, search for rules in Section III

2. **Update get_rule_codes() to handle both structures**
   ```python
   # Pseudo-code
   if has_section_II_methodology(text):
       # Structure B: search in Section II
       section_text = extract_section_II(text)
   else:
       # Structure A: search in Section III
       section_text = extract_section_III(text)
   ```

3. **Handle "APPLICABLE RULE" format properly**
   - Currently checks for "applicable rule" in lowercase
   - But only searches after "III"
   - Should search in the correct section based on structure

4. **Make section extraction more robust**
   - Handle variations: "ALLEGATION" vs "ALLEGATIONS" vs "ALLEGATION(S)"
   - Handle optional colons after section names
   - Handle rare lowercase "lll" or numeric "3", "4"
