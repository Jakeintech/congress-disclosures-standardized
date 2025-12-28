"""
API Lambda: Get Lobbying Network Graph
Returns comprehensive network graph with multiple node types and labeled relationships.

Node Types:
- 🏛️ member: Congress members
- 📜 bill: Bills being lobbied
- 🏢 client: Organizations funding lobbying
- 👔 lobbyist: Lobbying firms (registrants)

Edge Types (with labels):
- "funds": client → lobbyist
- "lobbies_for": lobbyist → bill
- "contacts": lobbyist → member (via govt entities contacted)
- "sponsors": member → bill (if bill sponsor data available)
"""

import json
import os
from typing import Dict, Any, List
import boto3
import pandas as pd
import io

# Import shared utilities
import sys
sys.path.append('/opt')  # Lambda layer path
from api.lib import success_response, error_response, ParquetQueryBuilder

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

# Initialize AWS clients
s3_client = boto3.client('s3')


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for network graph endpoint
    GET /v1/lobbying/network-graph?year=2025&include_bills=true&include_members=true
    """
    try:
        # Parse query parameters
        params = event.get('queryStringParameters') or {}
        year = params.get('year', '2025')
        limit = min(int(params.get('limit', '150')), 500)
        include_bills = params.get('include_bills', 'true').lower() == 'true'
        include_members = params.get('include_members', 'false').lower() == 'true'

        # Build network graph from Silver layer
        graph_data = build_comprehensive_network(year, limit, include_bills, include_members)

        return success_response({
            'graph': graph_data,
            'metadata': {
                'year': year,
                'node_count': len(graph_data['nodes']),
                'link_count': len(graph_data['links']),
                'node_types': list(set(n['type'] for n in graph_data['nodes'])),
                'edge_types': list(set(l['link_type'] for l in graph_data['links']))
            }
        })

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return error_response(str(e), 500)


def build_comprehensive_network(year: str, limit: int, include_bills: bool, include_members: bool) -> Dict[str, Any]:
    """
    Build comprehensive network graph with multiple node types and labeled edges.
    """
    nodes = []
    links = []
    node_map = {}

    # Load data
    qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
    
    # 1. Load Silver filings (client → registrant relationships)
    try:
        filings_df = qb.query_parquet(
            table_path=f"silver/lobbying/filings/year={year}",
            limit=2000
        )
        print(f"Loaded {len(filings_df)} filings")
    except Exception as e:
        print(f"Error loading filings: {e}")
        filings_df = pd.DataFrame()

    # 2. Load activity_bills (registrant → bill relationships)
    try:
        bills_df = qb.query_parquet(
            table_path=f"silver/lobbying/activity_bills/year={year}",
            limit=5000
        )
        print(f"Loaded {len(bills_df)} bill references")
    except Exception as e:
        print(f"Error loading bills: {e}")
        bills_df = pd.DataFrame()

    # 3. Load government entities contacted (registrant → member/agency relationships)
    try:
        govt_df = qb.query_parquet(
            table_path=f"silver/lobbying/government_entities/year={year}",
            limit=3000
        )
        print(f"Loaded {len(govt_df)} government entity contacts")
    except Exception as e:
        print(f"Error loading govt entities: {e}")
        govt_df = pd.DataFrame()

    if filings_df.empty:
        return {'nodes': [], 'links': []}

    # Process income to float
    filings_df['income_float'] = pd.to_numeric(filings_df['income'], errors='coerce').fillna(0)
    
    # Aggregate client-registrant relationships
    client_reg = filings_df.groupby(['client_id', 'client_name', 'registrant_id', 'registrant_name']).agg({
        'income_float': 'sum',
        'filing_uuid': 'count'
    }).reset_index()
    client_reg.columns = ['client_id', 'client_name', 'registrant_id', 'registrant_name', 'total_spend', 'filing_count']
    client_reg = client_reg.nlargest(limit, 'total_spend')

    # Build CLIENT and LOBBYIST nodes with "funds" edges
    for _, row in client_reg.iterrows():
        client_id = f"client_{row['client_id']}"
        reg_id = f"reg_{row['registrant_id']}"
        
        # Add client node (🏢)
        if client_id not in node_map:
            node_map[client_id] = {
                'id': client_id,
                'name': str(row['client_name'])[:50] if row['client_name'] else 'Unknown',
                'type': 'client',
                'icon': '🏢',
                'connections': 0,
                'spend': 0
            }
        node_map[client_id]['connections'] += 1
        node_map[client_id]['spend'] += float(row['total_spend'])
        
        # Add lobbyist/registrant node (👔)
        if reg_id not in node_map:
            node_map[reg_id] = {
                'id': reg_id,
                'name': str(row['registrant_name'])[:50] if row['registrant_name'] else 'Unknown',
                'type': 'lobbyist',
                'icon': '👔',
                'connections': 0,
                'spend': 0
            }
        node_map[reg_id]['connections'] += 1
        node_map[reg_id]['spend'] += float(row['total_spend'])
        
        # Add "funds" edge: client → lobbyist
        links.append({
            'source': client_id,
            'target': reg_id,
            'link_type': 'funds',
            'label': 'funds',
            'strength': min(100, int(float(row['total_spend']) / 10000 + row['filing_count'] * 5)),
            'weight': float(row['total_spend']),
            'filing_count': int(row['filing_count'])
        })

    # Add BILL nodes with "lobbies_for" edges
    if include_bills and not bills_df.empty:
        # Join bills to filings to get registrant
        bills_with_reg = bills_df.merge(
            filings_df[['filing_uuid', 'registrant_id', 'registrant_name', 'income_float']],
            on='filing_uuid',
            how='left'
        )
        
        # Get unique bill-registrant pairs with high confidence
        bill_lobby = bills_with_reg[bills_with_reg['confidence'] >= 0.5].groupby(
            ['bill_id_118', 'raw_reference', 'registrant_id']
        ).agg({
            'income_float': 'sum',
            'filing_uuid': 'count'
        }).reset_index()
        
        # Add top bills
        top_bills = bill_lobby.groupby('bill_id_118').agg({
            'income_float': 'sum',
            'filing_uuid': 'sum',
            'raw_reference': 'first'
        }).reset_index().nlargest(min(30, limit // 4), 'income_float')
        
        for _, row in top_bills.iterrows():
            bill_id = f"bill_{row['bill_id_118']}"
            
            if bill_id not in node_map:
                node_map[bill_id] = {
                    'id': bill_id,
                    'name': str(row['raw_reference'])[:40],
                    'type': 'bill',
                    'icon': '📜',
                    'connections': 0,
                    'spend': float(row['income_float'])
                }
        
        # Add "lobbies_for" edges: lobbyist → bill
        for _, row in bill_lobby.iterrows():
            reg_id = f"reg_{row['registrant_id']}"
            bill_id = f"bill_{row['bill_id_118']}"
            
            if reg_id in node_map and bill_id in node_map:
                node_map[bill_id]['connections'] += 1
                links.append({
                    'source': reg_id,
                    'target': bill_id,
                    'link_type': 'lobbies_for',
                    'label': 'lobbies for',
                    'strength': min(80, int(row['income_float'] / 5000 + row['filing_uuid'] * 10)),
                    'weight': float(row['income_float']),
                    'filing_count': int(row['filing_uuid'])
                })

    # Add MEMBER nodes with "contacts" edges (from government entities contacted)
    if include_members and not govt_df.empty:
        # Get entities that look like Congress members
        congress_entities = govt_df[
            govt_df['entity_name'].str.contains('House|Senate|Congress|Rep\.|Sen\.', case=False, na=False)
        ]
        
        if not congress_entities.empty:
            # Join to filings to get registrant
            entities_with_reg = congress_entities.merge(
                filings_df[['filing_uuid', 'registrant_id', 'registrant_name']],
                on='filing_uuid',
                how='left'
            )
            
            # Top contacted entities
            top_entities = entities_with_reg.groupby('entity_name').agg({
                'filing_uuid': 'count',
                'registrant_id': 'nunique'
            }).reset_index().nlargest(min(20, limit // 5), 'filing_uuid')
            
            for _, row in top_entities.iterrows():
                entity_id = f"member_{hash(row['entity_name']) % 100000}"
                
                if entity_id not in node_map:
                    node_map[entity_id] = {
                        'id': entity_id,
                        'name': str(row['entity_name'])[:40],
                        'type': 'member',
                        'icon': '🏛️',
                        'connections': int(row['registrant_id']),
                        'spend': 0
                    }
            
            # Add "contacts" edges: lobbyist → member/entity
            entity_reg = entities_with_reg.groupby(['entity_name', 'registrant_id']).agg({
                'filing_uuid': 'count'
            }).reset_index()
            
            for _, row in entity_reg.iterrows():
                entity_id = f"member_{hash(row['entity_name']) % 100000}"
                reg_id = f"reg_{row['registrant_id']}"
                
                if entity_id in node_map and reg_id in node_map:
                    links.append({
                        'source': reg_id,
                        'target': entity_id,
                        'link_type': 'contacts',
                        'label': 'contacts',
                        'strength': min(60, int(row['filing_uuid'] * 15)),
                        'weight': int(row['filing_uuid']),
                        'filing_count': int(row['filing_uuid'])
                    })

    nodes = list(node_map.values())
    
    # Deduplicate links
    seen_links = set()
    unique_links = []
    for link in links:
        key = (link['source'], link['target'], link['link_type'])
        if key not in seen_links:
            seen_links.add(key)
            unique_links.append(link)
    
    print(f"Built network: {len(nodes)} nodes, {len(unique_links)} links")
    
    return {
        'nodes': nodes,
        'links': unique_links
    }
