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
from backend.lib.api.response_models import (
    MemberProfile,
    TradingStats,
    FilingBrief,
    NetWorth,
    SectorAllocation
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def get_net_worth(qb, bioguide_id) -> NetWorth:
    """Calculate estimated net worth from latest annual filing."""
    try:
        # Find latest annual filing
        filings_df = qb.query_parquet(
            'gold/house/financial/facts/fact_filings',
            filters={'bioguide_id': bioguide_id, 'filing_type': 'annual'},
            order_by='filing_year DESC',
            limit=1
        )
        
        if filings_df.empty:
             return NetWorth(min=0, max=0)
             
        latest_filing = filings_df.iloc[0]
        filing_id = latest_filing.get('doc_id')
        year = latest_filing.get('filing_year')
        
        # Get assets for this filing
        assets_df = qb.query_parquet(
            'gold/house/financial/facts/fact_asset_holdings',
            filters={'filing_id': filing_id}
        )
        
        if assets_df.empty:
             return NetWorth(min=0, max=0, year=int(year) if year else None)
             
        min_nw = int(assets_df['value_min'].sum()) if 'value_min' in assets_df.columns else 0
        max_nw = int(assets_df['value_max'].sum()) if 'value_max' in assets_df.columns else 0
        
        return NetWorth(min=min_nw, max=max_nw, year=int(year) if year else None)
        
    except Exception as e:
        logger.warning(f"Error calculating net worth: {e}")
        return NetWorth(min=0, max=0)


def get_sector_allocation(qb, bioguide_id) -> list[SectorAllocation]:
    """Get portfolio sector allocation."""
    try:
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
            
        if 'sector' not in assets_df.columns:
            return []
            
        if 'value_min' in assets_df.columns and 'value_max' in assets_df.columns:
            assets_df['value'] = (assets_df['value_min'] + assets_df['value_max']) / 2
        else:
            assets_df['value'] = 0
            
        sector_usage = assets_df.groupby('sector')['value'].sum().reset_index()
        total_value = sector_usage['value'].sum()
        
        allocation = []
        for _, row in sector_usage.iterrows():
            pct = (row['value'] / total_value) * 100 if total_value > 0 else 0
            
            allocation.append(SectorAllocation(
                sector=row['sector'],
                value=float(row['value']),
                percentage=float(pct)
            ))
            
        return sorted(allocation, key=lambda x: x.value, reverse=True)
        
    except Exception as e:
        logger.warning(f"Error getting sector allocation: {e}")
        return []


def handler(event, context):
    """
    GET /v1/members/{bioguide_id}
    
    Path parameters:
    - bioguide_id: Member's bioguide ID (e.g., 'C001059')
    """
    try:
        path_params = event.get('pathParameters') or {}
        bioguide_id = path_params.get('bioguide_id')
        
        if not bioguide_id:
            return error_response(message="bioguide_id is required", status_code=400)
        
        logger.info(f"Fetching member profile: {bioguide_id}")
        qb = ParquetQueryBuilder(s3_bucket=S3_BUCKET)
        
        # 1. Basic Info
        member_df = qb.query_parquet(
            'gold/house/financial/dimensions/dim_members',
            filters={'bioguide_id': bioguide_id},
            limit=1
        )
        
        if member_df.empty:
            return error_response(message=f"Member not found: {bioguide_id}", status_code=404)
        
        row = member_df.to_dict('records')[0]
        
        # 2. Trading Stats
        try:
            trades_df = qb.query_parquet(
                'gold/house/financial/facts/fact_ptr_transactions',
                filters={'bioguide_id': bioguide_id}
            )
            
            trading_stats = TradingStats(
                total_trades=len(trades_df),
                unique_stocks=len(trades_df['ticker'].unique()) if not trades_df.empty else 0,
                latest_trade_date=str(trades_df['transaction_date'].max()) if not trades_df.empty else None
            )
        except Exception as e:
            logger.warning(f"Could not get trading stats: {e}")
            trading_stats = TradingStats(total_trades=0, unique_stocks=0)
        
        # 3. Recent Filings
        try:
            filings_df = qb.query_parquet(
                'gold/house/financial/facts/fact_filings',
                filters={'bioguide_id': bioguide_id},
                order_by='filing_date DESC',
                limit=10
            )
            
            recent_filings = [
                FilingBrief(
                    doc_id=f['doc_id'],
                    filing_type=f['filing_type'],
                    filing_date=f['filing_date']
                )
                for f in filings_df.to_dict('records')
            ]
        except Exception as e:
            logger.warning(f"Could not get filings: {e}")
            recent_filings = []
        
        # 4. Construct MemberProfile
        profile = MemberProfile(
            bioguide_id=row['bioguide_id'],
            name=row.get('full_name') or row.get('name', 'Unknown'),
            first_name=row.get('first_name'),
            last_name=row.get('last_name'),
            party=row['party'],
            state=row['state'],
            chamber=row.get('chamber', 'house'),
            district=str(row.get('district')) if row.get('district') is not None else None,
            in_office=bool(row.get('in_office', True)),
            trading_stats=trading_stats,
            recent_filings=recent_filings,
            net_worth=get_net_worth(qb, bioguide_id),
            sector_allocation=get_sector_allocation(qb, bioguide_id)
        )
        
        return success_response(profile.model_dump())
    
    except Exception as e:
        logger.error(f"Error fetching member profile: {e}", exc_info=True)
        return error_response(
            message="Failed to retrieve member profile",
            status_code=500,
            details=str(e)
        )
