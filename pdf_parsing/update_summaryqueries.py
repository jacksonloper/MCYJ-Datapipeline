#!/usr/bin/env python3
"""
Update sir_summaries.csv with AI-generated summaries for SIRs.

This script:
1. Runs violation parsing to identify all SIR document shas
2. Compares against existing summaries in pdf_parsing/sir_summaries.csv
3. Queries up to N missing SIRs using OpenRouter API
4. Appends new results to pdf_parsing/sir_summaries.csv
"""

import argparse
import ast
import csv
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd
import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from parse_parquet_violations import (
    extract_license_number,
    extract_agency_name,
    extract_document_title,
    extract_inspection_date,
    is_special_investigation,
    extract_violations
)

# Set up logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# OpenRouter API configuration
OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions'
MODEL = 'deepseek/deepseek-v3.2'  # DeepSeek v3.2

# Query to ask about each SIR
QUERY_TEXT = "Explain what went down here, in a few sentences. In one extra sentence, weigh in on culpability."


def get_api_key() -> str:
    """Get OpenRouter API key from environment variable."""
    api_key = os.environ.get('OPENROUTER_KEY')
    if not api_key:
        raise ValueError(
            "OPENROUTER_KEY environment variable not set. "
            "Please set it with your OpenRouter API key."
        )
    return api_key


def get_all_sir_shas(parquet_dir: str) -> Set[str]:
    """
    Get all SHA256 hashes for documents that are SIRs from parquet files.
    
    Args:
        parquet_dir: Directory containing parquet files
    
    Returns:
        Set of SHA256 hashes for SIR documents
    """
    parquet_path = Path(parquet_dir)
    parquet_files = sorted(parquet_path.glob("*.parquet"))
    
    sir_shas = set()
    
    for parquet_file in parquet_files:
        logger.info(f"Checking {parquet_file.name} for SIRs...")
        try:
            df = pd.read_parquet(parquet_file)
            
            for _, row in df.iterrows():
                # Parse text pages
                text_data = row['text']
                if isinstance(text_data, str):
                    text_stripped = text_data.strip()
                    if text_stripped.startswith('[') and text_stripped.endswith(']'):
                        text_pages = ast.literal_eval(text_data)
                    else:
                        continue
                else:
                    text_pages = list(text_data) if text_data is not None else []
                
                if not text_pages:
                    continue
                
                # Check if it's a SIR
                full_text = '\n\n'.join(text_pages)
                if is_special_investigation(full_text):
                    sir_shas.add(row['sha256'])
                    
        except Exception as e:
            logger.error(f"Error processing {parquet_file.name}: {e}")
            continue
    
    logger.info(f"Found {len(sir_shas)} SIRs in parquet files")
    return sir_shas


def get_existing_summary_shas(summaryqueries_path: str) -> Set[str]:
    """
    Get SHA256 hashes that already have summaries.
    
    Args:
        summaryqueries_path: Path to sir_summaries.csv
    
    Returns:
        Set of SHA256 hashes that already have summaries
    """
    if not Path(summaryqueries_path).exists():
        logger.info(f"No existing {summaryqueries_path}, will create new file")
        return set()
    
    try:
        df = pd.read_csv(summaryqueries_path)
        existing_shas = set(df['sha256'].unique())
        logger.info(f"Found {len(existing_shas)} existing summaries")
        return existing_shas
    except Exception as e:
        logger.error(f"Error reading {summaryqueries_path}: {e}")
        return set()


def load_document_from_parquet(sha256: str, parquet_dir: str) -> Optional[Dict]:
    """Load a document from parquet files by SHA256 hash."""
    parquet_path = Path(parquet_dir)
    parquet_files = list(parquet_path.glob("*.parquet"))
    
    for parquet_file in parquet_files:
        try:
            df = pd.read_parquet(parquet_file)
            matches = df[df['sha256'] == sha256]
            
            if not matches.empty:
                row = matches.iloc[0]
                
                # Parse text
                text_data = row['text']
                if isinstance(text_data, str):
                    text_stripped = text_data.strip()
                    if text_stripped.startswith('[') and text_stripped.endswith(']'):
                        text_pages = ast.literal_eval(text_data)
                    else:
                        text_pages = []
                else:
                    text_pages = list(text_data) if text_data is not None else []
                
                # Extract metadata
                full_text = '\n\n'.join(text_pages)
                
                return {
                    'sha256': row['sha256'],
                    'text_pages': text_pages,
                    'full_text': full_text,
                    'agency_id': extract_license_number(full_text) or '',
                    'agency_name': extract_agency_name(full_text) or '',
                    'document_title': extract_document_title(full_text) or '',
                    'date': extract_inspection_date(full_text) or '',
                    'violations_list': extract_violations(full_text)
                }
        except Exception as e:
            logger.debug(f"Error reading {parquet_file.name}: {e}")
            continue
    
    return None


