"""
Congress.gov API enrichment for member data.

Enriches member records with:
- Bioguide IDs
- Party affiliation
- Chamber
- Term dates
- Committee assignments

Features:
- Graceful fallback when API unavailable
- Validation of API responses
- Reference data fallback for common members
"""

import os
import requests
from typing import Optional, Dict, Any
from fuzzywuzzy import fuzz
import logging
import time

from .cache import EnrichmentCache

try:
    from ..api_contracts import (
        validate_enriched_member, 
        validate_member_list_response,
        CongressMemberResponse, 
        EnrichedMemberData
    )
except ImportError:
    # Fallback if contracts not available
    def validate_enriched_member(data):
        return data
    
    def validate_member_list_response(data):
        return data

logger = logging.getLogger(__name__)


class CongressAPIEnricher:
    """Enricher for Congress.gov API data."""

    BASE_URL = "https://api.congress.gov/v3"

    def __init__(self, api_key: str = None, use_cache: bool = True, fallback_enabled: bool = True):
        """
        Initialize Congress API enricher.

        Args:
            api_key: Congress.gov API key (defaults to CONGRESS_API_KEY env var)
            use_cache: Whether to use caching (default True)
            fallback_enabled: Whether to use reference data fallback (default True)
        """
        self.api_key = api_key or os.environ.get('CONGRESS_API_KEY') or os.environ.get('CONGRESS_GOV_API_KEY')
        self.fallback_enabled = fallback_enabled
        
        if not self.api_key:
            if fallback_enabled:
                logger.warning("Congress API key not found. Will use fallback reference data.")
            else:
                raise ValueError("Congress API key required (CONGRESS_API_KEY)")
        else:
            logger.info(f"Congress API key loaded: {self.api_key[:4]}...{self.api_key[-4:]}")

        self.cache = EnrichmentCache() if use_cache else None
        self._request_count = 0
        self._success_count = 0
        self._fallback_count = 0

    def _make_request(self, endpoint: str, params: Dict[str, Any] = None, retry_count: int = 3) -> Optional[Dict[str, Any]]:
        """Make API request with rate limiting, retries, and error handling."""
        if not self.api_key:
            logger.debug("No API key available, skipping request")
            return None
            
        url = f"{self.BASE_URL}/{endpoint}"

        if params is None:
            params = {}
        params['api_key'] = self.api_key

        for attempt in range(retry_count):
            try:
                self._request_count += 1
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 403:
                    logger.error("API Key Invalid or Expired (403 Forbidden)")
                    return None
                    
                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Congress API request failed after {retry_count} attempts: {e}")
                    return None
        
        return None

    def _fetch_all_members(self) -> list:
        """
        Fetch ALL members from Congress API with pagination.
        Returns cached list if available.
        """
        # Check memory cache first
        if hasattr(self, '_all_members_cache') and self._all_members_cache:
            return self._all_members_cache

        if not self.api_key:
            logger.warning("No API key available for fetching all members")
            return []

        all_members = []
        offset = 0
        limit = 250
        
        logger.info("Fetching full member list from Congress API...")
        
        while True:
            response = self._make_request(
                'member',
                params={
                    'format': 'json',
                    'limit': limit,
                    'offset': offset
                }
            )
            
            if not response:
                break
            
            # Validate response contract
            try:
                validated = validate_member_list_response(response)
                page_members = validated.get('members', [])
            except ValueError as e:
                logger.error(f"API contract violation: {e}")
                break
                
            if not page_members:
                break
                
            all_members.extend(page_members)
            logger.info(f"  Fetched {len(page_members)} members (total: {len(all_members)})")
            
            if len(page_members) < limit:
                break
                
            offset += limit
            
        self._all_members_cache = all_members
        logger.info(f"Cached {len(all_members)} total members")
        return all_members

    def search_member_by_name(
        self,
        first_name: str,
        last_name: str,
        state: str = None,
        fuzzy_threshold: int = 70
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
                # logger.info(f"Cache hit for {first_name} {last_name}")
                return cached

        # Get full member list (cached)
        members = self._fetch_all_members()
        
        if not members:
            logger.warning("No members found in API cache")
            return None
        
        logger.debug(f"Searching {len(members)} members for '{first_name} {last_name}'")
        logger.debug(f"First 3 members in list: {[m.get('name', 'NO NAME') for m in members[:3]]}")

        # Fuzzy match on full name
        best_match = None
        best_score = 0

        # Normalize target name
        target_first = first_name.lower().strip()
        target_last = last_name.lower().strip()
        target_full = f"{target_first} {target_last}"
        
        # Also create "last first" format for matching (API returns "Last, First")
        target_last_first = f"{target_last} {target_first}"
        
        # Convert state code to full name for API matching (API uses "New Jersey" not "NJ")
        try:
            from ..state_mapping import STATE_CODE_TO_NAME
            state_full_name = STATE_CODE_TO_NAME.get(state) if state else None
        except ImportError:
            state_full_name = None

        for i, member in enumerate(members):
            # Extract member info
            member_name = member.get('name', '')
            member_state = member.get('state')
            
            # Debug first few members to see name format
            if i < 3:
                logger.debug(f"Sample member {i}: name='{member_name}', state={member_state}")
            
            # Skip if state provided and doesn't match
            # API returns full state name like "New Jersey", not "NJ"
            if state_full_name and member_state and member_state != state_full_name:
                continue

            # Clean member name (remove comma, normalize)
            # API returns "Last, First" format
            member_name_clean = member_name.replace(',', '').lower().strip()

            # Calculate fuzzy match score using multiple strategies
            # 1. Token Sort Ratio (handles word order variations)
            score1 = fuzz.token_sort_ratio(member_name_clean, target_full)
            score2 = fuzz.token_sort_ratio(member_name_clean, target_last_first)
            
            # 2. Partial Ratio (handles "Robert Stephens" vs "Robert Christopher Stephens")
            score3 = fuzz.partial_ratio(member_name_clean, target_full)
            score4 = fuzz.partial_ratio(member_name_clean, target_last_first)
            
            # Take the best score across all strategies
            score = max(score1, score2, score3, score4)

            if score > best_score:
                best_score = score
                best_match = member

        if best_match and best_score >= fuzzy_threshold:
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

        logger.warning(f"No match found for {first_name} {last_name} {state or ''} (best score: {best_score}, best match: {best_match.get('name') if best_match else 'None'})")
        
        # Try MDM Normalization
        try:
            from ..mdm import MemberNameNormalizer
            norm_first, norm_last = MemberNameNormalizer.normalize(first_name, last_name)
            
            # If normalization changed the name, try searching again
            if norm_first != first_name.lower() or norm_last != last_name.lower():
                logger.info(f"Retrying with normalized name: {norm_first} {norm_last}")
                
                # Recursive call with normalized name, but prevent infinite recursion
                # by checking if we already normalized
                return self.search_member_by_name(norm_first, norm_last, state, fuzzy_threshold)
        except ImportError:
            pass
            
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

    def _get_fallback_party(self, first_name: str, last_name: str) -> Optional[str]:
        """Get party from fallback reference data."""
        if not self.fallback_enabled:
            return None
            
        # Import reference data here to avoid circular imports
        try:
            from ..reference_data import get_member_party
            party = get_member_party(first_name, last_name)
            if party:
                self._fallback_count += 1
                logger.debug(f"Using fallback party data for {first_name} {last_name}: {party}")
            return party
        except (ImportError, AttributeError):
            return None
    
    def enrich_member(
        self,
        first_name: str,
        last_name: str,
        state: str = None,
        district: int = None
    ) -> Dict[str, Any]:
        """
        Enrich member data with Congress API, with fallback to reference data.

        Args:
            first_name: Member's first name
            last_name: Member's last name
            state: Two-letter state code
            district: Congressional district number

        Returns:
            Enriched member data dict with validation
        """
        member_data = self.search_member_by_name(first_name, last_name, state)

        if not member_data:
            # Try fallback reference data
            fallback_party = self._get_fallback_party(first_name, last_name)
            
            result = {
                'bioguide_id': None,
                'party': fallback_party,
                'chamber': 'House',  # Assume House for financial disclosures
                'start_date': None,
                'end_date': None,
                'is_current': True,
                'enrichment_status': 'fallback' if fallback_party else 'not_found'
            }
            
            return validate_enriched_member(result)

        # Extract enriched fields
        # Party code from most recent term
        terms_data = member_data.get('terms', {})
        
        if isinstance(terms_data, list):
            terms = terms_data
        elif isinstance(terms_data, dict):
            terms = terms_data.get('item', [])
        else:
            terms = []
            
        latest_term = terms[-1] if terms else {}

        party_code = latest_term.get('party')
        if party_code == 'Democratic':
            party_code = 'Democrat'
            
        chamber = latest_term.get('chamber')
        start_year = latest_term.get('startYear')
        end_year = latest_term.get('endYear')
        
        # If API didn't return party, try fallback
        if not party_code and self.fallback_enabled:
            party_code = self._get_fallback_party(first_name, last_name)
            status = 'fallback' if party_code else 'success'
        else:
            status = 'success'
        
        self._success_count += 1

        result = {
            'bioguide_id': member_data.get('bioguideId'),
            'party': party_code,
            'chamber': chamber or 'House',
            'start_date': f"{start_year}-01-03" if start_year else None,
            'end_date': f"{end_year}-01-03" if end_year else None,
            'is_current': not end_year or int(end_year) >= 2025,
            'enrichment_status': status
        }
        
        return validate_enriched_member(result)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get enrichment statistics."""
        return {
            'total_requests': self._request_count,
            'api_success': self._success_count,
            'fallback_used': self._fallback_count,
            'success_rate': self._success_count / max(1, self._request_count)
        }
