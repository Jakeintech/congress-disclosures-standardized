
import requests
import sys
import json
import os
from datetime import datetime

# Configuration
API_BASE = os.environ.get('API_GATEWAY_URL', 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com')
HEADERS = {'User-Agent': 'CongressDisclosuresVerification/1.0'}

# Test Data Constants
TEST_CONGRESS = 119
TEST_BILL_ID = "119-sconres-23" # Known existing bill from previous task
TEST_MEMBER_ID = "P000197" # Nancy Pelosi
TEST_TICKER = "AAPL"
TEST_YEAR = 2025

def test_endpoint(name, method, path, params=None, expected_status=200):
    url = f"{API_BASE}{path}"
    print(f"Testing {name}: {method} {url} ...", end=" ", flush=True)
    
    try:
        if method == 'GET':
            response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        
        status = response.status_code
        if status == expected_status:
            try:
                data = response.json()
                # Check standard wrapper if applicable
                is_valid = True
                if 'data' in data:
                    is_valid = True
                elif 'results' in data and name == 'search': # Special case for search? Spec says data.results
                     pass
                
                print(f"✅ OK ({response.elapsed.total_seconds():.2f}s)")
                return True, data
            except json.JSONDecodeError:
                print(f"❌ FAIL (Invalid JSON)")
                return False, None
        else:
            print(f"❌ FAIL (Status {status})")
            print(f"  Response: {response.text[:200]}")
            return False, None
            
    except Exception as e:
        print(f"❌ ERROR ({str(e)})")
        return False, None

def run_verification():
    print(f"Starting API Verification against {API_BASE}")
    print("=" * 60)
    
    failures = []
    
    # 1. System Endpoints
    # -------------------
    ok, _ = test_endpoint("System Costs", "GET", "/v1/costs")
    if not ok: failures.append("System Costs")

    # 2. Member Endpoints
    # -------------------
    ok, _ = test_endpoint("List Members", "GET", "/v1/members", {'limit': 5})
    if not ok: failures.append("List Members")
    
    ok, _ = test_endpoint("Member Profile", "GET", f"/v1/members/{TEST_MEMBER_ID}")
    if not ok: failures.append("Member Profile")
    
    ok, _ = test_endpoint("Member Trades", "GET", f"/v1/members/{TEST_MEMBER_ID}/trades", {'limit': 5})
    if not ok: failures.append("Member Trades")
    
    ok, _ = test_endpoint("Member Portfolio", "GET", f"/v1/members/{TEST_MEMBER_ID}/portfolio")
    if not ok: failures.append("Member Portfolio")

    # 3. Trading Endpoints
    # --------------------
    ok, _ = test_endpoint("List Trades", "GET", "/v1/trades", {'limit': 5})
    if not ok: failures.append("List Trades")
    
    ok, _ = test_endpoint("Stock Summary", "GET", f"/v1/stocks/{TEST_TICKER}")
    if not ok: failures.append("Stock Summary")
    
    ok, _ = test_endpoint("Stock Activity", "GET", f"/v1/stocks/{TEST_TICKER}/activity")
    if not ok: failures.append("Stock Activity")
    
    ok, _ = test_endpoint("List Stocks", "GET", "/v1/stocks", {'limit': 5})
    if not ok: failures.append("List Stocks")

    # 4. Analytics Endpoints
    # ----------------------
    ok, _ = test_endpoint("Platform Summary", "GET", "/v1/analytics/summary")
    if not ok: failures.append("Platform Summary")
    
    ok, _ = test_endpoint("Top Traders", "GET", "/v1/analytics/top-traders", {'limit': 5})
    if not ok: failures.append("Top Traders")
    
    ok, _ = test_endpoint("Trending Stocks", "GET", "/v1/analytics/trending-stocks", {'limit': 5})
    if not ok: failures.append("Trending Stocks")
    
    ok, _ = test_endpoint("Sector Activity", "GET", "/v1/analytics/sector-activity")
    if not ok: failures.append("Sector Activity")
    
    ok, _ = test_endpoint("Compliance", "GET", "/v1/analytics/compliance")
    if not ok: failures.append("Compliance")
    
    ok, _ = test_endpoint("Trading Timeline", "GET", "/v1/analytics/trading-timeline")
    if not ok: failures.append("Trading Timeline")

    # 5. Search & Filings
    # -------------------
    ok, _ = test_endpoint("Search", "GET", "/v1/search", {'q': 'pelosi'})
    if not ok: failures.append("Search")
    
    # Get a filing ID first
    ok, data = test_endpoint("List Filings", "GET", "/v1/filings", {'limit': 1})
    if not ok: 
        failures.append("List Filings")
    else:
        # Try to get a valid doc_id for details check
        try:
            filings = data.get('data', [])
            if filings:
                doc_id = filings[0].get('doc_id') or filings[0].get('document_id')
                if doc_id:
                   test_endpoint("Filing Details", "GET", f"/v1/filings/{doc_id}")
            else:
                print("  Skipping Filing Details (No filings found)")
        except:
             print("  Skipping Filing Details (Error parsing list)")

    # 6. Congress Endpoints
    # ---------------------
    ok, _ = test_endpoint("List Bills", "GET", "/v1/congress/bills", {'congress': TEST_CONGRESS, 'limit': 5})
    if not ok: failures.append("List Bills")
    
    ok, _ = test_endpoint("Bill Detail", "GET", f"/v1/congress/bills/{TEST_BILL_ID}")
    if not ok: failures.append("Bill Detail")

    ok, _ = test_endpoint("Bill Text", "GET", f"/v1/congress/bills/{TEST_BILL_ID}/text")
    if not ok: failures.append("Bill Text")
    
    ok, _ = test_endpoint("List Congress Members", "GET", "/v1/congress/members", {'limit': 5})
    if not ok: failures.append("List Congress Members")
    
    ok, _ = test_endpoint("Congress Member Detail", "GET", f"/v1/congress/members/{TEST_MEMBER_ID}")
    if not ok: failures.append("Congress Member Detail")

    # 7. Lobbying Endpoints
    # ---------------------
    ok, _ = test_endpoint("Lobbying Filings", "GET", "/v1/lobbying/filings", {'limit': 5, 'filing_year': 2024})
    if not ok: failures.append("Lobbying Filings")
    
    ok, _ = test_endpoint("Lobbying Network", "GET", "/v1/lobbying/network", {'year': 2024, 'limit': 10})
    if not ok: failures.append("Lobbying Network")
    
    ok, _ = test_endpoint("Triple Correlations", "GET", "/v1/correlations/triple", {'year': 2024, 'limit': 5})
    if not ok: failures.append("Triple Correlations")


    print("=" * 60)
    if failures:
        print(f"FAILED: {len(failures)} endpoints failed verification.")
        print("\n".join(f"- {f}" for f in failures))
        sys.exit(1)
    else:
        print("SUCCESS: All endpoints verified successfully.")
        sys.exit(0)

if __name__ == "__main__":
    run_verification()
