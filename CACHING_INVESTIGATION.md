# OpenRouter Prompt Caching Investigation

## Overview

This document describes the implementation of prompt caching optimization for OpenRouter API queries to reduce costs when making multiple queries about the same document.

## Background

OpenRouter and some underlying LLM providers (like Anthropic) support **prompt caching**, which allows them to cache portions of the prompt that are repeated across multiple API calls. When the same prefix is sent in subsequent requests, the cached portion can be reused, significantly reducing input token costs.

The hypothesis was that by structuring queries so that the document text is a common prefix across all queries about that document, we could achieve substantial cost savings (potentially up to 10x according to the problem statement).

## Implementation

### Changes Made

1. **Query Format Update**
   - **Before**: `{query}\n\n{document_text}`
   - **After**: `Consider the following document.\n\n{document_text}\n\n{query}`
   
   By putting the document text first with a common prefix ("Consider the following document."), all queries about the same document will share the same prefix, enabling prompt caching.

2. **Cache Discount Tracking**
   - Added extraction of `cache_discount` field from OpenRouter API responses
   - Updated data models to store cache discount information:
     - Website: IndexedDB schema (bumped to v2)
     - Python scripts: Added `cache_discount` column to CSV outputs
   - Added display of cache discount in all UI components

3. **Files Modified**
   - `website/src/apiService.js`: Updated query format and added cache_discount extraction
   - `website/src/indexedDB.js`: Bumped DB version and added cache_discount field
   - `website/src/main.js`: Updated to display cache_discount in query results
   - `pdf_parsing/update_summaryqueries.py`: Updated query format and CSV schema
   - `pdf_parsing/update_violation_levels.py`: Updated query template and CSV schema

## How to Verify Caching Works

### Using the Website

1. Open a document with substantial text (e.g., SHA: `0453d1af31428435e3c7626952a4fa5ae530136d03d91680cbc9457a8c024698`)
2. Unlock AI queries with your API key
3. Submit your first query - this will **not** have cache discount (first time document is sent)
4. Submit a second query about the same document
5. Check the response metadata - you should see:
   - `💾 Cache Discount: $X.XXXXXX` (if caching worked)
   - The cache discount value indicates the cost savings from reusing the cached document

### Using Python Scripts

When running `update_summaryqueries.py` or `update_violation_levels.py`:

```bash
cd pdf_parsing
export OPENROUTER_KEY="your-api-key"
python3 update_summaryqueries.py --count 2
```

Look for the log output:
```
Response received:
  Input tokens: XXXX
  Output tokens: XXX
  Duration: X.XXs
  Cost: $X.XXXXXX
  Cache Discount: $X.XXXXXX  # <-- This line indicates caching savings
```

The CSV output files (`sir_summaries.csv`, `sir_violation_levels.csv`) will now include a `cache_discount` column showing the savings for each query.

## Expected Results

### First Query
- No cache discount (or $0.00)
- Full input token cost

### Subsequent Queries
- Positive cache discount value
- Reduced effective input token cost
- The discount represents the savings from not having to re-process the document text

## Important Notes

1. **Cache Duration**: Caches typically last for a limited time (5-10 minutes). If you wait too long between queries, the cache may expire.

2. **Exact Matching**: The cache key is based on the exact prompt text. Any change to the document portion will invalidate the cache.

3. **Provider Support**: Not all models/providers support prompt caching. DeepSeek v3.2 (the model used in this project) should support it through OpenRouter.

4. **Cost Savings**: The actual savings depend on:
   - Document size (larger documents = more savings)
   - Number of queries per document
   - Cache hit rate

## Testing Recommendations

To properly test caching effectiveness:

1. **Choose a large document** (10,000+ characters) like the one mentioned: `0453d1af31428435e3c7626952a4fa5ae530136d03d91680cbc9457a8c024698`

2. **Make multiple queries quickly** (within 5 minutes of each other) to ensure cache is still valid

3. **Monitor the cache_discount field** in responses to confirm caching is working

4. **Calculate actual savings**:
   - Compare costs with and without cache discount
   - Document shows approximately what factor of savings you're achieving

## Future Enhancements

Potential improvements to consider:

1. Add aggregate statistics showing total cache savings over time
2. Implement retry logic with exponential backoff if cache expires
3. Add warnings if cache_discount is unexpectedly zero on subsequent queries
4. Document which models/providers support caching best

## References

- OpenRouter API Documentation: https://openrouter.ai/docs
- Anthropic Prompt Caching: https://docs.anthropic.com/claude/docs/prompt-caching
