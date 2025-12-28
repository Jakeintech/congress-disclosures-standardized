"""
Lambda handler: GET /v1/analytics/conflicts

Conflict of Interest Detection - Returns potential conflicts between
member trading and legislative activity.

Query Parameters:
- severity: 'all' | 'critical' | 'high' | 'medium' | 'low' (default: 'all')
- member_id: Filter by bioguide_id (optional)
- limit: Number of results (default: 50, max: 200)
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
    """GET /v1/analytics/conflicts - Conflict detection results."""
    try:
        query_params = event.get('queryStringParameters') or {}
        
        # Parse parameters
        severity = query_params.get('severity', 'all').lower()
        if severity not in ['all', 'critical', 'high', 'medium', 'low']:
            severity = 'all'
        
        member_id = query_params.get('member_id')
        
        try:
            limit = int(query_params.get('limit', 50))
            limit = min(max(1, limit), 200)
        except ValueError:
            limit = 50
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Build filters
        filters = {}
        if member_id:
            filters['member_bioguide_id'] = member_id
        
        # Query conflicts table
        s3_prefix = f'gold/aggregates/agg_conflict_detection/severity={severity}'
        
        df = qb.query_parquet(
            s3_prefix,
            filters=filters if filters else None,
            order_by='conflict_score DESC',
            limit=limit
        )
        
        if df.empty:
            return success_response({
                'severity_filter': severity,
                'conflicts': [],
                'count': 0,
                'summary': {
                    'critical_count': 0,
                    'high_count': 0,
                    'medium_count': 0,
                    'low_count': 0
                }
            })
        
        # Calculate summary stats
        summary = {
            'critical_count': int((df['severity'] == 'CRITICAL').sum()) if 'severity' in df.columns else 0,
            'high_count': int((df['severity'] == 'HIGH').sum()) if 'severity' in df.columns else 0,
            'medium_count': int((df['severity'] == 'MEDIUM').sum()) if 'severity' in df.columns else 0,
            'low_count': int((df['severity'] == 'LOW').sum()) if 'severity' in df.columns else 0,
        }
        
        # Format response
        records = df.to_dict('records')
        
        # Clean up for JSON
        for record in records:
            for key, value in list(record.items()):
                if hasattr(value, 'item'):
                    record[key] = value.item()
                elif value != value:  # NaN
                    record[key] = None
        
        return success_response({
            'severity_filter': severity,
            'conflicts': records,
            'count': len(records),
            'summary': summary
        })
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return error_response("Failed to retrieve conflict data", 500, str(e))
