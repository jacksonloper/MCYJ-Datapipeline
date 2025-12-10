#!/bin/bash
# Demo script showing how to run the violations investigation

echo "=== MCYJ Violations Investigation Demo ==="
echo ""
echo "Step 1: Run the violations parser (if not already done)"
echo "Command: python3 parse_parquet_violations.py --parquet-dir pdf_parsing/parquet_files -o violations_output.csv"
echo ""

if [ ! -f violations_output.csv ]; then
    echo "Running violations parser..."
    python3 parse_parquet_violations.py --parquet-dir pdf_parsing/parquet_files -o violations_output.csv
else
    echo "✓ violations_output.csv already exists"
fi

echo ""
echo "Step 2: Look at some rows from the violations output"
echo "Command: head -10 violations_output.csv"
echo ""
head -10 violations_output.csv

echo ""
echo "Step 3: Show documents with violations"
echo "Command: grep -v ',0,' violations_output.csv | head -5"
echo ""
grep -v ',0,' violations_output.csv | head -5

echo ""
echo "Step 4: Run the errata investigation (sample of 3 documents)"
echo "Command: python3 investigate_violations_errata.py --sample-size 3 --non-interactive"
echo ""
python3 investigate_violations_errata.py --sample-size 3 --non-interactive 2>&1 | tail -60

echo ""
echo "=== Demo Complete ==="
echo ""
echo "For interactive investigation, run:"
echo "  python3 investigate_violations_errata.py --sample-size 10"
echo ""
echo "For full report, run:"
echo "  python3 investigate_violations_errata.py --sample-size 20 --non-interactive > full_report.txt"
