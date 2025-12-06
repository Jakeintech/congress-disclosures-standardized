"""
Lambda handler: GET /v1/lobbying/filings

Query lobbying filings with filters:
- client_id, registrant_id, issue_code, filing_year, min_income
- Sort by income or dt_posted
- Pagination support
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
    """Handle GET /v1/lobbying/filings request."""
    try:
        logger.info(f"Event: {json.dumps(event)}")

        # Parse query parameters
        params = event.get('queryStringParameters', {}) or {}

        client_id = params.get('client_id')
        registrant_id = params.get('registrant_id')
        issue_code = params.get('issue_code')
        filing_year = params.get('filing_year')
        min_income = params.get('min_income')

        sort_by = params.get('sort_by', 'income')  # income or dt_posted
        limit = int(params.get('limit', 100))
        offset = int(params.get('offset', 0))

        # Validate parameters
        if limit > 500:
            return error_response("Limit cannot exceed 500", 400)

        # Build query
        qb = ParquetQueryBuilder(S3_BUCKET)

        # Query Silver filings table
        filters = {}
        if client_id:
            filters['client_id'] = client_id
        if registrant_id:
            filters['registrant_id'] = registrant_id
        if filing_year:
            filters['filing_year'] = int(filing_year)

        # Get base filings
        base_path = f'silver/lobbying/filings/year={filing_year}' if filing_year else 'silver/lobbying/filings'

        df = qb.query_parquet(
            base_path,
            filters=filters if filters else None,
            limit=limit + offset + 100  # Get extra for filtering
        )

        if df.empty:
            return success_response({
                'filings': [],
                'total': 0,
                'limit': limit,
                'offset': offset
            })

        # Apply additional filters
        if min_income:
            df = df[df['income'] >= float(min_income)]

        if issue_code:
            # Need to join with activities to filter by issue code
            activities_df = qb.query_parquet(
                f'silver/lobbying/activities/year={filing_year}',
                filters=None,
                limit=10000
            )

            if not activities_df.empty:
                # Get filing_uuids that have this issue code
                matching_activities = activities_df[
                    activities_df['general_issue_code'] == issue_code
                ]
                matching_filing_uuids = matching_activities['filing_uuid'].unique()

                df = df[df['filing_uuid'].isin(matching_filing_uuids)]

        # Sort
        if sort_by == 'income':
            df = df.sort_values('income', ascending=False)
        elif sort_by == 'dt_posted':
            df = df.sort_values('dt_posted', ascending=False)

        # Get total before pagination
        total = len(df)

        # Apply pagination
        df = df.iloc[offset:offset + limit]

        # Convert to dict
        filings = df.to_dict('records')

        # Clean NaN values
        filings = [clean_nan(f) for f in filings]

        return success_response({
            'filings': filings,
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': offset + limit < total
        })

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return error_response(str(e), 500)
