#!/usr/bin/env python3
"""
Test script to verify enrichment fixes for ticker extraction.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from ingestion.lib.enrichment import StockAPIEnricher

def test_enrichment_fixes():
    """Test the fixed enrichment logic."""
    enricher = StockAPIEnricher(use_cache=False)

    # Test cases from actual problematic data
    test_cases = [
        # Case 1: Asset with SP prefix (should clean, lookup company name via fuzzy match)
        {
            'name': 'SP Citizens Financial Group, Inc.',
            'expected_ticker': 'CFG-PI',  # Found via company lookup (94% confidence)
            'expected_ownership': 'SP',
            'expected_cleaned': 'Citizens Financial Group, Inc'  # Trailing punctuation removed
        },
        # Case 2: Asset with JT prefix (company lookup should find ticker)
        {
            'name': 'JT Apple Inc',
            'expected_ticker': 'AAPL',  # Found via company lookup (100% confidence)
            'expected_ownership': 'JT',
            'expected_cleaned': 'Apple Inc'
        },
        # Case 3: Generic "STOCK" word (should be blacklisted)
        {
            'name': 'Company Common Stock',
            'expected_ticker': None,  # "STOCK" is blacklisted
            'expected_ownership': None,
            'expected_cleaned': 'Company Common Stock'
        },
        # Case 4: Proper ticker in parentheses (should extract correctly)
        {
            'name': 'Apple Inc. (AAPL)',
            'expected_ticker': 'AAPL',
            'expected_ownership': None,
            'expected_cleaned': 'Apple Inc. (AAPL)'
        },
        # Case 5: Asset with "TRUST" word (should be blacklisted)
        {
            'name': 'Investment Trust',
            'expected_ticker': None,  # "TRUST" is blacklisted
            'expected_ownership': None,
            'expected_cleaned': 'Investment Trust'
        },
        # Case 6: SP prefix with proper ticker
        {
            'name': 'SP Microsoft Corporation (MSFT)',
            'expected_ticker': 'MSFT',
            'expected_ownership': 'SP',
            'expected_cleaned': 'Microsoft Corporation (MSFT)'
        },
        # Case 7: Complex ownership prefix with company lookup
        {
            'name': 'F S: New\nS O: Trust Account\nSP Walt Disney Company',
            'expected_ticker': 'DIS',  # Found via company lookup (100% confidence)
            'expected_ownership': 'SP',  # Should detect SP
            'expected_cleaned': 'Walt Disney Company'  # Should clean all prefixes
        },
        # Case 8: Arrow notation with ticker after arrow
        {
            'name': 'Old Account ⇒ Tesla Inc (TSLA)',
            'expected_ticker': 'TSLA',
            'expected_ownership': None,
            'expected_cleaned': 'Old Account ⇒ Tesla Inc (TSLA)'
        },
        # Case 9: Bracket notation
        {
            'name': '[NVDA] NVIDIA Corporation',
            'expected_ticker': 'NVDA',
            'expected_ownership': None,
            'expected_cleaned': '[NVDA] NVIDIA Corporation'
        },
        # Case 10: Prefix notation with dash
        {
            'name': 'AMZN - Amazon.com Inc',
            'expected_ticker': 'AMZN',
            'expected_ownership': None,
            'expected_cleaned': 'AMZN - Amazon.com Inc'
        }
    ]

    print("=" * 80)
    print("TESTING ENRICHMENT FIXES")
    print("=" * 80)

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test['name'][:60]}")
        print("-" * 80)

        # Test cleaning
        cleaned_name, ownership = enricher.clean_asset_name(test['name'])
        print(f"  Cleaned name: '{cleaned_name}'")
        print(f"  Ownership indicator: {ownership}")

        # Test ticker extraction (returns tuple of (ticker, method) or None)
        ticker_result = enricher.extract_ticker_from_name(test['name'])
        ticker = ticker_result[0] if ticker_result else None
        extraction_method = ticker_result[1] if ticker_result else None
        print(f"  Extracted ticker: {ticker}")
        print(f"  Extraction method: {extraction_method}")

        # Verify results
        checks_passed = []
        checks_failed = []

        if cleaned_name.strip() == test['expected_cleaned'].strip():
            checks_passed.append("✓ Cleaned name matches")
        else:
            checks_failed.append(f"✗ Cleaned name mismatch: expected '{test['expected_cleaned']}', got '{cleaned_name}'")

        if ownership == test['expected_ownership']:
            checks_passed.append("✓ Ownership indicator matches")
        else:
            checks_failed.append(f"✗ Ownership mismatch: expected {test['expected_ownership']}, got {ownership}")

        if ticker == test['expected_ticker']:
            checks_passed.append("✓ Ticker extraction matches")
        else:
            checks_failed.append(f"✗ Ticker mismatch: expected {test['expected_ticker']}, got {ticker}")

        # Print results
        for check in checks_passed:
            print(f"  {check}")
        for check in checks_failed:
            print(f"  {check}")

        if checks_failed:
            failed += 1
            print(f"  ❌ FAILED")
        else:
            passed += 1
            print(f"  ✅ PASSED")

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total tests: {len(test_cases)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {failed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(test_enrichment_fixes())
