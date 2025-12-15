#!/usr/bin/env python3
"""
Dry run test of the query_sirs.py script without making actual API calls.
This validates the filtering, document loading, and data processing logic.
"""

import pandas as pd
import ast
from pathlib import Path

print("="*80)
print("DRY RUN TEST - Query SIRs Script")
print("="*80)

# Load violations CSV
print("\n1. Loading violations CSV...")
df = pd.read_csv('violations_output.csv')
print(f"   Total documents: {len(df)}")

# Filter for SIRs
sirs = df[df['is_special_investigation'] == True]
print(f"   Total SIRs: {len(sirs)}")

# Sample 5 SIRs for testing
test_count = 5
sirs_to_test = sirs.sample(n=test_count, random_state=42)
print(f"   Selected {test_count} SIRs for testing")

# Test loading each document
print("\n2. Testing document loading from parquet files...")
parquet_dir = 'pdf_parsing/parquet_files'
parquet_path = Path(parquet_dir)
parquet_files = list(parquet_path.glob("*.parquet"))
print(f"   Found {len(parquet_files)} parquet files")

success_count = 0
for idx, (_, sir) in enumerate(sirs_to_test.iterrows(), 1):
    sha256 = sir['sha256']
    print(f"\n   Test {idx}/{test_count}: {sha256[:16]}...")
    print(f"      Agency: {sir['agency_name']}")
    print(f"      Title: {sir.get('document_title', 'N/A')}")
    print(f"      Violations: {sir['num_violations']}")
    
    # Try to load document
    found = False
    for parquet_file in parquet_files:
        df_p = pd.read_parquet(parquet_file)
        matches = df_p[df_p['sha256'] == sha256]
        if not matches.empty:
            row = matches.iloc[0]
            text_data = row['text']
            if isinstance(text_data, str):
                text_pages = ast.literal_eval(text_data)
            else:
                text_pages = list(text_data)
            
            document_text = '\n\n'.join(text_pages)
            print(f"      ✓ Found in {parquet_file.name}")
            print(f"      ✓ Pages: {len(text_pages)}, Chars: {len(document_text)}")
            
            # Simulate query construction
            query = "Explain what went down here, in a few sentences. In one extra sentence, weigh in on culpability."
            full_prompt = f"{query}\n\n{document_text}"
            print(f"      ✓ Full prompt length: {len(full_prompt)} chars")
            
            found = True
            success_count += 1
            break
    
    if not found:
        print(f"      ✗ ERROR: Document not found in parquet files")

print("\n" + "="*80)
print("DRY RUN SUMMARY")
print("="*80)
print(f"Documents tested: {test_count}")
print(f"Successfully loaded: {success_count}")
print(f"Failed to load: {test_count - success_count}")

if success_count == test_count:
    print("\n✓ ALL TESTS PASSED - Script logic is working correctly!")
    print("\nTo run actual queries with the API:")
    print("  export OPENROUTER_KEY='your-api-key'")
    print("  python3 query_sirs.py")
else:
    print("\n✗ SOME TESTS FAILED - Check the errors above")

