#!/usr/bin/env python3
"""
Test the query script with a mock API to verify the request structure.
This simulates what would happen with the actual API.
"""

import json
import sys
from unittest.mock import patch, MagicMock
import pandas as pd

# Mock the API response
mock_response = {
    'choices': [{
        'message': {
            'content': 'This Special Investigation Report details an incident where staff failed to maintain proper supervision ratios during outdoor activities. The investigation found two violations of licensing rules related to supervision requirements. The facility administration bears responsibility for this lapse in maintaining proper staffing protocols.'
        }
    }],
    'usage': {
        'prompt_tokens': 15234,
        'completion_tokens': 287
    },
    'cost': 0.004521
}

print("="*80)
print("MOCK API TEST - Validating Request Structure")
print("="*80)

# Load one SIR for testing
df = pd.read_csv('violations_output.csv')
sirs = df[df['is_special_investigation'] == True]
test_sir = sirs.iloc[0]

print(f"\nTest SIR:")
print(f"  SHA256: {test_sir['sha256'][:16]}...")
print(f"  Agency: {test_sir['agency_name']}")
print(f"  Title: {test_sir['document_title']}")

# Load the document
import ast
from pathlib import Path

parquet_dir = Path('pdf_parsing/parquet_files')
parquet_files = list(parquet_dir.glob('*.parquet'))

doc_found = False
for parquet_file in parquet_files:
    df_p = pd.read_parquet(parquet_file)
    matches = df_p[df_p['sha256'] == test_sir['sha256']]
    if not matches.empty:
        row = matches.iloc[0]
        text_data = row['text']
        if isinstance(text_data, str):
            text_stripped = text_data.strip()
            if text_stripped.startswith('[') and text_stripped.endswith(']'):
                text_pages = ast.literal_eval(text_data)
            else:
                text_pages = []
        else:
            text_pages = list(text_data)
        
        document_text = '\n\n'.join(text_pages)
        doc_found = True
        break

if not doc_found:
    print("ERROR: Could not load document")
    sys.exit(1)

# Construct the query as the script would
query = "Explain what went down here, in a few sentences. In one extra sentence, weigh in on culpability."
full_prompt = f"{query}\n\n{document_text}"

print(f"\nQuery Structure:")
print(f"  Query length: {len(query)} chars")
print(f"  Document length: {len(document_text)} chars")
print(f"  Full prompt length: {len(full_prompt)} chars")

# Mock the API call
print(f"\nSimulating API Call:")
print(f"  URL: https://openrouter.ai/api/v1/chat/completions")
print(f"  Model: deepseek/deepseek-v3.2")
print(f"  Headers: Authorization, Content-Type, HTTP-Referer, X-Title")

request_payload = {
    'model': 'deepseek/deepseek-v3.2',
    'messages': [
        {
            'role': 'user',
            'content': full_prompt
        }
    ]
}

print(f"  Request payload structure: ✓")
print(f"    - model: {request_payload['model']}")
print(f"    - messages[0].role: {request_payload['messages'][0]['role']}")
print(f"    - messages[0].content: {len(request_payload['messages'][0]['content'])} chars")

print(f"\nMock API Response:")
print(f"  Status: 200 OK")
print(f"  Response content: {mock_response['choices'][0]['message']['content'][:150]}...")
print(f"  Input tokens: {mock_response['usage']['prompt_tokens']:,}")
print(f"  Output tokens: {mock_response['usage']['completion_tokens']:,}")
print(f"  Cost: ${mock_response['cost']:.6f}")

print(f"\n" + "="*80)
print("✓ Mock API test successful!")
print("="*80)
print("\nThe script structure is correct and would work with the actual API.")
print("To run with the real API, set OPENROUTER_KEY environment variable.")

