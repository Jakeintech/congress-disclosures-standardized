"""
Lambda handler: GET /v1/congress/members/{bioguide_id}

Get single Congress member details.
"""

import os
import json
import logging
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def handler(event, context):
    """
    GET /v1/congress/members/{bioguide_id}
    
    Path parameter:
    - bioguide_id: Member's bioguide ID (e.g., "P000197")
    
    Returns full member details with legislative stats.
    """
    try:
        path_params = event.get('pathParameters') or {}
        bioguide_id = path_params.get('bioguide_id', '')
        
        if not bioguide_id:
            return error_response(
                message="Missing bioguide_id parameter",
                status_code=400
            )
        
        logger.info(f"Fetching Congress member: {bioguide_id}")
        
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Get member from dim_members (House financial disclosures)
        members_df = qb.query_parquet(
            'gold/house/financial/dimensions/dim_members',
            filters={'bioguide_id': bioguide_id.upper()},
            limit=1
        )
        
        if members_df.empty:
            return error_response(
                message=f"Member not found: {bioguide_id}",
                status_code=404
            )
        
        member = members_df.iloc[0].to_dict()
        
        # Try to get legislative stats
        try:
            stats_df = qb.query_parquet(
                'gold/congress/aggregates/member_legislative_stats',
                filters={'bioguide_id': bioguide_id.upper()},
                limit=1
            )
            if not stats_df.empty:
                stats = stats_df.iloc[0].to_dict()
                member['bills_sponsored'] = stats.get('bills_sponsored', 0)
                member['bills_cosponsored'] = stats.get('bills_cosponsored', 0)
                member['fd_transaction_count'] = stats.get('fd_transaction_count', 0)
        except Exception as e:
            logger.warning(f"Could not fetch legislative stats: {e}")
        
        return success_response({'member': member}, metadata={'cache_seconds': 300})
    
    except Exception as e:
        logger.error(f"Error fetching Congress member: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve Congress member",
            status_code=500,
            details=str(e)
        )
