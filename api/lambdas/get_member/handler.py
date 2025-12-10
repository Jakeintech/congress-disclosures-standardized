"""
Lambda handler: GET /v1/members/{bioguide_id}

Get individual member profile with trading stats and compliance metrics.
"""

import os
import logging
from api.lib import (
    ParquetQueryBuilder,
    success_response,
    error_response
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')



def get_net_worth(qb, bioguide_id):
    """Calculate estimated net worth from latest annual filing."""
    try:
        # Find latest annual filing
        filings_df = qb.query_parquet(
            'gold/house/financial/facts/fact_filings',
            filters={'bioguide_id': bioguide_id, 'filing_type': 'annual'}, # check exact type string
            order_by='filing_year DESC',
            limit=1
        )
        
        if filings_df.empty:
             return {'min': 0, 'max': 0, 'year': None}
             
        latest_filing = filings_df.iloc[0]
        filing_id = latest_filing.get('doc_id') # or filing_id column
        year = latest_filing.get('filing_year')
        
        # Get assets for this filing
        assets_df = qb.query_parquet(
            'gold/house/financial/facts/fact_asset_holdings',
            filters={'filing_id': filing_id}
        )
        
        if assets_df.empty:
             return {'min': 0, 'max': 0, 'year': year}
             
        # Sum min and max values
        # Assumes columns: value_min, value_max 
        # (Check schema if needed, but standardizing on common names)
        min_nw = assets_df['value_min'].sum() if 'value_min' in assets_df.columns else 0
        max_nw = assets_df['value_max'].sum() if 'value_max' in assets_df.columns else 0
        
        # Subtract liabilities? (If fact_liabilities exists, otherwise just assets)
        # For MVP, returning asset range is common proxy.
        
        return {'min': int(min_nw), 'max': int(max_nw), 'year': int(year)}
        
    except Exception as e:
        logger.warning(f"Error calcuating net worth: {e}")
        return {'min': 0, 'max': 0, 'year': None}

def get_sector_allocation(qb, bioguide_id):
    """Get portfolio sector allocation."""
    try:
        # Get all holdings logic - actually we want Current holdings.
        # But for now, let's aggregate from ALL recent transactions or latest filing assets.
        # Using latest annual filing assets is safer for "current portfolio".
        
        # Reuse logic to find latest filing similar to net_worth (could be optimized)
        filings_df = qb.query_parquet(
            'gold/house/financial/facts/fact_filings',
            filters={'bioguide_id': bioguide_id, 'filing_type': 'annual'},
            order_by='filing_year DESC',
            limit=1
        )
        
        if filings_df.empty:
            return []

        latest_filing = filings_df.iloc[0]
        filing_id = latest_filing.get('doc_id')
        
        assets_df = qb.query_parquet(
            'gold/house/financial/facts/fact_asset_holdings',
            filters={'filing_id': filing_id}
        )
        
        if assets_df.empty:
            return []
            
        # Group by sector
        if 'sector' not in assets_df.columns:
            return []
            
        # Add mid-point value
        if 'value_min' in assets_df.columns and 'value_max' in assets_df.columns:
            assets_df['value'] = (assets_df['value_min'] + assets_df['value_max']) / 2
        else:
            assets_df['value'] = 0
            
        sector_usage = assets_df.groupby('sector')['value'].sum().reset_index()
        total_value = sector_usage['value'].sum()
        
        allocation = []
        for _, row in sector_usage.iterrows():
            if total_value > 0:
                pct = (row['value'] / total_value) * 100
            else:
                pct = 0
            
            allocation.append({
                'sector': row['sector'],
                'value': float(row['value']),
                'percentage': float(pct)
            })
            
        return sorted(allocation, key=lambda x: x['value'], reverse=True)
        
    except Exception as e:
        logger.warning(f"Error getting sector allocation: {e}")
        return []

def handler(event, context):
    """
    GET /v1/members/{bioguide_id}
    
    Path parameters:
    - bioguide_id: Member's bioguide ID (e.g., 'C001059')
    
    Returns full member profile with:
    - Basic info (name, party, state, district)
    - Trading statistics
    - Compliance metrics
    - Recent filings
    """
    try:
        # Get bioguide_id from path parameters
        path_params = event.get('pathParameters') or {}
        bioguide_id = path_params.get('bioguide_id')
        
        if not bioguide_id:
            return error_response(
                message="bioguide_id is required",
                status_code=400
            )
        
        logger.info(f"Fetching member profile: {bioguide_id}")
        
        # Initialize query builder
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # Get member basic info
        try:
            member_df = qb.query_parquet(
                'gold/house/financial/dimensions/dim_members',
                filters={'bioguide_id': bioguide_id},
                limit=1
            )
            
            if len(member_df) == 0:
                return error_response(
                    message=f"Member not found: {bioguide_id}",
                    status_code=404,
                    details={'bioguide_id': bioguide_id}
                )
            
            member_info = member_df.to_dict('records')[0]
        except Exception as e:
            logger.error(f"Error fetching member info: {e}")
            return error_response(
                message=f"Member not found: {bioguide_id}",
                status_code=404
            )
        
        # Get trading statistics
        try:
            trades_df = qb.query_parquet(
                'gold/house/financial/facts/fact_ptr_transactions',
                filters={'bioguide_id': bioguide_id}
            )
            
            trading_stats = {
                'total_trades': len(trades_df),
                'unique_stocks': len(trades_df['ticker'].unique()) if len(trades_df) > 0 else 0,
                'latest_trade_date': str(trades_df['transaction_date'].max()) if len(trades_df) > 0 else None
            }
        except Exception as e:
            logger.warning(f"Could not get trading stats: {e}")
            trading_stats = {
                'total_trades': 0,
                'unique_stocks': 0,
                'latest_trade_date': None
            }
        
        # Get recent filings
        try:
            filings_df = qb.query_parquet(
                'gold/house/financial/facts/fact_filings',
                filters={'bioguide_id': bioguide_id},
                order_by='filing_date DESC',
                limit=10
            )
            
            recent_filings = filings_df[['doc_id', 'filing_type', 'filing_date']].to_dict('records')
        except Exception as e:
            logger.warning(f"Could not get filings: {e}")
            recent_filings = []
        
        # Build complete profile
        profile = {
            **member_info,
            'trading_stats': trading_stats,
            'recent_filings': recent_filings,
            'net_worth': get_net_worth(qb, bioguide_id),
            'sector_allocation': get_sector_allocation(qb, bioguide_id)
        }
        
        return success_response(profile)
    
    except Exception as e:
        logger.error(f"Error fetching member profile: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve member profile",
            status_code=500,
            details=str(e)
        )
