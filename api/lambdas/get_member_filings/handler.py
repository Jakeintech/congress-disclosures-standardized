"""
Lambda handler for GET /v1/members/{name}/filings

Returns all filings for a specific congress member across all filing types.
Supports flexible name matching (case-insensitive, partial match).
"""
import os
import json
import logging
from lib.query_builder import ParquetQueryBuilder

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Constants
S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
GOLD_PREFIX = 'gold/house/financial/facts'

def lambda_handler(event, context):
    """
    Handle GET /v1/members/{name}/filings requests.
    
    Path parameters:
    - name: Member name (case-insensitive, supports partial match)
    
    Query parameters:
    - limit: Max records to return (default: 100)
    - offset: Pagination offset (default: 0)
    - filing_type: Filter by filing type (type_p, type_a, etc.)
    - year: Filter by filing year
    """
    try:
        # Extract path parameters
        member_name = event.get('pathParameters', {}).get('name')
        if not member_name:
            return {
                'statusCode': 400,
                'body': json.dumps({'success': False, 'error': 'Missing member name parameter'})
            }
        
        # Normalize name for search (case-insensitive)
        member_name = member_name.strip().lower()
        
        # Extract query parameters
        query_params = event.get('queryStringParameters') or {}
        limit = int(query_params.get('limit', 100))
        offset = int(query_params.get('offset', 0))
        
        # Build filters
        # Note: We'll use LIKE match on filer_name
        filters = {}
        if query_params.get('filing_type'):
            filters['filing_type'] = query_params['filing_type']
        if query_params.get('year'):
            filters['filing_year'] = int(query_params['year'])
        
        # Query fact_filings with name filter
        table_path = f"s3://{S3_BUCKET}/{GOLD_PREFIX}/fact_filings/"
        
        query_builder = ParquetQueryBuilder(
            table_path=table_path,
            s3_bucket=S3_BUCKET
        )
        
        # For name matching, we'll do post-filtering since DuckDB LIKE requires special handling
        result = query_builder.query(
            filters=filters,
            limit=limit * 2,  # Over-fetch to allow for name filtering
            offset=offset
        )
        
        # Post-filter by member name (case-insensitive partial match)
        filtered_data = [
            record for record in result['data']
            if record.get('filer_name') and member_name in record['filer_name'].lower()
        ]
        
        # Trim to requested limit
        filtered_data = filtered_data[:limit]
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'data': filtered_data,
                'pagination': {
                    'total': len(filtered_data),
                    'limit': limit,
                    'offset': offset
                }
            })
        }
        
    except Exception as e:
        logger.error(f"Error querying member filings: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': f'Internal server error: {str(e)}'
            })
        }
