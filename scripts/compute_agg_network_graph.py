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
    """Generate network graph nodes and edges with comprehensive SNA metrics."""
    if transactions_df.empty:
        return {'nodes': [], 'links': [], 'metadata': {}, 'summary_stats': {}}

    logger.info("Generating network graph data...")

    # Create member lookup maps
    member_data = {}
    if not members_df.empty:
        members_df['lookup_name'] = members_df['full_name'].str.lower().str.strip()
        for _, row in members_df.iterrows():
            member_data[row['lookup_name']] = {
                'party': row.get('party'),
                'state': row.get('state'),
                'chamber': row.get('chamber'),
                'bioguide_id': row.get('bioguide_id'),
                'district': row.get('district')
            }

    # Filter out invalid rows (must have ticker OR asset_name)
    df = transactions_df.copy()
    
    # Create a target column: use ticker if available, else try to extract from asset_name
    import re
    import math
    from datetime import datetime
    
    def get_target(row):
        # 1. Try explicit ticker
        ticker = row.get('ticker')
        if ticker and ticker != '--' and ticker != 'N/A':
            return ticker
        
        asset = row.get('asset_name')
        if not asset:
            return None
            
        # 2. Try to extract ticker from parenthesis e.g. "Apple Inc (AAPL)"
        match = re.search(r'\(([A-Z]{1,5})\)', asset)
        if match:
            return match.group(1)
            
        # 3. Fallback to truncated asset name
        return asset[:20] + '...' if len(asset) > 20 else asset

    df['target_node'] = df.apply(get_target, axis=1)
    df = df[df['target_node'].notna()]
    
    # Calculate estimated amount
    def estimate_amount(row):
        try:
            low = float(row.get('amount_low', 0) or 0)
            high = float(row.get('amount_high', 0) or 0)
            if high > 0:
                return (low + high) / 2
            return low or 1000
        except:
            return 1000

    df['estimated_amount'] = df.apply(estimate_amount, axis=1)
    df['member_name'] = df['first_name'] + ' ' + df['last_name']

    # Get date range
    dates = pd.to_datetime(df['transaction_date'], errors='coerce')
    date_range = {
        'start': str(dates.min()) if not dates.isna().all() else None,
        'end': str(dates.max()) if not dates.isna().all() else None
    }

    # Aggregate edges
    edges_df = df.groupby(['member_name', 'target_node', 'transaction_type']).agg({
        'estimated_amount': 'sum',
        'transaction_date': 'count'
    }).rename(columns={'transaction_date': 'count'}).reset_index()

    nodes = {}
    links = []
    member_transaction_counts = {}
    member_assets = {}  # Track which assets each member trades

    # Process edges and build nodes
    for _, row in edges_df.iterrows():
        source = row['member_name']
        target = row['target_node']
        value = row['estimated_amount']
        count = row['count']
        tx_type = row['transaction_type']

        # Track transaction counts per member
        member_transaction_counts[source] = member_transaction_counts.get(source, 0) + count
        
        # Track member-asset relationships for community detection
        if source not in member_assets:
            member_assets[source] = {}
        member_assets[source][target] = member_assets[source].get(target, 0) + value

        # Add/update member node
        if source not in nodes:
            lookup_key = source.lower().strip()
            member_info = member_data.get(lookup_key, {})
            
            nodes[source] = {
                'id': source,
                'group': 'member',
                'value': 0,
                'transaction_count': 0,
                'party': member_info.get('party', 'Unknown'),
                'state': member_info.get('state'),
                'chamber': member_info.get('chamber', 'House'),
                'bioguide_id': member_info.get('bioguide_id'),
                'district': member_info.get('district')
            }
        
        # Add/update asset node
        if target not in nodes:
            nodes[target] = {
                'id': target,
                'group': 'asset',
                'value': 0,
                'transaction_count': 0
            }

        # Update node weights and transaction counts
        nodes[source]['value'] += value
        nodes[target]['value'] += value
        nodes[source]['transaction_count'] += count
        nodes[target]['transaction_count'] += count

        # Add link
        links.append({
            'source': source,
            'target': target,
            'value': value,
            'count': int(count),
            'type': tx_type
        })
    
    # Assign community IDs to members based on their primary asset focus
    # This enables visual clustering of members who trade similar assets
    for member_name, assets in member_assets.items():
        if member_name in nodes:
            # Find the asset they trade most (by volume)
            primary_asset = max(assets.items(), key=lambda x: x[1])[0] if assets else None
            nodes[member_name]['primary_asset'] = primary_asset
            
            # Create clusters based on party + chamber for simpler community structure
            party = nodes[member_name].get('party', 'Unknown')
            chamber = nodes[member_name].get('chamber', 'House')
            community_id = f"{party}_{chamber}"
            nodes[member_name]['community_id'] = community_id

    # Calculate degree centrality (number of unique connections)
    degree = {}
    for link in links:
        degree[link['source']] = degree.get(link['source'], 0) + 1
        degree[link['target']] = degree.get(link['target'], 0) + 1

    # Calculate total network metrics for normalization
    total_volume = sum(n['value'] for n in nodes.values())
    total_transactions = sum(n['transaction_count'] for n in nodes.values())
    max_degree = max(degree.values()) if degree else 1

    # --- Aggregation Logic ---
    # Create aggregated nodes for Parties
    agg_nodes = {}
    agg_links = {}  # (Party, Asset) -> {value, count}

    # Initialize Party Nodes
    parties = ['Democrat', 'Republican']
    for p in parties:
        agg_nodes[p] = {
            'id': p,
            'group': 'party_agg',
            'value': 0,
            'transaction_count': 0,
            'party': p,
            'radius': 40, # Fixed large radius for aggregate nodes
            'importance_score': 1.0
        }

    # Convert nodes dict to list and calculate sophisticated importance scores
    node_list = []
    for node_id, n in nodes.items():
        # Add degree centrality
        n['degree'] = degree.get(node_id, 0)
        
        # Calculate normalized metrics (0-1 scale)
        degree_norm = n['degree'] / max_degree if max_degree > 0 else 0
        volume_norm = n['value'] / total_volume if total_volume > 0 else 0
        tx_count_norm = n['transaction_count'] / total_transactions if total_transactions > 0 else 0
        
        # Calculate composite importance score with weighted factors
        if n['group'] == 'asset':
            # For assets, emphasize:
            # - How many unique members trade it (degree centrality) - 35%
            # - Total volume traded (node strength) - 35%
            # - Transaction frequency - 20%
            # - Network concentration (share of total activity) - 10%
            importance_score = (
                (degree_norm * 0.35) +           # Popularity (unique traders)
                (volume_norm * 0.35) +           # Financial significance (total volume)
                (tx_count_norm * 0.20) +         # Activity level (frequency)
                (volume_norm * 0.10)             # Concentration (duplicate for emphasis)
            )
        else:  # member node
            # For members, emphasize:
            # - Transaction volume - 40%
            # - Number of unique assets - 30%
            # - Transaction frequency - 30%
            importance_score = (
                (volume_norm * 0.40) +           # Portfolio value
                (degree_norm * 0.30) +           # Portfolio diversity
                (tx_count_norm * 0.30)           # Trading activity
            )
            
            # Assign parentId for hierarchy
            party = n.get('party')
            if party in parties:
                n['parentId'] = party
                # Accumulate to aggregate node
                agg_nodes[party]['value'] += n['value']
                agg_nodes[party]['transaction_count'] += n['transaction_count']
        
        n['importance_score'] = importance_score
        
        # Calculate radius using importance score with log scaling for readability
        # Base radius of 5, scaled by log of importance with multiplier
        if importance_score > 0:
            # Use log scale to prevent extreme size differences
            radius = 5 + (math.log(importance_score * 1000 + 1) * 2.5)
        else:
            radius = 3
        
        n['radius'] = max(3, min(25, radius))  # Clamp between 3-25
        
        node_list.append(n)

    # Aggregate Links
    # Iterate through original links to build aggregated links
    for link in links:
        source_id = link['source']
        target_id = link['target']
        
        # Check if source is a member (it should be)
        if source_id in nodes and nodes[source_id]['group'] == 'member':
            party = nodes[source_id].get('party')
            if party in parties:
                key = (party, target_id)
                if key not in agg_links:
                    agg_links[key] = {'value': 0, 'count': 0, 'types': set()}
                
                agg_links[key]['value'] += link['value']
                agg_links[key]['count'] += link['count']
                agg_links[key]['types'].add(link['type'])

    # Convert agg_links to list
    agg_link_list = []
    for (source, target), data in agg_links.items():
        agg_link_list.append({
            'source': source,
            'target': target,
            'value': data['value'],
            'count': data['count'],
            'type': 'mixed' if len(data['types']) > 1 else list(data['types'])[0],
            'is_aggregated': True
        })

    # Add aggregated nodes to the main list (or keep separate? Let's keep separate list for clarity in JSON)
    agg_node_list = list(agg_nodes.values())

    # Calculate summary stats
    member_nodes = [n for n in node_list if n['group'] == 'member']
    asset_nodes = [n for n in node_list if n['group'] == 'asset']
    
    # Find top assets by importance
    top_assets = sorted(asset_nodes, key=lambda x: x['importance_score'], reverse=True)[:10]
    
    party_counts = {}
    for n in member_nodes:
        party = n.get('party', 'Unknown')
        party_counts[party] = party_counts.get(party, 0) + 1
    
    summary_stats = {
        'total_nodes': len(node_list),
        'total_member_nodes': len(member_nodes),
        'total_asset_nodes': len(asset_nodes),
        'total_links': len(links),
        'total_transactions': int(df.shape[0]),
        'total_volume': float(df['estimated_amount'].sum()),
        'party_distribution': party_counts,
        'date_range': date_range,
        'top_assets': [
            {
                'name': a['id'],
                'importance': round(a['importance_score'], 4),
                'unique_traders': a['degree'],
                'volume': a['value'],
                'transactions': a['transaction_count']
            }
            for a in top_assets
        ]
    }
    
    metadata = {
        'generated_at': datetime.utcnow().isoformat(),
        'total_nodes': len(node_list),
        'total_links': len(links),
        'total_transactions': int(df.shape[0]),
        'date_range': date_range,
        'data_quality': {
            'party_coverage': sum(1 for n in member_nodes if n.get('party') not in [None, 'Unknown', '']) / max(1, len(member_nodes))
        }
    }

    logger.info(f"Generated {len(node_list)} nodes and {len(links)} links")
    logger.info(f"Generated {len(agg_node_list)} aggregated nodes and {len(agg_link_list)} aggregated links")
    logger.info(f"Party coverage: {metadata['data_quality']['party_coverage']*100:.1f}%")
    
    return {
        'metadata': metadata,
        'nodes': node_list,
        'links': links,
        'aggregated_nodes': agg_node_list,
        'aggregated_links': agg_link_list,
        'summary_stats': summary_stats
    }

def write_to_s3(data: dict, bucket_name: str):
    """Write network graph JSON to S3 for website and locally for testing."""
    s3 = boto3.client('s3')
    key = 'website/data/network_graph.json'
    json_data = json.dumps(data, indent=2)
    
    # Write to S3
    logger.info(f"Uploading to s3://{bucket_name}/{key}...")
    s3.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json_data,
        ContentType='application/json',
        CacheControl='max-age=300'
    )
    logger.info("Upload complete")
    
    # Also write locally for testing
    local_path = Path('website/data/network_graph.json')
    local_path.parent.mkdir(parents=True, exist_ok=True)
    with open(local_path, 'w') as f:
        f.write(json_data)
    logger.info(f"Also written locally to {local_path}")

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
