#!/bin/bash

# Build script for generating website data and building the site

set -e  # Exit on error

# Store the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==> Installing uv if needed..."
if ! command -v uv &> /dev/null; then
    echo "uv not found, installing..."
    if pip install uv 2>/dev/null; then
        echo "uv installed successfully with pip"
    else
        echo "Failed to install uv with pip, trying official installer..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Add to PATH for this session
        export PATH="$HOME/.cargo/bin:$PATH"
        # Verify uv is now available
        if ! command -v uv &> /dev/null; then
            echo "ERROR: Failed to install uv"
            exit 1
        fi
    fi
else
    echo "uv is already installed"
fi

echo "==> Installing Python dependencies from pyproject.toml..."
cd "$PROJECT_ROOT"
uv pip install --system .

echo ""
echo "==> Step 1: Generating violations CSV from parquet files..."
python3 "$PROJECT_ROOT/parse_parquet_violations.py" \
  --parquet-dir "$PROJECT_ROOT/pdf_parsing/parquet_files" \
  -o "$PROJECT_ROOT/violations_output.csv"

echo ""
echo "==> Step 2: Generating JSON data for website..."
cd "$SCRIPT_DIR"
python3 generate_website_data.py \
  --violations-csv "$PROJECT_ROOT/violations_output.csv" \
  --output-dir public/data

echo ""
echo "==> Step 3: Building website with Vite..."
npm run build

echo ""
echo "==> Build complete! Output is in dist/"
