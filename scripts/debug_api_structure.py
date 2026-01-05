
import requests
import json
import os

API_BASE = os.environ.get('API_GATEWAY_URL', 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com')
HEADERS = {'User-Agent': 'CongressDisclosuresDebug/1.0'}

def inspect_endpoint(path, name):
    url = f"{API_BASE}{path}"
    print(f"\n--- Checking {name} ({url}) ---")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f"Status: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"Error Body: {resp.text[:300]}")
            return

        data = resp.json()
        
        if isinstance(data, dict):
            print("Root Type: dict")
            print(f"Root Keys: {list(data.keys())}")
            
            if 'data' in data:
                d = data['data']
                print(f"data Type: {type(d)}")
                if isinstance(d, dict):
                    print(f"data Keys: {list(d.keys())}")
                    if 'items' in d:
                        print(f"data.items Length: {len(d['items'])}")
                        if len(d['items']) > 0:
                            print(f"data.items[0] Keys: {list(d['items'][0].keys())}")
                elif isinstance(d, list):
                    print(f"data Length: {len(d)}")
                    if len(d) > 0:
                        print(f"data[0] Keys: {list(d[0].keys())}")
            
            if 'pagination' in data:
                 print(f"pagination: {data['pagination']}")

        elif isinstance(data, list):
            print("Root Type: list")
            print(f"Root Length: {len(data)}")
            if len(data) > 0:
                print(f"Root[0] Keys: {list(data[0].keys())}")
                
    except Exception as e:
        print(f"Exception: {e}")

print("Debugging API Structure to fix Integration Hell...")

# 1. Members
inspect_endpoint("/v1/members?limit=1", "GET /v1/members")
inspect_endpoint("/v1/congress/members?limit=1", "GET /v1/congress/members")

# 2. Trades
inspect_endpoint("/v1/trades?limit=1", "GET /v1/trades")

# 3. Top Traders
inspect_endpoint("/v1/analytics/top-traders?limit=1", "GET /v1/analytics/top-traders")

# 4. Network Graph
inspect_endpoint("/v1/network-graph?limit=10", "GET /v1/network-graph")

# 5. Bill Details (Known ID)
inspect_endpoint("/v1/congress/bills/119-sconres-23", "GET Bill Detail")
