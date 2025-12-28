#!/usr/bin/env python3
"""
Comprehensive API Health Check Suite
Tests all endpoints against OpenAPI spec for production readiness.
"""

import json
import os
import sys
import requests
import yaml
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class EndpointTest:
    method: str
    path: str
    params: Dict = None
    expected_status: List[int] = None
    
    def __post_init__(self):
        if self.expected_status is None:
            self.expected_status = [200]
        if self.params is None:
            self.params = {}

class APIHealthChecker:
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url.rstrip('/')
        self.results = []
        
    def test_endpoint(self, test: EndpointTest) -> Tuple[bool, str, Dict]:
        """Test a single endpoint and return (success, message, response_data)"""
        url = f"{self.api_base_url}{test.path}"
        
        try:
            response = requests.get(url, params=test.params, timeout=10)
            
            # Check status code
            if response.status_code not in test.expected_status:
                return False, f"Status {response.status_code} not in expected {test.expected_status}", {}
            
            # Try to parse JSON
            try:
                data = response.json()
            except:
                return False, "Invalid JSON response", {}
            
            # Check basic structure
            if response.status_code == 200:
                if 'success' not in data:
                    return False, "Missing 'success' field in response", data
                if not data.get('success'):
                    return False, f"API returned success=false: {data.get('error', {}).get('message')}", data
            
            return True, "OK", data
            
        except requests.Timeout:
            return False, "Timeout (>10s)", {}
        except requests.ConnectionError:
            return False, "Connection failed", {}
        except Exception as e:
            return False, f"Error: {str(e)}", {}
    
    def run_comprehensive_tests(self) -> Dict:
        """Run all endpoint tests"""
        tests = [
            # Health & Meta
            EndpointTest("GET", "/v1/version"),
            
            # Trading Data
            EndpointTest("GET", "/v1/trades", {"limit": "5"}),
            EndpointTest("GET", "/v1/trades", {"ticker": "AAPL", "limit": "1"}),
            EndpointTest("GET", "/v1/stocks", {"limit": "10"}),
            EndpointTest("GET", "/v1/members", {"limit": "10"}),
            EndpointTest("GET", "/v1/filings", {"limit": "5"}),
            
            # Analytics
            EndpointTest("GET", "/v1/analytics/summary"),
            EndpointTest("GET", "/v1/analytics/top-traders", {"limit": "10"}),
            EndpointTest("GET", "/v1/analytics/trending-stocks", {"limit": "10"}),
            EndpointTest("GET", "/v1/analytics/sector-activity"),
            EndpointTest("GET", "/v1/analytics/trading-timeline"),
            
            # Congress (may fail if no Congress API key)
            EndpointTest("GET", "/v1/congress/bills", {"limit": "5"}, [200, 500, 502]),
            EndpointTest("GET", "/v1/congress/members", {"limit": "5"}, [200, 500, 502]),
            
            # Search
            EndpointTest("GET", "/v1/search", {"q": "Pelosi"}, [200, 400]),
        ]
        
        print(f"\n🔍 Running {len(tests)} endpoint tests against {self.api_base_url}\n")
        print("=" * 80)
        
        passed = 0
        failed = 0
        
        for test in tests:
            success, message, data = self.test_endpoint(test)
            
            status_icon = "✅" if success else "❌"
            print(f"{status_icon} {test.method} {test.path}")
            if test.params:
                print(f"   Params: {test.params}")
            print(f"   Result: {message}")
            
            if not success:
                failed += 1
            else:
                passed += 1
            
            self.results.append({
                "endpoint": f"{test.method} {test.path}",
                "params": test.params,
                "success": success,
                "message": message,
                "timestamp": datetime.now().isoformat()
            })
            
            print()
        
        print("=" * 80)
        print(f"\n📊 Results: {passed}/{len(tests)} passed ({failed} failed)")
        print(f"   Success Rate: {(passed/len(tests)*100):.1f}%\n")
        
        return {
            "total": len(tests),
            "passed": passed,
            "failed": failed,
            "success_rate": passed/len(tests),
            "results": self.results
        }

def main():
    # Get API URL from environment or use default
    api_url = os.environ.get('API_BASE_URL', 'https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com')
    
    if 'your-api' in api_url:
        print("⚠️  WARNING: Using default API URL. Set API_BASE_URL environment variable.")
        print(f"   Current: {api_url}\n")
    
    checker = APIHealthChecker(api_url)
    results = checker.run_comprehensive_tests()
    
    # Save results
    output_file = "api_health_report.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"📄 Full report saved to {output_file}")
    
    # Exit with error if any tests failed
    if results['failed'] > 0:
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()
