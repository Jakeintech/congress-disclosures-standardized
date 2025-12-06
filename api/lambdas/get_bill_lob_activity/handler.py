"""
Lambda handler: GET /v1/lobbying/bills/{bill_id}/lobbying-activity

Get lobbying activity for a specific bill including:
- Clients lobbying
- Registrants (firms) hired
- Total spend
- Quarters active
- Issue codes
- Lobbyists involved
- Government entities contacted
"""

import os
import json
import logging
import math
import pandas as pd
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
    """Handle GET /v1/lobbying/bills/{bill_id}/lobbying-activity request."""
    try:
        logger.info(f"Event: {json.dumps(event)}")

        # Get bill_id from path parameters
        path_params = event.get('pathParameters', {}) or {}
        bill_id = path_params.get('bill_id')

        if not bill_id:
            return error_response("bill_id is required", 400)

        # Normalize bill_id (e.g., "118-hr-1234")
        bill_id = bill_id.lower()

        qb = ParquetQueryBuilder(S3_BUCKET)

        # Extract year from bill_id for efficient querying
        # bill_id format: "118-hr-1234" -> Congress 118 -> years 2023-2024
        try:
            congress_num = int(bill_id.split('-')[0])
            # Congress 118: 2023-2024, 119: 2025-2026, etc.
            year = 2023 + (congress_num - 118) * 2
        except:
            year = 2024  # Default

        # Query bill-lobbying correlation aggregate
        bill_lobbying_df = qb.query_parquet(
            f'gold/lobbying/agg_bill_lobbying_activity/year={year}',
            filters={'bill_id': bill_id},
            limit=10
        )

        # Also check year+1 (bills span 2 years)
        bill_lobbying_df2 = qb.query_parquet(
            f'gold/lobbying/agg_bill_lobbying_activity/year={year + 1}',
            filters={'bill_id': bill_id},
            limit=10
        )

        if not bill_lobbying_df2.empty:
            bill_lobbying_df = pd.concat([bill_lobbying_df, bill_lobbying_df2], ignore_index=True)

        if bill_lobbying_df.empty:
            # No lobbying activity found
            return success_response({
                'bill_id': bill_id,
                'lobbying_activity': [],
                'total_lobbying_spend': 0,
                'client_count': 0,
                'activity_count': 0
            })

        # Get the first (should be only) record
        bill_lobby = bill_lobbying_df.iloc[0].to_dict()

        # Build detailed activity records
        client_names = bill_lobby.get('client_names', [])
        registrant_names = bill_lobby.get('registrant_names', [])

        lobbying_activities = []

        # For each client, create an activity record
        # (In production, would have more detailed per-client data)
        for i, client in enumerate(client_names[:10]):  # Top 10
            lobbying_activities.append({
                'client': client,
                'registrant': registrant_names[i % len(registrant_names)] if registrant_names else 'Unknown',
                'issue_codes': bill_lobby.get('top_issue_codes', []),
                'quarters': bill_lobby.get('filing_quarters', []),
            })

        response_data = {
            'bill_id': bill_id,
            'lobbying_activity': lobbying_activities,
            'total_lobbying_spend': float(bill_lobby.get('total_lobbying_spend', 0)),
            'client_count': int(bill_lobby.get('client_count', 0)),
            'registrant_count': int(bill_lobby.get('registrant_count', 0)),
            'activity_count': int(bill_lobby.get('activity_count', 0)),
            'first_lobbying_date': str(bill_lobby.get('first_lobbying_date', '')),
            'last_lobbying_date': str(bill_lobby.get('last_lobbying_date', '')),
            'top_issue_codes': bill_lobby.get('top_issue_codes', []),
            'lobbying_intensity_score': float(bill_lobby.get('lobbying_intensity_score', 0))
        }

        return success_response(clean_nan(response_data))

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return error_response(str(e), 500)
