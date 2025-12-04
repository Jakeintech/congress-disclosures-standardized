"""Unit tests for Congress API client."""

import os
import time
from unittest.mock import Mock, patch, MagicMock

import pytest
import requests

from ingestion.lib.congress_api_client import (
    CongressAPIClient,
    CongressAPIError,
    CongressAPIRateLimitError,
    CongressAPINotFoundError,
)


@pytest.fixture
def api_key():
    """Test API key fixture."""
    return "test_api_key_12345"


@pytest.fixture
def client(api_key):
    """CongressAPIClient fixture with test configuration."""
    return CongressAPIClient(
        api_key=api_key,
        base_url="https://api.test.congress.gov/v3",
        rate_limit_per_hour=10,  # Low limit for faster testing
        timeout=5,
    )


@pytest.fixture
def mock_response():
    """Mock successful API response."""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "member": {
            "bioguideId": "A000360",
            "firstName": "Lamar",
            "lastName": "Alexander",
            "party": "R",
            "state": "TN",
        }
    }
    return response


class TestCongressAPIClientInit:
    """Test CongressAPIClient initialization."""

    def test_init_with_api_key(self, api_key):
        """Test initialization with explicit API key."""
        client = CongressAPIClient(api_key=api_key)
        assert client.api_key == api_key
        assert client.base_url == "https://api.congress.gov/v3"
        assert client.rate_limit_per_hour == 5000

    def test_init_from_env_var(self, api_key):
        """Test initialization from CONGRESS_API_KEY environment variable."""
        with patch.dict(os.environ, {"CONGRESS_API_KEY": api_key}):
            client = CongressAPIClient()
            assert client.api_key == api_key

    def test_init_without_api_key(self):
        """Test initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Congress API key required"):
                CongressAPIClient()

    def test_init_custom_base_url(self, api_key):
        """Test initialization with custom base URL."""
        custom_url = "https://custom.api.url/v3"
        client = CongressAPIClient(api_key=api_key, base_url=custom_url)
        assert client.base_url == custom_url

    def test_init_custom_rate_limit(self, api_key):
        """Test initialization with custom rate limit."""
        client = CongressAPIClient(api_key=api_key, rate_limit_per_hour=1000)
        assert client.rate_limit_per_hour == 1000


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_enforcement(self, client):
        """Test that rate limit is enforced."""
        # Client configured with 10 requests/hour
        # Make 10 requests quickly (should not sleep)
        start = time.time()
        for _ in range(10):
            client._enforce_rate_limit()
        duration = time.time() - start
        assert duration < 1  # Should be nearly instant

        # 11th request should trigger sleep
        start = time.time()
        client._enforce_rate_limit()
        duration = time.time() - start
        assert duration > 0  # Should sleep

    def test_rate_limit_sliding_window(self, client):
        """Test sliding window rate limiting."""
        # Make 5 requests
        for _ in range(5):
            client._enforce_rate_limit()

        # Wait for oldest to age out (simulate 1 hour passing)
        with patch.object(time, "time") as mock_time:
            # Set current time to 1 hour + 1 second in future
            mock_time.return_value = time.time() + 3601
            # Should not sleep now (old requests aged out)
            start = time.time()
            client._enforce_rate_limit()
            duration = time.time() - start
            assert duration < 1


class TestMakeRequest:
    """Test _make_request method."""

    @patch("ingestion.lib.congress_api_client.requests.get")
    def test_make_request_success(self, mock_get, client, mock_response):
        """Test successful API request."""
        mock_get.return_value = mock_response

        result = client._make_request("/member/A000360")

        assert result["member"]["bioguideId"] == "A000360"
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "/member/A000360" in call_args[0][0]
        assert call_args[1]["params"]["api_key"] == client.api_key

    @patch("ingestion.lib.congress_api_client.requests.get")
    def test_make_request_with_params(self, mock_get, client, mock_response):
        """Test API request with query parameters."""
        mock_get.return_value = mock_response

        client._make_request("/bill/118/hr", params={"limit": 50})

        call_args = mock_get.call_args
        assert call_args[1]["params"]["limit"] == 50
        assert call_args[1]["params"]["api_key"] == client.api_key

    @patch("ingestion.lib.congress_api_client.requests.get")
    def test_make_request_rate_limit_error(self, mock_get, client):
        """Test handling of HTTP 429 rate limit error."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_get.return_value = mock_response

        with pytest.raises(CongressAPIRateLimitError):
            client._make_request("/member/A000360")

    @patch("ingestion.lib.congress_api_client.requests.get")
    def test_make_request_not_found_error(self, mock_get, client):
        """Test handling of HTTP 404 not found error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_get.return_value = mock_response

        with pytest.raises(CongressAPINotFoundError):
            client._make_request("/member/INVALID")

    @patch("ingestion.lib.congress_api_client.requests.get")
    def test_make_request_generic_error(self, mock_get, client):
        """Test handling of other HTTP errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_get.return_value = mock_response

        with pytest.raises(CongressAPIError):
            client._make_request("/member/A000360")

    @patch("ingestion.lib.congress_api_client.requests.get")
    def test_make_request_invalid_json(self, mock_get, client):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        with pytest.raises(CongressAPIError, match="Invalid JSON"):
            client._make_request("/member/A000360")


