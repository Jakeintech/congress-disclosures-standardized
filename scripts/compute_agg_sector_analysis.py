#!/usr/bin/env python3
"""
Deep Sector Analysis Aggregation.

Provides comprehensive sector-level analytics:
1. Volume and trade count by sector
2. Sector rotation signals (buy/sell flow)
3. Party preferences by sector
4. Committee correlation with sector trading
5. Concentration metrics
6. Trend analysis over time

Output: gold/aggregates/agg_sector_analysis/
"""

import duckdb
import pandas as pd
import numpy as np
import boto3
import os
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

def get_duckdb_conn():
    """Create a DuckDB connection with S3 support."""
    conn = duckdb.connect(':memory:')
    conn.execute("INSTALL httpfs; LOAD httpfs;")
    conn.execute(f"SET s3_region='{os.environ.get('AWS_REGION', 'us-east-1')}';")
    conn.execute("SET s3_use_ssl=true;")
    return conn

def compute_sector_analytics(conn):
    """Compute all sector-related analytics using DuckDB."""
    logger.info("Starting high-speed sector analysis via DuckDB...")
    
    # 1. Base Query: Join Transactions with Assets and Members
    # This captures the enriched sector from dim_assets
    base_join_sql = f"""
        CREATE OR REPLACE VIEW transaction_enriched AS
        SELECT 
            t.*,
            COALESCE(a.sector, 'Other') as enriched_sector,
            COALESCE(a.industry, 'Other') as enriched_industry,
            m.party,
            m.chamber,
            m.state,
            (t.amount_low + t.amount_high) / 2.0 as amount_midpoint
        FROM read_parquet('s3://{BUCKET_NAME}/gold/house/financial/facts/fact_ptr_transactions/**/*.parquet') t
        LEFT JOIN read_parquet('s3://{BUCKET_NAME}/gold/house/financial/dimensions/dim_assets/**/*.parquet') a
            ON t.asset_key = a.asset_key
        LEFT JOIN read_parquet('s3://{BUCKET_NAME}/gold/house/financial/dimensions/dim_members/**/*.parquet') m
            ON t.bioguide_id = m.bioguide_id
    """
    conn.execute(base_join_sql)
    
    # 2. Sector Summary
    logger.info("Computing sector summary...")
    summary_sql = """
        SELECT 
            enriched_sector as sector,
            SUM(amount_midpoint) as total_volume,
            COUNT(*) as trade_count,
            AVG(amount_midpoint) as avg_trade_size,
            SUM(CASE WHEN transaction_type = 'Purchase' THEN amount_midpoint ELSE 0 END) as buy_volume,
            SUM(CASE WHEN transaction_type LIKE 'Sale%' THEN amount_midpoint ELSE 0 END) as sell_volume,
            COUNT(DISTINCT bioguide_id) as unique_traders,
            COUNT(DISTINCT ticker) as unique_tickers
        FROM transaction_enriched
        GROUP BY enriched_sector
        ORDER BY total_volume DESC
    """
    summary_df = conn.execute(summary_sql).df()
    
    # 3. Party Breakdown
    logger.info("Computing party preferences...")
    party_sql = """
        SELECT 
            enriched_sector as sector,
            party,
            SUM(amount_midpoint) as party_volume,
            COUNT(*) as party_trades
        FROM transaction_enriched
        WHERE party IN ('D', 'R', 'I')
        GROUP BY enriched_sector, party
    """
    party_df = conn.execute(party_sql).df()
    
    # 4. Timeseries (Monthly)
    logger.info("Computing monthly trends...")
    timeseries_sql = """
        SELECT 
            enriched_sector as sector,
            date_trunc('month', CAST(transaction_date AS DATE)) as month,
            SUM(amount_midpoint) as total_volume,
            COUNT(*) as trade_count
        FROM transaction_enriched
        GROUP BY enriched_sector, month
        ORDER BY month ASC, total_volume DESC
    """
    ts_df = conn.execute(timeseries_sql).df()
    
    return {
        'summary': summary_df,
        'party': party_df,
        'timeseries': ts_df
    }


def write_analysis_results(results):
    """Write all analysis dataframes to S3."""
    s3 = boto3.client('s3')
    
    for analysis_type, df in results.items():
        if df.empty:
            continue
            
        s3_key = f'gold/house/financial/aggregates/agg_sector_analysis/type={analysis_type}/part-0000.parquet'
        
        logger.info(f"Writing {analysis_type} results to s3://{BUCKET_NAME}/{s3_key}")
        
        # Write to buffer
        from io import BytesIO
        buffer = BytesIO()
        df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
        buffer.seek(0)
        
        s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
        logger.info(f"Successfully uploaded {len(df)} rows for {analysis_type}")

def main():
    logger.info("=" * 80)
    logger.info("Starting Optimized Sector Analysis")
    logger.info("=" * 80)
    
    conn = get_duckdb_conn()
    
    try:
        results = compute_sector_analytics(conn)
        write_analysis_results(results)
        logger.info("✅ Sector analysis complete!")
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}", exc_info=True)
    finally:
        conn.close()

if __name__ == '__main__':
    main()


if __name__ == '__main__':
    main()
