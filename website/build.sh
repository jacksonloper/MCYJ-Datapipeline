#!/bin/bash

# Build script for generating website data and building the site

set -e  # Exit on error

echo "==> Installing uv if needed..."
if ! command -v uv &> /dev/null; then
    echo "uv not found, installing..."
    pip install uv
else
    echo "uv is already installed"
fi

echo "==> Installing Python dependencies from pyproject.toml..."
cd ..
uv pip install --system .
cd website

echo ""
echo "==> Step 1: Generating violations CSV from parquet files..."
python3 ../parse_parquet_violations.py \
  --parquet-dir ../pdf_parsing/parquet_files \
  -o ../violations_output.csv

echo ""
echo "==> Step 2: Generating JSON data for website..."
python3 generate_website_data.py \
  --violations-csv ../violations_output.csv \
  --output-dir public/data

echo ""
echo "==> Step 3: Building website with Vite..."
npm run build

echo ""
echo "==> Build complete! Output is in dist/"
