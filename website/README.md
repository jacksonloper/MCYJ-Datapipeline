# Michigan Child Welfare Licensing Dashboard

A lightweight web dashboard built with Vite to display Michigan Child Welfare agency violations and reports.  Live [here](https://scintillating-licorice-0dd1c4.netlify.app/).

## Features

- **Agency Directory**: Browse all child welfare agencies
- **Violations Tracking**: View detailed violation reports for each agency
- **Search & Filter**: Search agencies by name or ID
- **Expandable Details**: Click any agency to view detailed violations
- **Summary Statistics**: Dashboard showing total agencies, violations, and reports

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

1. Runs `pdf_parsing/parse_parquet_violations.py` to generate violations from parquet files
2. Runs `generate_website_data.py` to create JSON files from violations CSV
3. Builds the static site with Vite

### Netlify Configuration

The `netlify.toml` file configures:
- Build command: `bash build.sh`
- Publish directory: `dist`
- Python version: 3.11
- SPA routing with redirects

## Data Sources

The dashboard uses data from:

- **Parquet Files**: PDF text extracts in `../pdf_parsing/parquet_files/`
- **Violations CSV**: Generated from parquet files via `pdf_parsing/parse_parquet_violations.py`

The dashboard derives all agency information directly from the violations data (no separate facility metadata required).

## Project Structure

```
website/
├── index.html               # Main HTML file
├── src/
│   └── main.js              # JavaScript application logic
├── public/
│   └── data/                # Generated JSON data files (git-ignored)
├── generate_website_data.py # Script to generate JSON from CSVs
├── build.sh                 # Build script for the entire site
├── vite.config.js           # Vite configuration
├── netlify.toml             # Netlify deployment configuration
├── package.json             # Node.js dependencies and scripts
└── README.md                # This file
```

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally
- `./build.sh` - Full build pipeline (data generation + site build)

## Data Generation

To regenerate the data manually:

```bash
# From the website directory
cd website

# Generate violations CSV from parquet files
python3 ../pdf_parsing/parse_parquet_violations.py \
  --parquet-dir ../pdf_parsing/parquet_files \
  -o ../violations_output.csv

# Generate JSON files for website (derives agency info from violations)
python3 generate_website_data.py \
  --violations-csv ../violations_output.csv \
  --output-dir public/data
```

## License

ISC
