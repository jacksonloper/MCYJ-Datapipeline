# FOM (Field Operations Manual) Format Analysis

## What is FOM?

**FOM** = **Field Operations Manual** - Michigan DHHS policy manual for child welfare casework operations.

## When is FOM Used Instead of Administrative Rules?

### Usage by License Type

| License Type | Description | Total SIRs | With FOM | % with FOM |
|--------------|-------------|-----------|----------|-----------|
| **CB** | Child Placing Agency, Private | 388 | 61 | **15.7%** |
| **CP** | Child Placing Agency, FIA/Government | 61 | 6 | **9.8%** |
| **CI** | Child Caring Institution, Private | 931 | 5 | **0.5%** |
| **Total** | | 1,708 | 72 | **4.2%** |

**Key Finding:** FOM is primarily used for **Child Placing Agencies** (both private and government).

## Why Two Different Reference Systems?

Based on document analysis:

### 1. Administrative Rules (Rule 400.xxx)
- **Used for:** Facility operations, physical environment, staff qualifications, resident care
- **Examples:**
  - Rule 400.4109 - Program Statement
  - Rule 400.4126 - Sufficiency of staff
  - Rule 400.4159 - Youth restraint
- **Who must follow:** All licensed facilities (institutions, group homes, agencies)
- **Enforcement:** Michigan licensing regulations

### 2. FOM References (FOM xxx-xx)
- **Used for:** Casework practice, foster care procedures, child welfare operations
- **Examples:**
  - FOM 722-03D - Placement Change
  - FOM 722-06B - Family Team Meeting
  - FOM 722-08E - Foster Care/Juvenile Justice Action Summary
- **Who must follow:** DHHS caseworkers and contracted child placing agencies
- **Enforcement:** DHHS contract requirements and MISEP (Michigan Interstate System for Education of Parents? - needs verification)

## Document Structure Differences

### Documents with Rule 400.xxx
```
APPLICABLE RULE
R 400.4159 Youth restraint...
(description of rule)
```

### Documents with FOM
```
APPLICABLE RULE
FOM 722-03D Placement Change
Page 2
When a caseworker suspects a child in foster care...
(description of policy)
```

## Parser Impact

### Current Implementation
- Pattern: `(?:R\s+)?(\d{3}\.\d+)` matches "400.4109"
- **Does NOT match:** FOM format with dash "722-03D"

### Issue
- 72 SIRs (4.2% of total) use FOM format
- Current parser extracts **0 rules** from these documents
- Should extract FOM references as valid rule codes

### Proposed Fix
Update `_extract_applicable_rule_format()` pattern to:
```python
rule_match = re.search(r"(?:R\s+)?(\d{3}\.\d+)|FOM\s+(\d+-\d+[A-Z]?)", text[i:e])
```

This would capture both:
- `400.4159` (administrative rules)
- `722-03D` (FOM policy references)

## Examples from Documents

### FOM 722-03D - Placement Change
```
The caregiver must be notified of the intent to move the child 14 days
prior to the intended date of the move unless the child's health or safety
is jeopardized. The DHS-30, Foster Parent/Caregiver Notification of Move,
must be used to notify the caregiver of the intent to move the child.
```

### FOM 722-06B - Family Team Meeting
```
Following the FTM, the caseworker is responsible for the following:
• Completing the DHS-1105, Family Team Meeting Report
• Providing the DHS-1105 to all participants
```

### FOM 722-08E - Foster Care/Juvenile Justice Action Summary
```
Three days prior to a planned placement change, or within three business
days of an emergency placement change, the caseworker must document...
```

## Summary

FOM represents DHHS field operations policies that govern **how caseworkers conduct their work**, while Rule 400.xxx represents licensing regulations that govern **how facilities operate**.

Child Placing Agencies are evaluated against both:
1. Licensing rules (for agency operations)
2. FOM policies (for casework practice)

This explains why ~16% of Child Placing Agency SIRs use FOM format instead of Rule 400.xxx format.
