"""
Lambda: gold_transform_ptr_transactions

Transforms PTR structured data from silver layer to gold layer fact_ptr_transactions.

Trigger: S3 event when structured.json created in silver/structured/

Actions:
1. Load structured.json from S3
2. Lookup member_key from dim_members
3. Lookup/create asset_key from dim_assets
4. Calculate derived metrics (days_to_filing, is_late, etc.)
5. Generate date_keys
6. Write to fact_ptr_transactions (partitioned by year/month)
7. Trigger aggregate updates
"""

import json
import os
import boto3
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
import logging
from urllib.parse import unquote_plus

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

# Environment variables
BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
GOLD_PREFIX = os.environ.get('S3_GOLD_PREFIX', 'gold/house/financial')


def lambda_handler(event, context):
    """
    Main Lambda handler triggered by S3 event.

    Event structure:
    {
        "Records": [{
            "s3": {
                "bucket": {"name": "..."},
                "object": {"key": "silver/structured/year=2025/doc_id=20026590/structured.json"}
            }
        }]
    }
    """
    try:
        # Parse S3 event
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = unquote_plus(record['s3']['object']['key'])

            logger.info(f"Processing: s3://{bucket}/{key}")

            # Extract doc_id and year from key
            # Key format: silver/structured/year=YYYY/doc_id=DOCID/structured.json
            parts = key.split('/')
            year = int(parts[3].replace('year=', ''))
            doc_id = parts[4].replace('doc_id=', '')

            # Load structured JSON
            structured_data = load_structured_json(bucket, key)

            # Transform to fact transactions
            transactions = transform_to_fact_transactions(
                structured_data,
                doc_id,
                year
            )

            if not transactions:
                logger.warning(f"No transactions found in {doc_id}")
                return {'statusCode': 200, 'body': 'No transactions'}

            # Write to gold layer
            write_to_gold(transactions, year)

            logger.info(f"✅ Transformed {len(transactions)} transactions from {doc_id}")

        return {
            'statusCode': 200,
            'body': json.dumps(f'Successfully transformed {len(transactions)} transactions')
        }

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise


def load_structured_json(bucket: str, key: str) -> Dict[str, Any]:
    """Load structured JSON from S3."""
    response = s3.get_object(Bucket=bucket, Key=key)
    data = json.loads(response['Body'].read().decode('utf-8'))
    return data


