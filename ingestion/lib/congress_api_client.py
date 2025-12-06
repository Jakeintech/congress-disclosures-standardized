"""Congress.gov API client with rate limiting and retry logic.

This module provides a Python client for the Congress.gov API v3 with:
- Rate limiting (5000 requests/hour by default)
- Exponential backoff retry logic
- Pagination support for list endpoints
- Comprehensive error handling

Example usage:
    from ingestion.lib.congress_api_client import CongressAPIClient

    client = CongressAPIClient(api_key="your_key_here")
    member = client.get_member("A000360")
    bills = list(client.list_bills(congress=118, bill_type="hr", limit=100))
"""

import logging
import os
import time
from typing import Any, Dict, Generator, Optional
from datetime import datetime, timezone

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_exception_type,
)
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

logger = logging.getLogger(__name__)

# Congress.gov API defaults
DEFAULT_API_BASE_URL = "https://api.congress.gov/v3"
DEFAULT_RATE_LIMIT_PER_HOUR = 5000
DEFAULT_TIMEOUT_SECONDS = 30


class CongressAPIError(Exception):
    """Base exception for Congress API errors."""

    pass


class CongressAPIRateLimitError(CongressAPIError):
    """Raised when API rate limit is exceeded (HTTP 429)."""

    pass


class CongressAPINotFoundError(CongressAPIError):
    """Raised when resource not found (HTTP 404)."""

    pass


