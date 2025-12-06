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

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def handler(event, context):
    """GET /v1/analytics/network-graph - Trading network for visualization."""
    try:
        query_params = event.get('queryStringParameters') or {}
        limit = min(int(query_params.get('limit', 100)), 500)
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Aggregate member-stock trading relationships
        trades_df = qb.aggregate_parquet(
            'gold/house/financial/facts/fact_ptr_transactions',
            group_by=['bioguide_id', 'first_name', 'last_name', 'party', 'state', 'ticker'],
            aggregations={
                'trade_count': 'COUNT(*)',
                'total_value': 'SUM(COALESCE(amount_low, 0))',
                'last_trade': 'MAX(transaction_date)',
                'buy_count': "SUM(CASE WHEN transaction_type = 'Purchase' THEN 1 ELSE 0 END)",
                'sell_count': "SUM(CASE WHEN transaction_type = 'Sale' THEN 1 ELSE 0 END)"
            },
            order_by='trade_count DESC',
            limit=limit * 10  # Get more rows since we'll dedupe
        )
        
        # Build nodes and links for D3.js force graph
        nodes = []
        links = []
        member_map = {}  # bioguide_id -> node index
        stock_map = {}   # ticker -> node index
        
        for _, row in trades_df.iterrows():
            bioguide_id = row['bioguide_id']
            ticker = row['ticker']
            
            # Handle pandas NA/None safely
            if pd.isna(bioguide_id) or pd.isna(ticker):
                continue
                
            party = row['party'] or 'Unknown'
            # Add member node if not exists
            if bioguide_id not in member_map:
                member_name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip() or bioguide_id
                member_map[bioguide_id] = len(nodes)
                nodes.append({
                    'id': bioguide_id,
                    'name': member_name,
                    'group': 'member',
                    'party': row.get('party', 'Unknown'),
                    'state': row.get('state', 'N/A'),
                    'chamber': 'House',  # Default to House (data source)
                    'value': 0,
                    'transaction_count': 0,
                    'degree': 0
                })
            
            # Add stock node if not exists
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
            
            # Update member node stats
            member_idx = member_map[bioguide_id]
            nodes[member_idx]['value'] += row.get('total_value', 0) or 0
            nodes[member_idx]['transaction_count'] += row.get('trade_count', 0) or 0
            nodes[member_idx]['degree'] += 1
            
            # Update stock node stats
            stock_idx = stock_map[stock_id]
            nodes[stock_idx]['value'] += row.get('total_value', 0) or 0
            nodes[stock_idx]['transaction_count'] += row.get('trade_count', 0) or 0
            nodes[stock_idx]['degree'] += 1
            
            # Add link
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
        
        # Limit nodes if too many
        if len(nodes) > limit * 2:
            # Keep top members and stocks by degree
            member_nodes = [n for n in nodes if n['group'] == 'member']
            stock_nodes = [n for n in nodes if n['group'] == 'asset']
            
            member_nodes.sort(key=lambda x: x['degree'], reverse=True)
            stock_nodes.sort(key=lambda x: x['degree'], reverse=True)
            
            top_members = set(n['id'] for n in member_nodes[:limit])
            top_stocks = set(n['id'] for n in stock_nodes[:limit])
            
            nodes = [n for n in nodes if n['id'] in top_members or n['id'] in top_stocks]
            links = [l for l in links if l['source'] in top_members and l['target'] in top_stocks]
        
        # Build aggregated nodes for party view
        dem_members = [n for n in nodes if n['group'] == 'member' and n.get('party') == 'D']
        rep_members = [n for n in nodes if n['group'] == 'member' and n.get('party') == 'R']
        
        aggregated_nodes = []
        if dem_members:
            aggregated_nodes.append({
                'id': 'Democrat',
                'group': 'party_agg',
                'party': 'D',
                'value': sum(n['value'] for n in dem_members),
                'transaction_count': sum(n['transaction_count'] for n in dem_members),
                'member_count': len(dem_members)
            })
        if rep_members:
            aggregated_nodes.append({
                'id': 'Republican',
                'group': 'party_agg',
                'party': 'R',
                'value': sum(n['value'] for n in rep_members),
                'transaction_count': sum(n['transaction_count'] for n in rep_members),
                'member_count': len(rep_members)
            })
        
        # Build aggregated links (party -> stock)
        aggregated_links = []
        party_stock_map = {'D': {}, 'R': {}}
        
        for link in links:
            source_node = next((n for n in nodes if n['id'] == link['source']), None)
            if source_node and source_node.get('party') in party_stock_map:
                party = source_node['party']
                target = link['target']
                if target not in party_stock_map[party]:
                    party_stock_map[party][target] = {'value': 0, 'count': 0}
                party_stock_map[party][target]['value'] += link['value']
                party_stock_map[party][target]['count'] += link['count']
        
        for party, stocks in party_stock_map.items():
            party_name = 'Democrat' if party == 'D' else 'Republican'
            for stock, stats in stocks.items():
                aggregated_links.append({
                    'source': party_name,
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
    
    except Exception as e:
        logger.error(f"Error generating network graph: {e}", exc_info=True)
        return error_response("Failed to retrieve network graph", 500, str(e))
