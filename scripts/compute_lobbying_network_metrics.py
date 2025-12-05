#!/usr/bin/env python3
"""
Compute Social Network Analysis Metrics for Lobbying Network

Calculates:
- Centrality measures (degree, betweenness, eigenvector)
- Community detection (Louvain algorithm)
- Influence scores (PageRank)
- Revolving door analysis
"""

import os
import sys
import pandas as pd
import numpy as np
import networkx as nx
from typing import Dict, List, Tuple
import boto3
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ingestion'))
from lib.parquet_writer import write_parquet_to_s3

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

# Initialize AWS clients
s3_client = boto3.client('s3')


def main():
    """
    Main execution function
    """
    print("=" * 80)
    print("COMPUTING LOBBYING NETWORK METRICS")
    print("=" * 80)

    year = sys.argv[1] if len(sys.argv) > 1 else '2024'
    print(f"\nProcessing year: {year}")

    # Load network data
    print("\n[1/5] Loading network data...")
    G = load_network_graph(year)
    print(f"   Network loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # Compute centrality metrics
    print("\n[2/5] Computing centrality metrics...")
    centrality_df = compute_centrality_metrics(G)
    print(f"   Computed metrics for {len(centrality_df)} entities")

    # Detect communities
    print("\n[3/5] Detecting communities...")
    communities_df = detect_communities(G)
    print(f"   Found {communities_df['community_id'].nunique()} communities")

    # Compute influence scores
    print("\n[4/5] Computing influence scores...")
    influence_df = compute_influence_scores(G, year)
    print(f"   Computed influence scores for {len(influence_df)} entities")

    # Revolving door analysis
    print("\n[5/5] Analyzing revolving door connections...")
    revolving_door_df = analyze_revolving_door(year)
    print(f"   Found {len(revolving_door_df)} revolving door lobbyists")

    # Write to Gold layer
    print("\n" + "=" * 80)
    print("WRITING TO GOLD LAYER")
    print("=" * 80)

    write_metrics_to_gold(centrality_df, communities_df, influence_df, revolving_door_df, year)

    print("\n✅ Network metrics computation complete!")
    print(f"   Output: s3://{S3_BUCKET}/gold/lobbying/aggregates/network_metrics/year={year}/")


def load_network_graph(year: str) -> nx.Graph:
    """
    Load network graph from Gold layer aggregates
    """
    G = nx.Graph()

    # Load member-lobbyist connections
    try:
        member_network_key = f"gold/lobbying/aggregates/member_lobbyist_network/year={year}/data.parquet"
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=member_network_key)
        member_df = pd.read_parquet(response['Body'])

        for _, row in member_df.iterrows():
            member_id = row['member_bioguide_id']
            lobbyist_id = row['lobbyist_id']
            score = row.get('connection_score', 50)

            G.add_node(member_id, type='member', name=row.get('member_name'))
            G.add_node(lobbyist_id, type='lobbyist', name=row.get('lobbyist_name'))
            G.add_edge(member_id, lobbyist_id, weight=score, edge_type='lobbied')

        print(f"   Loaded {len(member_df)} member-lobbyist connections")
    except Exception as e:
        print(f"   Warning: Could not load member-lobbyist network: {e}")

    # Load bill-lobbying connections
    try:
        bill_lobbying_key = f"gold/lobbying/aggregates/bill_lobbying_correlation/"
        # Find parquet files
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=bill_lobbying_key, MaxKeys=1000)

        if 'Contents' in response:
            for obj in response['Contents']:
                if obj['Key'].endswith('.parquet'):
                    obj_response = s3_client.get_object(Bucket=S3_BUCKET, Key=obj['Key'])
                    bill_df = pd.read_parquet(obj_response['Body'])

                    for _, row in bill_df.iterrows():
                        bill_id = row['bill_id']
                        client_id = row.get('client_id')

                        if client_id:
                            G.add_node(bill_id, type='bill', name=row.get('bill_id'))
                            G.add_node(client_id, type='client', name=row.get('client_name'))
                            G.add_edge(client_id, bill_id,
                                     weight=row.get('lobbying_intensity_score', 50),
                                     edge_type='lobbied')

                    print(f"   Loaded bill-lobbying connections from {obj['Key']}")
                    break  # Just load first file for now
    except Exception as e:
        print(f"   Warning: Could not load bill-lobbying network: {e}")

    # Load triple correlations (high-value connections)
    try:
        triple_key = f"gold/lobbying/aggregates/triple_correlation/year={year}/data.parquet"
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=triple_key)
        triple_df = pd.read_parquet(response['Body'])

        # Filter to high scores
        triple_df = triple_df[triple_df['correlation_score'] >= 70]

        for _, row in triple_df.iterrows():
            member_id = row['member_bioguide_id']
            bill_id = row['bill_id']

            G.add_node(member_id, type='member', name=row.get('member_name'))
            G.add_node(bill_id, type='bill', name=row.get('bill_id'))
            G.add_edge(member_id, bill_id,
                     weight=row['correlation_score'],
                     edge_type='sponsored')

        print(f"   Loaded {len(triple_df)} high-value triple correlations")
    except Exception as e:
        print(f"   Warning: Could not load triple correlations: {e}")

    return G


