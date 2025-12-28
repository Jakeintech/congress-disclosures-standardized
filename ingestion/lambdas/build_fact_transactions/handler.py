#!/usr/bin/env python3
"""
Lambda handler for building fact_ptr_transactions fact table.

Reads Silver layer Type P structured JSONs and creates normalized transaction records.
"""

import hashlib
import json
import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

import boto3
import pandas as pd

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')


def parse_amount_string(amount_str: str) -> Tuple[Optional[float], Optional[float]]:
    """Parse amount range string into low and high values."""
    if not amount_str:
        return None, None

    clean = str(amount_str).replace('$', '').replace(',', '').replace('\n', ' ').strip()
    low = None
    high = None

    try:
        if ' - ' in clean:
            parts = clean.split(' - ')
            low = float(parts[0])
            if len(parts) > 1:
                high = float(parts[1])
        elif '-' in clean:
            parts = clean.split('-')
            low = float(parts[0])
            if len(parts) > 1:
                high = float(parts[1])
        elif 'Over' in clean:
            val = clean.replace('Over', '').strip()
            low = float(val)
        else:
            try:
                low = float(clean)
            except:
                pass
    except:
        pass

    return low, high


def get_transaction_type(tx: Dict) -> Optional[str]:
    """Map transaction type code to full name."""
    tt = tx.get('trans_type') or tx.get('transaction_type')
    if not tt:
        return None

    tt = tt.upper().strip()
    mapping = {
        'P': 'Purchase',
        'S': 'Sale',
        'E': 'Exchange'
    }
    return mapping.get(tt, tt)


def generate_transaction_key(doc_id: str, txn: Dict) -> str:
    """Generate unique hash key for transaction."""
    raw = (f"{doc_id}_{txn.get('transaction_date')}_"
           f"{txn.get('ticker')}_{txn.get('amount')}_"
           f"{txn.get('transaction_type')}_{txn.get('asset_description', '')}")
    return hashlib.md5(raw.encode()).hexdigest()


def load_transactions_from_silver(bucket_name: str, year: Optional[int] = None) -> pd.DataFrame:
    """Load PTR transactions from Silver layer Type P structured JSONs."""
    logger.info("Loading PTR transactions from silver/house/financial/objects/...")

    prefix = 'silver/house/financial/objects/'
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    transactions = []
    processed_count = 0

    for page in pages:
        if 'Contents' not in page:
            continue

        for obj in page['Contents']:
            key = obj['Key']
            if not key.endswith('.json'):
                continue
            
            # Ensure it's a Type P filing
            if 'filing_type=type_p' not in key:
                continue

            # Optional: Filter by year if specified in event
            if year:
                # Support both partition structures: 
                # year=2024/filing_type=type_p OR filing_type=type_p/year=2024
                # Just extract year value and compare
                try:
                    import re
                    year_match = re.search(r'year=(\d{4})', key)
                    if year_match:
                        file_year = int(year_match.group(1))
                        if file_year != year:
                            continue
                except:
                    pass

            try:
                response = s3_client.get_object(Bucket=bucket_name, Key=obj['Key'])
                data = json.loads(response['Body'].read().decode('utf-8'))

                doc_id = data.get('doc_id')
                filing_date = data.get('filing_date')

                # Extract transactions
                for txn in data.get('transactions', []):
                    amount_low, amount_high = parse_amount_string(txn.get('amount'))

                    transaction = {
                        'transaction_key': generate_transaction_key(doc_id, txn),
                        'doc_id': doc_id,
                        'filing_date': filing_date,
                        'transaction_date': txn.get('transaction_date'),
                        'transaction_type': get_transaction_type(txn),
                        'asset_name': txn.get('asset_name', '').strip(),
                        'asset_description': txn.get('asset_description', '').strip(),
                        'ticker': txn.get('ticker', '').strip().upper() if txn.get('ticker') else None,
                        'amount_range_text': txn.get('amount'),
                        'amount_low': amount_low,
                        'amount_high': amount_high,
                        'owner': txn.get('owner', 'Self'),
                    }
                    transactions.append(transaction)

                processed_count += 1
                if processed_count % 100 == 0:
                    logger.info(f"  Processed {processed_count} files...")

            except Exception as e:
                logger.warning(f"Error processing {obj['Key']}: {e}")
                continue

    logger.info(f"Loaded {len(transactions):,} transactions from {processed_count} files")

    if not transactions:
        logger.warning("No transactions found")
        return pd.DataFrame()

    return pd.DataFrame(transactions)


def write_to_gold(df: pd.DataFrame, bucket_name: str) -> Dict[str, Any]:
    """Write fact_ptr_transactions to gold layer S3."""
    if df.empty:
        logger.warning("Empty dataframe - no files to write")
        return {'files_written': [], 'total_records': 0, 'years': []}

    logger.info("Writing to gold layer...")

    # Add partitioning columns
    df['year'] = pd.to_datetime(df['transaction_date']).dt.year
    df['month'] = pd.to_datetime(df['transaction_date']).dt.month

    files_written = []
    for (year, month), group in df.groupby(['year', 'month']):
        group = group.drop(columns=['year', 'month'])

        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            group.to_parquet(tmp.name, engine='pyarrow', compression='snappy', index=False)
            s3_key = f'gold/house/financial/facts/fact_ptr_transactions/year={int(year)}/month={int(month):02d}/part-0000.parquet'
            s3_client.upload_file(tmp.name, bucket_name, s3_key)
            logger.info(f"  Uploaded {len(group)} records to s3://{bucket_name}/{s3_key}")
            files_written.append(s3_key)
            os.unlink(tmp.name)

    return {
        'files_written': files_written,
        'total_records': len(df),
        'years': sorted([int(y) for y in df['year'].dropna().unique()])
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for building fact_ptr_transactions.

    Args:
        event: Event data with optional 'year' parameter
        context: Lambda context

    Returns:
        Dict with status, records_processed, files_written
    """
    try:
        logger.info("=" * 80)
        logger.info("Lambda: build_fact_transactions")
        logger.info("=" * 80)
        logger.info(f"Event: {json.dumps(event)}")

        # Get parameters
        bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
        if 'bucket_name' in event:
            bucket_name = event['bucket_name']

        year = event.get('year')  # Optional: filter by year

        # Step 1: Load transactions from Silver
        transactions_df = load_transactions_from_silver(bucket_name, year)

        # Step 2: Write to gold layer
        result = write_to_gold(transactions_df, bucket_name)

        logger.info("✅ fact_ptr_transactions build complete!")

        return {
            'statusCode': 200,
            'status': 'success',
            'fact_table': 'fact_ptr_transactions',
            'records_processed': result['total_records'],
            'files_written': result['files_written'],
            'years': result['years'],
            'execution_time_ms': context.get_remaining_time_in_millis() if context else None
        }

    except Exception as e:
        logger.error(f"❌ Error building fact_ptr_transactions: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'status': 'error',
            'fact_table': 'fact_ptr_transactions',
            'error': str(e),
            'error_type': type(e).__name__
        }
