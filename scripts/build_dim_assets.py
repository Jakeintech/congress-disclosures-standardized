#!/usr/bin/env python3
"""
Build dim_assets dimension table from PTR transactions with stock API enrichment.

This script:
1. Loads unique assets from silver/structured PTR data
2. Extracts ticker symbols using regex
3. Enriches with Yahoo Finance API (sector, industry, market cap)
4. Writes to gold/dimensions/dim_assets
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import boto3
import json
from datetime import datetime
import logging
from collections import Counter

from ingestion.lib.enrichment import StockAPIEnricher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_unique_assets_from_silver(bucket_name: str) -> pd.DataFrame:
    """Load unique assets from silver extraction JSON data."""
    s3 = boto3.client('s3')

    logger.info("Loading assets from silver objects layer...")

    # List all extraction JSON files (scan multiple filing types)
    prefixes = [
        'silver/house/financial/objects/',  # New path structure
    ]
    
    assets = []
    asset_occurrences = Counter()
    asset_first_seen = {}
    asset_last_seen = {}
    paginator = s3.get_paginator('list_objects_v2')

    for prefix in prefixes:
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        for page in pages:
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                if not obj['Key'].endswith('extraction.json'):
                    continue

                # Load extraction JSON
                try:
                    response = s3.get_object(Bucket=bucket_name, Key=obj['Key'])
                    data = json.loads(response['Body'].read().decode('utf-8'))

                    # Extract doc info from path
                    # Path: silver/house/financial/objects/year=2024/filing_type=type_p/doc_id=12345/extraction.json
                    path_parts = obj['Key'].split('/')
                    doc_id = None
                    year = None
                    for part in path_parts:
                        if part.startswith('doc_id='):
                            doc_id = part.replace('doc_id=', '')
                        if part.startswith('year='):
                            year = int(part.replace('year=', ''))
                    
                    filing_date = None  # Would need to join with filings table

                    # Extract transactions (PTR data)
                    transactions = data.get('transactions', [])
                    
                    # Also check schedule_a for annual filings (asset holdings)
                    schedule_a = data.get('schedule_a', [])

                    for txn in transactions:
                        asset_name = txn.get('asset_name', '').strip()
                        if not asset_name:
                            continue

                        # Track occurrences
                        asset_occurrences[asset_name] += 1

                        # Track first/last seen
                        txn_date = txn.get('transaction_date')
                        if txn_date:
                            if asset_name not in asset_first_seen or txn_date < asset_first_seen[asset_name]:
                                asset_first_seen[asset_name] = txn_date
                            if asset_name not in asset_last_seen or txn_date > asset_last_seen[asset_name]:
                                asset_last_seen[asset_name] = txn_date

                        assets.append(asset_name)
                    
                    # Also process schedule_a for asset holdings
                    for holding in schedule_a:
                        asset_name = holding.get('asset_name', '').strip()
                        if not asset_name:
                            continue
                        asset_occurrences[asset_name] += 1
                        assets.append(asset_name)

                except Exception as e:
                    logger.warning(f"Error processing {obj['Key']}: {e}")
                    continue

    logger.info(f"Loaded {len(assets):,} total asset transactions")

    # Create unique assets dataframe
    unique_assets = pd.DataFrame({
        'asset_name': list(set(assets))
    })

    # Add occurrence counts
    unique_assets['occurrence_count'] = unique_assets['asset_name'].map(asset_occurrences)
    unique_assets['first_seen_date'] = unique_assets['asset_name'].map(asset_first_seen)
    unique_assets['last_seen_date'] = unique_assets['asset_name'].map(asset_last_seen)

    # Fill missing dates with today
    today = datetime.now().strftime('%Y-%m-%d')
    unique_assets['first_seen_date'].fillna(today, inplace=True)
    unique_assets['last_seen_date'].fillna(today, inplace=True)

    logger.info(f"Found {len(unique_assets)} unique assets")
    logger.info(f"  Most common: {unique_assets.nlargest(5, 'occurrence_count')[['asset_name', 'occurrence_count']].to_dict('records')}")

    return unique_assets


def enrich_assets(assets_df: pd.DataFrame, stock_enricher: StockAPIEnricher) -> pd.DataFrame:
    """Enrich assets with stock API."""
    logger.info("Enriching assets with stock API...")

    enriched_records = []

    for idx, row in assets_df.iterrows():
        asset_name = row['asset_name']

        if idx % 100 == 0:
            logger.info(f"  [{idx+1}/{len(assets_df)}] Processing...")

        # Classify asset type
        asset_type = stock_enricher.classify_asset_type(asset_name)

        # Enrich with stock API (if Stock/ETF/Fund)
        if asset_type in ['Stock', 'ETF', 'Mutual Fund']:
            enriched = stock_enricher.enrich_asset(asset_name)
        else:
            enriched = {
                'ticker_symbol': None,
                'company_name': None,
                'sector': None,
                'industry': None,
                'market_cap': None,
                'market_cap_category': None,
                'exchange': None,
                'is_publicly_traded': False,
                'enrichment_status': 'non_stock_asset'
            }

        # Normalize asset name
        normalized_name = asset_name.strip()

        # Build dim_assets record
        record = {
            'asset_name': asset_name,
            'normalized_asset_name': normalized_name,
            'ticker_symbol': enriched.get('ticker_symbol'),
            'company_name': enriched.get('company_name'),
            'asset_type': asset_type,
            'sector': enriched.get('sector'),
            'industry': enriched.get('industry'),
            'market_cap_category': enriched.get('market_cap_category'),
            'is_publicly_traded': enriched.get('is_publicly_traded', False),
            'is_crypto': asset_type == 'Cryptocurrency',
            'exchange': enriched.get('exchange'),
            'cusip': None,  # Not currently extracted
            'first_seen_date': row['first_seen_date'],
            'last_seen_date': row['last_seen_date'],
            'occurrence_count': row['occurrence_count'],
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

        enriched_records.append(record)

    return pd.DataFrame(enriched_records)


def assign_asset_keys(df: pd.DataFrame) -> pd.DataFrame:
    """Assign surrogate keys to assets."""
    # Sort by occurrence (most common first), then alphabetically
    df = df.sort_values(['occurrence_count', 'asset_name'], ascending=[False, True]).reset_index(drop=True)
    df['asset_key'] = df.index + 1
    return df


def write_to_gold(df: pd.DataFrame, bucket_name: str):
    """Write dim_assets to gold layer."""
    logger.info("Writing to gold layer...")

    # Save locally
    output_dir = Path('data/gold/dimensions/dim_assets')
    output_dir.mkdir(parents=True, exist_ok=True)

    # No partitioning for assets (relatively small table)
    output_file = output_dir / 'part-0000.parquet'
    df.to_parquet(
        output_file,
        engine='pyarrow',
        compression='snappy',
        index=False
    )
    logger.info(f"  Wrote {len(df)} records -> {output_file}")

    # Also save CSV for reference
    csv_file = output_dir / 'dim_assets.csv'
    df.to_csv(csv_file, index=False)
    logger.info(f"  CSV: {csv_file}")

    # Upload to S3
    s3 = boto3.client('s3')

    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        df.to_parquet(tmp.name, engine='pyarrow', compression='snappy', index=False)

        s3_key = 'gold/house/financial/dimensions/dim_assets/part-0000.parquet'
        s3.upload_file(tmp.name, bucket_name, s3_key)
        logger.info(f"  Uploaded to s3://{bucket_name}/{s3_key}")

        os.unlink(tmp.name)


def main():
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

    logger.info("=" * 80)
    logger.info("Building dim_assets dimension table")
    logger.info("=" * 80)

    # Initialize enrichers
    stock_enricher = StockAPIEnricher(use_cache=True)

    # Load unique assets from silver layer
    assets_df = load_unique_assets_from_silver(bucket_name)

    # Enrich with stock API
    enriched_df = enrich_assets(assets_df, stock_enricher)

    # Handle empty results
    if len(enriched_df) == 0:
        logger.warning("No assets found to process - skipping write to Gold layer")
        return

    # Assign surrogate keys
    final_df = assign_asset_keys(enriched_df)

    logger.info(f"\nEnrichment summary:")
    logger.info(f"  Total assets: {len(final_df)}")
    logger.info(f"  With ticker: {final_df['ticker_symbol'].notna().sum()}")
    logger.info(f"  With sector: {final_df['sector'].notna().sum()}")
    logger.info(f"  Publicly traded: {final_df['is_publicly_traded'].sum()}")
    logger.info(f"  Ticker extraction rate: {(final_df['ticker_symbol'].notna().sum() / len(final_df) * 100):.1f}%")
    logger.info(f"\nAsset type breakdown:")
    logger.info(final_df['asset_type'].value_counts())

    # Write to gold layer
    write_to_gold(final_df, bucket_name)

    logger.info("\n✅ dim_assets build complete!")


if __name__ == '__main__':
    main()
