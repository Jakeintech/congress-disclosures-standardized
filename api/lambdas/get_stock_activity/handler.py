S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

"""Lambda handler: GET /v1/stocks/{ticker}/activity - Stock trading activity timeline."""
import os
import logging
from api.lib import ParquetQueryBuilder, success_response, error_response, parse_pagination_params, build_pagination_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """GET /v1/stocks/{ticker}/activity - All trades for stock."""
    try:
        ticker = ((event.get('pathParameters') or {}).get('ticker') or '').upper()
        if not ticker:
            return error_response("ticker is required", 400)
        
        query_params = event.get('queryStringParameters') or {}
        limit, offset = parse_pagination_params(query_params)
        
        filters = {'ticker': ticker}
        if 'start_date' in query_params:
            filters['transaction_date'] = {'gte': query_params['start_date']}
        if 'end_date' in query_params:
            filters.setdefault('transaction_date', {})['lte'] = query_params['end_date']
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        total = qb.count_records('gold/house/financial/facts/fact_ptr_transactions', filters)
        trades_df = qb.query_parquet('gold/house/financial/facts/fact_ptr_transactions', filters=filters, order_by='transaction_date DESC', limit=limit, offset=offset)
        
        response = build_pagination_response(trades_df.to_dict('records'), total, limit, offset, f'/v1/stocks/{ticker}/activity', {k: v for k, v in query_params.items() if k not in ['limit', 'offset']})
        return {'statusCode': 200, 'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}, 'body': str(response).replace("'", '"').replace('True', 'true').replace('False', 'false').replace('None', 'null')}
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return error_response("Failed to retrieve stock activity", 500, str(e))
