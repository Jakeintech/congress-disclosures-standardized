
import requests
import json
import math
import sys

API_BASE = "https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com"

ENDPOINTS = [
    "/v1/analytics/activity",
    "/v1/analytics/top-traders",
    "/v1/analytics/trending-stocks",
    "/v1/congress/bills/118/hr/1",
    "/v1/congress/committees/house/HSAG",
    "/v1/congress/committees/house/hlqj00",
    "/v1/congress/committees/house/HSAG/members",
    "/v1/congress/committees/house/HSAG/bills",
    "/v1/congress/committees/house/HSAG/reports",
    "/v1/trades?limit=10",
    "/v1/members/P000197/trades?limit=5",
    "/v1/congress/members?limit=10"
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
    success = True
    for endpoint in ENDPOINTS:
        if not check_endpoint(endpoint):
            success = False
        print("-" * 20)
    
    if not success:
        sys.exit(1)
    print("ALL HEALTH CHECKS PASSED")

if __name__ == "__main__":
    main()
