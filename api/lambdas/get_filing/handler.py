"""Lambda handler: GET /v1/filings/{doc_id} - Individual filing details."""
import os
import logging
from api.lib import ParquetQueryBuilder, success_response, error_response
import boto3
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

def handler(event, context):
    """GET /v1/filings/{doc_id} - Full filing details with extracted data."""
    try:
        doc_id = (event.get('pathParameters') or {}).get('doc_id')
        if not doc_id:
            return error_response("doc_id is required", 400)
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Get filing metadata
        filing_df = qb.query_parquet(
            'gold/house/financial/facts/fact_filings',
            filters={'doc_id': doc_id},
            limit=1
        )
        
        if len(filing_df) == 0:
            return error_response(f"Filing not found: {doc_id}", 404)
        
        filing_info = filing_df.to_dict('records')[0]
        
        # Try to load Silver structured JSON
        try:
            s3 = boto3.client('s3')
            # Determine path based on filing type and year
            filing_type = filing_info.get('filing_type', 'P')
            year = filing_info.get('filing_year', 2025)
            
            # Normalize filing type for path
            filing_type_path = filing_type.replace('/', '_').replace(' ', '_').lower()
            if len(filing_type_path) == 1:
                filing_type_path = f"type_{filing_type_path}"
            
            key = f"silver/objects/filing_type={filing_type_path}/year={year}/doc_id={doc_id}/extraction.json"
            
            response = s3.get_object(Bucket=S3_BUCKET, Key=key)
            structured_data = json.loads(response['Body'].read())
            filing_info['structured_data'] = structured_data
        except:
            logger.warning(f"Could not load structured data for {doc_id}")
            filing_info['structured_data'] = None
        
        return success_response(filing_info)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return error_response("Failed to retrieve filing", 500, str(e))
