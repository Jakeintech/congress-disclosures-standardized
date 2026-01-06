#!/usr/bin/env python3
"""
Compute agg_trending_stocks aggregate table.

Analyzes most traded stocks by Congress members using high-speed DuckDB queries.
"""

import duckdb
import pandas as pd
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

def compute_trending_stocks(conn):
    """Compute trending stocks based on real trading data via DuckDB."""
    logger.info("Computing real trending stocks via DuckDB...")
    
    # Aggregation SQL: Group by ticker and asset_key
    trending_sql = f"""
        WITH transaction_data AS (
            SELECT 
                t.ticker,
                t.asset_key,
                (t.amount_low + t.amount_high) / 2.0 as amount_midpoint,
                t.transaction_type,
                t.bioguide_id,
                a.asset_name as name
            FROM read_parquet('s3://{BUCKET_NAME}/gold/house/financial/facts/fact_ptr_transactions/**/*.parquet') t
            LEFT JOIN read_parquet('s3://{BUCKET_NAME}/gold/house/financial/dimensions/dim_assets/**/*.parquet') a
                ON t.asset_key = a.asset_key
            WHERE t.ticker IS NOT NULL AND t.ticker != 'Unknown'
        ),
        stock_stats AS (
            SELECT 
                ticker,
                MAX(name) as name,
                COUNT(*) as trade_count,
                SUM(amount_midpoint) as total_volume_usd,
                AVG(amount_midpoint) as avg_transaction_size,
                COUNT(DISTINCT bioguide_id) as unique_members,
                SUM(CASE WHEN transaction_type = 'Purchase' THEN 1 ELSE 0 END) as buy_count,
                SUM(CASE WHEN transaction_type LIKE 'Sale%' THEN 1 ELSE 0 END) as sell_count
            FROM transaction_data
            GROUP BY ticker
        )
        SELECT 
            *,
            CASE 
                WHEN buy_count > sell_count * 1.5 THEN 'Strongly Bullish'
                WHEN buy_count > sell_count THEN 'Bullish'
                WHEN sell_count > buy_count * 1.5 THEN 'Strongly Bearish'
                WHEN sell_count > buy_count THEN 'Bearish'
                ELSE 'Neutral'
            END as net_sentiment,
            current_date as period_end,
            current_date - interval '30 days' as period_start
        FROM stock_stats
        ORDER BY trade_count DESC
    """
    
    df = conn.execute(trending_sql).df()
    logger.info(f"Computed stats for {len(df)} trending stocks")
    return df

def write_to_gold(df: pd.DataFrame):
    """Write agg_trending_stocks to gold layer in S3."""
    logger.info("Writing results to S3...")
    s3 = boto3.client('s3')
    
    s3_key = 'gold/house/financial/aggregates/agg_trending_stocks/part-0000.parquet'
    
    logger.info(f"Writing {len(df)} records to s3://{BUCKET_NAME}/{s3_key}")
    
    from io import BytesIO
    buffer = BytesIO()
    df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
    buffer.seek(0)
    
    s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
    logger.info("Successfully uploaded trending stocks!")

def main():
    logger.info("=" * 80)
    logger.info("Starting Optimized Trending Stocks Computation")
    logger.info("=" * 80)
    
    conn = get_duckdb_conn()
    
    try:
        stocks_df = compute_trending_stocks(conn)
        
        if not stocks_df.empty:
            logger.info(f"Top trending ticker: {stocks_df.iloc[0]['ticker']} ({stocks_df.iloc[0]['trade_count']} trades)")
            write_to_gold(stocks_df)
        else:
            logger.warning("No trending stocks computed.")
            
        logger.info("✅ Trending stocks computation complete!")
    except Exception as e:
        logger.error(f"❌ Trending stocks computation failed: {e}", exc_info=True)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
