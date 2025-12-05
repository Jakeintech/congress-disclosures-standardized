"""
API Lambda: Get Lobbying Network Graph
Returns network graph data for visualization showing connections between members, bills, clients, and lobbyists.
"""

import json
import os
from typing import Dict, Any, List
import boto3
import pandas as pd

# Import shared utilities
import sys
sys.path.append('/opt')  # Lambda layer path
from api_lib import success_response, error_response, ParquetQueryBuilder

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

# Initialize AWS clients
s3_client = boto3.client('s3')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for network graph endpoint
    GET /v1/lobbying/network-graph?year=2024&congress=118
    """
    try:
        # Parse query parameters
        params = event.get('queryStringParameters') or {}
        year = params.get('year', '2024')
        congress = params.get('congress', '118')
        limit = min(int(params.get('limit', '500')), 1000)

        # Build network graph
        graph_data = build_network_graph(year, congress, limit)

        return success_response({
            'graph': graph_data,
            'metadata': {
                'year': year,
                'congress': congress,
                'node_count': len(graph_data['nodes']),
                'link_count': len(graph_data['links'])
            }
        })

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return error_response(str(e), 500)


def build_network_graph(year: str, congress: str, limit: int) -> Dict[str, Any]:
    """
    Build network graph data structure
    """
    nodes = []
    links = []
    node_ids = set()

    # 1. Load member-lobbyist network aggregate
    member_network = load_member_lobbyist_network(year)

    # 2. Load bill-lobbying correlations
    bill_lobbying = load_bill_lobbying_correlation(congress)

    # 3. Load triple correlations for high-strength connections
    triple_corr = load_triple_correlations(year, limit)

    # Build nodes and links from these sources
    nodes, links = combine_network_data(member_network, bill_lobbying, triple_corr)

    # Limit nodes for performance
    if len(nodes) > limit:
        # Keep highest degree nodes
        nodes = sorted(nodes, key=lambda n: n.get('connections', 0), reverse=True)[:limit]
        node_ids = set(n['id'] for n in nodes)
        links = [l for l in links if l['source'] in node_ids and l['target'] in node_ids]

    return {
        'nodes': nodes,
        'links': links
    }


def load_member_lobbyist_network(year: str) -> pd.DataFrame:
    """
    Load member-lobbyist network aggregate
    """
    try:
        query_builder = ParquetQueryBuilder(
            bucket=S3_BUCKET,
            prefix=f"gold/lobbying/aggregates/member_lobbyist_network/year={year}/"
        )
        df = query_builder.build_and_execute()
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        print(f"Error loading member network: {e}")
        return pd.DataFrame()


def load_bill_lobbying_correlation(congress: str) -> pd.DataFrame:
    """
    Load bill-lobbying correlation aggregate
    """
    try:
        query_builder = ParquetQueryBuilder(
            bucket=S3_BUCKET,
            prefix=f"gold/lobbying/aggregates/bill_lobbying_correlation/congress={congress}/"
        )
        df = query_builder.build_and_execute()
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        print(f"Error loading bill lobbying: {e}")
        return pd.DataFrame()


def load_triple_correlations(year: str, limit: int) -> pd.DataFrame:
    """
    Load triple correlations (high scores only)
    """
    try:
        query_builder = ParquetQueryBuilder(
            bucket=S3_BUCKET,
            prefix=f"gold/lobbying/aggregates/triple_correlation/year={year}/"
        )
        df = query_builder.build_and_execute()

        if df is not None and not df.empty:
            # Filter to high correlation scores
            df = df[df['correlation_score'] >= 60].head(limit)

        return df if df is not None else pd.DataFrame()
    except Exception as e:
        print(f"Error loading triple correlations: {e}")
        return pd.DataFrame()


def combine_network_data(
    member_network: pd.DataFrame,
    bill_lobbying: pd.DataFrame,
    triple_corr: pd.DataFrame
) -> tuple:
    """
    Combine all network data sources into nodes and links
    """
    nodes = []
    links = []
    node_map = {}  # Track nodes by ID to avoid duplicates

    # Process member-lobbyist network
    if not member_network.empty:
        for _, row in member_network.iterrows():
            member_id = row.get('member_bioguide_id')
            lobbyist_id = row.get('lobbyist_id')

            # Add member node
            if member_id and member_id not in node_map:
                node_map[member_id] = {
                    'id': member_id,
                    'name': row.get('member_name', member_id),
                    'type': 'member',
                    'party': row.get('member_party'),
                    'state': row.get('member_state'),
                    'connections': 0,
                    'bills_sponsored': row.get('sponsored_bill_count', 0)
                }

            # Add lobbyist node
            if lobbyist_id and lobbyist_id not in node_map:
                node_map[lobbyist_id] = {
                    'id': lobbyist_id,
                    'name': row.get('lobbyist_name', lobbyist_id),
                    'type': 'lobbyist',
                    'registrant_name': row.get('registrant_name'),
                    'covered_position': row.get('has_covered_position', False),
                    'connections': 0,
                    'contributions': row.get('total_contribution_amount', 0)
                }

            # Add link
            if member_id and lobbyist_id:
                connection_score = row.get('connection_score', 50)
                links.append({
                    'source': member_id,
                    'target': lobbyist_id,
                    'link_type': 'lobbied',
                    'strength': connection_score,
                    'weight': connection_score / 10
                })
                node_map[member_id]['connections'] += 1
                node_map[lobbyist_id]['connections'] += 1

    # Process bill-lobbying correlations
    if not bill_lobbying.empty:
        for _, row in bill_lobbying.iterrows():
            bill_id = row.get('bill_id')
            client_id = row.get('client_id')

            # Add bill node
            if bill_id and bill_id not in node_map:
                node_map[bill_id] = {
                    'id': bill_id,
                    'name': row.get('bill_title', bill_id),
                    'type': 'bill',
                    'bill_id': bill_id,
                    'sponsor_name': row.get('sponsor_name'),
                    'connections': 0,
                    'lobbying_spend': row.get('total_lobbying_spend', 0)
                }

            # Add client node
            if client_id and client_id not in node_map:
                node_map[client_id] = {
                    'id': client_id,
                    'name': row.get('client_name', client_id),
                    'type': 'client',
                    'connections': 0,
                    'spend': row.get('total_lobbying_spend', 0)
                }

            # Add link
            if bill_id and client_id:
                intensity = row.get('lobbying_intensity_score', 50)
                links.append({
                    'source': client_id,
                    'target': bill_id,
                    'link_type': 'lobbied',
                    'strength': min(intensity, 100),
                    'weight': intensity / 10
                })
                if bill_id in node_map:
                    node_map[bill_id]['connections'] += 1
                if client_id in node_map:
                    node_map[client_id]['connections'] += 1

    # Process triple correlations (adds high-value connections)
    if not triple_corr.empty:
        for _, row in triple_corr.iterrows():
            member_id = row.get('member_bioguide_id')
            bill_id = row.get('bill_id')
            ticker = row.get('ticker')

            # Add member node if not exists
            if member_id and member_id not in node_map:
                node_map[member_id] = {
                    'id': member_id,
                    'name': row.get('member_name', member_id),
                    'type': 'member',
                    'connections': 0
                }

            # Add bill node if not exists
            if bill_id and bill_id not in node_map:
                node_map[bill_id] = {
                    'id': bill_id,
                    'name': bill_id,
                    'type': 'bill',
                    'connections': 0
                }

            # Add member -> bill link (sponsorship/correlation)
            if member_id and bill_id:
                score = row.get('correlation_score', 50)
                links.append({
                    'source': member_id,
                    'target': bill_id,
                    'link_type': 'sponsored',
                    'strength': score,
                    'weight': score / 10
                })
                if member_id in node_map:
                    node_map[member_id]['connections'] += 1
                if bill_id in node_map:
                    node_map[bill_id]['connections'] += 1

    # Convert node_map to list
    nodes = list(node_map.values())

    return nodes, links
