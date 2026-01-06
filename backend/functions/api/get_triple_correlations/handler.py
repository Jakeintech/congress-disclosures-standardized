"""
API Lambda: Get Bill-Lobbying Correlations

Returns bill-lobbying correlation data showing which bills are being lobbied
and by whom. Adapted to use agg_bill_lobbying_activity data.
"""

import os
import logging
import json
from decimal import Decimal
from typing import Any, Dict

import sys
sys.path.append('/opt')  # Lambda layer path
from api.lib import success_response, error_response, ParquetQueryBuilder

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def clean_nan(obj: Any) -> Any:
    """Clean NaN/None values from response."""
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan(i) for i in obj]
    elif isinstance(obj, float) and (obj != obj):  # NaN check
        return None
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for bill-lobbying correlations.
    GET /v1/correlations/triple?year=2025&limit=20&min_score=50
    """
    try:
        params = event.get('queryStringParameters') or {}
        
        # Parse query parameters
        year = params.get('year', '2025')
        bill_id = params.get('bill_id') or params.get('bill')
        min_score = int(params.get('min_score', '0'))
        limit = min(int(params.get('limit', '50')), 200)
        offset = int(params.get('offset', '0'))
        
        logger.info(f"Querying correlations: year={year}, bill={bill_id}, min_score={min_score}")

        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)

        # Query bill-lobbying aggregate
        filters = {}
        if bill_id:
            filters['bill_id'] = bill_id.lower()

        try:
            df = qb.query_parquet(
                table_path=f'gold/lobbying/agg_bill_lobbying_activity/year={year}',
                filters=filters if filters else None,
                limit=limit + offset + 100
            )
        except Exception as e:
            if "No files found" in str(e) or "Hive partition" in str(e):
                logger.warning(f"No files found for correlations: {e}")
                return success_response({
                    'correlations': [],
                    'total': 0,
                    'limit': limit,
                    'offset': offset,
                    'message': 'No data found (empty S3)'
                })
            raise e

        if df.empty:
            return success_response({
                'correlations': [],
                'total': 0,
                'limit': limit,
                'offset': offset,
                'message': 'No bill-lobbying correlations found for the specified filters.'
            })

        # Rename columns to match expected schema
        df = df.rename(columns={
            'lobbying_intensity_score': 'correlation_score',
            'total_lobbying_spend': 'lobbying_amount'
        })
        
        # Add missing fields with defaults
        if 'correlation_score' not in df.columns:
            df['correlation_score'] = 50  # Default score
        
        # Filter by minimum score
        df = df[df['correlation_score'] >= min_score]

        # Sort by score
        df = df.sort_values('correlation_score', ascending=False)

        # Get total before pagination
        total = len(df)

        # Apply pagination
        df = df.iloc[offset:offset + limit]

        # Convert to dict
        correlations = df.to_dict('records')

        # Clean NaN values
        correlations = [clean_nan(c) for c in correlations]

        # Calculate summary statistics
        summary_stats = {
            'total_correlations': total,
            'high_scores': sum(1 for c in correlations if c.get('correlation_score', 0) >= 80),
            'total_lobbying_spend': sum(c.get('lobbying_amount', 0) for c in correlations),
            'unique_bills': len(set(c.get('bill_id', '') for c in correlations)),
        }

        return success_response({
            'correlations': correlations,
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': offset + limit < total,
            'summary': clean_nan(summary_stats),
            'filters': {
                'bill_id': bill_id,
                'min_score': min_score,
                'year': year
            }
        })

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return error_response(str(e), 500)
