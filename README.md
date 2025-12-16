# MCYJ Parsing Script

## 1. Get all the available documents from the Michigan Welfare public search API

```bash
python pull_agency_info_api.py --output-dir metadata_output --overwrite=False --verbose
```

This will output the agency info and correpsonding documents to the `metadata_output` directory.
The default behavior will output all available documents in both json and csv formats.

### 1. Output
```bash
ls metadata_output
#> 2025-10-30_agency_info.csv
#> 2025-10-30_all_agency_info.json
#> 2025-10-30_combined_pdf_content_details.csv
```

## 2. Get a list of extra and missing files in the downloaded files

```r
python get_download_list.py --download-folder Downloads --available-files "metadata_output/$(date +"%Y-%m-%d")_combined_pdf_content_details.csv"
```

### 2. Output
```bash
ls metadata_output
#> 2025-10-30_agency_info.csv
#> 2025-10-30_all_agency_info.json
#> 2025-10-30_combined_pdf_content_details.csv
#> extra_files.txt
#> missing_files.csv
```

  - `extra_files.txt` contains files that are in `Downloads` but are not found from the API (most likely due to naming discrepancies)
  - `missing_Files.csv` contains missing files in the csv format with header:

```
generated_filename,agency_name,agency_id,FileExtension,CreatedDate,Title,ContentBodyId,Id,ContentDocumentId
```

## 3. Download missing documents

```bash
python download_all_pdfs.py --csv metadata_output/missing_files.csv --output-dir Downloads
```

### 3. Output

```bash
$ ls downloads/ | head
# 42ND_CIRCUIT_COURT_-_FAMILY_DIVISION_42ND_CIRCUIT_COURT_-_FAMILY_DIVISION_Interim_2025_2025-07-18_069cs0000104BR0AAM.pdf
# ADOPTION_AND_FOSTER_CARE_SPECIALISTS,_INC._CB440295542_INSP_201_2020-03-14_0698z000005Hpu5AAC.pdf
# ADOPTION_AND_FOSTER_CARE_SPECIALISTS,_INC._CB440295542_ORIG.pdf_2008-06-24_0698z000005HozQAAS.pdf
# ADOPTION_ASSOCIATES,_INC_Adoption_Associates_INC_Renewal_2025_2025-08-20_069cs0000163byMAAQ.pdf
# ADOPTION_OPTION,_INC._CB560263403_ORIG.pdf_2004-05-08_0698z000005Hp18AAC.pdf
```

## 4. Check duplicates and update file metadata

check the md5sums

## 5. Extract text from PDFs and extract basic document info

Extract text from PDFs and save to parquet files:

```bash
python3 pdf_parsing/extract_pdf_text.py --pdf-dir Downloads --parquet-dir pdf_parsing/parquet_files
```

Extract basic document information from parquet files to CSV:

```bash
python3 pdf_parsing/extract_document_info.py --parquet-dir pdf_parsing/parquet_files -o document_info.csv
```

The output CSV contains:
- Agency ID (License #)
- Agency name
- Document title (extracted from document content, e.g., "Special Investigation Report", "Renewal Inspection Report")
- Inspection/report date
- Special Investigation Report indicator (whether document is a SIR)

## 6. Investigate documents

After running the document extraction script, you can investigate random documents to see the original text alongside the parsed information:

```bash
cd pdf_parsing
python3 investigate_violations.py
```

Categories:
- `sir` - Special Investigation Reports only (default)
- `all` - Any document

### Investigate a specific document by SHA

To investigate a specific document by its SHA256 hash:

```bash
python3 pdf_parsing/investigate_sha.py <sha256>
```

Example:
```bash
python3 pdf_parsing/investigate_sha.py 6e5b899cf078b4bf0829e4dce8113aaac61edfa5bc0958efa725ae8607008f68
```

This will display:
- Parsed violation information (agency, date, violations found)
- Original document text from the parquet file
- Useful for debugging parsing issues or verifying specific documents

See [pdf_parsing/README.md](pdf_parsing/README.md) for more details.

## 7. Web Dashboard

A lightweight web dashboard is included to visualize agency documents and reports.

### Building the Website

The website can be built with a single command:

```bash
cd website
./build.sh
```

This will:
1. Generate document info CSV from parquet files
2. Create JSON data files from the document info (deriving agency info automatically)
3. Build the static website with Vite

The built website will be in the `dist/` directory.

### Local Development

```bash
# Install dependencies
cd website
npm install

# Start development server
npm run dev
```

### Netlify Deployment

The site is configured for automatic deployment on Netlify:
- Push changes to your repository
- Netlify will automatically run the build process from the `website` directory
- The site will be deployed from the `dist/` directory

Configuration is in `website/netlify.toml`.

See [website/README.md](website/README.md) for more details about the dashboard.

## 8. AI-Powered SIR Summaries

Automatically generate and maintain AI summaries for Special Investigation Reports (SIRs) using OpenRouter API (DeepSeek v3.2).

### Automated Updates

A GitHub Actions workflow automatically:
1. Scans parquet files for new SIRs
2. Compares against existing summaries in `pdf_parsing/sir_summaries.csv`
3. Generates AI summaries for up to 100 new SIRs weekly
4. Commits results to the repository

**To trigger manually**: Go to Actions → "Update SIR Summaries" → Run workflow

### Local Usage

```bash
cd pdf_parsing
export OPENROUTER_KEY="your-api-key"
python3 update_summaryqueries.py --count 100
```

The AI analyzes each report to provide:
- **Summary**: Incident description and culpability assessment
- **Violation status**: Whether allegations were substantiated (y/n)

Results are appended to `pdf_parsing/sir_summaries.csv` with complete metadata including token usage and cost information.

See [pdf_parsing/README.md](pdf_parsing/README.md) for complete documentation.