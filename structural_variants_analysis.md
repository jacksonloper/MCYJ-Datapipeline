# SIR Document Structural Variants Analysis

Analysis of 1,708 Special Investigation Report documents to identify structural diversity.

**CORRECTED VERSION** - Original analysis had regex bug that missed "II. ALLEGATION(S)" due to parentheses.

## Summary Statistics

- **Total SIR documents**: 1,708
- **Unique structural patterns**: 18
- **Section III variants**:
  - 63.8% use "III. INVESTIGATION"
  - 35.2% use "III. METHODOLOGY"
  - 0.6% use "III. RECOMMENDATION(S)" (numbering errors)

## Major Structure Types (91.2% of documents)

### Structure Type A: Methodology with Embedded Allegation (63.6% - 1,086 documents)

```
I. IDENTIFYING INFORMATION
   └─ Contains allegation as embedded field (not separate section)
II. METHODOLOGY
III. INVESTIGATION
    └─ Contains rules in various formats
IV. RECOMMENDATION(S)
```

**Key characteristic**: Allegation appears as a labeled field within Section I, not as a separate Roman numeral section.

**Example SHA**: 61d8519dc19bc955...

**Where allegation appears** (embedded table in Section I):
```
Violation | Potential Rule | Violation Type | Allegation
--------- | -------------- | -------------- | ----------
...       | ...           | ...            | The agency did not provide...
```

---

### Structure Type B: Dedicated Allegation Section (27.6% - 471 documents)

```
I. IDENTIFYING INFORMATION
II. ALLEGATION(S)
    └─ Full section dedicated to allegations
III. METHODOLOGY
     └─ Contains nested INVESTIGATION subsection with rules
IV. RECOMMENDATION(S)
```

**Key characteristic**: Has separate "II. ALLEGATION(S)" section as a major heading.

**Example SHA**: 81f8c85b18909108... (the "Structure C" example)

**This is the SECOND most common format**, not a rare variant!

---

### Structure Type C: No Identifying Section (5.3% - 91 documents)

```
II. ALLEGATION(S)
III. METHODOLOGY
     └─ Contains rules
IV. RECOMMENDATION(S)
```

**Key characteristic**: No Section I, starts directly with II. ALLEGATION(S).

---

## Minor Structures (< 2% each)

### Skip Section II (1.2% - 21 documents)

```
I. IDENTIFYING INFORMATION
III. METHODOLOGY
     └─ Contains rules
IV. RECOMMENDATION(S)
```

**Key characteristic**: Jumps from Section I to Section III, skipping II entirely.

---

### No Section IV (0.5% - 8 documents)

```
I. IDENTIFYING INFORMATION
II. METHODOLOGY
     └─ Contains rules
III. RECOMMENDATION(S)
```

**Key characteristic**: Recommendations in Section III instead of IV. Rules must be in Section II.

**Example SHA**: b918cea3f07452e9...

---

## Unusual/Malformed Structures (< 1% each)

### Incorrect Section Numbering

**Example: Duplicate "II"** (2 documents)
```
I. IDENTIFYING INFORMATION
II. METHODOLOGY
III. INVESTIGATION
II. RECOMMENDATION(S)  ← Should be IV, not II
```
**Example SHA**: 5d387d05aca76d90...

---

**Example: Skip to VI** (1 document)
```
I. IDENTIFYING INFORMATION
III. METHODOLOGY  ← Skips II
VI. RECOMMENDATION(S)  ← Skips IV and V
```
**Example SHA**: 09633cdf2816cc29...

---

### Incomplete Documents

**Only Section IV** (1 document)
```
IV. RECOMMENDATION(S)
```
**Example SHA**: b99675606945d708... (likely truncated/corrupted)

**Only Section I** (1 document)
```
I. IDENTIFYING INFORMATION
```
**Example SHA**: 1e9bec398a9a33e3... (likely truncated/corrupted)

---

## Parser Implications

### What the Parser Actually Does

The current parser is **location-based**, not structure-based:

1. **For allegation extraction**: Searches for "Allegation:" label anywhere in document (Section I embedded field or Section II dedicated section)

2. **For rule extraction**:
   - Detects if "II. METHODOLOGY" exists without "III. INVESTIGATION"
     - If yes → Search Section II for rules
     - If no → Search Section III for rules (regardless of whether it says INVESTIGATION or METHODOLOGY)

### Why This Works for Most Cases

- **Types 1-4** (97.6%): Rules in Section III → Parser finds them
- **Type 5** (0.7%): Rules in Section II, no Section III → Parser correctly routes to Section II
- **Malformed** (<1%): May fail, but too rare to impact overall accuracy

### Current Blind Spots

1. **Documents with only Section IV** (b99675606945d708): No rules extracted (incomplete document anyway)
2. **Documents with duplicate numbering** (5d387d05aca76d90): May confuse section detection
3. **Documents skipping to VI** (09633cdf2816cc29): Regex may not handle Roman numeral gaps

## Recommendations

1. **Current approach is sound**: The location-based logic (Section II vs III) handles 99%+ of structural variance

2. **Don't over-engineer**: The 16 unique structures mostly differ in section numbering/labels, not content location

3. **Focus on content patterns**: More variance exists in rule format (Rule 400.xxx vs FOM) than in structure

4. **Document edge cases**: The malformed documents (<1%) should be noted but not drive parser design

## Key Insights

1. **Two main structures** account for 91.2% of documents:
   - **Type A (63.6%)**: Allegation embedded in Section I, "II. METHODOLOGY", "III. INVESTIGATION"
   - **Type B (27.6%)**: Dedicated "II. ALLEGATION(S)" section, "III. METHODOLOGY" with nested INVESTIGATION

2. **Initial regex bug** in analysis script:
   - Pattern `[A-Z\s]+?` missed parentheses in "II. ALLEGATION(S)"
   - This caused massive undercounting of Type B structures (27.6% actual vs 2.3% initially reported)
   - Fixed by adding parentheses to pattern: `[A-Z\s\(\)\-/]+?`

3. **Parser resilience**: The parser correctly handles both major structures by:
   - Searching for "Allegation:" label anywhere (handles both embedded and dedicated sections)
   - Using location logic (Section II vs III) for rule extraction, not rigid structure assumptions

4. **Section III variance**:
   - 63.8% use "III. INVESTIGATION"
   - 35.2% use "III. METHODOLOGY"
   - Parser handles both by searching Section III regardless of label

The structural diversity is real (18 unique patterns), but the parser's flexible label-based approach makes it resilient to most variants.
