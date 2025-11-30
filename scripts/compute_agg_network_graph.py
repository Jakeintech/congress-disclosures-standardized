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

    result = pd.concat(dfs, ignore_index=True)
    logger.info(f"Loaded {len(result):,} transactions")
    return result

def generate_network_graph_data(transactions_df: pd.DataFrame):
    """Generate network graph nodes and edges from transactions."""
    if transactions_df.empty:
        return {'nodes': [], 'links': []}

    logger.info("Generating network graph data...")

    # Filter out invalid tickers
    df = transactions_df.copy()
    df = df[df['ticker'].notna() & (df['ticker'] != '--') & (df['ticker'] != 'N/A')]
    
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

    # Aggregate Edges: Member -> Ticker
    # We sum the volume (estimated amount)
    edges_df = df.groupby(['member_name', 'ticker', 'transaction_type']).agg({
        'estimated_amount': 'sum'
    }).reset_index()

    # Filter low volume edges to keep graph readable (optional, can adjust threshold)
    # edges_df = edges_df[edges_df['estimated_amount'] > 5000] 

    nodes = {}
    links = []

    # Process Edges
    for _, row in edges_df.iterrows():
        source = row['member_name']
        target = row['ticker']
        value = row['estimated_amount']
        tx_type = row['transaction_type']

        # Add Nodes
        if source not in nodes:
            nodes[source] = {'id': source, 'group': 'member', 'value': 0}
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

    # Generate Graph
    graph_data = generate_network_graph_data(transactions_df)

    # Write to S3
    write_to_s3(graph_data, S3_BUCKET)

    logger.info("\n✅ agg_network_graph computation complete!")

if __name__ == '__main__':
    main()
