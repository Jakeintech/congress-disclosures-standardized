
"""Lambda handler: GET /v1/analytics/sector-activity - Sector trading breakdown."""
import os
import logging
from api.lib import ParquetQueryBuilder, success_response, error_response

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """GET /v1/analytics/sector-activity - Trading activity by sector."""
    try:
        # Note: This requires sector data in transactions or assets table
        # For now, return placeholder or aggregate available data
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Try to query from agg_sector_activity if it exists
        try:
            sector_df = qb.query_parquet('gold/aggregates/agg_sector_activity',limit=100)
            return success_response({'sectors': sector_df.to_dict('records')})
        except:
            # Fallback: basic aggregation
            return success_response({'sectors': [], 'message': 'Sector data not yet available'})
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return error_response("Failed to retrieve sector activity", 500, str(e))
