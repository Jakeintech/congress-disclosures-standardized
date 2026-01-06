"""
Simple member lookup using cached Congress data from Bronze layer.
Much simpler and more reliable than complex API enrichment.
"""

import json
import os
import boto3
from pathlib import Path
from typing import Optional, Dict
from fuzzywuzzy import fuzz
import logging

logger = logging.getLogger(__name__)

MEMBERS_FILE = Path(__file__).parent / "congress_members.json"
S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
S3_KEY = "bronze/reference/congress_members.json"

class SimpleMemberLookup:
    """Simple member lookup using cached data from Bronze layer."""
    
    def __init__(self):
        """Load cached member data from S3 Bronze layer or local fallback."""
        # Try S3 first (Bronze layer - single source of truth)
        try:
            s3 = boto3.client('s3')
            response = s3.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
            data = json.loads(response['Body'].read())
            self.members = data['members']
            logger.info(f"Loaded {len(self.members)} members from Bronze layer (S3)")
            return
        except Exception as e:
            logger.warning(f"Could not load from Bronze layer: {e}")
        
        # Fallback to local file
        if MEMBERS_FILE.exists():
            with open(MEMBERS_FILE) as f:
                data = json.load(f)
                self.members = data['members']
            logger.info(f"Loaded {len(self.members)} members from local cache (fallback)")
        else:
            raise FileNotFoundError(
                f"Members file not found. Run scripts/download_congress_members.py first."
            )
    
    def find_member(self, first_name: str, last_name: str, state_code: Optional[str] = None) -> Optional[Dict]:
        """
        Find member by name with simple, robust matching.
        
        Args:
            first_name: First name
            last_name: Last name  
            state_code: 2-letter state code (optional, helps narrow results)
        
        Returns:
            Member dict with bioguideId, partyName, etc. or None
        """
        # Clean inputs
        first = first_name.lower().strip()
        last = last_name.lower().strip()
        
        # Strategy 1: Exact last name match
        candidates = []
        for member in self.members:
            member_name = member.get('name', '')
            # Name format is "Last, First"
            if ',' in member_name:
                m_last, m_first = member_name.split(',', 1)
                m_last = m_last.lower().strip()
                m_first = m_first.lower().strip()
                
                # Exact last name match
                if m_last == last:
                    candidates.append(member)
        
        # If we have state, filter by it
        if state_code and candidates:
            from .state_mapping import STATE_CODE_TO_NAME
            state_full = STATE_CODE_TO_NAME.get(state_code)
            if state_full:
                state_matches = [m for m in candidates if m.get('state') == state_full]
                if state_matches:
                    candidates = state_matches
        
        # Strategy 2: If single exact last name match, return it
        if len(candidates) == 1:
            return candidates[0]
        
        # Strategy 3: Multiple matches - use first name to disambiguate
        if candidates:
            best_match = None
            best_score = 0
            
            for member in candidates:
                member_name = member.get('name', '')
                if ',' in member_name:
                    m_last, m_first = member_name.split(',', 1)
                    m_first = m_first.lower().strip()
                    
                    # Fuzzy match on first name
                    score = fuzz.ratio(first, m_first)
                    if score > best_score:
                        best_score = score
                        best_match = member
            
            if best_score >= 70:
                return best_match
        
        # Strategy 4: No exact last name match - try fuzzy on full name
        best_match = None
        best_score = 0
        
        target_full = f"{last} {first}"
        
        for member in self.members:
            member_name = member.get('name', '').replace(',', '').lower().strip()
            
            # Skip if state provided and doesn't match
            if state_code:
                from .state_mapping import STATE_CODE_TO_NAME
                state_full = STATE_CODE_TO_NAME.get(state_code)
                if state_full and member.get('state') != state_full:
                    continue
            
            score = fuzz.token_sort_ratio(member_name, target_full)
            if score > best_score:
                best_score = score
                best_match = member
        
        if best_score >= 80:  # Higher threshold for fuzzy
            return best_match
        
        return None
    
    def enrich_member(self, first_name: str, last_name: str, state: Optional[str] = None) -> Dict:
        """
        Enrich member data.
        
        Returns dict with: bioguide_id, party, chamber, etc.
        """
        member = self.find_member(first_name, last_name, state)
        
        if not member:
            return {
                'bioguide_id': None,
                'party': None,
                'chamber': 'House',  # Assume House for financial disclosures
                'state_full': None,
                'district': None,
                'enrichment_status': 'not_found'
            }
        
        # Extract party - it's in 'partyName' field, normalize it
        party = member.get('partyName')
        if party == 'Democratic':
            party = 'Democrat'
        
        # Get chamber from most recent term
        terms = member.get('terms', {}).get('item', [])
        chamber = terms[-1].get('chamber', 'House') if terms else 'House'
        # Simplify chamber name
        if 'House' in chamber:
            chamber = 'House'
        elif 'Senate' in chamber:
            chamber = 'Senate'
        
        return {
            'bioguide_id': member.get('bioguideId'),
            'party': party,
            'chamber': chamber,
            'state_full': member.get('state'),
            'district': member.get('district'),
            'enrichment_status': 'success'
        }
