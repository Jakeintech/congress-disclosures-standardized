#!/usr/bin/env python3
"""
Generate static network graph data for ISR (Incremental Static Regeneration).

This script generates pre-computed network graph JSON for the website.
Run daily via cron or Lambda to keep data fresh without client-side API calls.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import boto3
import json
from io import BytesIO
from collections import defaultdict
import logging
import math
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
CURRENT_CONGRESS = 119  # 119th Congress (2025-2027)


def read_parquet(s3_client, prefix: str) -> pd.DataFrame:
    """Read all Parquet files from a prefix."""
    logger.info(f"Reading from s3://{BUCKET_NAME}/{prefix}")
    
    paginator = s3_client.get_paginator('list_objects_v2')
    dfs = []
    
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.parquet'):
                response = s3_client.get_object(Bucket=BUCKET_NAME, Key=obj['Key'])
                df = pd.read_parquet(BytesIO(response['Body'].read()))
                dfs.append(df)
    
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


def clean_value(val):
    """Clean NaN/Inf values for JSON serialization."""
    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return val


def build_congress_network():
    """Build comprehensive Congress network graph."""
    s3 = boto3.client('s3')
    
    # Load all current members
    members_df = read_parquet(s3, 'gold/congress/dim_member/')
    logger.info(f"Loaded {len(members_df)} total members")
    
    # Filter to current members only
    if 'is_current' in members_df.columns:
        current_members = members_df[members_df['is_current'] == True].copy()
    else:
        current_members = members_df.copy()
    logger.info(f"Current members: {len(current_members)}")
    
    # Load bills for current congress
    bills_df = read_parquet(s3, 'gold/congress/dim_bill/')
    logger.info(f"Loaded {len(bills_df)} total bills")
    
    # Filter to current congress
    if 'congress' in bills_df.columns:
        current_bills = bills_df[bills_df['congress'] == CURRENT_CONGRESS].copy()
    else:
        current_bills = bills_df.copy()
    logger.info(f"119th Congress bills: {len(current_bills)}")
    
    # Build nodes
    nodes = []
    links = []
    member_ids = set()
    
    # Add member nodes
    for _, m in current_members.iterrows():
        member_id = m.get('bioguide_id')
        if not member_id:
            continue
        member_ids.add(member_id)
        
        nodes.append({
            'id': member_id,
            'label': f"{m.get('first_name', '')} {m.get('last_name', '')}".strip(),
            'type': 'member',
            'party': m.get('party'),
            'chamber': m.get('chamber'),
            'state': m.get('state'),
            'district': clean_value(m.get('district')),
            'bills_sponsored': int(m.get('sponsored_legislation_count', 0) or 0),
            'image_url': m.get('image_url')
        })
    
    # Add bill nodes and sponsor links
    bill_ids = set()
    policy_areas = defaultdict(list)
    
    for _, b in current_bills.iterrows():
        bill_id = f"{b.get('congress', '')}-{b.get('bill_type', '')}-{b.get('bill_number', '')}"
        if bill_id in bill_ids:
            continue
        bill_ids.add(bill_id)
        
        sponsor_id = b.get('sponsor_bioguide_id') or b.get('bioguide_id')
        policy_area = b.get('policy_area')
        
        nodes.append({
            'id': bill_id,
            'label': f"{(b.get('bill_type') or '').upper()} {b.get('bill_number', '')}",
            'type': 'bill',
            'title': b.get('title'),
            'title_short': b.get('title_short'),
            'policy_area': policy_area,
            'introduced_date': str(b.get('introduced_date', '')) if b.get('introduced_date') else None,
            'sponsor_id': sponsor_id
        })
        
        # Create sponsor link
        if sponsor_id and sponsor_id in member_ids:
            links.append({
                'source': sponsor_id,
                'target': bill_id,
                'type': 'sponsors'
            })
        
        # Track policy areas
        if policy_area:
            policy_areas[policy_area].append(bill_id)
    
    # Add policy area nodes and links
    for area, area_bills in policy_areas.items():
        area_id = f"policy-{area}"
        nodes.append({
            'id': area_id,
            'label': area,
            'type': 'policy',
            'bill_count': len(area_bills)
        })
        
        for bill_id in area_bills:
            links.append({
                'source': bill_id,
                'target': area_id,
                'type': 'policy'
            })
    
    # Calculate stats
    stats = {
        'total_nodes': len(nodes),
        'total_links': len(links),
        'members': len([n for n in nodes if n['type'] == 'member']),
        'bills': len([n for n in nodes if n['type'] == 'bill']),
        'policy_areas': len([n for n in nodes if n['type'] == 'policy']),
        'congress': CURRENT_CONGRESS,
        'generated_at': datetime.utcnow().isoformat() + 'Z'
    }
    
    # Party breakdown
    parties = defaultdict(int)
    chambers = defaultdict(int)
    for n in nodes:
        if n['type'] == 'member':
            parties[n.get('party', 'Unknown')] += 1
            chambers[n.get('chamber', 'unknown')] += 1
    
    stats['parties'] = dict(parties)
    stats['chambers'] = dict(chambers)
    
    graph_data = {
        'nodes': nodes,
        'links': links,
        'stats': stats,
        'metadata': {
            'congress': CURRENT_CONGRESS,
            'generated_at': stats['generated_at'],
            'data_sources': ['gold/congress/dim_member', 'gold/congress/dim_bill']
        }
    }
    
    logger.info(f"Generated graph: {stats['members']} members, {stats['bills']} bills, {stats['policy_areas']} policy areas, {len(links)} links")
    
    # Upload to S3
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key='website/data/congress_network.json',
        Body=json.dumps(graph_data, default=str),
        ContentType='application/json',
        CacheControl='public, max-age=3600'  # Cache for 1 hour
    )
    logger.info(f"✅ Uploaded to s3://{BUCKET_NAME}/website/data/congress_network.json")
    
    return graph_data


if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("Generating Congress Network Graph (ISR)")
    logger.info(f"Congress: {CURRENT_CONGRESS}th")
    logger.info("=" * 80)
    result = build_congress_network()
    print(f"\nStats: {json.dumps(result['stats'], indent=2)}")
