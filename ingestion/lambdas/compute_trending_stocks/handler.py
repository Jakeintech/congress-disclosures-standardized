#!/usr/bin/env python3
"""
Lambda handler for computing trending stocks aggregations.

Computes rolling window stock activity (7d, 30d, 90d) from fact_ptr_transactions.
"""

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, Any

import boto3
import pandas as pd

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')


def load_transactions(bucket_name: str, lookback_days: int = 365) -> pd.DataFrame:
    """Load recent transactions from gold layer."""
    logger.info(f"Loading transactions from last {lookback_days} days...")

    prefix = 'gold/house/financial/facts/fact_ptr_transactions/'
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    dfs = []
    cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

    for page in pages:
        if 'Contents' not in page:
            continue

        for obj in page['Contents']:
            if not obj['Key'].endswith('.parquet'):
                continue

            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
                    s3_client.download_file(bucket_name, obj['Key'], tmp.name)
                    df = pd.read_parquet(tmp.name)

                    # Filter to recent transactions
                    if 'transaction_date' in df.columns:
                        df['transaction_date'] = pd.to_datetime(df['transaction_date'])
                        df = df[df['transaction_date'] >= cutoff_date]

                    if len(df) > 0:
                        dfs.append(df)

                    os.unlink(tmp.name)

            except Exception as e:
                logger.warning(f"Error loading {obj['Key']}: {e}")
                continue

    if not dfs:
        logger.warning("No transaction data found")
        return pd.DataFrame()

    all_transactions = pd.concat(dfs, ignore_index=True)
    logger.info(f"Loaded {len(all_transactions):,} recent transactions")
    return all_transactions


def compute_trending_stocks(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Compute trending stocks for 7d, 30d, 90d windows."""
    if transactions_df.empty:
        logger.warning("No transactions to analyze")
        return pd.DataFrame()

    logger.info("Computing trending stocks...")

    now = datetime.utcnow()
    transactions_df['transaction_date'] = pd.to_datetime(transactions_df['transaction_date'])

    results = []

    for window_days, window_name in [(7, '7d'), (30, '30d'), (90, '90d')]:
        cutoff = now - timedelta(days=window_days)
        window_txns = transactions_df[transactions_df['transaction_date'] >= cutoff]

        if window_txns.empty:
            continue

        # Group by ticker and count transactions
        ticker_stats = window_txns.groupby('ticker').agg({
            'doc_id': 'count',
            'transaction_type': lambda x: (x == 'Purchase').sum(),
            'amount_low': 'sum'
        }).reset_index()

        ticker_stats.columns = ['ticker', 'transaction_count', 'purchase_count', 'total_volume']
        ticker_stats['window'] = window_name
        ticker_stats['window_start_date'] = cutoff.date().isoformat()
        ticker_stats['window_end_date'] = now.date().isoformat()

        # Sort by transaction count
        ticker_stats = ticker_stats.sort_values('transaction_count', ascending=False).head(100)

        results.append(ticker_stats)

    if not results:
        return pd.DataFrame()

    trending_stocks = pd.concat(results, ignore_index=True)
    trending_stocks['computed_at'] = datetime.utcnow().isoformat()

    logger.info(f"Computed trending stocks for {len(trending_stocks)} ticker-window combinations")
    return trending_stocks


def write_to_gold(df: pd.DataFrame, bucket_name: str) -> Dict[str, Any]:
    """Write trending stocks aggregation to gold layer."""
    if df.empty:
        logger.warning("Empty dataframe - no files to write")
        return {'files_written': [], 'total_records': 0}

    logger.info("Writing to gold layer...")

    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        df.to_parquet(tmp.name, engine='pyarrow', compression='snappy', index=False)
        s3_key = 'gold/house/financial/aggregates/trending_stocks/latest.parquet'
        s3_client.upload_file(tmp.name, bucket_name, s3_key)
        logger.info(f"  Uploaded to s3://{bucket_name}/{s3_key}")
        os.unlink(tmp.name)

    return {
        'files_written': [s3_key],
        'total_records': len(df)
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for computing trending stocks.

    Args:
        event: Event data with optional 'lookback_days'
        context: Lambda context

    Returns:
        Dict with status, records_processed, files_written
    """
    try:
        logger.info("=" * 80)
        logger.info("Lambda: compute_trending_stocks")
        logger.info("=" * 80)
        logger.info(f"Event: {json.dumps(event)}")

        # Get parameters
        bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
        if 'bucket_name' in event:
            bucket_name = event['bucket_name']

        lookback_days = event.get('lookback_days', 365)

        # Step 1: Load transactions
        transactions_df = load_transactions(bucket_name, lookback_days)

        # Step 2: Compute trending stocks
        trending_stocks = compute_trending_stocks(transactions_df)

        # Step 3: Write to gold layer
        result = write_to_gold(trending_stocks, bucket_name)

        logger.info("✅ trending_stocks computation complete!")

        return {
            'statusCode': 200,
            'status': 'success',
            'aggregate': 'trending_stocks',
            'records_processed': result['total_records'],
            'files_written': result['files_written'],
            'execution_time_ms': context.get_remaining_time_in_millis() if context else None
        }

    except Exception as e:
        logger.error(f"❌ Error computing trending_stocks: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'status': 'error',
            'aggregate': 'trending_stocks',
            'error': str(e),
            'error_type': type(e).__name__
        }
