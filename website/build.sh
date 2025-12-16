#!/bin/bash

# Build script for generating website data and building the site

set -e  # Exit on error

echo "==> Step 0: Installing Python dependencies with pip..."
# Install dependencies from pyproject.toml
cd ..
pip install -e .
cd website

echo ""
echo "==> Step 1: Generating document info CSV from parquet files..."
python3 ../pdf_parsing/extract_document_info.py \
  --parquet-dir ../pdf_parsing/parquet_files \
  -o ../document_info.csv

echo ""
echo "==> Step 2: Generating JSON data for website..."
python3 generate_website_data.py \
  --document-csv ../document_info.csv \
  --output-dir public/data

echo ""
echo "==> Step 2.5: Exporting parquet documents to individual JSON files..."
python3 export_parquet_to_json.py \
  --parquet-dir ../pdf_parsing/parquet_files \
  --output-dir public/documents \
  --document-csv ../document_info.csv

echo ""
echo "==> Step 3: Building website with Vite..."
npm run build

echo ""
echo "==> Build complete! Output is in dist/"
