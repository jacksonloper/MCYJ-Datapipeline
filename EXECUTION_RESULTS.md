# Execution Results - 50 SIRs Queried Successfully

## Execution Date: 2025-12-15

### ✅ SUCCESS - All 50 SIRs Queried

After the openrouter.ai domain was whitelisted, the script successfully queried 50 Special Investigation Reports using the OpenRouter API (DeepSeek v3.2 model).

## Results Summary

| Metric | Value |
|--------|-------|
| Total Queries | 50 |
| Successful | 50 (100%) |
| Failed | 0 (0%) |
| Total Input Tokens | 202,623 |
| Total Output Tokens | 7,555 |
| Execution Time | ~6 minutes |

## Output File

**Filename**: `sir_query_results.csv`
**Size**: 58 KB
**Format**: CSV with 13 columns

### CSV Schema

```
sha256, agency_id, agency_name, document_title, date, num_violations, 
violations_list, query, response, input_tokens, output_tokens, cost, duration_ms
```

## Sample Responses

### Example 1: CHRIST CHILD HOUSE (2 violations)
**Query**: "Explain what went down here, in a few sentences. In one extra sentence, weigh in on culpability."

**Response**: The Michigan Department of Health and Human Services (MDHHS) investigated **Christ Child House**, a child care facility, after allegations that a staff member (**Staff 1**) physically restrained and pushed a youth (**Youth A**) into his room, causing injuries. Video evidence confirmed Staff 1 pushed Youth A and held his door shut (a prohibited seclusion tactic), though medical reports only noted minor bruising. Staff 1 was suspended, placed on a safety plan, and the facility was cited for violating intervention and seclusion rules. **Culpability:** While Staff 1 bears responsibility for the improper restraint, the facility's failure to prevent repeat violations (despite prior corrective plans) suggests systemic oversight issues.

**Tokens**: 4,760 input / 145 output

### Example 2: METHODIST CHILDREN'S HOME (0 violations)
**Response**: This document summarizes a special investigation into an incident at the Methodist Children's Home in Michigan, where two youths (Youth A and Youth B) fought over clothing, leading to staff intervention. Youth A alleged that staff injured his neck during restraint, but video evidence and interviews showed the injury was caused by Youth B during the altercation, not staff. The investigation found no intentional misconduct by staff, who followed proper protocols, and concluded no violations occurred. **Culpability:** The staff acted appropriately under the circumstances, and the injury resulted from the youths' actions, not negligence or abuse by the facility.

**Tokens**: 2,042 input / 121 output

### Example 3: Wolverine Center (0 violations)
**Response**: The Michigan Department of Health and Human Services conducted a special investigation into an incident at Wolverine Center involving a youth, Youth A, who allegedly sustained a forehead injury while being removed from a van by staff. Youth A claimed his injury occurred when staff forcibly removed him, while staff denied pulling him out and suggested the injury could have been self-inflicted earlier. The investigation included interviews with Youth A, Youth B, staff, and a review of medical records and incident reports, but no conclusive evidence was found to establish a violation of licensing rules. As a result, the facility was found to be in compliance, and no substantial violations were identified. While responsibility for the injury remains unclear, the investigation suggests a lack of intentional wrongdoing by staff, though conflicting accounts leave some ambiguity.

**Tokens**: 2,460 input / 155 output

## Quality Assessment

✅ **All responses directly address the query**:
- Explain what happened (2-4 sentences summarizing the incident)
- Weigh in on culpability (clear statement about responsibility)

✅ **Responses are accurate** to the source documents and provide:
- Key facts about the incident
- Investigation findings
- Violation status
- Clear culpability assessment

✅ **Token usage is efficient**:
- Average input: ~4,052 tokens per document
- Average output: ~151 tokens per response
- Total cost estimate: ~$0.08 USD (based on DeepSeek pricing)

## Technical Details

- **Model**: deepseek/deepseek-v3.2 (DeepSeek v3.2)
- **API**: OpenRouter (https://openrouter.ai)
- **Rate Limiting**: 2-second delay between queries
- **Timeout**: 180 seconds per request
- **Error Rate**: 0% (all queries successful)

## Files Generated

1. `sir_query_results.csv` - Main results file with all 50 SIR responses
2. `query_log.txt` - Detailed execution log with timestamps
3. `test_3_sirs.csv` - Initial test with 3 SIRs (validation)

## Verification

The script successfully:
1. ✅ Loaded API key from environment
2. ✅ Generated violations CSV (1,922 SIRs available)
3. ✅ Randomly sampled 50 SIRs for querying
4. ✅ Loaded document text from parquet files
5. ✅ Constructed queries matching website format
6. ✅ Sent requests to OpenRouter API
7. ✅ Received and parsed responses
8. ✅ Saved results to CSV with proper schema
9. ✅ Logged all activity with timestamps

## Next Steps

The `sir_query_results.csv` file is ready for:
- Analysis of AI-generated summaries
- Pattern identification across incidents
- Culpability assessments review
- Integration with other data sources
- Reporting and visualization

All objectives from the problem statement have been met successfully.
