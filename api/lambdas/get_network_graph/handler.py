"""
Lambda handler: GET /v1/analytics/network-graph

Generates member-stock trading network graph data for D3.js visualization.
"""

import os
import logging
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response
)
import pandas as pd
from typing import Dict, Any, List, Optional

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

def handler(event, context):
    """GET /v1/analytics/network-graph - Trading network for visualization."""
    try:
        query_params = event.get('queryStringParameters') or {}
        limit = min(int(query_params.get('limit', 100)), 500)
        view_mode = query_params.get('view_mode', 'aggregate')
        bioguide_id_param = query_params.get('bioguide_id')
        congress_param = query_params.get('congress')
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        if view_mode == 'member_detail' and bioguide_id_param:
            return handle_member_detail_graph(qb, bioguide_id_param, congress_param)

        # Aggregate member-stock trading relationships (Original View)
        filters = {}
        if congress_param:
            filters['congress'] = congress_param

        trades_df = qb.aggregate_parquet(
            'gold/house/financial/facts/fact_ptr_transactions',
            group_by=['bioguide_id', 'first_name', 'last_name', 'party', 'state', 'chamber', 'ticker'],
            aggregations={
                'trade_count': 'COUNT(*)',
                'total_value': 'SUM((COALESCE(amount_low, 0) + COALESCE(amount_high, 0)) / 2.0)',
                'last_trade': 'MAX(transaction_date)',
                'buy_count': "SUM(CASE WHEN transaction_type = 'Purchase' THEN 1 ELSE 0 END)",
                'sell_count': "SUM(CASE WHEN transaction_type = 'Sale' THEN 1 ELSE 0 END)"
            },
            filters=filters,
            order_by='trade_count DESC',
            limit=limit * 10
        )
        
        return build_aggregate_graph_response(trades_df, limit)
    
    except Exception as e:
        logger.error(f"Error generating network graph: {e}", exc_info=True)
        return error_response("Failed to retrieve network graph", 500, str(e))

def handle_member_detail_graph(qb, bioguide_id, congress=None):
    """Generates a graph centered on a specific member with family and bills."""
    # 1. Fetch Transactions (including household lineage)
    filters = {'parent_bioguide_id': bioguide_id}
    if congress:
        filters['congress'] = congress

    trades_df = qb.aggregate_parquet(
        'gold/house/financial/facts/fact_ptr_transactions',
        group_by=['bioguide_id', 'owner_code', 'ticker', 'first_name', 'last_name', 'party'],
        aggregations={
            'trade_count': 'COUNT(*)',
            'total_value': 'SUM((COALESCE(amount_low, 0) + COALESCE(amount_high, 0)) / 2.0)'
        },
        filters=filters
    )

    # 2. Fetch Bills (sponsored by member)
    bill_filters = {'sponsor_bioguide_id': bioguide_id}
    if congress:
        bill_filters['congress'] = congress
    
    try:
        bills_df = qb.query_parquet(
            'gold/congress/dim_bill',
            filters=bill_filters,
            limit=20
        )
    except Exception as e:
        logger.warning(f"Could not fetch bills for graph: {e}")
        bills_df = pd.DataFrame()

    nodes = []
    links = []
    node_map = {} # node_id -> index

    # Add Primary Member Node
    member_name = bioguide_id
    party = "Unknown"
    if not trades_df.empty:
        row = trades_df.iloc[0]
        member_name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
        party = row.get('party', 'Unknown')
    
    primary_node = {
        'id': bioguide_id,
        'name': member_name,
        'group': 'member',
        'is_primary': True,
        'party': party,
        'degree': 0
    }
    nodes.append(primary_node)
    node_map[bioguide_id] = 0

    # Process Trades & Relationships
    for _, row in trades_df.iterrows():
        owner_code = row.get('owner_code')
        ticker = row.get('ticker')
        actual_bioguide = row.get('bioguide_id')
        
        if pd.isna(ticker) or ticker == 'None': continue

        # Determine node for the trade (could be Spouse/Dependent)
        trade_node_id = bioguide_id
        if owner_code and owner_code not in ('SELF', 'None'):
            # Create Family Node
            family_id = f"{bioguide_id}_{owner_code}"
            if family_id not in node_map:
                node_map[family_id] = len(nodes)
                nodes.append({
                    'id': family_id,
                    'name': 'Spouse' if owner_code == 'SP' else 'Dependent',
                    'group': 'person',
                    'subgroup': 'family',
                    'owner_code': owner_code,
                    'degree': 0
                })
                # Link Primary to Family
                links.append({
                    'source': bioguide_id,
                    'target': family_id,
                    'type': 'relationship'
                })
            trade_node_id = family_id
        
        # Add Asset Node
        asset_id = f"stock_{ticker}"
        if asset_id not in node_map:
            node_map[asset_id] = len(nodes)
            nodes.append({
                'id': ticker,
                'name': ticker,
                'group': 'asset',
                'degree': 0
            })
        
        # Link Person to Asset
        links.append({
            'source': trade_node_id,
            'target': ticker,
            'value': float(row.get('total_value', 0)),
            'count': int(row.get('trade_count', 0)),
            'type': 'trade'
        })
        nodes[node_map[trade_node_id]]['degree'] += 1
        nodes[node_map[asset_id]]['degree'] += 1

    # Process Bills
    for _, row in bills_df.iterrows():
        bill_id = row.get('bill_id')
        if not bill_id: continue
        
        if bill_id not in node_map:
            node_map[bill_id] = len(nodes)
            nodes.append({
                'id': bill_id,
                'name': f"{row.get('bill_type', '').upper()} {row.get('bill_number')}",
                'title': row.get('title'),
                'group': 'bill',
                'degree': 1
            })
            links.append({
                'source': bioguide_id,
                'target': bill_id,
                'type': 'sponsorship'
            })
            nodes[node_map[bioguide_id]]['degree'] += 1

    return success_response({
        'nodes': nodes,
        'links': links,
        'member_info': {
            'bioguide_id': bioguide_id,
            'name': member_name
        }
    })

