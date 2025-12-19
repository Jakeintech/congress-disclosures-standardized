import os
import sys
import logging
import boto3
from pathlib import Path

# Add script directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.consolidate_silver_tabular import consolidate_year_to_parquet

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Lambda wrapper for consolidate_silver_tabular.py
    Expects 'year' in event. If not present, processes current year.
    """
    try:
        year = event.get('year')
        if not year:
            from datetime import datetime
            year = datetime.now().year
            
        logger.info(f"Consolidating Silver Tabular for year {year}")
        
        # We need to ensure environment variables are set for the script
        bucket = os.environ.get('S3_BUCKET_NAME')
        if not bucket:
            # Fallback for orchestration
            bucket = event.get('s3_bucket', 'congress-disclosures-standardized')
            os.environ['S3_BUCKET_NAME'] = bucket

        consolidate_year_to_parquet(year, bucket)
        
        return {
            'statusCode': 200,
            'body': {
                'message': f'Successfully consolidated tabular data for {year}',
                'year': year
            }
        }
    except Exception as e:
        logger.error(f"Consolidation failed: {str(e)}", exc_info=True)
        raise e