def transform_to_fact_transactions(
    structured_data: Dict[str, Any],
    doc_id: str,
    year: int
) -> List[Dict[str, Any]]:
    """Transform structured PTR data to fact table records."""

    # Load dimension tables (for lookups)
    dim_members = load_dim_members()
    dim_assets = load_dim_assets()

    # Extract filer info
    filer_info = structured_data.get('filer_info', {})
    first_name = filer_info.get('first_name', '').strip()
    last_name = filer_info.get('last_name', '').strip()
    state_district = filer_info.get('state_district', '')

    # Lookup member_key
    member_key = lookup_member_key(dim_members, first_name, last_name, state_district)
    if not member_key:
        logger.warning(f"Member not found in dim_members: {first_name} {last_name} ({state_district})")
        return []

    # Extract metadata
    filing_date = structured_data.get('filing_date')
    extraction_metadata = structured_data.get('extraction_metadata', {})

    # Process transactions
    transactions = structured_data.get('transactions', [])
    fact_records = []

    for idx, txn in enumerate(transactions):
        # Lookup or create asset_key
        asset_name = txn.get('asset_name', '').strip()
        asset_key = lookup_or_create_asset_key(dim_assets, asset_name)

        # Parse dates
        transaction_date = txn.get('transaction_date')
        notification_date = txn.get('notification_date')

        # Calculate derived metrics
        days_to_filing = calculate_days_between(transaction_date, filing_date)
        days_to_notification = calculate_days_between(transaction_date, notification_date)
        is_late_filing = days_to_filing > 45 if days_to_filing is not None else None
        is_same_day_notification = (transaction_date == notification_date) if (transaction_date and notification_date) else False

        # Generate date keys
        transaction_date_key = date_to_key(transaction_date)
        notification_date_key = date_to_key(notification_date)
        filing_date_key = date_to_key(filing_date)

        # Parse amount
        amount_column = txn.get('amount_column', '')
        amount_low, amount_high = parse_amount_range(amount_column)
        amount_midpoint = (amount_low + amount_high) // 2 if (amount_low and amount_high) else None
        transaction_size_category = categorize_transaction_size(amount_low)

        # Owner codes
        owner_code = txn.get('owner_code')
        is_spouse = (owner_code == 'SP')
        is_dependent_child = (owner_code == 'DC')

        # Build fact record
        fact_record = {
            'member_key': member_key,
            'asset_key': asset_key,
            'filing_type_key': 1,  # PTR filing type
            'transaction_date_key': transaction_date_key,
            'notification_date_key': notification_date_key,
            'filing_date_key': filing_date_key,
            'doc_id': doc_id,
            'transaction_id': idx + 1,
            'transaction_type': txn.get('transaction_type'),
            'owner_code': owner_code,
            'amount_column': amount_column,
            'amount_range': txn.get('amount_range', ''),
            'amount_low': amount_low,
            'amount_high': amount_high,
            'amount_midpoint': amount_midpoint,
            'transaction_size_category': transaction_size_category,
            'days_to_notification': days_to_notification,
            'days_to_filing': days_to_filing,
            'is_late_filing': is_late_filing,
            'is_same_day_notification': is_same_day_notification,
            'is_spouse_transaction': is_spouse,
            'is_dependent_child_transaction': is_dependent_child,
            'extraction_confidence': extraction_metadata.get('confidence_score'),
            'extraction_method': extraction_metadata.get('extraction_method'),
            'pdf_type': extraction_metadata.get('pdf_type'),
            'data_completeness_pct': extraction_metadata.get('data_completeness', {}).get('completeness_percentage'),
            'requires_manual_review': extraction_metadata.get('confidence_score', 1.0) < 0.85,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'source_version': extraction_metadata.get('extraction_version', '1.0.0')
        }

        fact_records.append(fact_record)

    return fact_records


def load_dim_members() -> pd.DataFrame:
    """Load dim_members from gold layer."""
    # List all partitions
    prefix = f'{GOLD_PREFIX}/dimensions/dim_members/'
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)

    if 'Contents' not in response:
        logger.warning("dim_members not found, returning empty dataframe")
        return pd.DataFrame()

    # Download all parquet files
    dfs = []
    for obj in response['Contents']:
        if obj['Key'].endswith('.parquet'):
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
                s3.download_file(BUCKET_NAME, obj['Key'], tmp.name)
                df = pd.read_parquet(tmp.name)
                dfs.append(df)
                os.unlink(tmp.name)

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def load_dim_assets() -> pd.DataFrame:
    """Load dim_assets from gold layer."""
    prefix = f'{GOLD_PREFIX}/dimensions/dim_assets/'
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)

    if 'Contents' not in response:
        logger.warning("dim_assets not found, returning empty dataframe")
        return pd.DataFrame()

    # Download parquet file (no partitioning)
    for obj in response['Contents']:
        if obj['Key'].endswith('.parquet'):
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
                s3.download_file(BUCKET_NAME, obj['Key'], tmp.name)
                df = pd.read_parquet(tmp.name)
                os.unlink(tmp.name)
                return df

    return pd.DataFrame()


def lookup_member_key(dim_members: pd.DataFrame, first_name: str, last_name: str, state_district: str) -> Optional[int]:
    """Lookup member_key from dim_members."""
    if dim_members.empty:
        return None

    # Filter current members only
    current_members = dim_members[dim_members['is_current'] == True]

    # Exact match on names and state_district
    matches = current_members[
        (current_members['first_name'].str.upper() == first_name.upper()) &
        (current_members['last_name'].str.upper() == last_name.upper()) &
        (current_members['state_district'] == state_district)
    ]

    if len(matches) > 0:
        return int(matches.iloc[0]['member_key'])

    # Fallback: match on names only
    matches = current_members[
        (current_members['first_name'].str.upper() == first_name.upper()) &
        (current_members['last_name'].str.upper() == last_name.upper())
    ]

    if len(matches) > 0:
        return int(matches.iloc[0]['member_key'])

    return None