class CongressAPIClient:
    """Client for Congress.gov API v3 with rate limiting and retry logic.

    Attributes:
        api_key: Congress.gov API key
        base_url: API base URL (default: https://api.congress.gov/v3)
        rate_limit_per_hour: Max requests per hour (default: 5000)
        timeout: Request timeout in seconds (default: 30)

    Example:
        >>> client = CongressAPIClient(api_key=os.environ["CONGRESS_API_KEY"])
        >>> member = client.get_member("A000360")
        >>> print(member["member"]["firstName"], member["member"]["lastName"])
        Lamar Alexander
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        rate_limit_per_hour: Optional[int] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        """Initialize Congress API client.

        Args:
            api_key: Congress.gov API key (defaults to CONGRESS_API_KEY env var)
            base_url: API base URL (defaults to https://api.congress.gov/v3)
            rate_limit_per_hour: Max requests/hour (defaults to 5000)
            timeout: Request timeout in seconds (defaults to 30)

        Raises:
            ValueError: If API key is not provided and not in environment
        """
        self.api_key = api_key or os.environ.get("CONGRESS_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Congress API key required. Provide via api_key parameter or "
                "CONGRESS_API_KEY environment variable."
            )

        self.base_url = base_url or os.environ.get(
            "CONGRESS_API_BASE_URL", DEFAULT_API_BASE_URL
        )
        self.rate_limit_per_hour = rate_limit_per_hour or DEFAULT_RATE_LIMIT_PER_HOUR
        self.timeout = timeout

        # Rate limiting state (simple in-memory tracking)
        self._request_timestamps = []
        self._min_interval = 3600.0 / self.rate_limit_per_hour  # seconds between requests

        logger.info(
            f"Initialized CongressAPIClient: base_url={self.base_url}, "
            f"rate_limit={self.rate_limit_per_hour}/hour"
        )

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limit by sleeping if necessary.

        Uses a sliding window approach: tracks last N requests and ensures
        we don't exceed rate_limit_per_hour requests in any 1-hour window.
        """
        now = time.time()

        # Remove requests older than 1 hour
        cutoff = now - 3600
        self._request_timestamps = [
            ts for ts in self._request_timestamps if ts > cutoff
        ]

        # If at limit, sleep until oldest request falls outside window
        if len(self._request_timestamps) >= self.rate_limit_per_hour:
            oldest = self._request_timestamps[0]
            sleep_time = oldest + 3600 - now
            if sleep_time > 0:
                logger.warning(
                    f"Rate limit reached ({self.rate_limit_per_hour}/hour). "
                    f"Sleeping {sleep_time:.1f}s"
                )
                time.sleep(sleep_time)

        # Record this request
        self._request_timestamps.append(time.time())

    @retry(
        retry=retry_if_exception_type((requests.exceptions.RequestException, CongressAPIRateLimitError)),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP GET request to Congress.gov API with retry logic.

        Args:
            endpoint: API endpoint path (e.g., "/member/A000360")
            params: Optional query parameters

        Returns:
            Parsed JSON response as dict

        Raises:
            CongressAPIRateLimitError: If rate limit exceeded (HTTP 429)
            CongressAPINotFoundError: If resource not found (HTTP 404)
            CongressAPIError: For other API errors
            requests.exceptions.RequestException: For network errors
        """
        # Enforce rate limit before making request
        self._enforce_rate_limit()

        # Build URL and add API key
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        params["api_key"] = self.api_key

        # Log request (without API key)
        safe_params = {k: v for k, v in params.items() if k != "api_key"}
        logger.debug(f"GET {url} params={safe_params}")

        # Make request
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.error(f"Rate limit exceeded: {e}")
                raise CongressAPIRateLimitError(f"Rate limit exceeded: {e}") from e
            elif e.response.status_code == 404:
                logger.warning(f"Resource not found: {url}")
                raise CongressAPINotFoundError(f"Resource not found: {url}") from e
            else:
                logger.error(f"API error: {e}")
                raise CongressAPIError(f"API error: {e}") from e

        # Parse JSON
        try:
            data = response.json()
        except ValueError as e:
            logger.error(f"Invalid JSON response: {e}")
            raise CongressAPIError(f"Invalid JSON response: {e}") from e

        return data

    def _paginate(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Paginate through a list endpoint.

        Yields individual items from paginated API responses. Handles Congress.gov
        pagination automatically (offset-based).

        Args:
            endpoint: API endpoint path (e.g., "/bill/118/hr")
            params: Optional query parameters
            limit: Max items to yield (None = all)

        Yields:
            Individual items from the API response

        Example:
            >>> for bill in client._paginate("/bill/118/hr", limit=100):
            ...     print(bill["title"])
        """
        params = params or {}
        offset = 0
        limit_per_page = 250  # Congress.gov API max
        total_yielded = 0

        while True:
            # Set pagination params
            params["offset"] = offset
            params["limit"] = limit_per_page

            # Fetch page
            response = self._make_request(endpoint, params)

            # Extract items (varies by endpoint)
            # Most endpoints: response["bills"], response["members"], etc.
            # Try to auto-detect the list key
            items = None
            for key in ["bills", "members", "votes", "committees", "amendments"]:
                if key in response:
                    items = response[key]
                    break

            if items is None:
                logger.warning(f"No items found in response keys: {response.keys()}")
                break

            # Yield items
            for item in items:
                yield item
                total_yielded += 1
                if limit and total_yielded >= limit:
                    return

            # Check if more pages
            pagination = response.get("pagination", {})
            total_count = pagination.get("count", 0)
            if offset + limit_per_page >= total_count:
                break  # No more pages

            offset += limit_per_page

    # ==========================================================================
    # Member Endpoints
    # ==========================================================================

    def get_member(self, bioguide_id: str) -> Dict[str, Any]:
        """Get member details by bioguide ID.

        Args:
            bioguide_id: Bioguide ID (e.g., "A000360")

        Returns:
            Member data dict (includes member info, terms, etc.)

        Example:
            >>> member = client.get_member("A000360")
            >>> print(member["member"]["firstName"])
            Lamar
        """
        endpoint = f"/member/{bioguide_id}"
        return self._make_request(endpoint)

    def list_members(
        self, chamber: Optional[str] = None, limit: Optional[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """List all members.

        Args:
            chamber: Filter by chamber ("house" or "senate")
            limit: Max members to return (None = all)

        Yields:
            Member summary dicts

        Example:
            >>> for member in client.list_members(chamber="house", limit=10):
            ...     print(member["name"])
        """
        endpoint = "/member"
        params = {}
        if chamber:
            params["currentMember"] = "true"  # Only current members have chamber

        yield from self._paginate(endpoint, params, limit)

    # ==========================================================================
    # Bill Endpoints
    # ==========================================================================

    def get_bill(self, congress: int, bill_type: str, bill_number: int) -> Dict[str, Any]:
        """Get bill details.

        Args:
            congress: Congress number (e.g., 118)
            bill_type: Bill type ("hr", "s", "hjres", "sjres", etc.)
            bill_number: Bill number (e.g., 1)

        Returns:
            Bill data dict

        Example:
            >>> bill = client.get_bill(118, "hr", 1)
            >>> print(bill["bill"]["title"])
        """
        endpoint = f"/bill/{congress}/{bill_type}/{bill_number}"
        return self._make_request(endpoint)

    def list_bills(
        self,
        congress: int,
        bill_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """List bills for a Congress.

        Args:
            congress: Congress number (e.g., 118)
            bill_type: Optional bill type filter ("hr", "s", etc.)
            limit: Max bills to return (None = all)

        Yields:
            Bill summary dicts

        Example:
            >>> for bill in client.list_bills(118, "hr", limit=100):
            ...     print(bill["number"], bill["title"])
        """
        if bill_type:
            endpoint = f"/bill/{congress}/{bill_type}"
        else:
            endpoint = f"/bill/{congress}"

        yield from self._paginate(endpoint, limit=limit)

    def get_bill_actions(
        self, congress: int, bill_type: str, bill_number: int
    ) -> Dict[str, Any]:
        """Get bill actions (legislative timeline).

        Args:
            congress: Congress number
            bill_type: Bill type
            bill_number: Bill number

        Returns:
            Actions data dict

        Example:
            >>> actions = client.get_bill_actions(118, "hr", 1)
            >>> for action in actions["actions"]:
            ...     print(action["actionDate"], action["text"])
        """
        endpoint = f"/bill/{congress}/{bill_type}/{bill_number}/actions"
        return self._make_request(endpoint)

    def get_bill_cosponsors(
        self, congress: int, bill_type: str, bill_number: int
    ) -> Dict[str, Any]:
        """Get bill cosponsors.

        Args:
            congress: Congress number
            bill_type: Bill type
            bill_number: Bill number

        Returns:
            Cosponsors data dict

        Example:
            >>> cosponsors = client.get_bill_cosponsors(118, "hr", 1)
            >>> print(len(cosponsors["cosponsors"]))
        """
        endpoint = f"/bill/{congress}/{bill_type}/{bill_number}/cosponsors"
        return self._make_request(endpoint)

    def get_bill_committees(
        self, congress: int, bill_type: str, bill_number: int
    ) -> Dict[str, Any]:
        """Get bill committee referrals.

        Args:
            congress: Congress number
            bill_type: Bill type
            bill_number: Bill number

        Returns:
            Committees data dict
        """
        endpoint = f"/bill/{congress}/{bill_type}/{bill_number}/committees"
        return self._make_request(endpoint)

    def get_bill_subjects(
        self, congress: int, bill_type: str, bill_number: int
    ) -> Dict[str, Any]:
        """Get bill subjects (policy areas, legislative subjects).

        Args:
            congress: Congress number
            bill_type: Bill type
            bill_number: Bill number

        Returns:
            Subjects data dict
        """
        endpoint = f"/bill/{congress}/{bill_type}/{bill_number}/subjects"
        return self._make_request(endpoint)

    def get_bill_titles(
        self, congress: int, bill_type: str, bill_number: int
    ) -> Dict[str, Any]:
        """Get all bill titles (short, long, official).

        Args:
            congress: Congress number
            bill_type: Bill type
            bill_number: Bill number

        Returns:
            Titles data dict
        """
        endpoint = f"/bill/{congress}/{bill_type}/{bill_number}/titles"
        return self._make_request(endpoint)

    # ==========================================================================
    # Vote Endpoints
    # ==========================================================================

    def get_house_vote(self, congress: int, session: int, roll_call: int) -> Dict[str, Any]:
        """Get House roll call vote.

        Args:
            congress: Congress number
            session: Session number (1 or 2)
            roll_call: Roll call vote number

        Returns:
            Vote data dict (includes member votes)

        Example:
            >>> vote = client.get_house_vote(118, 1, 42)
            >>> print(vote["vote"]["question"], vote["vote"]["result"])
        """
        endpoint = f"/vote/{congress}/house/{roll_call}"
        return self._make_request(endpoint)

    def get_senate_vote(self, congress: int, session: int, roll_call: int) -> Dict[str, Any]:
        """Get Senate roll call vote.

        Args:
            congress: Congress number
            session: Session number (1 or 2)
            roll_call: Roll call vote number

        Returns:
            Vote data dict
        """
        endpoint = f"/vote/{congress}/senate/{roll_call}"
        return self._make_request(endpoint)

    # ==========================================================================
    # Committee Endpoints
    # ==========================================================================

    def get_committee(self, chamber: str, committee_code: str) -> Dict[str, Any]:
        """Get committee details.

        Args:
            chamber: Chamber ("house", "senate", or "joint")
            committee_code: Committee system code (e.g., "hsif00")

        Returns:
            Committee data dict

        Example:
            >>> committee = client.get_committee("house", "hsif00")
            >>> print(committee["committee"]["name"])
        """
        endpoint = f"/committee/{chamber}/{committee_code}"
        return self._make_request(endpoint)

    def list_committees(
        self, chamber: Optional[str] = None, limit: Optional[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """List committees.

        Args:
            chamber: Filter by chamber ("house", "senate", "joint")
            limit: Max committees to return (None = all)

        Yields:
            Committee summary dicts
        """
        if chamber:
            endpoint = f"/committee/{chamber}"
        else:
            endpoint = "/committee"

        yield from self._paginate(endpoint, limit=limit)
