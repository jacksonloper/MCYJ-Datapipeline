# PDF Text Extraction Tool

A Python script that extracts text from PDF files using [pdfplumber](https://github.com/jsvine/pdfplumber) and saves the results to compressed Parquet files.

## Overview

This script facilitates the production of a directory of parquet files that store text versions of each file in a directory of pdfs (such as that downloaded by ../ingestion).  We assume the pdf directory is continually being updated, and, as such, the script may need to be run again and again.  Each time the script it run, it:

- **Looks at the parquet files storing the text information we already have**.  These parquet files store both sha256 hashes of the original pdfs and the text that was extracted.
- **Looks at the sha256 of files in the directory**.
- **Figures out files that still need to be processed**.
- **Processes them** into a new parquet file that is added into the parquet directory.

By default the text information is stored in parquet_files, as that is where they are stored in this git repository for this project.  For this project's use, we find 500 pdf files boil down to about 1.5 megabytes.

## Usage

**Note**: All commands should be run from the project root directory.

### Basic Usage

Extract text from all PDFs in a directory:

```bash
uv run pdf_parsing/extract_pdf_text.py --pdf-dir /path/to/pdf/directory
```

This creates timestamped Parquet files in `pdf_parsing/parquet_files/` by default (e.g., `20251103_143052_pdf_text.parquet` with `%Y%m%d_%H%M%S` timestamp).

### Custom Output Directory

Specify a custom output directory:

```bash
uv run pdf_parsing/extract_pdf_text.py --pdf-dir /path/to/pdf/directory --parquet-dir /path/to/output
```

### Limit Processing

Process only a limited number of PDFs (useful for testing or incremental processing):

```bash
uv run pdf_parsing/extract_pdf_text.py --pdf-dir /path/to/pdf/directory --limit 100
```

This will process at most 100 PDFs. Note that already-processed PDFs (skipped files) don't count toward the limit.

### Spot Check

Verify existing extractions by re-processing N random PDFs:

```bash
uv run pdf_parsing/extract_pdf_text.py --pdf-dir /path/to/pdf/directory --spot-check 10
```

This will:
- Load existing records from all Parquet files in the output directory
- Randomly select up to 10 PDFs that have been previously processed
- Re-extract text from those PDFs
- Compare the newly extracted text with the stored text
- Report pass/fail for each PDF

Spot checking exits with code 0 if all checks pass, or code 1 if any fail.

## Output Format

The script outputs compressed Parquet files with the following schema:

### Fields

- **`sha256`** (string): SHA256 hash of the PDF file (hex digest)
- **`dateprocessed`** (string): ISO 8601 timestamp of when the PDF was processed
- **`text`** (list of strings): Text content, one string per page

### File Naming

Each processing run creates a new file named: `YYYYMMDD_HHMMSS_pdf_text.parquet`

Example: `20251103_143052_pdf_text.parquet`