def compute_centrality_metrics(G: nx.Graph) -> pd.DataFrame:
    """
    Compute centrality metrics for all nodes
    """
    records = []

    # Degree centrality
    degree_centrality = nx.degree_centrality(G)

    # Betweenness centrality (sampling for large graphs)
    if G.number_of_nodes() > 1000:
        betweenness = nx.betweenness_centrality(G, k=min(100, G.number_of_nodes()))
    else:
        betweenness = nx.betweenness_centrality(G)

    # Eigenvector centrality (with fallback)
    try:
        eigenvector = nx.eigenvector_centrality(G, max_iter=100)
    except:
        print("   Warning: Eigenvector centrality failed, using degree as fallback")
        eigenvector = degree_centrality

    # PageRank
    pagerank = nx.pagerank(G, weight='weight')

    # Compile metrics
    for node in G.nodes():
        node_data = G.nodes[node]

        records.append({
            'entity_id': node,
            'entity_type': node_data.get('type', 'unknown'),
            'entity_name': node_data.get('name', node),
            'degree_centrality': degree_centrality.get(node, 0),
            'betweenness_centrality': betweenness.get(node, 0),
            'eigenvector_centrality': eigenvector.get(node, 0),
            'pagerank': pagerank.get(node, 0),
            'degree': G.degree(node),
            'weighted_degree': sum(G[node][neighbor].get('weight', 1) for neighbor in G.neighbors(node))
        })

    df = pd.DataFrame(records)

    # Add percentile ranks
    for metric in ['degree_centrality', 'betweenness_centrality', 'eigenvector_centrality', 'pagerank']:
        df[f'{metric}_percentile'] = df[metric].rank(pct=True) * 100

    # Sort by PageRank
    df = df.sort_values('pagerank', ascending=False).reset_index(drop=True)

    return df


def detect_communities(G: nx.Graph) -> pd.DataFrame:
    """
    Detect communities using Louvain algorithm
    """
    try:
        import community as community_louvain
    except ImportError:
        print("   Warning: python-louvain not installed, using connected components instead")
        # Fallback to connected components
        communities = list(nx.connected_components(G))
        partition = {}
        for i, community in enumerate(communities):
            for node in community:
                partition[node] = i
    else:
        # Use Louvain algorithm
        partition = community_louvain.best_partition(G, weight='weight')

    records = []

    for node, community_id in partition.items():
        node_data = G.nodes[node]

        records.append({
            'entity_id': node,
            'entity_type': node_data.get('type', 'unknown'),
            'entity_name': node_data.get('name', node),
            'community_id': community_id,
            'degree': G.degree(node)
        })

    df = pd.DataFrame(records)

    # Compute community statistics
    community_stats = df.groupby('community_id').agg({
        'entity_id': 'count',
        'degree': 'sum'
    }).rename(columns={'entity_id': 'member_count', 'degree': 'total_connections'})

    df = df.merge(community_stats, on='community_id', how='left')

    # Identify bridge nodes (nodes connecting multiple communities)
    bridge_scores = []
    for node in G.nodes():
        neighbor_communities = set()
        for neighbor in G.neighbors(node):
            neighbor_communities.add(partition[neighbor])
        bridge_score = len(neighbor_communities)
        bridge_scores.append({'entity_id': node, 'bridge_score': bridge_score})

    bridge_df = pd.DataFrame(bridge_scores)
    df = df.merge(bridge_df, on='entity_id', how='left')

    return df


