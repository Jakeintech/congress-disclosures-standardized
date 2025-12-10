
"""Lambda handler: GET /v1/analytics/compliance - Compliance metrics."""
import os
import logging
from api.lib import ParquetQueryBuilder, success_response, error_response

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

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
            
            # Group by member_key
            compliance = filings_df.groupby('member_key').size().reset_index(name='filing_count')
            
            # Map member_key to bioguide_id
            members_df = qb.query_parquet('gold/house/financial/dimensions/dim_members', columns=['member_key', 'bioguide_id'])
            # Create mapping dict: member_key -> bioguide_id
            key_map = dict(zip(members_df['member_key'], members_df['bioguide_id']))
            
            # Add bioguide_id to compliance df
            compliance['bioguide_id'] = compliance['member_key'].map(key_map)
            
            return success_response({'compliance': compliance.head(100).to_dict('records'), 'note': 'Basic metrics'})
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return error_response("Failed to retrieve compliance metrics", 500, str(e))
