#!/usr/bin/env python3
"""
Compute agg_member_trading_stats aggregate table.

Analyzes trading activity by member including:
- Total trades and volume
- Buy vs sell ratios
- Average transaction size
- Trading frequency
- Most active periods
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

def compute_member_stats(conn):
    """Compute member-level trading statistics using DuckDB."""
    logger.info("Computing member trading stats via DuckDB...")
    
    # Aggregation SQL
    # This query handles volume, count, buy/sell ratios, and frequency in one go
    stats_sql = f"""
        WITH member_txs AS (
            SELECT 
                t.*,
                m.filer_name as full_name,
                m.party,
                m.state,
                (t.amount_low + t.amount_high) / 2.0 as amount_midpoint
            FROM read_parquet('s3://{BUCKET_NAME}/gold/house/financial/facts/fact_ptr_transactions/**/*.parquet') t
            LEFT JOIN read_parquet('s3://{BUCKET_NAME}/gold/house/financial/dimensions/dim_members/**/*.parquet') m
                ON t.bioguide_id = m.bioguide_id
        ),
        agg_stats AS (
            SELECT 
                bioguide_id as member_key,
                full_name as name,
                party,
                state,
                COUNT(*) as total_trades,
                SUM(amount_midpoint) as total_volume,
                AVG(amount_midpoint) as avg_transaction_size,
                MIN(amount_midpoint) as min_transaction_size,
                MAX(amount_midpoint) as max_transaction_size,
                SUM(CASE WHEN transaction_type = 'Purchase' THEN 1 ELSE 0 END) as buy_count,
                SUM(CASE WHEN transaction_type LIKE 'Sale%' THEN 1 ELSE 0 END) as sell_count,
                MIN(CAST(transaction_date AS DATE)) as first_transaction_date,
                MAX(CAST(transaction_date AS DATE)) as last_transaction_date,
                -- Frequency: (last - first) / trades
                (CAST(MAX(CAST(transaction_date AS DATE)) AS DATE) - CAST(MIN(CAST(transaction_date AS DATE)) AS DATE)) / NULLIF(COUNT(*), 0) as avg_days_between_trades
            FROM member_txs
            WHERE bioguide_id IS NOT NULL
            GROUP BY bioguide_id, full_name, party, state
        )
        SELECT 
            *,
            CAST(buy_count AS DOUBLE) / NULLIF(sell_count, 0) as buy_sell_ratio
        FROM agg_stats
        ORDER BY total_volume DESC
    """
    
    df = conn.execute(stats_sql).df()
    logger.info(f"Computed stats for {len(df)} members")
    return df

    logger.info(f"Computed stats for {len(stats_df)} members")
    return stats_df


def write_to_gold(df: pd.DataFrame):
    """Write agg_member_trading_stats to gold layer in S3."""
    logger.info("Writing results to S3...")
    s3 = boto3.client('s3')
    
    # In a real scenario, we might want to partition by year or update all
    # For now, we write to a single aggregate destination
    s3_key = 'gold/house/financial/aggregates/agg_member_trading_stats/part-0000.parquet'
    
    logger.info(f"Writing {len(df)} records to s3://{BUCKET_NAME}/{s3_key}")
    
    from io import BytesIO
    buffer = BytesIO()
    df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
    buffer.seek(0)
    
    s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
    logger.info("Successfully uploaded member stats!")

def main():
    logger.info("=" * 80)
    logger.info("Starting Optimized Member Stats Computation")
    logger.info("=" * 80)
    
    conn = get_duckdb_conn()
    
    try:
        stats_df = compute_member_stats(conn)
        
        if not stats_df.empty:
            logger.info(f"Top trader: {stats_df.iloc[0]['name']} (${stats_df.iloc[0]['total_volume']:,.0f})")
            write_to_gold(stats_df)
        else:
            logger.warning("No stats computed.")
            
        logger.info("✅ Member trading stats complete!")
    except Exception as e:
        logger.error(f"❌ Member stats computation failed: {e}", exc_info=True)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
