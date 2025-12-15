#!/usr/bin/env python3
"""
Query OpenRouter API (DeepSeek) on 50 Special Investigation Reports (SIRs).

This script:
1. Reads the violations CSV to find SIRs
2. Loads the full document text from parquet files
3. Queries the OpenRouter API with the document text
4. Saves results to a CSV file

The query format matches the website implementation:
- Query text + "\n\n" + document text
- Uses DeepSeek v3.2 model via OpenRouter
"""

import argparse
import ast
import csv
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests

# Set up logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# OpenRouter API configuration
OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions'
MODEL = 'deepseek/deepseek-chat'  # DeepSeek v3.2

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
                
                # Parse text - it's stored as a list or numpy array
                text_data = row['text']
                if isinstance(text_data, str):
                    # If stored as string, parse it safely
                    try:
                        text_stripped = text_data.strip()
                        if text_stripped.startswith('[') and text_stripped.endswith(']'):
                            text_pages = ast.literal_eval(text_data)
                            if not isinstance(text_pages, list):
                                logger.warning(f"Parsed text is not a list for document {sha256}")
                                text_pages = []
                        else:
                            logger.warning(f"Text data is not in list format for document {sha256}")
                            text_pages = []
                    except (ValueError, SyntaxError) as e:
                        logger.warning(f"Failed to parse text for document {sha256}: {e}")
                        text_pages = []
                else:
                    # If already a list or array, convert to list
                    text_pages = list(text_data) if text_data is not None else []
                
                return {
                    'sha256': row['sha256'],
                    'dateprocessed': row['dateprocessed'],
                    'text': text_pages
                }
        except Exception as e:
            logger.error(f"Error reading {parquet_file.name}: {e}")
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
        'X-Title': 'MCYJ Datapipeline SIR Query Script'
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
        timeout=180  # 3 minute timeout (configurable for large documents)
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
        'cost': cost,
        'duration_ms': duration_ms
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Query OpenRouter API on 50 SIRs and save results to CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query 50 SIRs with API key from environment
  export OPENROUTER_KEY="your-api-key"
  python3 query_sirs.py

  # Specify custom number of SIRs and output file
  python3 query_sirs.py --count 10 --output my_results.csv

  # Use custom violations CSV and parquet directory
  python3 query_sirs.py --violations-csv custom_violations.csv --parquet-dir custom_parquets/
        """
    )
    parser.add_argument(
        '--violations-csv',
        default='violations_output.csv',
        help='Path to violations CSV file (default: violations_output.csv)'
    )
    parser.add_argument(
        '--parquet-dir',
        default='pdf_parsing/parquet_files',
        help='Directory containing parquet files (default: pdf_parsing/parquet_files)'
    )
    parser.add_argument(
        '--output',
        '-o',
        default='sir_query_results.csv',
        help='Output CSV file path (default: sir_query_results.csv)'
    )
    parser.add_argument(
        '--count',
        '-n',
        type=int,
        default=50,
        help='Number of SIRs to query (default: 50)'
    )
    parser.add_argument(
        '--query',
        default=QUERY_TEXT,
        help=f'Query text to use (default: "{QUERY_TEXT}")'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose debug output'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Check if files exist
    if not Path(args.violations_csv).exists():
        logger.error(f"Violations CSV not found: {args.violations_csv}")
        logger.info("Run: python3 pdf_parsing/parse_parquet_violations.py --parquet-dir pdf_parsing/parquet_files -o violations_output.csv")
        sys.exit(1)
    
    if not Path(args.parquet_dir).exists():
        logger.error(f"Parquet directory not found: {args.parquet_dir}")
        sys.exit(1)
    
    # Get API key
    try:
        api_key = get_api_key()
        logger.info("API key loaded from environment")
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    
    # Load violations CSV and filter for SIRs
    logger.info(f"Loading violations from: {args.violations_csv}")
    df = pd.read_csv(args.violations_csv)
    sirs = df[df['is_special_investigation'] == True].copy()
    
    logger.info(f"Found {len(sirs)} SIRs in total")
    
    # Sample the requested number of SIRs
    if len(sirs) < args.count:
        logger.warning(f"Only {len(sirs)} SIRs available, querying all of them")
        sirs_to_query = sirs
    else:
        # Sample randomly for variety
        sirs_to_query = sirs.sample(n=args.count, random_state=42)
        logger.info(f"Randomly selected {args.count} SIRs to query")
    
    # Prepare results list
    results = []
    
    # Query each SIR
    for idx, (_, sir) in enumerate(sirs_to_query.iterrows(), 1):
        sha256 = sir['sha256']
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing SIR {idx}/{len(sirs_to_query)}: {sha256}")
        logger.info(f"Agency: {sir['agency_name']}")
        logger.info(f"Title: {sir.get('document_title', 'N/A')}")
        logger.info(f"Date: {sir['date']}")
        logger.info(f"Violations: {sir['num_violations']}")
        
        # Load document from parquet
        logger.info("Loading document from parquet...")
        doc = load_document_from_parquet(sha256, args.parquet_dir)
        
        if not doc:
            logger.error(f"Could not find document in parquet files: {sha256}")
            continue
        
        # Concatenate all pages
        document_text = '\n\n'.join(doc['text'])
        logger.info(f"Document loaded: {len(doc['text'])} pages, {len(document_text)} characters")
        
        # Query the API
        logger.info("Querying OpenRouter API...")
        try:
            result = query_openrouter(api_key, args.query, document_text)
            
            logger.info(f"Response received:")
            logger.info(f"  Input tokens: {result['input_tokens']}")
            logger.info(f"  Output tokens: {result['output_tokens']}")
            logger.info(f"  Duration: {result['duration_ms']/1000:.2f}s")
            if result['cost']:
                logger.info(f"  Cost: ${result['cost']:.6f}")
            logger.info(f"  Response preview: {result['response'][:150]}...")
            
            # Store result
            results.append({
                'sha256': sha256,
                'agency_id': sir['agency_id'],
                'agency_name': sir['agency_name'],
                'document_title': sir.get('document_title', ''),
                'date': sir['date'],
                'num_violations': sir['num_violations'],
                'violations_list': sir.get('violations_list', ''),
                'query': args.query,
                'response': result['response'],
                'input_tokens': result['input_tokens'],
                'output_tokens': result['output_tokens'],
                'cost': result['cost'] if result['cost'] else '',
                'duration_ms': result['duration_ms']
            })
            
            # Add a small delay to avoid rate limiting
            if idx < len(sirs_to_query):
                logger.info("Waiting 2 seconds before next query...")
                time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error querying API: {e}")
            # Store error result
            results.append({
                'sha256': sha256,
                'agency_id': sir['agency_id'],
                'agency_name': sir['agency_name'],
                'document_title': sir.get('document_title', ''),
                'date': sir['date'],
                'num_violations': sir['num_violations'],
                'violations_list': sir.get('violations_list', ''),
                'query': args.query,
                'response': f"ERROR: {str(e)}",
                'input_tokens': 0,
                'output_tokens': 0,
                'cost': '',
                'duration_ms': 0
            })
    
    # Write results to CSV
    logger.info(f"\n{'='*80}")
    logger.info(f"Writing {len(results)} results to {args.output}")
    
    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    
    logger.info("Done!")
    logger.info(f"\nResults saved to: {args.output}")
    
    # Print summary
    successful = sum(1 for r in results if not r['response'].startswith('ERROR:'))
    failed = len(results) - successful
    total_input_tokens = sum(r['input_tokens'] for r in results)
    total_output_tokens = sum(r['output_tokens'] for r in results)
    
    logger.info(f"\nSummary:")
    logger.info(f"  Total queries: {len(results)}")
    logger.info(f"  Successful: {successful}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Total input tokens: {total_input_tokens}")
    logger.info(f"  Total output tokens: {total_output_tokens}")


if __name__ == "__main__":
    main()
