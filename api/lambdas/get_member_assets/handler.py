"""
Lambda handler for GET /v1/members/{name}/portfolio

Returns current asset holdings for a member from their latest annual filing.
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

def handler(event, context):
    """
    Handle GET /v1/members/{name}/portfolio requests.
    
    Returns asset holdings from the member's most recent annual disclosure.
    
    Path parameters:
    - name: Member name (case-insensitive, supports partial match)
    
    Query parameters:
    - limit: Max records to return (default: 100)
    - offset: Pagination offset (default: 0)
    - asset_type: Filter by asset type
    """
    try:
        # Extract path parameters
        member_name = event.get('pathParameters', {}).get('name')
        if not member_name:
            return {
                'statusCode': 400,
                'body': json.dumps({'success': False, 'error': 'Missing member name parameter'})
            }
        
        # Normalize name
        member_name = member_name.strip().lower()
        
        # Extract query parameters
        query_params = event.get('queryStringParameters') or {}
        limit = int(query_params.get('limit', 100))
        offset = int(query_params.get('offset', 0))
        
        # Step 1: Find member's latest Type A/B/C filing
        filings_table = f"s3://{S3_BUCKET}/{GOLD_PREFIX}/fact_filings/"
        filings_qb = ParquetQueryBuilder(
            table_path=filings_table,
            s3_bucket=S3_BUCKET
        )
        
        # Get all filings, filter by name, find latest annual
        filings_result = filings_qb.query(
            filters={},
            limit=1000,
            offset=0
        )
        
        # Filter for this member's annual filings
        member_filings = [
            f for f in filings_result['data']
            if f.get('filer_name') and member_name in f['filer_name'].lower()
            and f.get('filing_type') in ['type_a', 'type_b', 'type_c']
        ]
        
        if not member_filings:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'success': False,
                    'error': 'No annual filings found for member'
                })
            }
        
        # Sort by year descending to get latest
        member_filings.sort(key=lambda x: x.get('filing_year', 0), reverse=True)
        latest_filing = member_filings[0]
        latest_doc_id = latest_filing['doc_id']
        
        # Step 2: Get asset holdings from that filing
        filters = {'doc_id': latest_doc_id}
        if query_params.get('asset_type'):
            filters['asset_type'] = query_params['asset_type']
        
        assets_table = f"s3://{S3_BUCKET}/{GOLD_PREFIX}/fact_asset_holdings/"
        assets_qb = ParquetQueryBuilder(
            table_path=assets_table,
            s3_bucket=S3_BUCKET
        )
        
        assets_result = assets_qb.query(
            filters=filters,
            limit=limit,
            offset=offset
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'member': latest_filing.get('filer_name'),
                'filing_doc_id': latest_doc_id,
                'filing_year': latest_filing.get('filing_year'),
                'data': assets_result['data'],
                'pagination': assets_result['pagination']
            })
        }
        
    except Exception as e:
        logger.error(f"Error querying member portfolio: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': f'Internal server error: {str(e)}'
            })
        }
