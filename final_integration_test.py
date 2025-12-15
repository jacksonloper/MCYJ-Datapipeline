#!/usr/bin/env python3
"""
Final integration test to validate all components are ready.
"""

import sys
import os
from pathlib import Path

print("="*80)
print("FINAL INTEGRATION TEST")
print("="*80)

tests_passed = 0
tests_failed = 0

# Test 1: Check if all required files exist
print("\n1. Checking required files...")
required_files = [
    'query_sirs.py',
    'decrypt_api_key.py',
    'run_sir_queries.sh',
    'RUN_SIR_QUERY.md',
    'violations_output.csv',
    'test_query_dry_run.py',
    '.github/workflows/query-sirs.yml'
]

for file in required_files:
    if Path(file).exists():
        print(f"   ✓ {file}")
        tests_passed += 1
    else:
        print(f"   ✗ {file} NOT FOUND")
        tests_failed += 1

# Test 2: Check if parquet files exist
print("\n2. Checking parquet files...")
parquet_dir = Path('pdf_parsing/parquet_files')
if parquet_dir.exists():
    parquet_files = list(parquet_dir.glob('*.parquet'))
    if parquet_files:
        print(f"   ✓ Found {len(parquet_files)} parquet files")
        tests_passed += 1
    else:
        print(f"   ✗ No parquet files found")
        tests_failed += 1
else:
    print(f"   ✗ Parquet directory not found")
    tests_failed += 1

# Test 3: Check violations CSV
print("\n3. Checking violations CSV...")
try:
    import pandas as pd
    df = pd.read_csv('violations_output.csv')
    sirs = df[df['is_special_investigation'] == True]
    print(f"   ✓ Violations CSV loaded: {len(df)} documents, {len(sirs)} SIRs")
    tests_passed += 1
except Exception as e:
    print(f"   ✗ Error loading violations CSV: {e}")
    tests_failed += 1

# Test 4: Test document loading
print("\n4. Testing document loading...")
try:
    import ast
    parquet_files = list(parquet_dir.glob('*.parquet'))
    sir = sirs.iloc[0]
    sha = sir['sha256']
    
    found = False
    for parquet_file in parquet_files:
        df_p = pd.read_parquet(parquet_file)
        matches = df_p[df_p['sha256'] == sha]
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
            print(f"   ✓ Successfully loaded document: {len(text_pages)} pages, {len(document_text)} chars")
            found = True
            tests_passed += 1
            break
    
    if not found:
        print(f"   ✗ Could not load document")
        tests_failed += 1
        
except Exception as e:
    print(f"   ✗ Error testing document loading: {e}")
    tests_failed += 1

# Test 5: Check scripts are executable
print("\n5. Checking scripts are executable...")
import stat
for script in ['query_sirs.py', 'decrypt_api_key.py', 'run_sir_queries.sh']:
    if Path(script).exists():
        st = os.stat(script)
        if st.st_mode & stat.S_IXUSR:
            print(f"   ✓ {script} is executable")
            tests_passed += 1
        else:
            print(f"   ✗ {script} is not executable")
            tests_failed += 1

# Test 6: Check imports
print("\n6. Checking Python dependencies...")
try:
    import requests
    print(f"   ✓ requests library available")
    tests_passed += 1
except ImportError:
    print(f"   ✗ requests library not available")
    tests_failed += 1

try:
    from cryptography.hazmat.primitives.ciphers import Cipher
    print(f"   ✓ cryptography library available")
    tests_passed += 1
except ImportError:
    print(f"   ✗ cryptography library not available (optional)")
    # Not a critical failure

# Test 7: Validate query script help
print("\n7. Testing query script...")
import subprocess
result = subprocess.run(['python3', 'query_sirs.py', '--help'], 
                       capture_output=True, text=True)
if result.returncode == 0 and 'Query OpenRouter API' in result.stdout:
    print(f"   ✓ query_sirs.py help works correctly")
    tests_passed += 1
else:
    print(f"   ✗ query_sirs.py help failed")
    tests_failed += 1

# Summary
print("\n" + "="*80)
print("TEST SUMMARY")
print("="*80)
print(f"Tests passed: {tests_passed}")
print(f"Tests failed: {tests_failed}")
print(f"Total tests: {tests_passed + tests_failed}")

if tests_failed == 0:
    print("\n✅ ALL TESTS PASSED!")
    print("\nThe implementation is complete and ready to execute.")
    print("\nTo run the actual queries:")
    print("  export OPENROUTER_KEY='your-api-key'")
    print("  ./run_sir_queries.sh")
    print("\nOr trigger the GitHub Actions workflow from the Actions tab.")
    sys.exit(0)
else:
    print(f"\n⚠️  {tests_failed} TEST(S) FAILED")
    print("\nPlease review the errors above.")
    sys.exit(1)

