# Michigan Child Welfare Licensing Dashboard

A lightweight web dashboard built with Vite to display Michigan Child Welfare agency information, violations, and documents.

## Features

- **Agency Directory**: Browse all child welfare agencies with key information
- **Violations Tracking**: View detailed violation reports for each agency
- **Document Management**: Access available documents for each agency
- **Search & Filter**: Search agencies by name, city, county, or license number
- **Expandable Details**: Click any agency to view detailed violations and documents
- **Summary Statistics**: Dashboard showing total agencies, violations, reports, and documents

## Development

### Prerequisites

- Node.js (v18 or later recommended)
- Python 3.11+
- pandas and pyarrow Python packages

### Local Development

1. Install dependencies:
   ```bash
   npm install
   ```

2. Generate the data files:
   ```bash
   ./build.sh
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open your browser to `http://localhost:5173` (or the port shown in the terminal)

### Building for Production

Run the build script which:
1. Generates violations CSV from parquet files
2. Creates JSON data files from CSVs
3. Builds the static website

```bash
./build.sh
```

The built files will be in the `dist/` directory.

## Netlify Deployment

The site is configured for automatic deployment on Netlify. The build process:

1. Runs `parse_parquet_violations.py` to generate violations from parquet files
2. Runs `generate_website_data.py` to create JSON files from CSVs
3. Builds the static site with Vite

### Netlify Configuration

The `netlify.toml` file configures:
- Build command: `bash build.sh`
- Publish directory: `dist`
- Python version: 3.11
- SPA routing with redirects

## Data Sources

The dashboard uses data from:

- **Parquet Files**: PDF text extracts in `pdf_parsing/parquet_files/`
- **Agency CSV**: Agency information from `metadata_output/*_agency_info.csv`
- **Documents CSV**: Document listings from `metadata_output/*_combined_pdf_content_details.csv`
- **Violations CSV**: Generated from parquet files via `parse_parquet_violations.py`

## Project Structure

```
.
├── website/
│   ├── index.html           # Main HTML file
│   ├── src/
│   │   └── main.js          # JavaScript application logic
│   └── public/
│       └── data/            # Generated JSON data files (git-ignored)
├── generate_website_data.py # Script to generate JSON from CSVs
├── build.sh                 # Build script for the entire site
├── vite.config.js          # Vite configuration
├── netlify.toml            # Netlify deployment configuration
└── package.json            # Node.js dependencies and scripts
```

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally
- `./build.sh` - Full build pipeline (data generation + site build)

## Data Generation

To regenerate the data:

```bash
# Generate violations CSV from parquet files
python3 parse_parquet_violations.py \
  --parquet-dir pdf_parsing/parquet_files \
  -o violations_output.csv

# Generate JSON files for website
python3 generate_website_data.py \
  --violations-csv violations_output.csv \
  --agency-csv metadata_output/YYYY-MM-DD_agency_info.csv \
  --documents-csv metadata_output/YYYY-MM-DD_combined_pdf_content_details.csv \
  --output-dir website/public/data
```

## License

ISC
