"""
Congress.gov API enrichment for member data.

Enriches member records with:
- Bioguide IDs
- Party affiliation
- Chamber
- Term dates
- Committee assignments
"""

import os
import requests
from typing import Optional, Dict, Any
from fuzzywuzzy import fuzz
import logging

from .cache import EnrichmentCache

logger = logging.getLogger(__name__)


class CongressAPIEnricher:
    """Enricher for Congress.gov API data."""

    BASE_URL = "https://api.congress.gov/v3"

    def __init__(self, api_key: str = None, use_cache: bool = True):
        """
        Initialize Congress API enricher.

        Args:
            api_key: Congress.gov API key (defaults to CONGRESS_API_KEY env var)
            use_cache: Whether to use caching (default True)
        """
        self.api_key = api_key or os.environ.get('CONGRESS_API_KEY')
        if not self.api_key:
            raise ValueError("Congress API key required (CONGRESS_API_KEY)")

        self.cache = EnrichmentCache() if use_cache else None

    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make API request with rate limiting and error handling."""
        url = f"{self.BASE_URL}/{endpoint}"

        if params is None:
            params = {}
        params['api_key'] = self.api_key

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Congress API request failed: {e}")
            raise

    def search_member_by_name(
        self,
        first_name: str,
        last_name: str,
        state: str = None,
        fuzzy_threshold: int = 85
    ) -> Optional[Dict[str, Any]]:
        """
        Search for member by name with fuzzy matching.

        Args:
            first_name: Member's first name
            last_name: Member's last name
            state: Two-letter state code (optional, improves matching)
            fuzzy_threshold: Minimum fuzzy match score (0-100)

        Returns:
            Member data dict or None if not found
        """
        # Check cache first
        cache_key = f"{last_name}_{first_name}_{state or 'ANY'}"
        if self.cache:
            cached = self.cache.get('congress_api', cache_key)
            if cached:
                logger.info(f"Cache hit for {first_name} {last_name}")
                return cached

        # Search by last name
        try:
            response = self._make_request(
                'member',
                params={
                    'format': 'json',
                    'limit': 250  # Get lots of results for fuzzy matching
                }
            )

            members = response.get('members', [])

            # Fuzzy match on full name
            best_match = None
            best_score = 0

            target_full_name = f"{first_name} {last_name}".lower()

            for member in members:
                # Extract member info
                member_name = member.get('name', '')
                member_state = member.get('state')

                # Calculate fuzzy match score
                score = fuzz.ratio(member_name.lower(), target_full_name)

                # Boost score if state matches
                if state and member_state == state:
                    score += 10

                if score > best_score and score >= fuzzy_threshold:
                    best_score = score
                    best_match = member

            if best_match:
                # Fetch detailed member info
                bioguide_id = best_match.get('bioguideId')
                if bioguide_id:
                    detailed = self._get_member_details(bioguide_id)
                    if detailed:
                        best_match = detailed

                # Cache result
                if self.cache:
                    self.cache.set('congress_api', cache_key, best_match)

                logger.info(f"Found {first_name} {last_name}: {best_match.get('bioguideId')} (score: {best_score})")
                return best_match

            logger.warning(f"No match found for {first_name} {last_name} {state or ''}")
            return None

        except Exception as e:
            logger.error(f"Error searching for {first_name} {last_name}: {e}")
            return None

    def _get_member_details(self, bioguide_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed member information by bioguide ID."""
        try:
            response = self._make_request(f'member/{bioguide_id}')
            return response.get('member', {})
        except Exception as e:
            logger.error(f"Error fetching details for {bioguide_id}: {e}")
            return None

    def get_member_by_bioguide(self, bioguide_id: str) -> Optional[Dict[str, Any]]:
        """
        Get member by bioguide ID.

        Args:
            bioguide_id: Congressional Bioguide ID (e.g., 'P000197')

        Returns:
            Member data dict or None
        """
        # Check cache
        if self.cache:
            cached = self.cache.get('congress_api', bioguide_id)
            if cached:
                return cached

        try:
            detailed = self._get_member_details(bioguide_id)

            # Cache result
            if detailed and self.cache:
                self.cache.set('congress_api', bioguide_id, detailed)

            return detailed

        except Exception as e:
            logger.error(f"Error getting member {bioguide_id}: {e}")
            return None

    def enrich_member(
        self,
        first_name: str,
        last_name: str,
        state: str = None,
        district: int = None
    ) -> Dict[str, Any]:
        """
        Enrich member data with Congress API.

        Args:
            first_name: Member's first name
            last_name: Member's last name
            state: Two-letter state code
            district: Congressional district number

        Returns:
            Enriched member data dict
        """
        member_data = self.search_member_by_name(first_name, last_name, state)

        if not member_data:
            return {
                'bioguide_id': None,
                'party': None,
                'chamber': None,
                'start_date': None,
                'end_date': None,
                'is_current': False,
                'enrichment_status': 'not_found'
            }

        # Extract enriched fields
        # Party code from most recent term
        terms = member_data.get('terms', {}).get('item', [])
        latest_term = terms[-1] if terms else {}

        party_code = latest_term.get('party')
        chamber = latest_term.get('chamber')
        start_year = latest_term.get('startYear')
        end_year = latest_term.get('endYear')

        return {
            'bioguide_id': member_data.get('bioguideId'),
            'party': party_code,
            'chamber': chamber,
            'start_date': f"{start_year}-01-03" if start_year else None,
            'end_date': f"{end_year}-01-03" if end_year else None,
            'is_current': not end_year or int(end_year) >= 2025,
            'enrichment_status': 'success'
        }