def compute_influence_scores(G: nx.Graph, year: str) -> pd.DataFrame:
    """
    Compute influence scores based on network position + money
    """
    # Get centrality metrics
    pagerank = nx.pagerank(G, weight='weight')

    # Load financial data
    member_scores = {}

    try:
        # Load member trading stats
        trading_key = f"gold/house/financial/aggregates/member_trading_stats/year={year}/data.parquet"
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=trading_key)
        trading_df = pd.read_parquet(response['Body'])

        for _, row in trading_df.iterrows():
            bioguide = row['bioguide_id']
            if bioguide in G.nodes():
                member_scores[bioguide] = {
                    'trade_volume': row.get('total_volume', 0),
                    'trade_count': row.get('total_transactions', 0)
                }
    except Exception as e:
        print(f"   Warning: Could not load trading stats: {e}")

    # Compute composite influence score
    records = []

    for node in G.nodes():
        node_data = G.nodes[node]
        node_type = node_data.get('type', 'unknown')

        # Base score from PageRank
        base_score = pagerank.get(node, 0) * 1000

        # Adjust by entity type
        if node_type == 'member':
            # Members: boost by trading activity
            if node in member_scores:
                trade_boost = np.log1p(member_scores[node]['trade_volume']) / 100
                base_score += trade_boost

        elif node_type == 'client':
            # Clients: boost by lobbying spend (would need to join with dim_client)
            pass

        elif node_type == 'lobbyist':
            # Lobbyists: boost by contribution amount (would need to join with dim_lobbyist)
            pass

        records.append({
            'entity_id': node,
            'entity_type': node_type,
            'entity_name': node_data.get('name', node),
            'influence_score': base_score,
            'pagerank': pagerank.get(node, 0),
            'degree': G.degree(node)
        })

    df = pd.DataFrame(records)

    # Add percentile rank
    df['influence_percentile'] = df['influence_score'].rank(pct=True) * 100

    # Sort by influence score
    df = df.sort_values('influence_score', ascending=False).reset_index(drop=True)

    return df


def analyze_revolving_door(year: str) -> pd.DataFrame:
    """
    Analyze revolving door connections (lobbyists with government experience)
    """
    try:
        # Load dim_lobbyist
        lobbyist_key = f"gold/lobbying/dimensions/dim_lobbyist/data.parquet"
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=lobbyist_key)
        lobbyist_df = pd.read_parquet(response['Body'])

        # Filter to those with covered positions
        revolving_df = lobbyist_df[
            (lobbyist_df['has_covered_position'] == True) |
            (lobbyist_df['covered_position_org'].notna())
        ].copy()

        # Load their contribution data
        try:
            contrib_key = f"silver/lobbying/contributions/year={year}/data.parquet"
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=contrib_key)
            contrib_df = pd.read_parquet(response['Body'])

            # Aggregate contributions by lobbyist
            contrib_agg = contrib_df.groupby('lobbyist_id').agg({
                'amount': 'sum',
                'contribution_id': 'count'
            }).rename(columns={'amount': 'total_contributions', 'contribution_id': 'contribution_count'})

            revolving_df = revolving_df.merge(contrib_agg, left_on='lobbyist_id', right_index=True, how='left')
        except Exception as e:
            print(f"   Warning: Could not load contribution data: {e}")
            revolving_df['total_contributions'] = 0
            revolving_df['contribution_count'] = 0

        # Fill NaN values
        revolving_df['total_contributions'] = revolving_df['total_contributions'].fillna(0)
        revolving_df['contribution_count'] = revolving_df['contribution_count'].fillna(0)

        # Calculate revolving door score
        # Higher score = more concerning (high contributions + high-level former position)
        revolving_df['revolving_door_score'] = (
            np.log1p(revolving_df['total_contributions']) * 10 +
            revolving_df['contribution_count'] * 5
        )

        # Sort by score
        revolving_df = revolving_df.sort_values('revolving_door_score', ascending=False)

        return revolving_df

    except Exception as e:
        print(f"   Error in revolving door analysis: {e}")
        return pd.DataFrame()


def write_metrics_to_gold(
    centrality_df: pd.DataFrame,
    communities_df: pd.DataFrame,
    influence_df: pd.DataFrame,
    revolving_door_df: pd.DataFrame,
    year: str
):
    """
    Write all computed metrics to Gold layer
    """
    # Centrality metrics
    if not centrality_df.empty:
        centrality_key = f"gold/lobbying/aggregates/network_metrics/year={year}/centrality.parquet"
        write_parquet_to_s3(centrality_df, S3_BUCKET, centrality_key)
        print(f"   ✓ Centrality metrics: {centrality_key}")

    # Community detection
    if not communities_df.empty:
        communities_key = f"gold/lobbying/aggregates/network_metrics/year={year}/communities.parquet"
        write_parquet_to_s3(communities_df, S3_BUCKET, communities_key)
        print(f"   ✓ Communities: {communities_key}")

    # Influence scores
    if not influence_df.empty:
        influence_key = f"gold/lobbying/aggregates/network_metrics/year={year}/influence.parquet"
        write_parquet_to_s3(influence_df, S3_BUCKET, influence_key)
        print(f"   ✓ Influence scores: {influence_key}")

    # Revolving door
    if not revolving_door_df.empty:
        revolving_key = f"gold/lobbying/aggregates/network_metrics/year={year}/revolving_door.parquet"
        write_parquet_to_s3(revolving_door_df, S3_BUCKET, revolving_key)
        print(f"   ✓ Revolving door: {revolving_key}")


if __name__ == '__main__':
    main()