class TestPagination:
    """Test pagination functionality."""

    @patch("ingestion.lib.congress_api_client.requests.get")
    def test_paginate_single_page(self, mock_get, client):
        """Test pagination with single page of results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bills": [
                {"number": 1, "title": "Bill 1"},
                {"number": 2, "title": "Bill 2"},
            ],
            "pagination": {"count": 2},
        }
        mock_get.return_value = mock_response

        items = list(client._paginate("/bill/118/hr"))

        assert len(items) == 2
        assert items[0]["number"] == 1
        assert items[1]["number"] == 2

    @patch("ingestion.lib.congress_api_client.requests.get")
    def test_paginate_multiple_pages(self, mock_get, client):
        """Test pagination with multiple pages."""
        # First page
        page1 = Mock()
        page1.status_code = 200
        page1.json.return_value = {
            "bills": [{"number": 1}, {"number": 2}],
            "pagination": {"count": 4},
        }

        # Second page
        page2 = Mock()
        page2.status_code = 200
        page2.json.return_value = {
            "bills": [{"number": 3}, {"number": 4}],
            "pagination": {"count": 4},
        }

        mock_get.side_effect = [page1, page2]

        items = list(client._paginate("/bill/118/hr"))

        assert len(items) == 4
        assert items[2]["number"] == 3
        assert items[3]["number"] == 4

    @patch("ingestion.lib.congress_api_client.requests.get")
    def test_paginate_with_limit(self, mock_get, client):
        """Test pagination respects limit parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bills": [{"number": i} for i in range(1, 251)],
            "pagination": {"count": 1000},
        }
        mock_get.return_value = mock_response

        items = list(client._paginate("/bill/118/hr", limit=10))

        assert len(items) == 10


class TestMemberEndpoints:
    """Test member-related endpoints."""

    @patch("ingestion.lib.congress_api_client.requests.get")
    def test_get_member(self, mock_get, client, mock_response):
        """Test get_member method."""
        mock_get.return_value = mock_response

        result = client.get_member("A000360")

        assert result["member"]["bioguideId"] == "A000360"
        assert result["member"]["firstName"] == "Lamar"

    @patch("ingestion.lib.congress_api_client.requests.get")
    def test_list_members(self, mock_get, client):
        """Test list_members method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "members": [
                {"bioguideId": "A000360", "name": "Alexander, Lamar"},
                {"bioguideId": "A000370", "name": "Adams, Alma S."},
            ],
            "pagination": {"count": 2},
        }
        mock_get.return_value = mock_response

        members = list(client.list_members(limit=2))

        assert len(members) == 2
        assert members[0]["bioguideId"] == "A000360"


class TestBillEndpoints:
    """Test bill-related endpoints."""

    @patch("ingestion.lib.congress_api_client.requests.get")
    def test_get_bill(self, mock_get, client):
        """Test get_bill method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bill": {
                "congress": 118,
                "type": "HR",
                "number": "1",
                "title": "Lower Energy Costs Act",
            }
        }
        mock_get.return_value = mock_response

        result = client.get_bill(118, "hr", 1)

        assert result["bill"]["title"] == "Lower Energy Costs Act"
        call_args = mock_get.call_args
        assert "/bill/118/hr/1" in call_args[0][0]

    @patch("ingestion.lib.congress_api_client.requests.get")
    def test_list_bills(self, mock_get, client):
        """Test list_bills method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bills": [
                {"number": "1", "title": "Bill 1"},
                {"number": "2", "title": "Bill 2"},
            ],
            "pagination": {"count": 2},
        }
        mock_get.return_value = mock_response

        bills = list(client.list_bills(118, "hr", limit=2))

        assert len(bills) == 2

    @patch("ingestion.lib.congress_api_client.requests.get")
    def test_get_bill_actions(self, mock_get, client):
        """Test get_bill_actions method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "actions": [
                {"actionDate": "2023-01-09", "text": "Introduced in House"}
            ]
        }
        mock_get.return_value = mock_response

        result = client.get_bill_actions(118, "hr", 1)

        assert len(result["actions"]) == 1
        call_args = mock_get.call_args
        assert "/bill/118/hr/1/actions" in call_args[0][0]


class TestVoteEndpoints:
    """Test vote-related endpoints."""

    @patch("ingestion.lib.congress_api_client.requests.get")
    def test_get_house_vote(self, mock_get, client):
        """Test get_house_vote method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "vote": {"rollCall": 42, "question": "On Passage", "result": "Passed"}
        }
        mock_get.return_value = mock_response

        result = client.get_house_vote(118, 1, 42)

        assert result["vote"]["result"] == "Passed"
        call_args = mock_get.call_args
        assert "/vote/118/house/42" in call_args[0][0]


class TestCommitteeEndpoints:
    """Test committee-related endpoints."""

    @patch("ingestion.lib.congress_api_client.requests.get")
    def test_get_committee(self, mock_get, client):
        """Test get_committee method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "committee": {
                "systemCode": "hsif00",
                "name": "Energy and Commerce Committee",
            }
        }
        mock_get.return_value = mock_response

        result = client.get_committee("house", "hsif00")

        assert result["committee"]["name"] == "Energy and Commerce Committee"
        call_args = mock_get.call_args
        assert "/committee/house/hsif00" in call_args[0][0]
