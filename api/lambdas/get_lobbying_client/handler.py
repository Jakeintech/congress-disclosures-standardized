"""
Lambda handler: GET /v1/lobbying/clients/{client_id}

Get detailed client information including:
- Client details
- Total spend by year
- Top issues lobbied
- Bills lobbied (top 10)
- Registrants hired
- Industry classification
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
    """Handle GET /v1/lobbying/clients/{client_id} request."""
    try:
        logger.info(f"Event: {json.dumps(event)}")

        # Get client_id from path parameters
        path_params = event.get('pathParameters', {}) or {}
        client_id = path_params.get('client_id')

        if not client_id:
            return error_response("client_id is required", 400)

        client_id = int(client_id)

        qb = ParquetQueryBuilder(S3_BUCKET)

        # Get client details from dimension table
        client_df = qb.query_parquet(
            'gold/lobbying/dim_client',
            filters={'client_id': client_id},
            limit=1
        )

        if client_df.empty:
            return error_response("Client not found", 404)

        client_details = client_df.iloc[0].to_dict()

        # Get filings for this client
        filings_df = qb.query_parquet(
            'silver/lobbying/filings',
            filters={'client_id': client_id},
            limit=1000
        )

        # Calculate spend by year
        if not filings_df.empty:
            spend_by_year = filings_df.groupby('filing_year').agg({
                'income': 'sum',
                'expenses': 'sum',
                'filing_uuid': 'count'
            }).reset_index()

            spend_by_year.columns = ['year', 'income', 'expenses', 'filing_count']
            spend_by_year = spend_by_year.to_dict('records')
        else:
            spend_by_year = []

        # Get registrants hired
        if not filings_df.empty:
            registrants = filings_df.groupby(['registrant_id', 'registrant_name']).agg({
                'income': 'sum',
                'filing_uuid': 'count'
            }).reset_index()

            registrants.columns = ['registrant_id', 'registrant_name', 'total_paid', 'filing_count']
            registrants = registrants.sort_values('total_paid', ascending=False)
            registrants_list = registrants.head(20).to_dict('records')
        else:
            registrants_list = []

        # Get bills lobbied from bill_lobbying aggregate
        # Find bills where this client appeared
        # (This requires scanning multiple years - simplified for now)
        bills_lobbied = []

        # Response
        response_data = {
            'client_id': client_id,
            'client_details': clean_nan(client_details),
            'spend_by_year': [clean_nan(s) for s in spend_by_year],
            'registrants_hired': [clean_nan(r) for r in registrants_list],
            'bills_lobbied': bills_lobbied,  # TODO: Implement bill lookup
            'total_filings': len(filings_df) if not filings_df.empty else 0
        }

        return success_response(response_data)

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return error_response(str(e), 500)
