"""
Lambda handler: GET /v1/members/{bioguide}/lobbying-connections

Get lobbying connections for a member including:
- Contributions received from lobbyists
- Bills sponsored that were lobbied
- Industry overlap (member's trades vs lobbying clients)
- Network graph data (nodes/edges for visualization)
"""

import os
import json
import logging
import math
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def clean_nan(obj):
    """Replace NaN/Inf values with None for JSON serialization."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    elif isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan(v) for v in obj]
    return obj


def handler(event, context):
    """Handle GET /v1/members/{bioguide}/lobbying-connections request."""
    try:
        logger.info(f"Event: {json.dumps(event)}")

        # Get bioguide from path parameters
        path_params = event.get('pathParameters', {}) or {}
        bioguide_id = path_params.get('bioguide')

        if not bioguide_id:
            return error_response("bioguide is required", 400)

        # Parse query parameters
        params = event.get('queryStringParameters', {}) or {}
        year = int(params.get('year', 2024))

        qb = ParquetQueryBuilder(S3_BUCKET)

        # Get member-lobbyist network connections
        network_df = qb.query_parquet(
            f'gold/lobbying/agg_member_lobbyist_connections/year={year}',
            filters={'member_bioguide_id': bioguide_id},
            limit=100
        )

        if network_df.empty:
            connections = []
            total_connection_score = 0
        else:
            connections = network_df.to_dict('records')
            total_connection_score = network_df['total_connection_score'].sum()

        # Get contributions received
        # (Would need to link lobbyist IDs to member name - simplified)
        contributions_received = []  # TODO: Implement

        # Get bills sponsored that were lobbied
        sponsored_bills = []

        if not network_df.empty:
            # Extract unique bills from connections
            all_bills = []
            for conn in connections:
                bills = conn.get('bills_in_common', [])
                all_bills.extend(bills)

            sponsored_bills = list(set(all_bills))

        # Build network graph data
        # Nodes: Member (center), Clients (around), Bills (connected)
        nodes = [
            {
                'id': bioguide_id,
                'type': 'member',
                'label': bioguide_id
            }
        ]

        edges = []

        for conn in connections[:20]:  # Top 20 connections
            client_name = conn.get('client_name', '')

            # Add client node
            nodes.append({
                'id': f'client_{client_name}',
                'type': 'client',
                'label': client_name
            })

            # Add edge
            edges.append({
                'source': bioguide_id,
                'target': f'client_{client_name}',
                'weight': conn.get('total_connection_score', 0),
                'type': ','.join(conn.get('connection_types', []))
            })

        response_data = {
            'bioguide_id': bioguide_id,
            'year': year,
            'connections': [clean_nan(c) for c in connections],
            'connection_count': len(connections),
            'total_connection_score': float(total_connection_score),
            'contributions_received': contributions_received,
            'bills_sponsored_with_lobbying': sponsored_bills,
            'network_graph': {
                'nodes': nodes,
                'edges': edges
            }
        }

        return success_response(response_data)

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return error_response(str(e), 500)
