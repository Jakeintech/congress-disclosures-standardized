#!/usr/bin/env python3
"""
Build House FD Member Reference Data from XML Indices

Parses all House Financial Disclosure XML index files (2010-2025) to extract
unique member names, states, and districts for fuzzy matching against Congress.gov data.

Output: data/reference/members/house_fd_members.parquet

Schema:
- member_name: Name as appears in House FD XML (various formats)
- state: Two-letter state code
- district: District number (or "00" for at-large)
- filing_count: Number of filings by this name
- first_seen_year: Earliest year this name appears
- last_seen_year: Most recent year this name appears
- name_variations: JSON array of all observed name formats
- source: "house_fd_xml"

Usage:
    python backend/scripts/build_reference_house_fd_members.py

Requires:
    - Bronze layer House FD XML indices in S3
    - defusedxml library for safe XML parsing
"""

import os
import sys
import json
from typing import List, Dict, Set, Any
from collections import defaultdict
from datetime import datetime

import pandas as pd
import boto3
from defusedxml import ElementTree as ET

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.lib.ingestion.s3_utils import download_file_from_s3, upload_file_to_s3

# Configuration
BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
BRONZE_PREFIX = "data/bronze/house_fd/"
OUTPUT_S3_PATH = "data/reference/members/house_fd_members.parquet"
LOCAL_OUTPUT = "/tmp/house_fd_members.parquet"

# Years to process (2010-2025)
YEARS_TO_PROCESS = list(range(2010, 2026))

s3_client = boto3.client('s3')


def find_all_xml_indices() -> List[str]:
    """
    Find all XML index files in S3 Bronze layer.

    Returns:
        List of S3 keys for XML indices
    """

    print("Finding XML index files in S3...")

    xml_indices = []

    for year in YEARS_TO_PROCESS:
        # House FD indices are stored at: bronze/house_fd/year=YYYY/index/YYYYFD.xml
        prefix = f"{BRONZE_PREFIX}year={year}/index/"

        try:
            response = s3_client.list_objects_v2(
                Bucket=BUCKET,
                Prefix=prefix
            )

            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    if key.endswith('.xml'):
                        xml_indices.append(key)
                        print(f"  Found: {key}")
        except Exception as e:
            print(f"  WARNING: Could not list {prefix}: {e}")
            continue

    print(f"\nFound {len(xml_indices)} XML index files")
    return xml_indices


def parse_xml_index(s3_key: str) -> List[Dict[str, Any]]:
    """
    Parse a single XML index file and extract member records.

    Args:
        s3_key: S3 key for XML file

    Returns:
        List of member record dicts
    """

    year = int(s3_key.split('year=')[1].split('/')[0])

    # Download XML from S3
    local_xml = f"/tmp/{os.path.basename(s3_key)}"

    try:
        download_file_from_s3(BUCKET, s3_key, local_xml)
    except Exception as e:
        print(f"  ERROR downloading {s3_key}: {e}")
        return []

    # Parse XML
    try:
        tree = ET.parse(local_xml)
        root = tree.getroot()
    except Exception as e:
        print(f"  ERROR parsing XML {s3_key}: {e}")
        return []

    members = []

    # House FD XML structure:
    # <FilingList>
    #   <Filing>
    #     <Name>Pelosi, Nancy</Name>
    #     <State>CA</State>
    #     <District>12</District>
    #     ...
    #   </Filing>
    # </FilingList>

    for filing in root.findall('.//Filing'):
        name_elem = filing.find('Name')
        state_elem = filing.find('State')
        district_elem = filing.find('District')

        if name_elem is not None and name_elem.text:
            member_name = name_elem.text.strip()
            state = state_elem.text.strip() if state_elem is not None and state_elem.text else None
            district = district_elem.text.strip() if district_elem is not None and district_elem.text else None

            members.append({
                'member_name': member_name,
                'state': state,
                'district': district,
                'year': year
            })

    # Clean up temp file
    if os.path.exists(local_xml):
        os.remove(local_xml)

    return members


