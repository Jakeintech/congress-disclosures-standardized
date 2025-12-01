#!/usr/bin/env python3
"""
Compute agg_network_graph aggregate table.

Generates network graph data (Nodes and Edges) for Member-Asset relationships
based on actual transaction data from the Silver layer.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import boto3
import logging
import json
import io

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

def load_transactions(bucket_name: str) -> pd.DataFrame:
    """Load transactions from silver/house/financial/ptr_transactions/."""
    s3 = boto3.client('s3')
    logger.info("Loading transactions from silver layer...")

    prefix = 'silver/house/financial/ptr_transactions/'
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    dfs = []
    for page in pages:
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.parquet'):
                try:
                    response = s3.get_object(Bucket=bucket_name, Key=obj['Key'])
                    buffer = io.BytesIO(response['Body'].read())
                    df = pd.read_parquet(buffer)
                    dfs.append(df)
                except Exception as e:
                    logger.warning(f"Failed to read {obj['Key']}: {e}")

    if not dfs:
        logger.warning("No transaction data found.")
        return pd.DataFrame()

    if not dfs:
        logger.warning("No transaction data found.")
        return pd.DataFrame()

    result = pd.concat(dfs, ignore_index=True)
    logger.info(f"Loaded {len(result):,} transactions")
    return result

def load_dim_members(bucket_name: str) -> pd.DataFrame:
    """Load dim_members for party lookup."""
    s3 = boto3.client('s3')
    logger.info("Loading dim_members...")

    prefix = 'gold/house/financial/dimensions/dim_members/'
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    dfs = []
    for page in pages:
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.parquet'):
                try:
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
                        s3.download_file(bucket_name, obj['Key'], tmp.name)
                        df = pd.read_parquet(tmp.name)
                        dfs.append(df)
                        os.unlink(tmp.name)
                except Exception as e:
                    logger.warning(f"Failed to read {obj['Key']}: {e}")

    if not dfs:
        logger.warning("No dim_members found.")
        return pd.DataFrame()

    result = pd.concat(dfs, ignore_index=True)
    # Create a lookup key: "FirstName LastName" -> Party
    result['full_name'] = result['first_name'] + ' ' + result['last_name']
    logger.info(f"Loaded {len(result):,} members")
    return result

def generate_network_graph_data(transactions_df: pd.DataFrame, members_df: pd.DataFrame):
    """Generate network graph nodes and edges from transactions."""
    if transactions_df.empty:
        return {'nodes': [], 'links': []}

    logger.info("Generating network graph data...")

    # Create Party Lookup
    party_map = {}
    if not members_df.empty:
        # Normalize names for better matching
        members_df['lookup_name'] = members_df['full_name'].str.lower().str.strip()
        party_map = dict(zip(members_df['lookup_name'], members_df['party']))

    # Filter out invalid rows (must have ticker OR asset_name)
    df = transactions_df.copy()
    
    # Create a target column: use ticker if available, else try to extract from asset_name
    import re
    
    def get_target(row):
        # 1. Try explicit ticker
        ticker = row.get('ticker')
        if ticker and ticker != '--' and ticker != 'N/A':
            return ticker
        
        asset = row.get('asset_name')
        if not asset:
            return None
            
        # 2. Try to extract ticker from parenthesis e.g. "Apple Inc (AAPL)"
        # Look for 1-5 uppercase letters in parens
        match = re.search(r'\(([A-Z]{1,5})\)', asset)
        if match:
            return match.group(1)
            
        # 3. Fallback to truncated asset name
        return asset[:20] + '...' if len(asset) > 20 else asset

    df['target_node'] = df.apply(get_target, axis=1)
    
    # Filter where we have a target
    df = df[df['target_node'].notna()]
    
    # Calculate estimated amount
    def estimate_amount(row):
        try:
            low = float(row.get('amount_low', 0) or 0)
            high = float(row.get('amount_high', 0) or 0)
            if high > 0:
                return (low + high) / 2
            return low or 1000 # Default fallback
        except:
            return 1000

    df['estimated_amount'] = df.apply(estimate_amount, axis=1)
    
    # Create Full Name
    df['member_name'] = df['first_name'] + ' ' + df['last_name']

    # Aggregate Edges: Member -> Target Node
    # We sum the volume (estimated amount) and count transactions
    edges_df = df.groupby(['member_name', 'target_node', 'transaction_type']).agg({
        'estimated_amount': 'sum',
        'transaction_date': 'count' # Use date to count rows
    }).rename(columns={'transaction_date': 'count'}).reset_index()

    nodes = {}
    links = []

    # Process Edges
    for _, row in edges_df.iterrows():
        source = row['member_name']
        target = row['target_node']
        value = row['estimated_amount']
        count = row['count']
        tx_type = row['transaction_type']

        # Add Nodes
        if source not in nodes:
            # Lookup Party
            party = party_map.get(source.lower().strip(), 'Unknown')
            nodes[source] = {'id': source, 'group': 'member', 'value': 0, 'party': party}
        
        if target not in nodes:
            nodes[target] = {'id': target, 'group': 'asset', 'value': 0}

        # Update Node Weights
        nodes[source]['value'] += value
        nodes[target]['value'] += value

        # Add Link
        links.append({
            'source': source,
            'target': target,
            'value': value,
            'count': int(count),
            'type': tx_type
        })

    # Convert nodes dict to list
    node_list = []
    for n in nodes.values():
        # Scale radius based on log of value
        import math
        radius = math.log(n['value'] + 1000) / 2
        n['radius'] = max(3, min(20, radius)) # Clamp radius
        node_list.append(n)

    logger.info(f"Generated {len(node_list)} nodes and {len(links)} links")
    return {'nodes': node_list, 'links': links}

def write_to_s3(data: dict, bucket_name: str):
    """Write network graph JSON to S3 for website."""
    s3 = boto3.client('s3')
    key = 'website/data/network_graph.json'
    
    logger.info(f"Uploading to s3://{bucket_name}/{key}...")
    s3.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps(data, indent=2),
        ContentType='application/json',
        CacheControl='max-age=300'
    )
    logger.info("Upload complete")

def main():
    logger.info("=" * 80)
    logger.info("Computing agg_network_graph (Real Data)")
    logger.info("=" * 80)

    # Load Data
    transactions_df = load_transactions(S3_BUCKET)
    members_df = load_dim_members(S3_BUCKET)

    # Generate Graph
    graph_data = generate_network_graph_data(transactions_df, members_df)

    # Write to S3
    write_to_s3(graph_data, S3_BUCKET)

    logger.info("\n✅ agg_network_graph computation complete!")

if __name__ == '__main__':
    main()
