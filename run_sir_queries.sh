#!/bin/bash
# Quick script to run SIR queries with the OpenRouter API
# Usage: ./run_sir_queries.sh [number_of_sirs]

set -e

# Configuration
COUNT=${1:-50}
OUTPUT="sir_query_results.csv"
PARQUET_DIR="pdf_parsing/parquet_files"
VIOLATIONS_CSV="violations_output.csv"

echo "========================================"
echo "SIR Query Runner"
echo "========================================"
echo ""

# Check for API key or decrypt from password
if [ -z "$OPENROUTER_KEY" ]; then
    if [ ! -z "$OPENROUTER_PASSWORD" ]; then
        echo "Decrypting API key with password..."
        # Install cryptography if needed
        pip install -q cryptography 2>/dev/null || true
        export OPENROUTER_KEY=$(python3 decrypt_api_key.py --password "$OPENROUTER_PASSWORD")
        if [ $? -ne 0 ]; then
            echo "ERROR: Failed to decrypt API key"
            exit 1
        fi
        echo "✓ API key decrypted successfully"
    else
        echo "ERROR: Neither OPENROUTER_KEY nor OPENROUTER_PASSWORD is set"
        echo ""
        echo "Option 1 - Use API key directly:"
        echo "  export OPENROUTER_KEY='your-api-key-here'"
        echo ""
        echo "Option 2 - Use encrypted key with password:"
        echo "  export OPENROUTER_PASSWORD='your-secret-password'"
        echo ""
        echo "Get an API key at: https://openrouter.ai/"
        exit 1
    fi
else
    echo "✓ API key found in environment"
fi



# Check for parquet files
if [ ! -d "$PARQUET_DIR" ] || [ -z "$(ls -A $PARQUET_DIR/*.parquet 2>/dev/null)" ]; then
    echo "ERROR: No parquet files found in $PARQUET_DIR"
    echo ""
    echo "Please extract PDF text first:"
    echo "  python3 pdf_parsing/extract_pdf_text.py --pdf-dir Downloads --parquet-dir $PARQUET_DIR"
    exit 1
fi

echo "✓ Parquet files found"

# Check for violations CSV
if [ ! -f "$VIOLATIONS_CSV" ]; then
    echo "Violations CSV not found. Generating..."
    python3 pdf_parsing/parse_parquet_violations.py \
        --parquet-dir "$PARQUET_DIR" \
        -o "$VIOLATIONS_CSV"
    echo "✓ Violations CSV generated"
else
    echo "✓ Violations CSV found"
fi

# Run the query script
echo ""
echo "Starting queries on $COUNT SIRs..."
echo "Output will be saved to: $OUTPUT"
echo ""

python3 query_sirs.py \
    --count "$COUNT" \
    --output "$OUTPUT" \
    --verbose

echo ""
echo "========================================"
echo "Done! Results saved to: $OUTPUT"
echo "========================================"