def aggregate_member_records(all_members: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Aggregate member records by unique name, collecting metadata.

    Args:
        all_members: List of all member records from all years

    Returns:
        DataFrame with aggregated member data
    """

    print(f"\nAggregating {len(all_members):,} member records...")

    # Group by member_name
    member_data = defaultdict(lambda: {
        'states': set(),
        'districts': set(),
        'years': set(),
        'name_variations': set(),
        'filing_count': 0
    })

    for record in all_members:
        name = record['member_name']
        state = record.get('state')
        district = record.get('district')
        year = record['year']

        member_data[name]['name_variations'].add(name)
        member_data[name]['filing_count'] += 1
        member_data[name]['years'].add(year)

        if state:
            member_data[name]['states'].add(state)
        if district:
            member_data[name]['districts'].add(district)

    # Convert to DataFrame records
    records = []
    for name, data in member_data.items():
        # Determine primary state (most common)
        primary_state = list(data['states'])[0] if data['states'] else None

        # Determine primary district (most recent)
        primary_district = list(data['districts'])[0] if data['districts'] else None

        years_list = sorted(data['years'])

        records.append({
            'member_name': name,
            'state': primary_state,
            'district': primary_district,
            'filing_count': data['filing_count'],
            'first_seen_year': min(years_list) if years_list else None,
            'last_seen_year': max(years_list) if years_list else None,
            'years_active': json.dumps(years_list),
            'name_variations': json.dumps(list(data['name_variations'])),
            'states_seen': json.dumps(list(data['states'])),
            'districts_seen': json.dumps(list(data['districts'])),
            'source': 'house_fd_xml',
            'parsed_at': datetime.utcnow().isoformat()
        })

    df = pd.DataFrame(records)
    df = df.sort_values('filing_count', ascending=False)

    print(f"  Aggregated to {len(df):,} unique member names")
    print(f"  Total filings: {df['filing_count'].sum():,}")
    print(f"  Most active filer: {df.iloc[0]['member_name']} ({df.iloc[0]['filing_count']} filings)")

    return df


def main():
    """Main execution."""

    print("=" * 80)
    print("House FD Member Reference Data Builder")
    print("=" * 80)

    # Find all XML indices
    xml_indices = find_all_xml_indices()

    if not xml_indices:
        print("\nWARNING: No XML indices found in Bronze layer!")
        print("Have you run the House FD ingestion pipeline yet?")
        print(f"Expected location: s3://{BUCKET}/{BRONZE_PREFIX}year=YYYY/index/")
        return 1

    # Parse all XML files
    all_members = []

    for xml_key in xml_indices:
        print(f"\nParsing {xml_key}...")
        members = parse_xml_index(xml_key)
        print(f"  Extracted {len(members):,} member records")
        all_members.extend(members)

    if not all_members:
        print("\nERROR: No member records extracted!")
        return 1

    # Aggregate by unique name
    df = aggregate_member_records(all_members)

    # Save to Parquet
    print(f"\nSaving to Parquet...")
    df.to_parquet(
        LOCAL_OUTPUT,
        index=False,
        compression='snappy',
        engine='pyarrow'
    )

    print(f"  ✓ Saved locally: {LOCAL_OUTPUT} ({os.path.getsize(LOCAL_OUTPUT) / 1024:.1f} KB)")

    # Upload to S3
    try:
        upload_file_to_s3(LOCAL_OUTPUT, BUCKET, OUTPUT_S3_PATH)
        print(f"  ✓ Uploaded to S3: s3://{BUCKET}/{OUTPUT_S3_PATH}")
    except Exception as e:
        print(f"  WARNING: Failed to upload to S3: {e}")

    # Summary
    print("\n" + "=" * 80)
    print("✓ House FD member reference data build complete")
    print("=" * 80)
    print(f"Unique members: {len(df):,}")
    print(f"Total filings: {df['filing_count'].sum():,}")
    print(f"Year range: {df['first_seen_year'].min()}-{df['last_seen_year'].max()}")
    print(f"Output: s3://{BUCKET}/{OUTPUT_S3_PATH}")
    print("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
