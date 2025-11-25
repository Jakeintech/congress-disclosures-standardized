#!/usr/bin/env python3
"""
Build dim_members dimension table - FIXED VERSION

Loads only ACTUAL Congress members from PTR transactions, not all filers.
Properly matches against Congress API using cleaned names.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import boto3
from datetime import datetime
import logging

from ingestion.lib.enrichment import CongressAPIEnricher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_actual_members_from_ptr_transactions(bucket_name: str) -> pd.DataFrame:
    """
    Load only ACTUAL Congress members from PTR transactions.

    This filters out candidates, staff, and other non-members.
    """
    s3 = boto3.client('s3')

    logger.info("Loading PTR transactions to identify actual members...")

    # List all PTR transaction parquet files
    prefix = 'silver/house/financial/ptr_transactions/'
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

    if 'Contents' not in response:
        raise ValueError(f"No PTR transactions found in s3://{bucket_name}/{prefix}")

    # Download and concatenate all PTR transaction files
    dfs = []
    for obj in response['Contents']:
        if obj['Key'].endswith('.parquet'):
            logger.info(f"  Reading {obj['Key']}")

            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
                s3.download_file(bucket_name, obj['Key'], tmp.name)
                df = pd.read_parquet(tmp.name)
                dfs.append(df)
                os.unlink(tmp.name)

    all_transactions = pd.concat(dfs, ignore_index=True)
    logger.info(f"Loaded {len(all_transactions):,} transactions")

    # Extract unique members (filer_type = 'Member' means actual Congress member)
    unique_members = all_transactions[
        all_transactions['filer_type'] == 'Member'
    ][[
        'first_name', 'last_name', 'state_district', 'filer_full_name'
    ]].drop_duplicates()

    # Parse state and district (MA04 → state=MA, district=4)
    unique_members = unique_members.copy()
    unique_members['state'] = unique_members['state_district'].str[:2]

    # Extract district number (handle both formats: MA04, MA-04, etc.)
    unique_members['district'] = unique_members['state_district'].str.extract(r'(\d+)$')[0]
    unique_members['district'] = pd.to_numeric(unique_members['district'], errors='coerce').astype('Int64')

    logger.info(f"Found {len(unique_members)} actual Congress members with PTR transactions")
    logger.info(f"\nSample members:")
    for _, row in unique_members.head(10).iterrows():
        logger.info(f"  {row['first_name']} {row['last_name']} ({row['state_district']})")

    return unique_members


def enrich_members(members_df: pd.DataFrame, congress_enricher: CongressAPIEnricher) -> pd.DataFrame:
    """Enrich members with Congress.gov API."""
    logger.info("\n" + "=" * 80)
    logger.info("Enriching with Congress.gov API...")
    logger.info("=" * 80)

    enriched_records = []
    matched_count = 0
    unmatched_count = 0

    for idx, row in members_df.iterrows():
        logger.info(f"[{idx+1}/{len(members_df)}] {row['first_name']} {row['last_name']} ({row['state']})")

        # Enrich with Congress API
        enriched = congress_enricher.enrich_member(
            first_name=row['first_name'],
            last_name=row['last_name'],
            state=row['state'],
            district=row['district']
        )

        if enriched and enriched.get('bioguide_id'):
            matched_count += 1
        else:
            unmatched_count += 1

        # Build dim_members record
        record = {
            'bioguide_id': enriched.get('bioguide_id'),
            'first_name': row['first_name'],
            'last_name': row['last_name'],
            'full_name': f"{row['first_name']} {row['last_name']}",
            'official_full_name': row.get('filer_full_name', ''),
            'party': enriched.get('party'),
            'state': row['state'],
            'district': row['district'],
            'state_district': row['state_district'],
            'chamber': enriched.get('chamber', 'House'),  # Default to House for financial disclosures
            'member_type': 'Member',
            'start_date': enriched.get('start_date'),
            'end_date': enriched.get('end_date'),
            'is_current': enriched.get('is_current', True),
            'effective_from': datetime.utcnow().isoformat(),
            'effective_to': None,
            'version': 1
        }

        enriched_records.append(record)

    logger.info(f"\n✅ Matched: {matched_count}")
    logger.info(f"❌ Unmatched: {unmatched_count}")
    logger.info(f"📊 Match rate: {matched_count/(matched_count+unmatched_count)*100:.1f}%")

    return pd.DataFrame(enriched_records)


def write_to_gold(df: pd.DataFrame, bucket_name: str):
    """Write dim_members to gold layer."""
    logger.info("\n" + "=" * 80)
    logger.info("Writing to gold layer...")
    logger.info("=" * 80)

    # Save locally
    output_dir = Path('data/gold/dimensions/dim_members')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Partition by year of effective_from
    df['year'] = pd.to_datetime(df['effective_from']).dt.year

    for year in df['year'].unique():
        year_df = df[df['year'] == year].drop(columns=['year'])
        year_output_dir = output_dir / f'year={year}'
        year_output_dir.mkdir(parents=True, exist_ok=True)

        output_file = year_output_dir / 'part-0000.parquet'
        year_df.to_parquet(
            output_file,
            engine='pyarrow',
            compression='snappy',
            index=False
        )
        logger.info(f"  Wrote {year}: {len(year_df)} records -> {output_file}")

    # Upload to S3
    s3 = boto3.client('s3')

    for year in df['year'].unique():
        year_df = df[df['year'] == year].drop(columns=['year'])

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            year_df.to_parquet(tmp.name, engine='pyarrow', compression='snappy', index=False)

            s3_key = f'gold/house/financial/dimensions/dim_members/year={year}/part-0000.parquet'
            s3.upload_file(tmp.name, bucket_name, s3_key)
            logger.info(f"  Uploaded to s3://{bucket_name}/{s3_key}")

            os.unlink(tmp.name)


def main():
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

    logger.info("=" * 80)
    logger.info("Building dim_members dimension table (FIXED VERSION)")
    logger.info("=" * 80)

    # Initialize enrichers
    congress_enricher = CongressAPIEnricher(use_cache=True)

    # Load only actual members from PTR transactions
    members_df = load_actual_members_from_ptr_transactions(bucket_name)

    # Enrich with Congress API
    enriched_df = enrich_members(members_df, congress_enricher)

    # Write to gold layer
    write_to_gold(enriched_df, bucket_name)

    logger.info("\n" + "=" * 80)
    logger.info("✅ dim_members build complete!")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