def lookup_or_create_asset_key(dim_assets: pd.DataFrame, asset_name: str) -> int:
    """Lookup or create asset_key from dim_assets."""
    if dim_assets.empty:
        # No dim_assets yet, use hash-based key
        return abs(hash(asset_name)) % 1000000 + 1

    # Exact match
    matches = dim_assets[dim_assets['asset_name'] == asset_name]

    if len(matches) > 0:
        return int(matches.iloc[0]['asset_key'])

    # Not found - assign new key (max + 1)
    max_key = int(dim_assets['asset_key'].max())
    return max_key + 1


def calculate_days_between(date1_str: Optional[str], date2_str: Optional[str]) -> Optional[int]:
    """Calculate days between two dates."""
    if not date1_str or not date2_str:
        return None

    try:
        date1 = datetime.fromisoformat(date1_str)
        date2 = datetime.fromisoformat(date2_str)
        return (date2 - date1).days
    except:
        return None


def date_to_key(date_str: Optional[str]) -> Optional[int]:
    """Convert ISO date string to date_key (YYYYMMDD)."""
    if not date_str:
        return None

    try:
        dt = datetime.fromisoformat(date_str)
        return int(dt.strftime('%Y%m%d'))
    except:
        return None


def parse_amount_range(amount_column: str) -> tuple:
    """Parse amount column code to numeric range."""
    # Amount ranges from PTR schema
    AMOUNT_RANGES = {
        'A': (1001, 15000),
        'B': (15001, 50000),
        'C': (50001, 100000),
        'D': (100001, 250000),
        'E': (250001, 500000),
        'F': (500001, 1000000),
        'G': (1000001, 5000000),
        'H': (5000001, 25000000),
        'I': (25000001, 50000000),
        'J': (50000001, 999999999),
        'K': (1000, 999999999)  # Over $50M
    }

    return AMOUNT_RANGES.get(amount_column, (0, 0))


def categorize_transaction_size(amount_low: Optional[int]) -> str:
    """Categorize transaction size."""
    if not amount_low:
        return 'Unknown'

    if amount_low < 15000:
        return 'Small'
    elif amount_low < 50000:
        return 'Medium'
    elif amount_low < 500000:
        return 'Large'
    else:
        return 'Mega'


def write_to_gold(transactions: List[Dict[str, Any]], year: int):
    """Write transactions to gold layer fact table."""
    df = pd.DataFrame(transactions)

    # Generate transaction_key (surrogate key)
    # In production, use a sequence or UUID
    df['transaction_key'] = range(1, len(df) + 1)

    # Partition by year and month of transaction_date
    if 'transaction_date_key' in df.columns:
        df['year'] = df['transaction_date_key'].astype(str).str[:4].astype(int)
        df['month'] = df['transaction_date_key'].astype(str).str[4:6].astype(int)

        # Group by partition
        for (part_year, part_month), group_df in df.groupby(['year', 'month']):
            # Drop partition columns before writing
            group_df = group_df.drop(columns=['year', 'month'])

            # Write to S3
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
                group_df.to_parquet(tmp.name, engine='pyarrow', compression='snappy', index=False)

                s3_key = f'{GOLD_PREFIX}/facts/fact_ptr_transactions/year={part_year}/month={part_month:02d}/part-{datetime.now().timestamp()}.parquet'
                s3.upload_file(tmp.name, BUCKET_NAME, s3_key)
                logger.info(f"Wrote {len(group_df)} transactions to s3://{BUCKET_NAME}/{s3_key}")

                os.unlink(tmp.name)
    else:
        logger.warning("No transaction_date_key found, skipping partition write")
