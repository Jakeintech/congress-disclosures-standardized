"""
Lambda handler: GET /v1/congress/bills/{bill_id}

Get single bill details by ID.
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
    """
    GET /v1/congress/bills/{bill_id}
    
    Path parameter:
    - bill_id: Bill ID in format "congress-type-number" (e.g., "118-hr-1")
    
    Returns full bill details.
    """
    try:
        # Extract bill_id from path
        path_params = event.get('pathParameters') or {}
        bill_id = path_params.get('bill_id', '')
        
        if not bill_id:
            return error_response(
                message="Missing bill_id parameter",
                status_code=400
            )
        
        # Parse bill_id: "118-hr-1" -> congress=118, bill_type=hr, bill_number=1
        parts = bill_id.split('-')
        if len(parts) != 3:
            return error_response(
                message="Invalid bill_id format. Expected: congress-type-number (e.g., 118-hr-1)",
                status_code=400
            )
        
        try:
            congress = int(parts[0])
            bill_type = parts[1].lower()
            bill_number = int(parts[2])
        except ValueError:
            return error_response(
                message="Invalid bill_id format",
                status_code=400
            )
        
        logger.info(f"Fetching bill: congress={congress}, type={bill_type}, number={bill_number}")
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Query specific bill
        filters = {
            'congress': congress,
            'bill_type': bill_type,
            'bill_number': bill_number
        }
        
        bills_df = qb.query_parquet(
            'gold/congress/dim_bill',
            filters=filters,
            limit=1
        )
        
        if bills_df.empty:
            return error_response(
                message=f"Bill not found: {bill_id}",
                status_code=404
            )
        
        bill = bills_df.iloc[0].to_dict()
        
        # Add bill_id to response
        bill['bill_id'] = bill_id
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'public, max-age=300'
            },
            'body': json.dumps({'bill': clean_nan(bill)}, default=str)
        }
    
    except Exception as e:
        logger.error(f"Error fetching bill: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve bill",
            status_code=500,
            details=str(e)
        )
