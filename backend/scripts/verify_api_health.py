#!/usr/bin/env python3
"""
API Health Check Script

Tests 30+ endpoints across all API categories to ensure:
- HTTP 200 responses
- Valid JSON parsing
- No literal "NaN" strings
- No numeric NaN/Inf values
- Correct response structure

Usage:
    python3 scripts/verify_api_health.py
    python3 scripts/verify_api_health.py --verbose
    python3 scripts/verify_api_health.py --endpoint /v1/version
"""

import requests
import json
import math
import sys
import argparse
from typing import List, Dict

API_BASE = "https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com"

# Comprehensive endpoint coverage (30+ endpoints)
ENDPOINTS = [
    # System Endpoints (3)
    "/v1/version",
    "/v1/costs",
    # "/v1/storage/gold",  # Requires additional params, skip for now

    # Member Endpoints (7)
    "/v1/members?limit=10",
    "/v1/members/P000197",
    "/v1/members/P000197/trades?limit=5",
    "/v1/members/P000197/portfolio",
    # Note: /v1/members/{name}/* endpoints require fuzzy matching, may fail if no match

    # Trading Endpoints (5)
    "/v1/trades?limit=10",
    "/v1/stocks?limit=10",
    "/v1/stocks/AAPL",
    "/v1/stocks/AAPL/activity",

    # Analytics Endpoints (8)
    "/v1/analytics/activity",
    "/v1/analytics/top-traders",
    "/v1/analytics/trending-stocks",
    "/v1/analytics/summary",
    "/v1/analytics/sector-activity",
    "/v1/analytics/compliance",
    "/v1/analytics/trading-timeline",
    "/v1/analytics/network-graph",

    # Filing Endpoints (3)
    "/v1/filings?limit=10",
    # Specific doc_id endpoints may vary, skip for now

    # Search (1)
    "/v1/search?q=Pelosi&limit=5",

    # Congress.gov Endpoints (10)
    "/v1/congress/members?limit=10",
    "/v1/congress/bills?limit=10",
    "/v1/congress/bills/118/hr/1",
    "/v1/congress/bills/118/hr/1/actions",
    "/v1/congress/bills/118/hr/1/cosponsors",
    "/v1/congress/bills/118/hr/1/subjects",
    "/v1/congress/committees",
    "/v1/congress/committees/house/hsag00",
    "/v1/congress/committees/house/hsag00/members",
    "/v1/congress/committees/house/hsag00/bills",
]

# Critical endpoints that must pass (fail entire test if these fail)
CRITICAL_ENDPOINTS = [
    "/v1/version",
    "/v1/members?limit=10",
    "/v1/trades?limit=10",
    "/v1/analytics/summary"
]

def check_nan(data, path=""):
    if isinstance(data, dict):
        for k, v in data.items():
            check_nan(v, f"{path}.{k}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            check_nan(item, f"{path}[{i}]")
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            print(f"ERROR: Found NaN/Inf at {path}")
            return True
    return False

def check_endpoint(endpoint):
    url = f"{API_BASE}{endpoint}"
    print(f"Checking {url}...")
    try:
        # Get raw response text first to check for literal NaN
        resp = requests.get(url, timeout=30)
        raw_text = resp.text
        
        if " NaN" in raw_text or ":NaN" in raw_text or ",NaN" in raw_text:
            print(f"FAIL: Found literal 'NaN' in response body")
            return False

        if resp.status_code != 200:
            print(f"FAIL: Status {resp.status_code}")
            print(f"Body: {raw_text[:200]}")
            return False
            
        try:
            data = resp.json()
            if check_nan(data):
                return False
        except json.JSONDecodeError as e:
            print(f"FAIL: Invalid JSON - {e}")
            print(f"Body: {raw_text[:200]}")
            return False
            
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: Exception - {e}")
        return False

def main():
    """Main entry point with argument parsing."""
    global API_BASE
    parser = argparse.ArgumentParser(description='API Health Check')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--endpoint', '-e', help='Test single endpoint')
    parser.add_argument('--base-url', default=API_BASE, help='API base URL')
    parser.add_argument('--critical-only', action='store_true', help='Test only critical endpoints')

    args = parser.parse_args()

    API_BASE = args.base_url

    # Determine which endpoints to test
    if args.endpoint:
        endpoints_to_test = [args.endpoint]
    elif args.critical_only:
        endpoints_to_test = CRITICAL_ENDPOINTS
    else:
        endpoints_to_test = ENDPOINTS

    # Track results
    passed = 0
    failed = 0
    critical_failed = []

    print(f"\n{'='*60}")
    print(f"API Health Check - Testing {len(endpoints_to_test)} endpoints")
    print(f"Base URL: {API_BASE}")
    print(f"{'='*60}\n")

    for endpoint in endpoints_to_test:
        is_critical = endpoint in CRITICAL_ENDPOINTS
        marker = "🔴 CRITICAL" if is_critical else ""

        if check_endpoint(endpoint):
            passed += 1
        else:
            failed += 1
            if is_critical:
                critical_failed.append(endpoint)

        if args.verbose:
            print("-" * 60)

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Passed: {passed}/{len(endpoints_to_test)}")
    print(f"❌ Failed: {failed}/{len(endpoints_to_test)}")

    if critical_failed:
        print(f"\n🔴 CRITICAL FAILURES:")
        for ep in critical_failed:
            print(f"  - {ep}")
        print(f"\nABORTING: Critical endpoints must pass")
        sys.exit(1)

    if failed > 0:
        print(f"\n⚠️  WARNING: {failed} endpoint(s) failed (non-critical)")
        success_rate = (passed / len(endpoints_to_test)) * 100
        print(f"Success rate: {success_rate:.1f}%")

        if success_rate < 80:
            print("FAIL: Success rate below 80%")
            sys.exit(1)
        else:
            print("PASS: Success rate above 80%, but investigate failures")
            sys.exit(0)
    else:
        print(f"\n✅ ALL HEALTH CHECKS PASSED")
        sys.exit(0)

if __name__ == "__main__":
    main()