def query_openrouter(api_key: str, query: str, document_text: str) -> Dict:
    """
    Query OpenRouter API with the document.
    
    Args:
        api_key: OpenRouter API key
        query: The query text
        document_text: Full document text (all pages concatenated)
    
    Returns:
        Dict with response, tokens, cost, and duration
    """
    start_time = time.time()
    
    # Combine query with document as the website does
    full_prompt = f"{query}\n\n{document_text}"
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://github.com/jacksonloper/MCYJ-Datapipeline',
        'X-Title': 'MCYJ Datapipeline SIR Summary Updates'
    }
    
    payload = {
        'model': MODEL,
        'messages': [
            {
                'role': 'user',
                'content': full_prompt
            }
        ]
    }
    
    response = requests.post(
        OPENROUTER_API_URL,
        headers=headers,
        json=payload,
        timeout=180  # 3 minute timeout
    )
    
    end_time = time.time()
    duration_ms = int((end_time - start_time) * 1000)
    
    if not response.ok:
        error_msg = f"API request failed: {response.status_code} {response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    data = response.json()
    
    # Extract response and token usage
    ai_response = data.get('choices', [{}])[0].get('message', {}).get('content', 'No response received')
    usage = data.get('usage', {})
    input_tokens = usage.get('prompt_tokens', 0)
    output_tokens = usage.get('completion_tokens', 0)
    
    # Try to extract cost if provided by OpenRouter
    cost = data.get('cost', None)
    
    return {
        'response': ai_response,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'cost': cost if cost else '',
        'duration_ms': duration_ms
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update sir_summaries.csv with AI summaries for missing SIRs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--parquet-dir',
        default='parquet_files',
        help='Directory containing parquet files (default: parquet_files)'
    )
    parser.add_argument(
        '--output',
        '-o',
        default='sir_summaries.csv',
        help='Output CSV file path (default: sir_summaries.csv)'
    )
    parser.add_argument(
        '--count',
        '-n',
        type=int,
        default=100,
        help='Maximum number of new SIRs to query (default: 100)'
    )
    parser.add_argument(
        '--query',
        default=QUERY_TEXT,
        help=f'Query text to use (default: "{QUERY_TEXT}")'
    )
    
    args = parser.parse_args()
    
    # Resolve paths relative to script directory
    script_dir = Path(__file__).parent
    parquet_dir = script_dir / args.parquet_dir
    output_path = script_dir / args.output
    
    # Get API key
    try:
        api_key = get_api_key()
        logger.info("API key loaded from environment")
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    
    # Get all SIR shas from parquet files
    logger.info(f"Scanning parquet files in {parquet_dir}...")
    all_sir_shas = get_all_sir_shas(str(parquet_dir))
    
    if not all_sir_shas:
        logger.warning("No SIRs found in parquet files")
        sys.exit(0)
    
    # Get existing summary shas
    existing_shas = get_existing_summary_shas(str(output_path))
    
    # Find missing shas
    missing_shas = all_sir_shas - existing_shas
    logger.info(f"Found {len(missing_shas)} SIRs without summaries")
    
    if not missing_shas:
        logger.info("All SIRs already have summaries!")
        sys.exit(0)
    
    # Limit to requested count
    shas_to_query = sorted(list(missing_shas))[:args.count]
    logger.info(f"Will query {len(shas_to_query)} SIRs")
    
    # Prepare results list
    results = []
    
    # Query each SIR
    for idx, sha in enumerate(shas_to_query, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing SIR {idx}/{len(shas_to_query)}: {sha}")
        
        # Load document from parquet
        logger.info("Loading document from parquet...")
        doc = load_document_from_parquet(sha, str(parquet_dir))
        
        if not doc:
            logger.error(f"Could not find document in parquet files: {sha}")
            continue
        
        logger.info(f"Agency: {doc['agency_name']}")
        logger.info(f"Title: {doc['document_title']}")
        logger.info(f"Date: {doc['date']}")
        logger.info(f"Document: {len(doc['text_pages'])} pages, {len(doc['full_text'])} characters")
        
        # Query the API
        logger.info("Querying OpenRouter API...")
        try:
            result = query_openrouter(api_key, args.query, doc['full_text'])
            
            logger.info(f"Response received:")
            logger.info(f"  Input tokens: {result['input_tokens']}")
            logger.info(f"  Output tokens: {result['output_tokens']}")
            logger.info(f"  Duration: {result['duration_ms']/1000:.2f}s")
            if result['cost']:
                logger.info(f"  Cost: ${result['cost']:.6f}")
            logger.info(f"  Response preview: {result['response'][:150]}...")
            
            # Count violations
            violations = doc['violations_list']
            num_violations = len(violations)
            violations_str = '; '.join(violations) if violations else ''
            
            # Store result
            results.append({
                'sha256': sha,
                'agency_id': doc['agency_id'],
                'agency_name': doc['agency_name'],
                'document_title': doc['document_title'],
                'date': doc['date'],
                'num_violations': num_violations,
                'violations_list': violations_str if violations_str else 'nan',
                'query': args.query,
                'response': result['response'],
                'input_tokens': result['input_tokens'],
                'output_tokens': result['output_tokens'],
                'cost': result['cost'],
                'duration_ms': result['duration_ms']
            })
            
            # Add a small delay to avoid rate limiting
            if idx < len(shas_to_query):
                logger.info("Waiting 2 seconds before next query...")
                time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error querying API: {e}")
            continue
    
    if not results:
        logger.warning("No results to save")
        sys.exit(0)
    
    # Append results to CSV
    logger.info(f"\n{'='*80}")
    logger.info(f"Appending {len(results)} results to {output_path}")
    
    file_exists = output_path.exists()
    
    with open(output_path, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ['sha256', 'agency_id', 'agency_name', 'document_title', 'date', 
                     'num_violations', 'violations_list', 'query', 'response', 
                     'input_tokens', 'output_tokens', 'cost', 'duration_ms']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerows(results)
    
    logger.info("Done!")
    
    # Print summary
    successful = len(results)
    total_input_tokens = sum(r['input_tokens'] for r in results)
    total_output_tokens = sum(r['output_tokens'] for r in results)
    
    logger.info(f"\nSummary:")
    logger.info(f"  New summaries added: {successful}")
    logger.info(f"  Total input tokens: {total_input_tokens:,}")
    logger.info(f"  Total output tokens: {total_output_tokens:,}")
    logger.info(f"  Output file: {output_path}")


if __name__ == "__main__":
    main()
