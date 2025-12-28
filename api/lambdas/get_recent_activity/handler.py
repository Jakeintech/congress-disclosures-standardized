"""
Lambda handler: GET /v1/analytics/activity

Returns an aggregated feed of recent activity across trades, bill updates, and lobbying filings.
"""

import os
import logging
import duckdb
import pandas as pd
from datetime import datetime
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response,
    clean_nan_values
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

def handler(event, context):
    try:
        # Connect to DuckDB via ParquetQueryBuilder
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        db = qb.conn
        
        # Define paths
        year = datetime.now().year
        congress = 119
        
        trades_path = f"s3://{S3_BUCKET}/gold/house/financial/facts/fact_ptr_transactions/year={year}/*.parquet"
        bills_path = f"s3://{S3_BUCKET}/gold/congress/dim_bill/congress={congress}/**/*.parquet"
        lobbying_path = f"s3://{S3_BUCKET}/gold/lobbying/facts/fact_lobbying/year={year}/*.parquet"
        
        logger.info(f"Querying activity from S3: {trades_path}, {bills_path}, {lobbying_path}")
        
        activity_items = []
        
        # 1. Fetch Trades
        try:
            trades_df = db.execute(f"""
                SELECT 
                    'trade' as type,
                    COALESCE(member_name, filer_name, full_name, 'Unknown Member') as actor,
                    ticker as subject,
                    transaction_date as date,
                    transaction_type as action,
                    amount as detail,
                    bioguide_id as actor_id
                FROM read_parquet('{trades_path}', union_by_name=True)
                ORDER BY transaction_date DESC
                LIMIT 10
            """).df()
            activity_items.append(trades_df)
        except Exception as e:
            logger.warning(f"Failed to fetch trades activity: {e}")
            
        # 2. Fetch Bills
        try:
            bills_df = db.execute(f"""
                SELECT 
                    'bill' as type,
                    '' as actor,
                    title as subject,
                    update_date as date,
                    'updated' as action,
                    bill_number as detail,
                    bill_id as subject_id
                FROM read_parquet('{bills_path}', union_by_name=True)
                ORDER BY update_date DESC
                LIMIT 10
            """).df()
            activity_items.append(bills_df)
        except Exception as e:
            logger.warning(f"Failed to fetch bills activity: {e}")
            
        # 3. Fetch Lobbying
        try:
            lobbying_df = db.execute(f"""
                SELECT 
                    'lobbying' as type,
                    registrant_name as actor,
                    client_name as subject,
                    filing_date as date,
                    'filed' as action,
                    filing_type as detail,
                    filing_id as subject_id
                FROM read_parquet('{lobbying_path}', union_by_name=True)
                ORDER BY filing_date DESC
                LIMIT 10
            """).df()
            activity_items.append(lobbying_df)
        except Exception as e:
            logger.warning(f"Failed to fetch lobbying activity: {e}")
            
        if not activity_items:
            return success_response({'activity': []})
            
        # Combine and sort
        combined_df = pd.concat(activity_items, ignore_index=True)
        # Convert dates to datetime objects for sorting
        combined_df['date'] = pd.to_datetime(combined_df['date'], errors='coerce')
        combined_df = combined_df.sort_values('date', ascending=False).head(20)
        
        # Format for response
        combined_df['date'] = combined_df['date'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        result = clean_nan_values(combined_df.to_dict(orient='records'))
        
        return success_response({
            'activity': result,
            'count': len(result)
        })
        
    except Exception as e:
        logger.error(f"Error in get_recent_activity: {e}", exc_info=True)
        return error_response(message="Internal error", status_code=500, details=str(e))