def build_aggregate_graph_response(trades_df, limit):
    nodes = []
    links = []
    member_map = {}  # bioguide_id -> node index
    stock_map = {}   # ticker -> node index
    
    for _, row in trades_df.iterrows():
        bioguide_id = row['bioguide_id']
        ticker = row['ticker']
        
        if pd.isna(bioguide_id) or pd.isna(ticker):
            continue
            
        if bioguide_id not in member_map:
            member_name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip() or bioguide_id
            member_map[bioguide_id] = len(nodes)
            nodes.append({
                'id': bioguide_id,
                'name': member_name,
                'group': 'member',
                'party': row.get('party', 'Unknown'),
                'state': row.get('state', 'N/A'),
                'chamber': row.get('chamber', 'House'),
                'value': 0,
                'transaction_count': 0,
                'degree': 0
            })
        
        stock_id = f"stock_{ticker}"
        if stock_id not in stock_map:
            stock_map[stock_id] = len(nodes)
            nodes.append({
                'id': ticker,
                'name': ticker,
                'group': 'asset',
                'value': 0,
                'transaction_count': 0,
                'degree': 0
            })
        
        member_idx = member_map[bioguide_id]
        nodes[member_idx]['value'] += row.get('total_value', 0) or 0
        nodes[member_idx]['transaction_count'] += row.get('trade_count', 0) or 0
        nodes[member_idx]['degree'] += 1
        
        stock_idx = stock_map[stock_id]
        nodes[stock_idx]['value'] += row.get('total_value', 0) or 0
        nodes[stock_idx]['transaction_count'] += row.get('trade_count', 0) or 0
        nodes[stock_idx]['degree'] += 1
        
        trade_count = row.get('trade_count', 0) or 0
        buy_count = row.get('buy_count', 0) or 0
        sell_count = row.get('sell_count', 0) or 0
        
        link_type = 'mixed'
        if buy_count > 0 and sell_count == 0:
            link_type = 'purchase'
        elif sell_count > 0 and buy_count == 0:
            link_type = 'sale'
        
        links.append({
            'source': bioguide_id,
            'target': ticker,
            'value': row.get('total_value', 0) or 0,
            'count': trade_count,
            'type': link_type
        })
    
    if len(nodes) > limit * 2:
        member_nodes = [n for n in nodes if n['group'] == 'member']
        stock_nodes = [n for n in nodes if n['group'] == 'asset']
        member_nodes.sort(key=lambda x: x['degree'], reverse=True)
        stock_nodes.sort(key=lambda x: x['degree'], reverse=True)
        top_members = set(n['id'] for n in member_nodes[:limit])
        top_stocks = set(n['id'] for n in stock_nodes[:limit])
        nodes = [n for n in nodes if n['id'] in top_members or n['id'] in top_stocks]
        links = [l for l in links if l['source'] in top_members and l['target'] in top_stocks]
    
    # Party Aggregation
    dem_members = [n for n in nodes if n['group'] == 'member' and n.get('party') in ('D', 'Democrat', 'Democratic')]
    rep_members = [n for n in nodes if n['group'] == 'member' and n.get('party') in ('R', 'Republican')]

    aggregated_nodes = []
    if dem_members:
        aggregated_nodes.append({
            'id': 'Democrat',
            'group': 'party_agg',
            'party': 'Democrat',
            'value': sum(n['value'] for n in dem_members),
            'transaction_count': sum(n['transaction_count'] for n in dem_members),
            'member_count': len(dem_members)
        })
    if rep_members:
        aggregated_nodes.append({
            'id': 'Republican',
            'group': 'party_agg',
            'party': 'Republican',
            'value': sum(n['value'] for n in rep_members),
            'transaction_count': sum(n['transaction_count'] for n in rep_members),
            'member_count': len(rep_members)
        })
    
    aggregated_links = []
    party_stock_map = {'Democrat': {}, 'Republican': {}}

    for link in links:
        source_node = next((n for n in nodes if n['id'] == link['source']), None)
        if source_node and source_node.get('group') == 'member':
            party = source_node.get('party')
            if party in ('D', 'Democrat', 'Democratic'): party = 'Democrat'
            elif party in ('R', 'Republican'): party = 'Republican'
            else: continue

            target = link['target']
            if target not in party_stock_map[party]:
                party_stock_map[party][target] = {'value': 0, 'count': 0}
            party_stock_map[party][target]['value'] += link['value']
            party_stock_map[party][target]['count'] += link['count']

    for party, stocks in party_stock_map.items():
        for stock, stats in stocks.items():
            aggregated_links.append({
                'source': party,
                'target': stock,
                'value': stats['value'],
                'count': stats['count'],
                'type': 'mixed',
                'is_aggregated': True
            })
    
    return success_response({
        'nodes': nodes,
        'links': links,
        'aggregated_nodes': aggregated_nodes,
        'aggregated_links': aggregated_links,
        'summary_stats': {
            'total_members': len([n for n in nodes if n['group'] == 'member']),
            'total_assets': len([n for n in nodes if n['group'] == 'asset']),
            'total_links': len(links),
            'total_transactions': sum(l['count'] for l in links)
        }
    })
