"""
Lambda handler for GET /v1/filings/{doc_id}/positions

Returns positions (Schedule E) for a specific filing.
"""
import os
import json
import logging
from lib.query_builder import ParquetQueryBuilder
from api.lib import success_response, error_response

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Constants
S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
GOLD_PREFIX = 'gold/house/financial/facts'

def handler(event, context):
    """
    Handle GET /v1/filings/{doc_id}/positions requests.
    
    Path parameters:
    - doc_id: Filing document ID
    
    Query parameters:
    - limit: Max records to return (default: 100)
    - offset: Pagination offset (default: 0)
    """
    try:
        # Extract path parameters
        doc_id = event.get('pathParameters', {}).get('doc_id')
        if not doc_id:
            return error_response('Missing doc_id parameter', 400)
        
        # Extract query parameters
        query_params = event.get('queryStringParameters') or {}
        limit = int(query_params.get('limit', 100))
        offset = int(query_params.get('offset', 0))
        
        # Build filters
        filters = {'doc_id': doc_id}
        
        # Query fact_positions
        table_path = f"s3://{S3_BUCKET}/{GOLD_PREFIX}/fact_positions/"
        
        query_builder = ParquetQueryBuilder(
            table_path=table_path,
            s3_bucket=S3_BUCKET
        )
        
        result = query_builder.query(
            filters=filters,
            limit=limit,
            offset=offset
        )

        return success_response({
            'data': result['data'],
            'pagination': result['pagination']
        })

    except Exception as e:
        logger.error(f"Error querying positions: {e}", exc_info=True)
        return error_response('Internal server error', 500, str(e))
