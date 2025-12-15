# Running AI Queries on Special Investigation Reports (SIRs)

This guide explains how to run AI queries on 50 Special Investigation Reports using the OpenRouter API.

## Prerequisites

1. **Python 3.11+** with dependencies installed:
   ```bash
   pip install -e .
   ```

2. **OpenRouter API Key**: You need access to the `OPENROUTER_KEY` repository secret or your own API key from [OpenRouter](https://openrouter.ai/).

3. **Parquet Files**: Ensure PDF text has been extracted to parquet files:
   ```bash
   python3 pdf_parsing/extract_pdf_text.py --pdf-dir Downloads --parquet-dir pdf_parsing/parquet_files
   ```

4. **Violations CSV**: Generate the violations CSV if not already present:
   ```bash
   python3 pdf_parsing/parse_parquet_violations.py --parquet-dir pdf_parsing/parquet_files -o violations_output.csv
   ```

## Running the Query Script

### Method 1: Using Repository Secret (For repository maintainers)

If you have access to the repository secret OPENROUTER_KEY:

```bash
# Set the API key from the repository secret
export OPENROUTER_KEY="your-openrouter-api-key"

# Run the query script (queries 50 SIRs by default)
python3 query_sirs.py
```

Or use the convenience script:
```bash
export OPENROUTER_KEY="your-openrouter-api-key"
./run_sir_queries.sh
```

### Method 2: Using Encrypted Key with Password (For authorized users)

If you have the password to decrypt the encrypted key stored in the repository:

```bash
# Set the password
export OPENROUTER_PASSWORD="your-secret-password"

# Run with the convenience script (it will auto-decrypt)
./run_sir_queries.sh
```

Or decrypt and use manually:
```bash
# Install cryptography library if needed
pip install cryptography

# Decrypt the key
export OPENROUTER_KEY=$(python3 decrypt_api_key.py --password "your-secret-password")

# Run the query script
python3 query_sirs.py
```

### Method 3: Using Your Own API Key

If you have your own OpenRouter API key:

```bash
# Set your API key
export OPENROUTER_KEY="your-openrouter-api-key"

# Run the query script
python3 query_sirs.py
```

### Method 4: Custom Configuration

You can customize various parameters:

```bash
# Query only 10 SIRs for testing
python3 query_sirs.py --count 10 --output test_results.csv

# Use a custom query
python3 query_sirs.py --query "What violations occurred and who was responsible?"

# Verbose output for debugging
python3 query_sirs.py --verbose

# Custom paths
python3 query_sirs.py \
  --violations-csv custom_violations.csv \
  --parquet-dir custom_parquets/ \
  --output custom_results.csv
```

## Output

The script generates a CSV file (`sir_query_results.csv` by default) with the following columns:

- `sha256`: Document hash identifier
- `agency_id`: Agency license number
- `agency_name`: Name of the agency
- `document_title`: Document title (e.g., "Special Investigation Report #2019C0114036")
- `date`: Report date
- `num_violations`: Number of violations found
- `violations_list`: List of violations
- `query`: The query text sent to the API
- `response`: AI response from DeepSeek
- `input_tokens`: Number of input tokens used
- `output_tokens`: Number of output tokens generated
- `cost`: API cost (if provided by OpenRouter)
- `duration_ms`: Query duration in milliseconds

## Query Details

- **Model**: DeepSeek v3.2 via OpenRouter (`deepseek/deepseek-v3.2`)
- **Query Text**: "Explain what went down here, in a few sentences. In one extra sentence, weigh in on culpability."
- **Document Format**: The query is concatenated with the full document text (all pages joined with `\n\n`)
- **Rate Limiting**: The script includes a 2-second delay between queries to avoid rate limits

## Example Output

```csv
sha256,agency_id,agency_name,document_title,date,num_violations,violations_list,query,response,input_tokens,output_tokens,cost,duration_ms
aaacc8e6b4d0728c8f67a381f231d909e71d02a103b7965333bc7bd0d04e69fd,CB040201041,Child Family Services of NE Michigan,Special Investigation Report #2019C0114036,2019-11-12,3,"R 400.9403(1); R 400.9407(3); R 400.9407(5)(b)","Explain what went down here, in a few sentences. In one extra sentence, weigh in on culpability.","This Special Investigation Report details an investigation into allegations...",15234,287,0.004521,2341
```

## Notes

- The script randomly samples 50 SIRs from all available SIRs (1922 total as of the latest data)
- Each query typically takes 2-5 seconds plus the 2-second rate limit delay
- Total execution time for 50 queries: approximately 4-7 minutes
- The script handles errors gracefully and continues processing remaining documents
- All results are logged to console with detailed progress information

## Troubleshooting

### "OPENROUTER_KEY environment variable not set"
Make sure you've exported the API key before running the script.

### "Violations CSV not found"
Run the violations parser first:
```bash
python3 pdf_parsing/parse_parquet_violations.py --parquet-dir pdf_parsing/parquet_files -o violations_output.csv
```

### "No module named 'pandas'"
Install the dependencies:
```bash
pip install -e .
```

### API Rate Limits
If you hit rate limits, the script will log the error. You can:
- Reduce the count: `python3 query_sirs.py --count 25`
- Increase the delay between queries (modify `time.sleep(2)` in the script)

## Cost Estimation

Based on DeepSeek v3.2 pricing via OpenRouter:
- Input: ~$0.25 per million tokens
- Output: ~$0.38 per million tokens

For 50 SIRs with average document size:
- Estimated total cost: $1-5 (depends on document length and response length)
- Per-document cost: ~$0.02-0.10

The actual cost is returned in the output CSV if provided by OpenRouter.
