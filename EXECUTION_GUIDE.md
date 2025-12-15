# How to Execute the SIR Query Script

This document provides step-by-step instructions for running the SIR query script to generate AI summaries and culpability assessments for 50 Special Investigation Reports.

## Prerequisites - Already Complete ✅

All prerequisites are already in place:
- ✅ Python 3.11+ with dependencies installed
- ✅ Parquet files extracted (5 files, 3510 documents)
- ✅ Violations CSV generated (1922 SIRs available)
- ✅ Query script tested and validated (16/16 tests passed)
- ✅ GitHub Actions workflow configured

## Execution Options

### Option 1: GitHub Actions Workflow (Recommended)

This is the easiest way to run the queries with the repository secret:

1. Go to the repository on GitHub
2. Click on the **Actions** tab
3. Select **"Query SIRs with OpenRouter"** from the workflow list
4. Click **"Run workflow"** button
5. Optionally adjust:
   - Number of SIRs (default: 50)
   - Output filename (default: sir_query_results.csv)
6. Click **"Run workflow"** to start

The workflow will:
- Generate violations CSV if needed
- Run queries on the specified number of SIRs
- Upload results as an artifact
- Display a summary of tokens and costs

Download the results artifact from the workflow run page.

### Option 2: Local Execution with Shell Script

#### If you have the repository secret (OPENROUTER_KEY):

```bash
# Set the API key
export OPENROUTER_KEY="sk-or-v1-..."

# Run the script (queries 50 SIRs by default)
./run_sir_queries.sh

# Or specify a custom count
./run_sir_queries.sh 25
```

#### If you have the encryption password:

```bash
# Set the password
export OPENROUTER_PASSWORD="your-secret-password"

# Run the script (will auto-decrypt the key)
./run_sir_queries.sh
```

### Option 3: Direct Python Script

For more control over the execution:

```bash
# Set API key
export OPENROUTER_KEY="sk-or-v1-..."

# Query 50 SIRs (default)
python3 query_sirs.py

# Query only 10 SIRs for testing
python3 query_sirs.py --count 10 --output test_results.csv

# Custom query text
python3 query_sirs.py --query "Summarize the incident and identify responsible parties."

# Verbose output for debugging
python3 query_sirs.py --verbose
```

## Expected Output

The script will generate a CSV file (default: `sir_query_results.csv`) with these columns:

| Column | Description |
|--------|-------------|
| sha256 | Document hash identifier |
| agency_id | Agency license number |
| agency_name | Name of the agency |
| document_title | Document title (e.g., "Special Investigation Report #2019C0114036") |
| date | Report date |
| num_violations | Number of violations found in the report |
| violations_list | List of violated rules |
| query | The query text sent to the AI |
| response | AI-generated response from DeepSeek |
| input_tokens | Number of input tokens used |
| output_tokens | Number of output tokens generated |
| cost | API cost (if provided by OpenRouter) |
| duration_ms | Query duration in milliseconds |

## Expected Runtime and Costs

For 50 SIRs:
- **Runtime**: 4-7 minutes (2-5 seconds per query + 2-second rate limit delay)
- **Input tokens**: ~500k-1M tokens (10k-20k per document)
- **Output tokens**: ~5k-15k tokens (100-300 per response)
- **Estimated cost**: $1-5 USD

Cost breakdown (DeepSeek v3.2 pricing):
- Input: $0.25 per million tokens
- Output: $0.38 per million tokens

## Progress Monitoring

The script provides detailed progress logs:

```
Processing SIR 1/50: aaacc8e6b4d0728c8f67a381f231d909e71d02a103b7965333bc7bd0d04e69fd
Agency: Child Family Services of NE Michigan
Title: Special Investigation Report #2019C0114036
Date: 2019-11-12
Violations: 3
Loading document from parquet...
Document loaded: 9 pages, 11460 characters
Querying OpenRouter API...
Response received:
  Input tokens: 15234
  Output tokens: 287
  Duration: 2.34s
  Cost: $0.004521
  Response preview: This Special Investigation Report details an investigation...
```

## Verification

After execution, verify the results:

```bash
# View first few rows
head -5 sir_query_results.csv

# Count total rows
wc -l sir_query_results.csv

# Check for any errors
grep "ERROR:" sir_query_results.csv

# Calculate total cost (if using jq)
python3 -c "
import pandas as pd
df = pd.read_csv('sir_query_results.csv')
print(f'Total queries: {len(df)}')
print(f'Successful: {len(df[~df[\"response\"].str.startswith(\"ERROR:\", na=False)])}')
print(f'Total input tokens: {df[\"input_tokens\"].sum():,}')
print(f'Total output tokens: {df[\"output_tokens\"].sum():,}')
if df['cost'].notna().any():
    print(f'Total cost: \${df[\"cost\"].sum():.6f}')
"
```

## Troubleshooting

### "OPENROUTER_KEY environment variable not set"
Make sure you've exported the API key before running the script.

### "Violations CSV not found"
The script will auto-generate it if needed, but you can manually run:
```bash
python3 pdf_parsing/parse_parquet_violations.py --parquet-dir pdf_parsing/parquet_files -o violations_output.csv
```

### API Rate Limits
If you hit rate limits, reduce the count:
```bash
python3 query_sirs.py --count 25
```

### Timeout Errors
Large documents may timeout. The script uses a 3-minute timeout per request.

## Next Steps After Execution

1. Review the `sir_query_results.csv` file
2. Analyze the AI responses for patterns
3. Calculate aggregate statistics
4. Share results with stakeholders
5. Archive the results for future reference

## Support

For issues or questions:
1. Check the logs for specific error messages
2. Review [RUN_SIR_QUERY.md](RUN_SIR_QUERY.md) for detailed documentation
3. Open an issue in the repository
