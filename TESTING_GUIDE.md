# Testing Guide: Prompt Caching Verification

## Quick Test Instructions

This guide helps you verify that the prompt caching implementation is working correctly.

## Website Testing

### Prerequisites
- Access to the deployed website
- An OpenRouter API key
- Access to the document with SHA: `0453d1af31428435e3c7626952a4fa5ae530136d03d91680cbc9457a8c024698` (or another large document)

### Steps

1. **Navigate to the document**
   - Open the website
   - Use the SHA lookup feature or find the document in the agency list
   - Click "📄 View Full Document"

2. **Unlock AI queries**
   - Enter the secret password to unlock API access
   - Click "🔓 Unlock"

3. **Submit first query**
   ```
   What are the main findings in this report?
   ```
   - Click "🚀 Submit Query"
   - Wait for the response
   - **Expected**: No cache discount (or $0.00) shown
   - Note the input tokens and cost

4. **Submit second query (within 5 minutes)**
   ```
   Who was involved in this incident?
   ```
   - Click "🚀 Submit Query"
   - Wait for the response
   - **Expected**: Should see `💾 Cache Discount: $X.XXXXXX` where X > 0
   - The cache discount indicates savings from reusing the cached document

5. **Verify in Query History**
   - Scroll down to the "Query History" section
   - Both queries should be listed
   - The second query should show the cache discount

### Success Criteria

✅ First query: No cache discount or $0.00
✅ Second query: Positive cache discount value (e.g., $0.002341)
✅ Cache discount displayed in query result and history
✅ Both queries return correct responses

## Python Script Testing

### Prerequisites
- Python environment set up
- `OPENROUTER_KEY` environment variable set
- Access to parquet files with document data

### Testing update_summaryqueries.py

1. **Run the script with a small count**
   ```bash
   cd pdf_parsing
   export OPENROUTER_KEY="your-api-key"
   python3 update_summaryqueries.py --count 2
   ```

2. **Check the console output**
   Look for these lines in the logs:
   ```
   Response received:
     Input tokens: XXXX
     Output tokens: XXX
     Duration: X.XXs
     Cost: $X.XXXXXX
     Cache Discount: $X.XXXXXX  # <-- This line should appear if caching worked
   ```

3. **Check the CSV output**
   ```bash
   tail -n 2 sir_summaries.csv
   ```
   - Verify the `cache_discount` column exists
   - Check if values are populated (may be empty on first runs, populated on subsequent runs)

### Testing update_violation_levels.py

1. **Run the script**
   ```bash
   cd pdf_parsing
   export OPENROUTER_KEY="your-api-key"
   python3 update_violation_levels.py --max-count 2
   ```

2. **Check logs and CSV**
   - Same verification steps as update_summaryqueries.py
   - Check `sir_violation_levels.csv` for cache_discount column

### Success Criteria

✅ Logs show "Cache Discount: $X.XXXXXX" lines
✅ CSV files have `cache_discount` column
✅ Values are reasonable (typically a fraction of the cost)

## Understanding the Results

### What Cache Discount Means

- **$0.00 or empty**: No caching occurred (first query, or cache expired)
- **Positive value** (e.g., $0.002341): This is the amount saved by reusing cached content
- **Typical savings**: 80-95% on input tokens for cached portions

### Calculating Effective Cost Savings

If you see:
- Cost: $0.003000
- Cache Discount: $0.002500

Then:
- Effective cost paid: $0.000500 ($0.003000 - $0.002500)
- Savings: 83% on this query

### Factors Affecting Caching

1. **Document Size**: Larger documents = more savings
2. **Time Between Queries**: Caches expire after ~5-10 minutes
3. **Exact Match**: Any change to the document invalidates cache
4. **Provider Support**: Not all models support caching equally

## Troubleshooting

### Cache Discount Always $0.00

**Possible causes:**
1. Waiting too long between queries (cache expired)
2. Document text changed between queries
3. Model/provider doesn't support caching
4. First query for this document

**Solutions:**
- Submit queries quickly (within 5 minutes)
- Ensure document text is identical
- Check OpenRouter documentation for model support

### Cache Discount Not Showing in UI

**Possible causes:**
1. Using old version of the code
2. Browser cached old JavaScript
3. IndexedDB not upgraded

**Solutions:**
- Hard refresh browser (Ctrl+Shift+R)
- Clear browser cache
- Check browser console for errors

### CSV Missing cache_discount Column

**Possible causes:**
1. Using old version of script
2. Reading old CSV file

**Solutions:**
- Pull latest code changes
- Check file modification date
- Create new CSV file by renaming old one

## Expected Benchmark

For the large document (SHA: 0453d1af31428435e3c7626952a4fa5ae530136d03d91680cbc9457a8c024698):

- Document length: ~10,000+ characters
- First query cost: ~$0.003-0.005
- Second query cost: ~$0.0005-0.001
- Expected savings: 70-90%

This demonstrates the potential 10x cost reduction mentioned in the problem statement.

## Reporting Results

When reporting your findings, please include:

1. Document SHA tested
2. Document size (character count)
3. Number of queries submitted
4. Cache discount values observed
5. Total cost vs total with cache
6. Any issues encountered

Example:
```
Document: 0453d1af31428435e3c7626952a4fa5ae530136d03d91680cbc9457a8c024698
Size: 12,543 characters
Queries: 3
Cache discounts: $0.00, $0.002341, $0.002298
Total cost: $0.004123
Cost without cache: $0.008762
Savings: 53% (or 2.1x)
```
