"""
Lambda handler: GET /v1/analytics/alpha

Congressional Alpha Engine - Returns trading performance metrics:
- Member-level alpha (individual performance vs benchmark)
- Party-level alpha (D vs R comparison)
- Sector rotation signals

Query Parameters:
- type: 'member' | 'party' | 'sector_rotation' (default: 'member')
- limit: Number of results (default: 20, max: 100)
- sort: 'alpha' | 'volume' | 'trades' (default: 'alpha')
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
    """GET /v1/analytics/alpha - Congressional Alpha metrics."""
    try:
        query_params = event.get('queryStringParameters') or {}
        
        # Parse parameters
        alpha_type = query_params.get('type', 'member')
        if alpha_type not in ['member', 'party', 'sector_rotation']:
            alpha_type = 'member'
        
        try:
            limit = int(query_params.get('limit', 20))
            limit = min(max(1, limit), 100)
        except ValueError:
            limit = 20
        
        sort_field = query_params.get('sort', 'alpha')
        if sort_field not in ['alpha', 'volume', 'trades']:
            sort_field = 'alpha'
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Map sort field to actual column
        sort_mapping = {
            'alpha': 'alpha',
            'volume': 'total_volume',
            'trades': 'total_trades'
        }
        order_by = f"{sort_mapping[sort_field]} DESC"
        
        # Query the appropriate alpha table
        s3_prefix = f'gold/aggregates/agg_congressional_alpha/type={alpha_type}'
        
        df = qb.query_parquet(
            s3_prefix,
            order_by=order_by,
            limit=limit
        )
        
        if df.empty:
            # Return empty response with structure
            return success_response({
                'alpha_type': alpha_type,
                'data': [],
                'count': 0,
                'metadata': {
                    'benchmark': 'S&P 500',
                    'measurement_period': '30 days',
                    'note': 'Alpha calculated as excess return vs benchmark'
                }
            })
        
        # Format response based on type
        records = df.to_dict('records')
        
        # Clean up numeric fields for JSON serialization
        for record in records:
            for key, value in list(record.items()):
                if hasattr(value, 'item'):  # numpy type
                    record[key] = value.item()
                elif value != value:  # NaN check
                    record[key] = None
        
        return success_response({
            'alpha_type': alpha_type,
            'data': records,
            'count': len(records),
            'metadata': {
                'benchmark': 'S&P 500',
                'measurement_period': '30 days',
                'note': 'Alpha calculated as excess return vs benchmark'
            }
        })
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return error_response("Failed to retrieve alpha data", 500, str(e))
