#!/usr/bin/env python3
"""
Build Congress Network Data for ISR Pre-Rendering.

Generates static JSON files for instant page load:
- members.json - All current Congress members with stats
- bills.json - Bills from current Congress (119th)
- edges.json - Pre-computed relationship edges for each view mode

Run daily via cron/EventBridge to refresh data.
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
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
CURRENT_CONGRESS = 119
OUTPUT_PREFIX = 'website/data/congress_network'


def read_parquet_prefix(s3_client, prefix: str) -> pd.DataFrame:
    """Read all Parquet files from S3 prefix."""
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


def clean_for_json(obj):
    """Replace NaN/Inf with None for valid JSON."""
    import math
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    elif isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(v) for v in obj]
    return obj


def build_members_data(s3_client) -> list:
    """Build member nodes with enriched stats."""
    members_df = read_parquet_prefix(s3_client, 'gold/congress/dim_member/')
    
    # Filter to current members
    current_members = members_df[members_df['is_current'] == True].copy()
    
    # Load member stats if available
    try:
        stats_df = read_parquet_prefix(s3_client, 'gold/congress/aggregates/member_legislative_stats/')
        if not stats_df.empty:
            current_members = current_members.merge(
                stats_df[['bioguide_id', 'bills_sponsored_count', 'fd_transaction_count']],
                on='bioguide_id',
                how='left',
                suffixes=('', '_stats')
            )
    except Exception as e:
        logger.warning(f"Could not load member stats: {e}")
    
    members = []
    for _, m in current_members.iterrows():
        members.append({
            'id': m.get('bioguide_id'),
            'name': m.get('direct_order_name', f"{m.get('first_name', '')} {m.get('last_name', '')}"),
            'first_name': m.get('first_name'),
            'last_name': m.get('last_name'),
            'party': m.get('party'),
            'state': m.get('state'),
            'district': int(m['district']) if pd.notna(m.get('district')) else None,
            'chamber': m.get('chamber', '').lower(),
            'image_url': m.get('image_url'),
            'official_url': m.get('official_url'),
            'bills_sponsored': int(m.get('sponsored_legislation_count', 0) or 0),
            'bills_cosponsored': int(m.get('cosponsored_legislation_count', 0) or 0),
            'fd_trades': int(m.get('fd_transaction_count', 0) or 0),
            'type': 'member'
        })
    
    logger.info(f"Built {len(members)} member nodes")
    return members


def build_bills_data(s3_client, congress: int = CURRENT_CONGRESS) -> list:
    """Build bill nodes for specified Congress."""
    bills_df = read_parquet_prefix(s3_client, f'gold/congress/dim_bill/congress={congress}/')
    
    bills = []
    for _, b in bills_df.iterrows():
        bill_id = f"{congress}-{b.get('bill_type', 'hr')}-{b.get('bill_number', 0)}"
        bills.append({
            'id': bill_id,
            'congress': congress,
            'bill_type': b.get('bill_type', '').upper(),
            'bill_number': int(b.get('bill_number', 0)),
            'title': b.get('title', '')[:200],  # Truncate for performance
            'title_short': b.get('title_short'),
            'sponsor_id': b.get('sponsor_bioguide_id'),
            'sponsor_name': b.get('sponsor_name'),
            'policy_area': b.get('policy_area'),
            'introduced_date': str(b.get('introduced_date', ''))[:10],
            'cosponsors_count': int(b['cosponsors_count']) if pd.notna(b.get('cosponsors_count')) else 0,
            'type': 'bill'
        })
    
    logger.info(f"Built {len(bills)} bill nodes for Congress {congress}")
    return bills


def build_state_delegation_edges(members: list) -> list:
    """Build edges connecting members from same state."""
    edges = []
    state_members = defaultdict(list)
    
    for m in members:
        if m.get('state'):
            state_members[m['state']].append(m['id'])
    
    for state, member_ids in state_members.items():
        if len(member_ids) > 1:
            # Create edges between all members of same state
            for i, m1 in enumerate(member_ids):
                for m2 in member_ids[i+1:]:
                    edges.append({
                        'source': m1,
                        'target': m2,
                        'type': 'state_delegation',
                        'state': state,
                        'weight': 1
                    })
    
    logger.info(f"Built {len(edges)} state delegation edges")
    return edges


def build_sponsorship_edges(members: list, bills: list) -> list:
    """Build edges from sponsors to their bills."""
    edges = []
    member_ids = {m['id'] for m in members}
    
    for b in bills:
        sponsor_id = b.get('sponsor_id')
        if sponsor_id and sponsor_id in member_ids:
            edges.append({
                'source': sponsor_id,
                'target': b['id'],
                'type': 'sponsors',
                'weight': 1
            })
    
    logger.info(f"Built {len(edges)} sponsorship edges")
    return edges


def build_policy_clusters(bills: list) -> tuple:
    """Build policy area nodes and edges."""
    policy_nodes = []
    policy_edges = []
    policy_areas = set()
    
    for b in bills:
        area = b.get('policy_area')
        if area:
            policy_areas.add(area)
            policy_edges.append({
                'source': b['id'],
                'target': f"policy-{area}",
                'type': 'policy_area',
                'weight': 1
            })
    
    for area in policy_areas:
        policy_nodes.append({
            'id': f"policy-{area}",
            'name': area,
            'type': 'policy'
        })
    
    logger.info(f"Built {len(policy_nodes)} policy nodes, {len(policy_edges)} edges")
    return policy_nodes, policy_edges


def build_party_aggregates(members: list) -> tuple:
    """Build aggregated party nodes for high-level view."""
    party_counts = defaultdict(int)
    for m in members:
        party = m.get('party', 'I')
        party_counts[party] += 1
    
    party_nodes = [
        {'id': 'party-D', 'name': 'Democrats', 'type': 'party', 'count': party_counts.get('D', 0)},
        {'id': 'party-R', 'name': 'Republicans', 'type': 'party', 'count': party_counts.get('R', 0)},
        {'id': 'party-I', 'name': 'Independents', 'type': 'party', 'count': party_counts.get('I', 0)},
    ]
    
    party_edges = []
    for m in members:
        party = m.get('party', 'I')
        party_edges.append({
            'source': m['id'],
            'target': f"party-{party}",
            'type': 'party_membership',
            'weight': 1
        })
    
    return party_nodes, party_edges


def build_chamber_aggregates(members: list) -> tuple:
    """Build aggregated chamber nodes."""
    chamber_nodes = [
        {'id': 'chamber-house', 'name': 'House', 'type': 'chamber', 
         'count': sum(1 for m in members if m.get('chamber') == 'house')},
        {'id': 'chamber-senate', 'name': 'Senate', 'type': 'chamber',
         'count': sum(1 for m in members if m.get('chamber') == 'senate')},
    ]
    
    chamber_edges = []
    for m in members:
        chamber = m.get('chamber', 'house')
        chamber_edges.append({
            'source': m['id'],
            'target': f"chamber-{chamber}",
            'type': 'chamber_membership',
            'weight': 1
        })
    
    return chamber_nodes, chamber_edges


def upload_json(s3_client, key: str, data: dict):
    """Upload JSON to S3 with correct content type."""
    body = json.dumps(clean_for_json(data), default=str)
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=body,
        ContentType='application/json',
        CacheControl='max-age=3600'  # 1 hour cache
    )
    logger.info(f"Uploaded s3://{BUCKET_NAME}/{key} ({len(body)} bytes)")


def main():
    logger.info("=" * 80)
    logger.info(f"Building Congress Network Data (Congress {CURRENT_CONGRESS})")
    logger.info("=" * 80)
    
    s3 = boto3.client('s3')
    
    # Build base data
    members = build_members_data(s3)
    bills = build_bills_data(s3, CURRENT_CONGRESS)
    
    # Also get 118th Congress bills for comparison
    bills_118 = build_bills_data(s3, 118)
    
    # Build edges for each view mode
    state_edges = build_state_delegation_edges(members)
    sponsor_edges = build_sponsorship_edges(members, bills)
    policy_nodes, policy_edges = build_policy_clusters(bills)
    party_nodes, party_edges = build_party_aggregates(members)
    chamber_nodes, chamber_edges = build_chamber_aggregates(members)
    
    # Combine all auxiliary nodes
    aux_nodes = policy_nodes + party_nodes + chamber_nodes
    
    # Build complete network data
    network_data = {
        'generated_at': datetime.utcnow().isoformat(),
        'congress': CURRENT_CONGRESS,
        'stats': {
            'total_members': len(members),
            'house_members': sum(1 for m in members if m.get('chamber') == 'house'),
            'senate_members': sum(1 for m in members if m.get('chamber') == 'senate'),
            'democrats': sum(1 for m in members if m.get('party') == 'D'),
            'republicans': sum(1 for m in members if m.get('party') == 'R'),
            'total_bills_119': len(bills),
            'total_bills_118': len(bills_118),
            'policy_areas': len(policy_nodes),
        },
        'nodes': {
            'members': members,
            'bills': bills,
            'bills_118': bills_118,
            'auxiliary': aux_nodes,
        },
        'edges': {
            'state_delegation': state_edges,
            'sponsorship': sponsor_edges,
            'policy_area': policy_edges,
            'party': party_edges,
            'chamber': chamber_edges,
        }
    }
    
    # Upload complete network file
    upload_json(s3, f'{OUTPUT_PREFIX}/network.json', network_data)
    
    # Also upload legacy format for old network.html compatibility
    legacy_data = {
        'nodes': members + [{'id': b['id'], 'label': f"{b['bill_type']} {b['bill_number']}", 
                             'group': 'bill', **b} for b in bills[:100]],
        'links': sponsor_edges[:500],
        'summary_stats': network_data['stats']
    }
    upload_json(s3, 'website/data/network_graph.json', legacy_data)
    
    logger.info("=" * 80)
    logger.info("✅ Congress Network Data Build Complete!")
    logger.info(f"   Members: {len(members)}")
    logger.info(f"   Bills (119th): {len(bills)}")
    logger.info(f"   Bills (118th): {len(bills_118)}")
    logger.info(f"   State edges: {len(state_edges)}")
    logger.info(f"   Sponsor edges: {len(sponsor_edges)}")
    logger.info(f"   Policy clusters: {len(policy_nodes)}")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
