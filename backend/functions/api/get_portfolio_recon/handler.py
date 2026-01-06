"""
Lambda handler: GET /v1/analytics/portfolio

Portfolio Reconstruction - Returns estimated portfolio holdings
reconstructed from cumulative trading activity.

Query Parameters:
- member_id: Get specific member's portfolio (optional)
- limit: Number of portfolios (default: 20, max: 100)
- include_holdings: Include individual holdings (default: false)
"""

import os
import json
import logging
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def handler(event, context):
    """GET /v1/analytics/portfolio - Portfolio reconstruction."""
    try:
        query_params = event.get('queryStringParameters') or {}
        
        member_id = query_params.get('member_id')
        include_holdings = query_params.get('include_holdings', 'false').lower() == 'true'
        
        try:
            limit = int(query_params.get('limit', 20))
            limit = min(max(1, limit), 100)
        except ValueError:
            limit = 20
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Query portfolio reconstruction table
        filters = {}
        if member_id:
            filters['member_key'] = member_id
        
        df = qb.query_parquet(
            'gold/aggregates/agg_portfolio_reconstruction',
            filters=filters if filters else None,
            order_by='estimated_portfolio_value DESC',
            limit=limit
        )
        
        if df.empty:
            return success_response({
                'portfolios': [],
                'count': 0,
                'metadata': {
                    'description': 'Reconstructed portfolios from cumulative trading',
                    'confidence_note': 'Confidence score (0-100) indicates estimation reliability'
                }
            })
        
        # Format portfolio records
        portfolios = df.to_dict('records')
        
        # Clean up for JSON serialization
        for portfolio in portfolios:
            # Handle top_holdings which may be stored as string
            if 'top_holdings' in portfolio:
                holdings = portfolio['top_holdings']
                if isinstance(holdings, str):
                    try:
                        portfolio['top_holdings'] = json.loads(holdings.replace("'", '"'))
                    except:
                        portfolio['top_holdings'] = []
            
            # Handle sector_allocation
            if 'sector_allocation' in portfolio:
                allocation = portfolio['sector_allocation']
                if isinstance(allocation, str):
                    try:
                        portfolio['sector_allocation'] = json.loads(allocation.replace("'", '"'))
                    except:
                        portfolio['sector_allocation'] = {}
            
            # Clean numeric values
            for key, value in list(portfolio.items()):
                if hasattr(value, 'item'):
                    portfolio[key] = value.item()
                elif value != value:  # NaN
                    portfolio[key] = None
        
        response = {
            'portfolios': portfolios,
            'count': len(portfolios),
            'metadata': {
                'description': 'Reconstructed portfolios from cumulative trading',
                'confidence_note': 'Confidence score (0-100) indicates estimation reliability'
            }
        }
        
        # Optionally include detailed holdings
        if include_holdings and member_id:
            holdings_df = qb.query_parquet(
                'gold/aggregates/agg_portfolio_holdings',
                filters={'member_key': member_id},
                order_by='estimated_value DESC',
                limit=50
            )
            
            if not holdings_df.empty:
                holdings = holdings_df.to_dict('records')
                for h in holdings:
                    for key, value in list(h.items()):
                        if hasattr(value, 'item'):
                            h[key] = value.item()
                        elif value != value:
                            h[key] = None
                response['holdings'] = holdings
        
        return success_response(response)
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return error_response("Failed to retrieve portfolio data", 500, str(e))
