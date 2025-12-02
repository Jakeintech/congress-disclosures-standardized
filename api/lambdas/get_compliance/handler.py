S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

"""Lambda handler: GET /v1/analytics/compliance - Compliance metrics."""
import os
import logging
from api.lib import ParquetQueryBuilder, success_response, error_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """GET /v1/analytics/compliance - Filing compliance statistics."""
    try:
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Try to load compliance metrics if available
        try:
            compliance_df = qb.query_parquet('gold/aggregates/agg_compliance_metrics', limit=500)
            return success_response({'compliance': compliance_df.to_dict('records'), 'count': len(compliance_df)})
        except:
            # Fallback: calculate from filings
            filings_df = qb.query_parquet('gold/house/financial/facts/fact_filings', limit=10000)
            # Basic compliance: count filings per member
            compliance = filings_df.groupby('bioguide_id').size().reset_index(name='filing_count')
            return success_response({'compliance': compliance.head(100).to_dict('records'), 'note': 'Basic metrics'})
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return error_response("Failed to retrieve compliance metrics", 500, str(e))
