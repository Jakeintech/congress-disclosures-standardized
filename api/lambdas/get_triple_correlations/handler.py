"""
Lambda handler: GET /v1/correlations/triple (STAR API)

Get Trade-Bill-Lobbying triple correlations with filters:
- member_bioguide, bill_id, ticker, min_score, year
- Sort by correlation_score (default)

Returns full context for each correlation including explanation text.
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


def lambda_handler(event, context):
    """Handle GET /v1/correlations/triple request."""
    try:
        logger.info(f"Event: {json.dumps(event)}")

        # Parse query parameters
        params = event.get('queryStringParameters', {}) or {}

        member_bioguide = params.get('member_bioguide')
        bill_id = params.get('bill_id')
        ticker = params.get('ticker')
        min_score = int(params.get('min_score', 50))
        year = int(params.get('year', 2024))

        sort_by = params.get('sort_by', 'correlation_score')
        limit = int(params.get('limit', 50))
        offset = int(params.get('offset', 0))

        # Validate
        if limit > 200:
            return error_response("Limit cannot exceed 200", 400)

        qb = ParquetQueryBuilder(S3_BUCKET)

        # Query triple correlation aggregate
        filters = {}
        if member_bioguide:
            filters['member_bioguide_id'] = member_bioguide
        if bill_id:
            filters['bill_id'] = bill_id.lower()
        if ticker:
            filters['ticker'] = ticker.upper()

        # Read from Gold aggregate
        df = qb.query_parquet(
            f'gold/lobbying/agg_trade_bill_lobbying_correlation/year={year}',
            filters=filters if filters else None,
            limit=limit + offset + 100
        )

        if df.empty:
            return success_response({
                'correlations': [],
                'total': 0,
                'limit': limit,
                'offset': offset
            })

        # Filter by minimum score
        df = df[df['correlation_score'] >= min_score]

        # Sort
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
        if correlations:
            summary_stats = {
                'total_correlations': total,
                'perfect_scores': sum(1 for c in correlations if c['correlation_score'] == 100),
                'high_scores': sum(1 for c in correlations if c['correlation_score'] >= 80),
                'average_score': sum(c['correlation_score'] for c in correlations) / len(correlations),
                'unique_members': len(set(c['member_bioguide_id'] for c in correlations)),
                'unique_bills': len(set(c['bill_id'] for c in correlations)),
                'unique_tickers': len(set(c['ticker'] for c in correlations))
            }
        else:
            summary_stats = {
                'total_correlations': 0,
                'perfect_scores': 0,
                'high_scores': 0,
                'average_score': 0,
                'unique_members': 0,
                'unique_bills': 0,
                'unique_tickers': 0
            }

        return success_response({
            'correlations': correlations,
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': offset + limit < total,
            'summary': clean_nan(summary_stats),
            'filters': {
                'member_bioguide': member_bioguide,
                'bill_id': bill_id,
                'ticker': ticker,
                'min_score': min_score,
                'year': year
            }
        })

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return error_response(str(e), 500)
