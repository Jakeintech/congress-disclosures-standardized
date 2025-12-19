import os
import sys
import logging
import boto3
from pathlib import Path

# Add script directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.consolidate_stock_cache import consolidate_stock_cache

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Lambda wrapper for consolidate_stock_cache.py
    """
    try:
        logger.info("Consolidating Ticker Enrichment Cache")
        
        # Ensure environment variables are set
        bucket = os.environ.get('S3_BUCKET_NAME')
        if not bucket:
            bucket = event.get('s3_bucket', 'congress-disclosures-standardized')
            os.environ['S3_BUCKET_NAME'] = bucket

        consolidate_stock_cache()
        
        return {
            'statusCode': 200,
            'body': {
                'message': 'Successfully consolidated ticker cache'
            }
        }
    except Exception as e:
        logger.error(f"Cache consolidation failed: {str(e)}", exc_info=True)
        raise e
