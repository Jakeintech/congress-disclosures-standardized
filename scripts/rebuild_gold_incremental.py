#!/usr/bin/env python3
"""
Incremental gold layer rebuild automation.

This script intelligently rebuilds only the gold layer tables that need updating
based on changes in the silver layer.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import boto3
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_s3_last_modified(bucket: str, prefix: str) -> datetime:
    """Get the last modified timestamp for objects in a prefix."""
    s3 = boto3.client('s3')

    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1000)

        if 'Contents' not in response:
            return datetime.min

        timestamps = [obj['LastModified'] for obj in response['Contents']]
        return max(timestamps) if timestamps else datetime.min
    except Exception as e:
        logger.warning(f"Could not get timestamp for {prefix}: {e}")
        return datetime.min


def should_rebuild_fact_filings(bucket: str) -> bool:
    """Check if fact_filings needs rebuilding."""
    silver_filings_ts = get_s3_last_modified(bucket, 'silver/house/financial/filings/')
    silver_docs_ts = get_s3_last_modified(bucket, 'silver/house/financial/documents/')
    gold_fact_ts = get_s3_last_modified(bucket, 'gold/house/financial/facts/fact_filings/')

    # Rebuild if silver is newer than gold
    needs_rebuild = max(silver_filings_ts, silver_docs_ts) > gold_fact_ts

    if needs_rebuild:
        logger.info(f"fact_filings needs rebuild:")
        logger.info(f"  Silver filings: {silver_filings_ts}")
        logger.info(f"  Silver documents: {silver_docs_ts}")
        logger.info(f"  Gold fact_filings: {gold_fact_ts}")

    return needs_rebuild


def should_rebuild_agg_document_quality(bucket: str) -> bool:
    """Check if agg_document_quality needs rebuilding."""
    gold_fact_ts = get_s3_last_modified(bucket, 'gold/house/financial/facts/fact_filings/')
    gold_agg_ts = get_s3_last_modified(bucket, 'gold/house/financial/aggregates/agg_document_quality/')

    needs_rebuild = gold_fact_ts > gold_agg_ts

    if needs_rebuild:
        logger.info(f"agg_document_quality needs rebuild:")
        logger.info(f"  Gold fact_filings: {gold_fact_ts}")
        logger.info(f"  Gold agg: {gold_agg_ts}")

    return needs_rebuild


def should_rebuild_manifest(bucket: str) -> bool:
    """Check if website manifest needs rebuilding."""
    gold_agg_ts = get_s3_last_modified(bucket, 'gold/house/financial/aggregates/agg_document_quality/')
    manifest_ts = get_s3_last_modified(bucket, 'website/data/document_quality.json')

    needs_rebuild = gold_agg_ts > manifest_ts

    if needs_rebuild:
        logger.info(f"Website manifest needs rebuild:")
        logger.info(f"  Gold agg: {gold_agg_ts}")
        logger.info(f"  Manifest: {manifest_ts}")

    return needs_rebuild


def rebuild_fact_filings():
    """Rebuild fact_filings table."""
    logger.info("Rebuilding fact_filings...")
    import subprocess
    result = subprocess.run([sys.executable, 'scripts/build_fact_filings.py'],
                          capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"fact_filings rebuild failed:\n{result.stderr}")
        return False
    logger.info("✅ fact_filings rebuilt")
    return True


def rebuild_agg_document_quality():
    """Rebuild agg_document_quality table."""
    logger.info("Rebuilding agg_document_quality...")
    import subprocess
    result = subprocess.run([sys.executable, 'scripts/compute_agg_document_quality.py'],
                          capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"agg_document_quality rebuild failed:\n{result.stderr}")
        return False
    logger.info("✅ agg_document_quality rebuilt")
    return True


def rebuild_manifest():
    """Rebuild website manifest."""
    logger.info("Rebuilding website manifest...")
    import subprocess
    result = subprocess.run([sys.executable, 'scripts/generate_document_quality_manifest.py'],
                          capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Manifest rebuild failed:\n{result.stderr}")
        return False
    logger.info("✅ Website manifest rebuilt")
    return True


def main():
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

    logger.info("=" * 80)
    logger.info("Incremental Gold Layer Rebuild")
    logger.info("=" * 80)

    rebuild_count = 0

    # Check and rebuild fact_filings
    if should_rebuild_fact_filings(bucket_name):
        if rebuild_fact_filings():
            rebuild_count += 1
    else:
        logger.info("fact_filings is up-to-date, skipping")

    # Check and rebuild aggregates
    if should_rebuild_agg_document_quality(bucket_name):
        if rebuild_agg_document_quality():
            rebuild_count += 1
    else:
        logger.info("agg_document_quality is up-to-date, skipping")

    # Check and rebuild manifest
    if should_rebuild_manifest(bucket_name):
        if rebuild_manifest():
            rebuild_count += 1
    else:
        logger.info("Website manifest is up-to-date, skipping")

    logger.info(f"\n✅ Incremental rebuild complete: {rebuild_count} tables updated")


if __name__ == '__main__':
    main()
