"""
Lambda handler: GET /v1/analytics/insights

Pattern Recognition & Insights - Returns trending patterns and insights:
- Trading timing heatmaps
- Sector analysis
- Party preferences
- Unusual patterns

Query Parameters:
- type: 'timing' | 'sector' | 'trending' (default: 'trending')
- period: 'week' | 'month' | 'year' (default: 'month')
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
    """GET /v1/analytics/insights - Pattern recognition insights."""
    try:
        query_params = event.get('queryStringParameters') or {}
        
        insight_type = query_params.get('type', 'trending')
        if insight_type not in ['timing', 'sector', 'trending']:
            insight_type = 'trending'
        
        period = query_params.get('period', 'month')
        if period not in ['week', 'month', 'year']:
            period = 'month'
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        result = {}
        
        if insight_type == 'timing':
            # Get timing heatmap data
            day_heatmap = qb.query_parquet(
                'gold/aggregates/agg_timing_heatmap/type=day_of_week',
                limit=10
            )
            
            month_heatmap = qb.query_parquet(
                'gold/aggregates/agg_timing_heatmap/type=month_of_year',
                limit=15
            )
            
            result = {
                'insight_type': 'timing',
                'day_of_week': day_heatmap.to_dict('records') if not day_heatmap.empty else [],
                'month_of_year': month_heatmap.to_dict('records') if not month_heatmap.empty else [],
                'metadata': {
                    'description': 'Trading activity patterns by time period',
                    'deviation_note': 'Positive deviation = above expected activity'
                }
            }
        
        elif insight_type == 'sector':
            # Get sector analysis
            summary = qb.query_parquet(
                'gold/aggregates/agg_sector_analysis/type=summary',
                order_by='total_volume DESC',
                limit=15
            )
            
            party = qb.query_parquet(
                'gold/aggregates/agg_sector_analysis/type=party',
                limit=15
            )
            
            result = {
                'insight_type': 'sector',
                'sector_summary': summary.to_dict('records') if not summary.empty else [],
                'party_preferences': party.to_dict('records') if not party.empty else [],
                'metadata': {
                    'description': 'Sector-level trading analysis',
                    'flow_signal_note': 'STRONG_BUY/SELL indicates significant imbalance'
                }
            }
        
        else:  # trending
            # Get trending stocks and rotation signals
            rotation = qb.query_parquet(
                'gold/aggregates/agg_congressional_alpha/type=sector_rotation',
                order_by='net_flow DESC',
                limit=20
            )
            
            # Get top stocks by sector
            top_stocks = qb.query_parquet(
                'gold/aggregates/agg_sector_analysis/type=top_stocks',
                order_by='total_volume DESC',
                limit=30
            )
            
            result = {
                'insight_type': 'trending',
                'sector_rotation': rotation.to_dict('records') if not rotation.empty else [],
                'top_stocks': top_stocks.to_dict('records') if not top_stocks.empty else [],
                'metadata': {
                    'description': 'Current trading trends and momentum',
                    'period': period
                }
            }
        
        # Clean up all numeric values
        def clean_records(records):
            for record in records:
                for key, value in list(record.items()):
                    if hasattr(value, 'item'):
                        record[key] = value.item()
                    elif value != value:  # NaN
                        record[key] = None
            return records
        
        for key, value in result.items():
            if isinstance(value, list):
                result[key] = clean_records(value)
        
        return success_response(result)
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return error_response("Failed to retrieve insights", 500, str(e))
