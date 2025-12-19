
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
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Query from the new optimized aggregate table
        # Path: gold/house/financial/aggregates/agg_sector_analysis/type=summary/
        try:
            sector_df = qb.query_parquet(
                'gold/house/financial/aggregates/agg_sector_analysis/type=summary',
                limit=100
            )
            
            if sector_df.empty:
                return success_response({'sectors': [], 'message': 'No sector data found'})
                
            return success_response({
                'sectors': sector_df.to_dict('records'),
                'metadata': {
                    'total_sectors': len(sector_df),
                    'last_updated': sector_df['dt_computed'].iloc[0] if 'dt_computed' in sector_df.columns else None
                }
            })
        except Exception as e:
            logger.warning(f"Failed to query aggregate table: {e}")
            return success_response({'sectors': [], 'message': 'Sector analytics currently unavailable'})
            
    except Exception as e:
        logger.error(f"Error retrieving sector activity: {e}", exc_info=True)
        return error_response("Failed to retrieve sector activity", 500, str(e))
