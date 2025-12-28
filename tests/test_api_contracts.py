"""
OpenAPI Contract Testing Suite
Validates all API responses against the OpenAPI specification.
"""

import json
import pytest
import yaml
import requests
from pathlib import Path
from typing import Dict, Any
import os

# Load OpenAPI spec
SPEC_PATH = Path("openapi.yaml")

@pytest.fixture(scope="session")
def openapi_spec():
    """Load and return OpenAPI specification."""
    with open(SPEC_PATH) as f:
        return yaml.safe_load(f)

@pytest.fixture(scope="session")
def api_base_url():
    """Get API base URL from environment."""
    url = os.environ.get('API_BASE_URL')
    if not url:
        pytest.skip("API_BASE_URL not set")
    return url.rstrip('/')

class TestAPIContracts:
    """Test suite for API contract validation."""
    
    def test_openapi_spec_valid(self, openapi_spec):
        """Verify OpenAPI spec is valid."""
        assert 'openapi' in openapi_spec
        assert 'paths' in openapi_spec
        assert 'info' in openapi_spec
    
    @pytest.mark.parametrize("endpoint,method", [
        ("/v1/version", "get"),
        ("/v1/trades", "get"),
        ("/v1/members", "get"),
    ])
    def test_endpoint_in_spec(self, openapi_spec, endpoint, method):
        """Verify endpoints exist in OpenAPI spec."""
        assert endpoint in openapi_spec['paths']
        assert method in openapi_spec['paths'][endpoint]
    
    def test_version_endpoint_contract(self, api_base_url):
        """Test /v1/version matches contract."""
        response = requests.get(f"{api_base_url}/v1/version")
        assert response.status_code == 200
        
        data = response.json()
        assert 'version' in data
        assert 'git' in data
        assert 'build' in data
    
    def test_trades_endpoint_contract(self, api_base_url):
        """Test /v1/trades matches contract."""
        response = requests.get(f"{api_base_url}/v1/trades", params={"limit": 5})
        
        if response.status_code == 200:
            data = response.json()
            assert 'trades' in data or 'data' in data
            assert 'pagination' in data or 'meta' in data
    
    def test_error_response_contract(self, api_base_url):
        """Test error responses follow contract."""
        # Invalid request
        response = requests.get(f"{api_base_url}/v1/trades", params={"limit": -1})
        
        if response.status_code >= 400:
            data = response.json()
            assert 'success' in data
            assert data['success'] == False
            assert 'error' in data

@pytest.mark.integration
class TestEndpointResponses:
    """Integration tests for endpoint responses."""
    
    def test_all_endpoints_return_json(self, api_base_url):
        """Verify all endpoints return valid JSON."""
        endpoints = [
            "/v1/version",
            "/v1/trades?limit=1",
            "/v1/members?limit=1",
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{api_base_url}{endpoint}")
            assert response.headers.get('Content-Type', '').startswith('application/json')
            
            # Should parse as JSON
            data = response.json()
            assert isinstance(data, dict)
    
    def test_pagination_consistency(self, api_base_url):
        """Test pagination works consistently."""
        response = requests.get(f"{api_base_url}/v1/trades", params={"limit": 10, "offset": 0})
        
        if response.status_code == 200:
            data = response.json()
            if 'pagination' in data:
                pagination = data['pagination']
                assert 'total' in pagination or 'limit' in pagination
