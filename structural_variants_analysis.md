# SIR Document Structural Variants Analysis

Analysis of 1,708 Special Investigation Report documents to identify structural diversity.

## Summary Statistics

- **Total SIR documents**: 1,708
- **Unique structural patterns**: 16
- **Section III variants**:
  - 63.8% use "III. INVESTIGATION"
  - 35.2% use "III. METHODOLOGY"
  - 0.6% use "III. RECOMMENDATION(S)" (numbering errors)

## Major Structure Types

### Structure Type 1: Standard Format (63.6% - 1,086 documents)

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

**Where allegation appears**:
```
Violation | Potential Rule | Violation Type | Allegation
--------- | -------------- | -------------- | ----------
...       | ...           | ...            | The agency did not provide...
```

---

### Structure Type 2: No Section II (26.5% - 453 documents)

```
I. IDENTIFYING INFORMATION
   └─ Contains allegation as embedded field
III. METHODOLOGY
     └─ Contains rules
IV. RECOMMENDATION(S)
```

**Key characteristic**: Skips Section II entirely, jumps from I to III.

---

### Structure Type 3: Minimal Header (5.2% - 88 documents)

```
III. METHODOLOGY
     └─ Contains rules
IV. RECOMMENDATION(S)
```

**Key characteristic**: No Section I or II, starts directly with III.

---

### Structure Type 4: Dedicated Allegation Section (2.3% - 39 documents)

```
I. IDENTIFYING INFORMATION
II. ALLEGATION(S)
    └─ Full section dedicated to allegations
III. METHODOLOGY
     └─ Contains nested INVESTIGATION subsection with rules
IV. RECOMMENDATION(S)
```

**Key characteristic**: Has separate "II. ALLEGATION(S)" section, not just embedded field.

**Example SHA**: 81f8c85b18909108... (previously called "Structure C")

**This is the minority format!** Only 2.3% of documents use this structure.

---

### Structure Type 5: Classic Investigation Section (0.7% - 10 documents)

```
I. IDENTIFYING INFORMATION
II. METHODOLOGY
III. RECOMMENDATION(S)
```

**Key characteristic**: No Section IV, recommendations are in Section III. Rules must be in Section II.

**Example SHA**: b918cea3f07452e9... (previously called "Structure B")

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

## Key Insight

**Original assumption was wrong**: We thought "Structure A" (I → II. ALLEGATION → III. INVESTIGATION → IV) was standard, but actually:
- Only **2.3%** have dedicated "II. ALLEGATION(S)" section
- **63.6%** embed allegations in Section I as labeled fields
- The parser correctly handles both by searching for "Allegation:" label anywhere

The structure diversity is real, but the parser's flexible approach (search by label, not by section number) makes it resilient to most variants.
