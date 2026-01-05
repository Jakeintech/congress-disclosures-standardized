#!/usr/bin/env python3
"""
Lambda handler for computing member trading statistics.

Computes per-member trading volume, frequency, compliance metrics.
"""

import json
import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, Any

import boto3
import pandas as pd

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')


def load_filings_and_transactions(bucket_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load filings and transactions from gold layer."""
    logger.info("Loading filings and transactions...")

    # Load filings
    filings_prefix = 'gold/house/financial/facts/fact_filings/'
    filings_dfs = []

    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=filings_prefix)
    if 'Contents' in response:
        for obj in response['Contents']:
            if obj['Key'].endswith('.parquet'):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
                    s3_client.download_file(bucket_name, obj['Key'], tmp.name)
                    df = pd.read_parquet(tmp.name)
                    filings_dfs.append(df)
                    os.unlink(tmp.name)

    filings = pd.concat(filings_dfs, ignore_index=True) if filings_dfs else pd.DataFrame()

    # Load transactions
    txn_prefix = 'gold/house/financial/facts/fact_ptr_transactions/'
    txn_dfs = []

    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=txn_prefix)

    for page in pages:
        if 'Contents' not in page:
            continue
        for obj in page['Contents']:
            if obj['Key'].endswith('.parquet'):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
                        s3_client.download_file(bucket_name, obj['Key'], tmp.name)
                        df = pd.read_parquet(tmp.name)
                        txn_dfs.append(df)
                        os.unlink(tmp.name)
                except Exception as e:
                    logger.warning(f"Error loading {obj['Key']}: {e}")

    transactions = pd.concat(txn_dfs, ignore_index=True) if txn_dfs else pd.DataFrame()

    logger.info(f"Loaded {len(filings):,} filings and {len(transactions):,} transactions")
    return filings, transactions


def compute_member_stats(filings: pd.DataFrame, transactions: pd.DataFrame) -> pd.DataFrame:
    """Compute member trading statistics including compliance score."""
    if filings.empty:
        logger.warning("No filings to analyze")
        return pd.DataFrame()

    logger.info("Computing member statistics...")

    # Ensure filer_name exists FIRST (before any operations)
    if 'filer_name' not in filings.columns or filings['filer_name'].isna().all():
        logger.warning("filer_name column missing or empty, creating from first_name + last_name")
        if 'first_name' in filings.columns and 'last_name' in filings.columns:
            filings = filings.copy()  # Avoid modifying original
            filings['filer_name'] = (
                filings['first_name'].fillna('') + ' ' +
                filings['last_name'].fillna('')
            ).str.strip()
            logger.info(f"Created filer_name for {filings['filer_name'].notna().sum()} records")
        else:
            logger.error(f"Cannot create filer_name. Available columns: {filings.columns.tolist()}")
            raise KeyError("filer_name column missing and cannot be created")

    # Group filings by member
    member_filing_stats = filings.groupby('filer_name').agg({
        'doc_id': 'count',
        'filing_date': ['min', 'max'],
        'state_district': 'first'
    }).reset_index()

    # Flatten multi-level columns from agg IMMEDIATELY
    member_filing_stats.columns = ['filer_name', 'total_filings', 'first_filing_date',
                                     'latest_filing_date', 'state_district']
    
    # Calculate late filing count for compliance score
    # Late filing = filed > 45 days after transaction date
    late_filing_counts = pd.DataFrame()
    if not transactions.empty and 'filer_name' in transactions.columns:
        txn_copy = transactions.copy()
        # Ensure date columns are datetime
        if 'filing_date' in txn_copy.columns and 'transaction_date' in txn_copy.columns:
            txn_copy['filing_date'] = pd.to_datetime(txn_copy['filing_date'], errors='coerce')
            txn_copy['transaction_date'] = pd.to_datetime(txn_copy['transaction_date'], errors='coerce')
            txn_copy['days_to_file'] = (txn_copy['filing_date'] - txn_copy['transaction_date']).dt.days
            txn_copy['is_late'] = txn_copy['days_to_file'] > 45
            
            late_filing_counts = txn_copy.groupby('filer_name').agg({
                'is_late': 'sum',
                'transaction_key': 'count'
            }).reset_index()
            late_filing_counts.columns = ['filer_name', 'late_filing_count', 'transaction_count_for_compliance']
    
    # Merge late filing counts if available
    if not late_filing_counts.empty:
        member_filing_stats = member_filing_stats.merge(late_filing_counts, on='filer_name', how='left')
        member_filing_stats['late_filing_count'] = member_filing_stats['late_filing_count'].fillna(0).astype(int)
        member_filing_stats['transaction_count_for_compliance'] = member_filing_stats['transaction_count_for_compliance'].fillna(0).astype(int)
    else:
        member_filing_stats['late_filing_count'] = 0
        member_filing_stats['transaction_count_for_compliance'] = 0

    # If we have transactions, compute transaction stats
    if not transactions.empty:
        # Transactions already have filer_name, so use it directly
        # But filter to only those with non-null filer_name
        txn_with_name = transactions[transactions['filer_name'].notna()].copy()

        if len(txn_with_name) > 0:
            member_txn_stats = txn_with_name.groupby('filer_name').agg({
                'transaction_key': 'count',
                'amount_low': 'sum',
                'ticker': 'nunique'
            }).reset_index()

            member_txn_stats.columns = ['filer_name', 'total_transactions',
                                         'total_volume', 'unique_stocks']

            # Merge with filing stats
            member_stats = member_filing_stats.merge(member_txn_stats, on='filer_name', how='left')
        else:
            logger.warning("No transactions with filer_name found")
            member_stats = member_filing_stats.copy()
            member_stats['total_transactions'] = 0
            member_stats['total_volume'] = 0.0
            member_stats['unique_stocks'] = 0
    else:
        member_stats = member_filing_stats.copy()
        member_stats['total_transactions'] = 0
        member_stats['total_volume'] = 0.0
        member_stats['unique_stocks'] = 0

    # Fill NaN values from the merge
    member_stats['total_transactions'] = member_stats['total_transactions'].fillna(0).astype(int)
    member_stats['total_volume'] = member_stats['total_volume'].fillna(0.0)
    member_stats['unique_stocks'] = member_stats['unique_stocks'].fillna(0).astype(int)
    
    # Calculate compliance score (0.0 - 1.0)
    # compliance_score = 1.0 - (late_filing_count / total_transactions)
    # If no transactions, default to 1.0 (perfect compliance)
    if 'late_filing_count' in member_stats.columns and 'transaction_count_for_compliance' in member_stats.columns:
        member_stats['compliance_score'] = 1.0 - (
            member_stats['late_filing_count'] / 
            member_stats['transaction_count_for_compliance'].replace(0, 1)  # Avoid division by zero
        )
        # Ensure compliance_score is between 0.0 and 1.0
        member_stats['compliance_score'] = member_stats['compliance_score'].clip(0.0, 1.0)
    else:
        member_stats['compliance_score'] = 1.0  # Default perfect compliance if no data

    # Add computed timestamp
    member_stats['computed_at'] = datetime.utcnow().isoformat()

    # Sort by transaction count
    member_stats = member_stats.sort_values('total_transactions', ascending=False)

    logger.info(f"Computed stats for {len(member_stats)} members")
    return member_stats


def write_to_gold(df: pd.DataFrame, bucket_name: str) -> Dict[str, Any]:
    """Write member stats aggregation to gold layer."""
    if df.empty:
        logger.warning("Empty dataframe - no files to write")
        return {'files_written': [], 'total_records': 0}

    logger.info("Writing to gold layer...")

    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        df.to_parquet(tmp.name, engine='pyarrow', compression='snappy', index=False)
        s3_key = 'gold/house/financial/aggregates/agg_member_trading_stats/latest.parquet'
        s3_client.upload_file(tmp.name, bucket_name, s3_key)
        logger.info(f"  Uploaded to s3://{bucket_name}/{s3_key}")
        os.unlink(tmp.name)

    return {
        'files_written': [s3_key],
        'total_records': len(df)
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for computing member trading statistics.

    Args:
        event: Event data
        context: Lambda context

    Returns:
        Dict with status, records_processed, files_written
    """
    try:
        logger.info("=" * 80)
        logger.info("Lambda: compute_member_stats")
        logger.info("=" * 80)
        logger.info(f"Event: {json.dumps(event)}")

        # Get bucket name
        bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
        if 'bucket_name' in event:
            bucket_name = event['bucket_name']

        # Step 1: Load filings and transactions
        filings, transactions = load_filings_and_transactions(bucket_name)

        # Step 2: Compute member stats
        member_stats = compute_member_stats(filings, transactions)

        # Step 3: Write to gold layer
        result = write_to_gold(member_stats, bucket_name)

        logger.info("✅ member_stats computation complete!")

        return {
            'statusCode': 200,
            'status': 'success',
            'aggregate': 'member_trading_stats',
            'records_processed': result['total_records'],
            'files_written': result['files_written'],
            'execution_time_ms': context.get_remaining_time_in_millis() if context else None
        }

    except Exception as e:
        logger.error(f"❌ Error computing member_stats: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'status': 'error',
            'aggregate': 'member_trading_stats',
            'error': str(e),
            'error_type': type(e).__name__
        }
