#!/usr/bin/env python3
"""
Generate network_graph.json for the website visualization.

Creates a graph structure with:
- Member nodes
- Asset nodes  
- Links between members and assets based on transactions
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


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


def build_network_graph():
    """Build network graph JSON from Gold layer data."""
    s3 = boto3.client('s3')
    
    # Load members
    members_df = read_parquet(s3, 'gold/congress/dim_member/')
    logger.info(f"Loaded {len(members_df)} members")
    
    # Build nodes
    nodes = []
    links = []
    
    # Add member nodes
    for _, m in members_df.iterrows():
        nodes.append({
            'id': m.get('direct_order_name', f"{m.get('first_name', '')} {m.get('last_name', '')}"),
            'bioguide_id': m.get('bioguide_id'),
            'group': 'member',
            'party': {
                'D': 'Democrat',
                'R': 'Republican'
            }.get(m.get('party'), 'Unknown'),
            'chamber': m.get('chamber', '').title(),
            'state': m.get('state'),
            'bills_sponsored': int(m.get('bills_sponsored_count', 0)),
            'image_url': m.get('image_url')
        })
    
    # Try to load transactions if available
    tx_df = read_parquet(s3, 'gold/house/financial/facts/fact_ptr_transactions/')
    
    if not tx_df.empty and 'ticker' in tx_df.columns:
        logger.info(f"Loaded {len(tx_df)} transactions")
        
        # Group by filer and ticker to create links
        asset_values = defaultdict(lambda: {'value': 0, 'count': 0, 'types': set()})
        
        for _, tx in tx_df.iterrows():
            filer = tx.get('filer_name', 'Unknown')
            ticker = tx.get('ticker')
            if not ticker or ticker == 'N/A':
                continue
                
            key = (filer, ticker)
            # Parse amount range
            amount_str = str(tx.get('amount', '0'))
            try:
                if '-' in amount_str:
                    parts = amount_str.replace('$', '').replace(',', '').split('-')
                    amount = (float(parts[0]) + float(parts[1])) / 2
                else:
                    amount = float(amount_str.replace('$', '').replace(',', ''))
            except:
                amount = 0
            
            asset_values[key]['value'] += amount
            asset_values[key]['count'] += 1
            asset_values[key]['types'].add(tx.get('transaction_type', 'unknown'))
        
        # Add asset nodes and links
        seen_assets = set()
        for (filer, ticker), data in asset_values.items():
            if ticker not in seen_assets:
                nodes.append({
                    'id': ticker,
                    'group': 'asset',
                    'type': 'stock'
                })
                seen_assets.add(ticker)
            
            links.append({
                'source': filer,
                'target': ticker,
                'value': data['value'],
                'count': data['count'],
                'type': ', '.join(data['types'])
            })
    else:
        logger.info("No transaction data available - creating member-only graph")
    
    # Calculate summary stats
    summary_stats = {
        'total_members': len([n for n in nodes if n.get('group') == 'member']),
        'total_assets': len([n for n in nodes if n.get('group') == 'asset']),
        'total_transactions': sum(l.get('count', 0) for l in links),
        'total_volume': sum(l.get('value', 0) for l in links)
    }
    
    graph_data = {
        'nodes': nodes,
        'links': links,
        'summary_stats': summary_stats
    }
    
    logger.info(f"Generated graph: {len(nodes)} nodes, {len(links)} links")
    
    # Upload to S3
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key='website/data/network_graph.json',
        Body=json.dumps(graph_data, default=str),
        ContentType='application/json'
    )
    logger.info(f"✅ Uploaded to s3://{BUCKET_NAME}/website/data/network_graph.json")
    
    return graph_data


if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("Generating Network Graph JSON")
    logger.info("=" * 80)
    build_network_graph()
