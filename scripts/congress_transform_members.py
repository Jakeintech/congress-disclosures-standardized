#!/usr/bin/env python3
"""
Transform Bronze Congress members to Silver dimension table.

Reads gzipped JSON files from bronze/congress/member/ and writes consolidated
Parquet files to silver/congress/dim_member/.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import boto3
import json
import gzip
from io import BytesIO
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def extract_member_data(member_json: dict) -> dict:
    """Extract relevant fields from raw member JSON."""
    m = member_json.get('member', member_json)
    
    # Get current party
    party_history = m.get('partyHistory', [])
    current_party = party_history[0].get('partyAbbreviation') if party_history else None
    
    # Get current term info
    terms = m.get('terms', m.get('termsOfService', []))
    current_term = terms[-1] if terms else {}
    
    return {
        'bioguide_id': m.get('bioguideId'),
        'first_name': m.get('firstName'),
        'last_name': m.get('lastName'),
        'direct_order_name': m.get('directOrderName'),
        'party': current_party,
        'state': m.get('state') or current_term.get('stateCode'),
        'district': m.get('district'),
        'chamber': 'house' if m.get('district') else 'senate',
        'birth_year': m.get('birthYear'),
        'image_url': m.get('depiction', {}).get('imageUrl'),
        'official_url': m.get('officialWebsiteUrl'),
        'is_current': m.get('currentMember', False),
        'sponsored_legislation_count': m.get('sponsoredLegislation', {}).get('count', 0),
        'cosponsored_legislation_count': m.get('cosponsoredLegislation', {}).get('count', 0),
    }


def transform_bronze_to_silver():
    """Read all Bronze members and write consolidated Silver parquet."""
    s3 = boto3.client('s3')
    
    # List all member files in Bronze
    prefixes = [
        'bronze/congress/member/chamber=house/',
        'bronze/congress/member/chamber=house of representatives/',
        'bronze/congress/member/chamber=senate/',
    ]
    
    all_members = []
    
    for prefix in prefixes:
        logger.info(f"Scanning {prefix}")
        paginator = s3.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
            for obj in page.get('Contents', []):
                key = obj['Key']
                if not key.endswith('.json.gz') and not key.endswith('.json'):
                    continue
                
                try:
                    response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
                    body = response['Body'].read()
                    
                    # Decompress if gzipped
                    if key.endswith('.gz'):
                        body = gzip.decompress(body)
                    
                    member_json = json.loads(body)
                    member_data = extract_member_data(member_json)
                    
                    if member_data['bioguide_id']:
                        all_members.append(member_data)
                        
                except Exception as e:
                    logger.warning(f"Error processing {key}: {e}")
                    continue
    
    if not all_members:
        logger.error("No members found in Bronze layer")
        return
    
    logger.info(f"Extracted {len(all_members)} members from Bronze")
    
    # Deduplicate by bioguide_id (keep latest)
    df = pd.DataFrame(all_members)
    df = df.drop_duplicates(subset=['bioguide_id'], keep='last')
    
    logger.info(f"After dedup: {len(df)} unique members")
    
    # Add metadata
    df['silver_created_at'] = datetime.utcnow().isoformat()
    
    # Write partitioned by chamber and is_current
    for chamber in df['chamber'].unique():
        for is_current in [True, False]:
            partition_df = df[(df['chamber'] == chamber) & (df['is_current'] == is_current)]
            if partition_df.empty:
                continue
                
            s3_key = f"silver/congress/dim_member/chamber={chamber}/is_current={str(is_current).lower()}/part-0000.parquet"
            
            buffer = BytesIO()
            partition_df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
            buffer.seek(0)
            
            s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
            logger.info(f"Wrote {len(partition_df)} records to s3://{BUCKET_NAME}/{s3_key}")
    
    logger.info(f"\n✅ Silver dim_member transform complete! Total: {len(df)} members")
    logger.info(f"   By chamber: {df['chamber'].value_counts().to_dict()}")
    logger.info(f"   Current members: {df['is_current'].sum()}")


if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("Transforming Bronze Congress members to Silver")
    logger.info("=" * 80)
    transform_bronze_to_silver()
