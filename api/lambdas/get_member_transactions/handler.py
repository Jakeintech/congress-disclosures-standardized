"""
Lambda handler for GET /v1/members/{name}/transactions

Returns all PTR transactions for a specific congress member.
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
    Handle GET /v1/members/{name}/transactions requests.
    
    Path parameters:
    - name: Member name (case-insensitive, supports partial match)
    
    Query parameters:
    - limit: Max records to return (default: 100)
    - offset: Pagination offset (default: 0)
    - year: Filter by transaction year
    - ticker: Filter by stock ticker
    - transaction_type: Filter by type (Purchase, Sale, Exchange)
    """
    try:
        # Extract path parameters
        member_name = event.get('pathParameters', {}).get('name')
        if not member_name:
            return error_response('Missing member name parameter', 400)
        
        # Normalize name for search
        member_name = member_name.strip().lower()
        
        # Extract query parameters
        query_params = event.get('queryStringParameters') or {}
        limit = int(query_params.get('limit', 100))
        offset = int(query_params.get('offset', 0))
        
        # Build filters
        filters = {}
        if query_params.get('year'):
            filters['filing_year'] = int(query_params['year'])
        if query_params.get('ticker'):
            filters['ticker'] = query_params['ticker'].upper()
        if query_params.get('transaction_type'):
            filters['transaction_type'] = query_params['transaction_type']
        
        # Query fact_ptr_transactions
        table_path = f"s3://{S3_BUCKET}/{GOLD_PREFIX}/fact_ptr_transactions/"
        
        query_builder = ParquetQueryBuilder(
            table_path=table_path,
            s3_bucket=S3_BUCKET
        )
        
        # Over-fetch for name filtering
        result = query_builder.query(
            filters=filters,
            limit=limit * 2,
            offset=offset
        )
        
        # Post-filter by member name
        filtered_data = [
            record for record in result['data']
            if record.get('filer_name') and member_name in record['filer_name'].lower()
        ]
        
        # Trim to limit
        filtered_data = filtered_data[:limit]

        return success_response({
            'data': filtered_data,
            'pagination': {
                'total': len(filtered_data),
                'limit': limit,
                'offset': offset
            }
        })

    except Exception as e:
        logger.error(f"Error querying member transactions: {e}", exc_info=True)
        return error_response('Internal server error', 500, str(e))
