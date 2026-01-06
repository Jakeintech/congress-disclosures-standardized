#!/usr/bin/env python3
"""
Build dim_members dimension table from silver layer filings (WITHOUT Congress API enrichment).

This simplified version creates dim_members with just the data we have from filings.
Congress API enrichment can be added later as a separate step.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import boto3
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_unique_members_from_silver(bucket_name: str) -> pd.DataFrame:
    """Load unique members from silver layer filings."""
    s3 = boto3.client('s3')
    logger.info("Loading filings from silver layer...")

    # Read from Gold layer fact_filings (source of truth for filings)
    prefix = 'gold/house/financial/facts/fact_filings/'
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

    if 'Contents' not in response:
        raise ValueError(f"No filings found in s3://{bucket_name}/{prefix}")

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

    all_filings = pd.concat(dfs, ignore_index=True)
    logger.info(f"Loaded {len(all_filings):,} filings")

    # Handle missing name columns by parsing filer_name
    if 'first_name' not in all_filings.columns:
        logger.info("Parsing names from filer_name...")
        
        def parse_name(full_name):
            if not full_name:
                return pd.Series([None, None])
            
            parts = full_name.strip().split(',')
            if len(parts) == 2:
                # Format: Last, First
                return pd.Series([parts[1].strip(), parts[0].strip()])
            
            parts = full_name.strip().split(' ')
            if len(parts) >= 2:
                # Format: First Last (simple assumption)
                return pd.Series([parts[0], ' '.join(parts[1:])])
            
            return pd.Series([full_name, None])

        all_filings[['first_name', 'last_name']] = all_filings['filer_name'].apply(parse_name)

    unique_members = all_filings[[
        'first_name', 'last_name', 'state_district'
    ]].drop_duplicates()

    unique_members['state'] = unique_members['state_district'].str[:2]
    unique_members['district'] = unique_members['state_district'].str[3:].replace('', None).astype('Int64')

    logger.info(f"Found {len(unique_members)} unique members")
    return unique_members


def build_dim_members(members_df: pd.DataFrame) -> pd.DataFrame:
    """Build dim_members without external enrichment."""
    logger.info("Building dim_members records...")

    records = []
    for idx, row in members_df.iterrows():
        record = {
            'bioguide_id': None,  # No API enrichment
            'first_name': row['first_name'],
            'last_name': row['last_name'],
            'full_name': f"{row['first_name']} {row['last_name']}",
            'party': None,  # No API enrichment
            'state': row['state'],
            'district': row['district'],
            'state_district': row['state_district'],
            'chamber': 'House',  # We only have House data
            'member_type': 'Member',
            'start_date': None,
            'end_date': None,
            'is_current': True,  # Assume current
            'effective_from': datetime.utcnow().isoformat(),
            'effective_to': None,
            'version': 1
        }
        records.append(record)

    df = pd.DataFrame(records)

    # Assign surrogate keys
    df = df.sort_values(['last_name', 'first_name', 'state']).reset_index(drop=True)
    df['member_key'] = df.index + 1

    return df


def write_to_gold(df: pd.DataFrame, bucket_name: str):
    """Write dim_members to gold layer."""
    logger.info("Writing to gold layer...")

    output_dir = Path('data/gold/dimensions/dim_members')
    output_dir.mkdir(parents=True, exist_ok=True)

    df['year'] = pd.to_datetime(df['effective_from']).dt.year

    for year in df['year'].unique():
        year_df = df[df['year'] == year].drop(columns=['year'])
        year_output_dir = output_dir / f'year={year}'
        year_output_dir.mkdir(parents=True, exist_ok=True)

        output_file = year_output_dir / 'part-0000.parquet'
        year_df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
        logger.info(f"  Wrote {year}: {len(year_df)} records -> {output_file}")

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
    logger.info("Building dim_members (simplified - no API enrichment)")
    logger.info("=" * 80)

    members_df = load_unique_members_from_silver(bucket_name)
    final_df = build_dim_members(members_df)

    logger.info(f"\nSummary:")
    logger.info(f"  Total members: {len(final_df)}")
    logger.info(f"  Note: bioguide_id and party are NULL (no API enrichment)")

    write_to_gold(final_df, bucket_name)
    logger.info("\n✅ dim_members build complete!")


if __name__ == '__main__':
    main()
