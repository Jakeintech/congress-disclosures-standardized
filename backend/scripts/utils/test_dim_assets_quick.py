#!/usr/bin/env python3
"""
Quick test of dim_assets with first 100 assets only.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import boto3
import json
import logging
from datetime import datetime
from collections import Counter

from ingestion.lib.enrichment import StockAPIEnricher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_sample_assets(bucket_name: str, limit: int = 100) -> pd.DataFrame:
    """Load first N unique assets from silver extraction JSON data."""
    s3 = boto3.client('s3')

    logger.info(f"Loading first {limit} assets from silver objects layer...")

    assets = []
    asset_occurrences = Counter()
    paginator = s3.get_paginator('list_objects_v2')

    prefix = 'silver/house/financial/objects/'
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    for page in pages:
        if 'Contents' not in page:
            continue

        for obj in page['Contents']:
            if not obj['Key'].endswith('extraction.json'):
                continue

            try:
                response = s3.get_object(Bucket=bucket_name, Key=obj['Key'])
                data = json.loads(response['Body'].read().decode('utf-8'))

                transactions = data.get('transactions', [])
                schedule_a = data.get('schedule_a', [])

                for txn in transactions:
                    asset_name = txn.get('asset_name', '').strip()
                    if asset_name:
                        asset_occurrences[asset_name] += 1
                        assets.append(asset_name)

                for holding in schedule_a:
                    asset_name = holding.get('asset_name', '').strip()
                    if asset_name:
                        asset_occurrences[asset_name] += 1
                        assets.append(asset_name)

                # Stop if we have enough unique assets
                if len(set(assets)) >= limit:
                    break

            except Exception as e:
                logger.warning(f"Error processing {obj['Key']}: {e}")
                continue

        if len(set(assets)) >= limit:
            break

    logger.info(f"Loaded {len(assets):,} total asset transactions")

    unique_assets = pd.DataFrame({
        'asset_name': list(set(assets))[:limit]
    })

    unique_assets['occurrence_count'] = unique_assets['asset_name'].map(asset_occurrences)
    unique_assets['first_seen_date'] = datetime.now().strftime('%Y-%m-%d')
    unique_assets['last_seen_date'] = datetime.now().strftime('%Y-%m-%d')

    logger.info(f"Returning {len(unique_assets)} unique assets for testing")
    return unique_assets


def main():
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

    logger.info("=" * 80)
    logger.info("QUICK TEST: Building dim_assets with first 100 assets")
    logger.info("=" * 80)

    # Initialize enricher
    stock_enricher = StockAPIEnricher(use_cache=True)

    # Load sample assets
    assets_df = load_sample_assets(bucket_name, limit=100)

    # Track metrics
    enrichment_stats = {
        'total': 0,
        'ticker_extracted': 0,
        'api_success': 0,
        'api_failed': 0,
        'ticker_not_found': 0,
        'non_stock_asset': 0,
        'ownership_indicators': Counter(),
        'blacklist_hits': []
    }

    logger.info(f"\nProcessing {len(assets_df)} assets...")

    for idx, row in assets_df.iterrows():
        asset_name = row['asset_name']
        enrichment_stats['total'] += 1

        if idx % 10 == 0:
            logger.info(f"  [{idx+1}/{len(assets_df)}] Processing...")

        # Show first few examples in detail
        if idx < 5:
            logger.info(f"\n  Example {idx+1}: '{asset_name[:80]}'")

        # Classify and enrich
        asset_type = stock_enricher.classify_asset_type(asset_name)

        if asset_type in ['Stock', 'ETF', 'Mutual Fund']:
            enriched = stock_enricher.enrich_asset(asset_name)

            # Show detailed results for first few
            if idx < 5:
                logger.info(f"    Asset type: {asset_type}")
                logger.info(f"    Cleaned name: '{enriched.get('cleaned_asset_name', '')[:60]}'")
                logger.info(f"    Ownership: {enriched.get('ownership_indicator')}")
                logger.info(f"    Ticker: {enriched.get('ticker_symbol')}")
                logger.info(f"    Status: {enriched.get('enrichment_status')}")

            # Track stats
            status = enriched.get('enrichment_status', 'unknown')
            if status == 'success':
                enrichment_stats['api_success'] += 1
            elif status == 'api_failed':
                enrichment_stats['api_failed'] += 1
            elif status == 'ticker_not_found':
                enrichment_stats['ticker_not_found'] += 1

            if enriched.get('ticker_symbol'):
                enrichment_stats['ticker_extracted'] += 1

            if enriched.get('ownership_indicator'):
                enrichment_stats['ownership_indicators'][enriched['ownership_indicator']] += 1
        else:
            enrichment_stats['non_stock_asset'] += 1

    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("QUICK TEST RESULTS")
    logger.info("=" * 80)
    logger.info(f"Total assets processed: {enrichment_stats['total']:,}")
    logger.info(f"  Ticker extracted: {enrichment_stats['ticker_extracted']:,} ({enrichment_stats['ticker_extracted']/enrichment_stats['total']*100:.1f}%)")
    logger.info(f"  API enrichment success: {enrichment_stats['api_success']:,} ({enrichment_stats['api_success']/enrichment_stats['total']*100:.1f}%)")
    logger.info(f"  API enrichment failed: {enrichment_stats['api_failed']:,}")
    logger.info(f"  Ticker not found: {enrichment_stats['ticker_not_found']:,}")
    logger.info(f"  Non-stock assets: {enrichment_stats['non_stock_asset']:,}")

    logger.info(f"\nOwnership indicators found:")
    if enrichment_stats['ownership_indicators']:
        for indicator, count in enrichment_stats['ownership_indicators'].most_common():
            logger.info(f"  {indicator}: {count:,}")
    else:
        logger.info("  None found")

    logger.info("=" * 80)
    logger.info("\n✅ Quick test complete!")


if __name__ == '__main__':
    main()
