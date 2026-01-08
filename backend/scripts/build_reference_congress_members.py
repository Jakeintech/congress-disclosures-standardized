#!/usr/bin/env python3
"""
Build Congress.gov Member Reference Data

Fetches all members (historical + current) from Congress.gov API to create
a master bioguide registry for cross-source data linkage.

Output: data/reference/members/congress_api_members.parquet

Schema:
- bioguide_id: Primary identifier (e.g., "P000197")
- full_name: Canonical name (e.g., "Nancy Pelosi")
- first_name, middle_name, last_name: Name components
- party: Current/most recent party affiliation
- state: Two-letter state code
- chamber: "house" or "senate"
- terms: Array of term records with start/end dates
- current_member: Boolean (active in 118th+ Congress)
- source: "congress_api"

Usage:
    python backend/scripts/build_reference_congress_members.py

Requires:
    - CONGRESS_GOV_API_KEY environment variable
    - Internet connection
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import List, Dict, Any

import pandas as pd
import requests

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.lib.ingestion.s3_utils import upload_file_to_s3

# Configuration
CONGRESS_API_BASE_URL = "https://api.congress.gov/v3"
API_KEY = os.environ.get('CONGRESS_GOV_API_KEY')
BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
OUTPUT_S3_PATH = "data/reference/members/congress_api_members.parquet"
LOCAL_OUTPUT = "/tmp/congress_api_members.parquet"

# Rate limiting
RATE_LIMIT_DELAY = 0.2  # 200ms between requests (5 req/sec)


def fetch_all_members() -> List[Dict[str, Any]]:
    """
    Fetch all members from Congress.gov API with pagination.

    Returns:
        List of member dictionaries with full details
    """

    if not API_KEY:
        raise ValueError(
            "CONGRESS_GOV_API_KEY environment variable not set. "
            "Get a free API key at: https://api.congress.gov/sign-up/"
        )

    all_members = []
    offset = 0
    limit = 250  # Max allowed by API

    print("Fetching members from Congress.gov API...")
    print(f"API Key: {'*' * 20}{API_KEY[-4:]}")

    while True:
        url = f"{CONGRESS_API_BASE_URL}/member"
        params = {
            'api_key': API_KEY,
            'offset': offset,
            'limit': limit,
            'format': 'json'
        }

        print(f"  Fetching offset {offset}...")

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"ERROR fetching members: {e}")
            if offset == 0:
                raise  # Fatal on first request
            else:
                print("Continuing with members fetched so far...")
                break

        members = data.get('members', [])

        if not members:
            print(f"  No more members (total: {len(all_members)})")
            break

        all_members.extend(members)
        print(f"  Fetched {len(members)} members (total: {len(all_members)})")

        # Check pagination
        pagination = data.get('pagination', {})
        next_offset = pagination.get('next')

        if not next_offset:
            break

        offset = next_offset
        time.sleep(RATE_LIMIT_DELAY)  # Rate limiting

    return all_members


def parse_member_record(member: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a member record from Congress.gov API into standardized format.

    Args:
        member: Raw member dict from API

    Returns:
        Standardized member record
    """

    # Extract name components
    name_parts = member.get('name', '')
    bioguide_id = member.get('bioguideId', '')

    # Parse party (most recent/current)
    party_history = member.get('partyHistory', [])
    current_party = party_history[0].get('partyCode') if party_history else None

    # Parse terms
    terms = member.get('terms', {}).get('item', [])

    # Determine chamber (from most recent term)
    chamber = None
    if terms:
        recent_term = terms[0]
        chamber = recent_term.get('chamber', '').lower()

    # State (from most recent term)
    state = None
    if terms:
        state = terms[0].get('stateName') or terms[0].get('stateCode')

    # Check if current member (served in 118th+ Congress)
    current_member = False
    if terms:
        for term in terms:
            congress = term.get('congress')
            if congress and int(congress) >= 118:
                current_member = True
                break

    return {
        'bioguide_id': bioguide_id,
        'full_name': name_parts,
        'party': current_party,
        'state': state,
        'chamber': chamber,
        'terms_count': len(terms),
        'current_member': current_member,
        'party_history': json.dumps(party_history) if party_history else None,
        'terms': json.dumps(terms) if terms else None,
        'source': 'congress_api',
        'fetched_at': datetime.utcnow().isoformat()
    }


def build_member_dataframe(members: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert list of member records to pandas DataFrame.

    Args:
        members: List of raw member dicts from API

    Returns:
        DataFrame with standardized member records
    """

    print(f"\nParsing {len(members)} member records...")

    parsed_members = []
    for member in members:
        try:
            parsed = parse_member_record(member)
            parsed_members.append(parsed)
        except Exception as e:
            bioguide = member.get('bioguideId', 'UNKNOWN')
            print(f"  WARNING: Failed to parse member {bioguide}: {e}")
            continue

    df = pd.DataFrame(parsed_members)

    print(f"  Successfully parsed {len(df)} members")
    print(f"  - Current members (118th+ Congress): {df['current_member'].sum()}")
    print(f"  - House: {len(df[df['chamber'] == 'house'])}")
    print(f"  - Senate: {len(df[df['chamber'] == 'senate'])}")
    print(f"  - Party breakdown: {df['party'].value_counts().to_dict()}")

    return df


def save_to_parquet(df: pd.DataFrame, local_path: str, s3_path: str):
    """
    Save DataFrame to Parquet (local + S3).

    Args:
        df: DataFrame to save
        local_path: Local file path
        s3_path: S3 key path
    """

    print(f"\nSaving to Parquet...")

    # Save locally
    df.to_parquet(
        local_path,
        index=False,
        compression='snappy',
        engine='pyarrow'
    )

    print(f"  ✓ Saved locally: {local_path} ({os.path.getsize(local_path) / 1024:.1f} KB)")

    # Upload to S3
    try:
        upload_file_to_s3(local_path, BUCKET, s3_path)
        print(f"  ✓ Uploaded to S3: s3://{BUCKET}/{s3_path}")
    except Exception as e:
        print(f"  WARNING: Failed to upload to S3: {e}")
        print(f"  Data is still available locally at: {local_path}")


def main():
    """Main execution."""

    print("=" * 80)
    print("Congress.gov Member Reference Data Builder")
    print("=" * 80)

    # Fetch all members
    members = fetch_all_members()

    if not members:
        print("\nERROR: No members fetched!")
        return 1

    # Parse into DataFrame
    df = build_member_dataframe(members)

    # Save to Parquet
    save_to_parquet(df, LOCAL_OUTPUT, OUTPUT_S3_PATH)

    # Summary
    print("\n" + "=" * 80)
    print("✓ Congress.gov member reference data build complete")
    print("=" * 80)
    print(f"Total members: {len(df):,}")
    print(f"Current members: {df['current_member'].sum():,}")
    print(f"Output: s3://{BUCKET}/{OUTPUT_S3_PATH}")
    print("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
