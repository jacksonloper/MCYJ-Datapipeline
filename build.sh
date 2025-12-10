#!/bin/bash

# Build script for generating website data and building the site

set -e  # Exit on error

echo "==> Step 1: Generating violations CSV from parquet files..."
python3 parse_parquet_violations.py \
  --parquet-dir pdf_parsing/parquet_files \
  -o violations_output.csv

echo ""
echo "==> Step 2: Finding latest metadata files..."

# Find the latest agency and documents CSV files
AGENCY_CSV=$(find metadata_output -name "*_agency_info.csv" 2>/dev/null | sort -r | head -1)
DOCUMENTS_CSV=$(find metadata_output -name "*_combined_pdf_content_details.csv" 2>/dev/null | sort -r | head -1)

if [ -z "$AGENCY_CSV" ]; then
  echo "Warning: No agency CSV file found in metadata_output/"
  echo "Please run pull_agency_info_api.py first or provide sample data"
  exit 1
fi

echo "Using agency CSV: $AGENCY_CSV"
if [ -n "$DOCUMENTS_CSV" ]; then
  echo "Using documents CSV: $DOCUMENTS_CSV"
else
  echo "Warning: No documents CSV found, proceeding without documents"
  DOCUMENTS_CSV=""
fi

echo ""
echo "==> Step 3: Generating JSON data for website..."
if [ -n "$DOCUMENTS_CSV" ]; then
  python3 generate_website_data.py \
    --violations-csv violations_output.csv \
    --agency-csv "$AGENCY_CSV" \
    --documents-csv "$DOCUMENTS_CSV" \
    --output-dir website/public/data
else
  python3 generate_website_data.py \
    --violations-csv violations_output.csv \
    --agency-csv "$AGENCY_CSV" \
    --output-dir website/public/data
fi

echo ""
echo "==> Step 4: Building website with Vite..."
npm run build

echo ""
echo "==> Build complete! Output is in dist/"
