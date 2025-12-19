#!/usr/bin/env python3
"""
Compute agg_network_graph aggregate table.

Generates network graph data (Nodes and Edges) for Member-Asset relationships
based on actual transaction data from the Silver layer.
"""

import duckdb
import pandas as pd
import boto3
import os
import logging
import json
from datetime import datetime
from pathlib import Path
import math

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

def get_duckdb_conn():
    """Create a DuckDB connection with S3 support."""
    conn = duckdb.connect(':memory:')
    conn.execute("INSTALL httpfs; LOAD httpfs;")
    conn.execute(f"SET s3_region='{os.environ.get('AWS_REGION', 'us-east-1')}';")
    conn.execute("SET s3_use_ssl=true;")
    return conn

def compute_graph_data(conn):
    """Compute nodes and edges for the network graph via DuckDB."""
    logger.info("Computing network graph data via DuckDB...")
    
    # 1. Base Query: Enriched nodes and edges
    # We join transactions with assets and members to get a clean source-target set
    base_sql = f"""
        WITH transaction_data AS (
            SELECT 
                COALESCE(m.filer_name, t.filer_name) as member_name,
                COALESCE(t.ticker, a.ticker, 'Unknown') as ticker,
                COALESCE(a.asset_name, t.asset_description) as asset_display_name,
                (t.amount_low + t.amount_high) / 2.0 as amount_midpoint,
                t.transaction_type,
                t.bioguide_id,
                m.party,
                m.chamber
            FROM read_parquet('s3://{BUCKET_NAME}/gold/house/financial/facts/fact_ptr_transactions/**/*.parquet') t
            LEFT JOIN read_parquet('s3://{BUCKET_NAME}/gold/house/financial/dimensions/dim_assets/**/*.parquet') a
                ON t.asset_key = a.asset_key
            LEFT JOIN read_parquet('s3://{BUCKET_NAME}/gold/house/financial/dimensions/dim_members/**/*.parquet') m
                ON t.bioguide_id = m.bioguide_id
            WHERE t.bioguide_id IS NOT NULL
        )
        SELECT * FROM transaction_data
    """
    conn.execute(f"CREATE OR REPLACE VIEW graph_base AS {base_sql}")
    
    # 2. Edges: Member -> Stock
    edges_sql = """
        SELECT 
            member_name as source,
            ticker as target,
            SUM(amount_midpoint) as value,
            COUNT(*) as count,
            MAX(transaction_type) as type
        FROM graph_base
        WHERE ticker != 'Unknown'
        GROUP BY member_name, ticker
    """
    edges_df = conn.execute(edges_sql).df()
    
    # 3. Nodes: Members and Assets
    # Member nodes with metrics
    members_sql = """
        SELECT 
            member_name as id,
            'member' as "group",
            SUM(amount_midpoint) as value,
            COUNT(*) as transaction_count,
            MAX(party) as party,
            MAX(chamber) as chamber,
            MAX(bioguide_id) as bioguide_id
        FROM graph_base
        GROUP BY member_name
    """
    member_nodes_df = conn.execute(members_sql).df()
    
    # Asset nodes with metrics
    assets_sql = """
        SELECT 
            ticker as id,
            'asset' as "group",
            SUM(amount_midpoint) as value,
            COUNT(*) as transaction_count,
            COUNT(DISTINCT bioguide_id) as degree
        FROM graph_base
        WHERE ticker != 'Unknown'
        GROUP BY ticker
    """
    asset_nodes_df = conn.execute(assets_sql).df()
    
    return {
        'members': member_nodes_df,
        'assets': asset_nodes_df,
        'edges': edges_df
    }

def generate_graph_json(data):
    """Convert raw dataframes into the specialized network graph JSON format."""
    logger.info("Formatting graph JSON...")
    
    member_nodes = data['members']
    asset_nodes = data['assets']
    edges = data['edges']
    
    # Calculate normalization factors
    total_volume = member_nodes['value'].sum() + asset_nodes['value'].sum()
    total_tx = member_nodes['transaction_count'].sum()
    max_degree = asset_nodes['degree'].max() if not asset_nodes.empty else 1
    
    nodes = []
    
    # Process Member Nodes
    for _, row in member_nodes.iterrows():
        # Calculate importance score for members
        # Weighted by volume (40%), tx count (30%), and distinct assets (handled later)
        importance = (row['value'] / total_volume * 0.4) + (row['transaction_count'] / total_tx * 0.3)
        
        nodes.append({
            'id': row['id'],
            'group': 'member',
            'value': float(row['value']),
            'transaction_count': int(row['transaction_count']),
            'party': row['party'] or 'Unknown',
            'chamber': row['chamber'] or 'Unknown',
            'bioguide_id': row['bioguide_id'],
            'importance_score': float(importance),
            'radius': max(5, min(20, 5 + (math.log(importance * 1000 + 1) * 2.5)))
        })
        
    # Process Asset Nodes
    for _, row in asset_nodes.iterrows():
        # Calculate importance score for assets
        # Weighted by volume (40%), degree (traders) (40%), tx frequency (20%)
        importance = (row['value'] / total_volume * 0.4) + (row['degree'] / max_degree * 0.4) + (row['transaction_count'] / total_tx * 0.2)
        
        nodes.append({
            'id': row['id'],
            'group': 'asset',
            'value': float(row['value']),
            'transaction_count': int(row['transaction_count']),
            'degree': int(row['degree']),
            'importance_score': float(importance),
            'radius': max(5, min(30, 5 + (math.log(importance * 1000 + 1) * 3.5)))
        })
        
    links = []
    for _, row in edges.iterrows():
        links.append({
            'source': row['source'],
            'target': row['target'],
            'value': float(row['value']),
            'count': int(row['count']),
            'type': row['type']
        })
        
    # Additional Aggregated Nodes (Parties)
    aggregated_nodes = []
    for party in ['D', 'R', 'I']:
        party_members = member_nodes[member_nodes['party'] == party]
        if not party_members.empty:
            label = 'Democrat' if party == 'D' else 'Republican' if party == 'R' else 'Independent'
            aggregated_nodes.append({
                'id': label,
                'group': 'party_agg',
                'value': float(party_members['value'].sum()),
                'transaction_count': int(party_members['transaction_count'].sum()),
                'radius': 40
            })
            
    return {
        'metadata': {
            'generated_at': datetime.utcnow().isoformat(),
            'total_nodes': len(nodes),
            'total_links': len(links)
        },
        'nodes': nodes,
        'links': links,
        'aggregated_nodes': aggregated_nodes,
        'summary_stats': {
            'total_volume': float(total_volume),
            'total_trades': int(total_tx)
        }
    }

def write_to_s3(data: dict):
    """Write network graph JSON to S3."""
    s3 = boto3.client('s3')
    key = 'website/data/network_graph.json'
    
    logger.info(f"Uploading to s3://{BUCKET_NAME}/{key}...")
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=json.dumps(data, indent=2),
        ContentType='application/json'
    )
    logger.info("Upload complete!")

def main():
    logger.info("=" * 80)
    logger.info("Starting Optimized Network Graph Computation")
    logger.info("=" * 80)
    
    conn = get_duckdb_conn()
    
    try:
        data = compute_graph_data(conn)
        graph_json = generate_graph_json(data)
        write_to_s3(graph_json)
        logger.info("✅ Network graph complete!")
    except Exception as e:
        logger.error(f"❌ Graph computation failed: {e}", exc_info=True)
    finally:
        conn.close()

if __name__ == '__main__':
    main()

if __name__ == '__main__':
    main()
