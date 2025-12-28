#!/usr/bin/env python3
"""
Sync S3 Data to Local Directory

Downloads data from your S3 bucket to local_data/ for inspection and debugging.
This lets you examine all your pipeline data without AWS Console.

Usage:
    # Download everything
    python3 scripts/sync_s3_to_local.py

    # Download only Bronze layer
    python3 scripts/sync_s3_to_local.py --layer bronze

    # Download specific year
    python3 scripts/sync_s3_to_local.py --year 2025

    # Dry run (see what would be downloaded)
    python3 scripts/sync_s3_to_local.py --dry-run
"""

import os
import sys
import argparse
import boto3
from pathlib import Path
from datetime import datetime
import logging
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
LOCAL_DATA_DIR = Path(__file__).parent.parent / "local_data"
DEFAULT_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def download_s3_object(s3_client, bucket: str, key: str, local_path: Path, dry_run: bool = False) -> bool:
    """Download a single S3 object to local path.

    Args:
        s3_client: boto3 S3 client
        bucket: S3 bucket name
        key: S3 object key
        local_path: Local file path
        dry_run: If True, don't actually download

    Returns:
        True if successful, False otherwise
    """
    if dry_run:
        logger.info(f"[DRY RUN] Would download: s3://{bucket}/{key} -> {local_path}")
        return True

    try:
        # Create parent directory
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Download file
        s3_client.download_file(bucket, key, str(local_path))

        # Download metadata if it exists
        try:
            metadata_response = s3_client.head_object(Bucket=bucket, Key=key)
            metadata = metadata_response.get('Metadata', {})

            if metadata:
                metadata_path = local_path.parent / f"{local_path.name}.metadata.json"
                import json
                with open(metadata_path, 'w') as f:
                    json.dump({'Metadata': metadata}, f, indent=2)

        except Exception:
            pass  # Metadata is optional

        return True

    except Exception as e:
        logger.error(f"Failed to download {key}: {e}")
        return False


def sync_s3_prefix(s3_client, bucket: str, prefix: str, local_base: Path,
                   dry_run: bool = False, max_files: Optional[int] = None) -> dict:
    """Sync all files under an S3 prefix to local directory.

    Args:
        s3_client: boto3 S3 client
        bucket: S3 bucket name
        prefix: S3 prefix (folder path)
        local_base: Local base directory
        dry_run: If True, don't actually download
        max_files: Maximum files to download (None for all)

    Returns:
        Dict with statistics
    """
    stats = {
        'total_files': 0,
        'downloaded': 0,
        'skipped': 0,
        'failed': 0,
        'total_bytes': 0
    }

    logger.info(f"🔍 Scanning s3://{bucket}/{prefix}")

    try:
        paginator = s3_client.get_paginator('list_objects_v2')

        file_count = 0

        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            contents = page.get('Contents', [])

            for obj in contents:
                key = obj['Key']
                size = obj['Size']

                # Skip directories (keys ending with /)
                if key.endswith('/'):
                    continue

                stats['total_files'] += 1
                stats['total_bytes'] += size

                # Check max files limit
                if max_files and file_count >= max_files:
                    logger.info(f"⚠️  Reached max files limit ({max_files}), stopping")
                    return stats

                # Create local path
                # Remove bucket prefix if present in key
                local_key = key
                local_path = local_base / bucket / local_key

                # Skip if file already exists and has same size
                if local_path.exists() and local_path.stat().st_size == size and not dry_run:
                    stats['skipped'] += 1
                    if stats['skipped'] % 100 == 0:
                        logger.info(f"   Skipped {stats['skipped']} existing files...")
                    continue

                # Download file
                if download_s3_object(s3_client, bucket, key, local_path, dry_run):
                    stats['downloaded'] += 1
                    file_count += 1

                    if not dry_run and stats['downloaded'] % 50 == 0:
                        logger.info(f"   Downloaded {stats['downloaded']} files ({stats['total_bytes'] // (1024*1024)} MB)...")
                else:
                    stats['failed'] += 1

        return stats

    except Exception as e:
        logger.error(f"Error syncing prefix {prefix}: {e}")
        return stats


def main():
    parser = argparse.ArgumentParser(
        description="Sync S3 data to local directory"
    )
    parser.add_argument(
        '--bucket',
        default=DEFAULT_BUCKET,
        help=f'S3 bucket name (default: {DEFAULT_BUCKET})'
    )
    parser.add_argument(
        '--layer',
        choices=['bronze', 'silver', 'gold', 'all'],
        default='all',
        help='Which layer to download (default: all)'
    )
    parser.add_argument(
        '--source',
        choices=['house', 'congress', 'lobbying', 'all'],
        default='all',
        help='Which data source to download (default: all)'
    )
    parser.add_argument(
        '--year',
        type=int,
        help='Download only specific year (optional)'
    )
    parser.add_argument(
        '--prefix',
        help='Download only specific S3 prefix (e.g., bronze/house/financial/)'
    )
    parser.add_argument(
        '--max-files',
        type=int,
        help='Maximum files to download (for testing)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be downloaded without actually downloading'
    )
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Clean local_data directory before syncing'
    )

    args = parser.parse_args()

    # Banner
    print("\n" + "=" * 80)
    print("📦 S3 TO LOCAL SYNC".center(80))
    print("=" * 80)
    print(f"☁️  S3 Bucket: {args.bucket}")
    print(f"📁 Local Dir: {LOCAL_DATA_DIR.absolute()}")
    print(f"🎯 Layer: {args.layer}")
    print(f"📊 Source: {args.source}")
    if args.year:
        print(f"📅 Year: {args.year}")
    if args.dry_run:
        print(f"🔍 Mode: DRY RUN (no files will be downloaded)")
    print("=" * 80 + "\n")

    # Clean if requested
    if args.clean and not args.dry_run:
        import shutil
        logger.info(f"🧹 Cleaning local data directory...")
        if LOCAL_DATA_DIR.exists():
            shutil.rmtree(LOCAL_DATA_DIR)
        LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Cleaned\n")

    # Create S3 client
    try:
        s3_client = boto3.client('s3')
        # Test connection
        s3_client.head_bucket(Bucket=args.bucket)
        logger.info(f"✅ Connected to S3 bucket: {args.bucket}\n")
    except Exception as e:
        logger.error(f"❌ Failed to connect to S3: {e}")
        logger.error("   Make sure your AWS credentials are configured")
        return 1

    # Determine prefixes to sync
    prefixes = []

    if args.prefix:
        # Custom prefix
        prefixes.append(args.prefix)
    else:
        # Build prefixes based on layer and source
        layers = ['bronze', 'silver', 'gold'] if args.layer == 'all' else [args.layer]
        sources = ['house', 'congress', 'lobbying'] if args.source == 'all' else [args.source]

        for layer in layers:
            for source in sources:
                if source == 'house':
                    prefix = f"{layer}/house/financial/"
                elif source == 'congress':
                    prefix = f"{layer}/congress/"
                elif source == 'lobbying':
                    prefix = f"{layer}/lobbying/"

                # Add year filter if specified
                if args.year and layer == 'bronze':
                    prefix += f"year={args.year}/"

                prefixes.append(prefix)

    # Sync each prefix
    total_stats = {
        'total_files': 0,
        'downloaded': 0,
        'skipped': 0,
        'failed': 0,
        'total_bytes': 0
    }

    for prefix in prefixes:
        logger.info(f"\n📦 Syncing: {prefix}")
        stats = sync_s3_prefix(
            s3_client,
            args.bucket,
            prefix,
            LOCAL_DATA_DIR,
            dry_run=args.dry_run,
            max_files=args.max_files
        )

        # Aggregate stats
        for key in total_stats:
            total_stats[key] += stats[key]

        logger.info(f"   ✅ {prefix}: {stats['downloaded']} downloaded, {stats['skipped']} skipped")

    # Print summary
    print("\n" + "=" * 80)
    print("📊 SYNC SUMMARY".center(80))
    print("=" * 80)
    print(f"Total files scanned: {total_stats['total_files']}")
    print(f"Files downloaded: {total_stats['downloaded']}")
    print(f"Files skipped (already exist): {total_stats['skipped']}")
    print(f"Files failed: {total_stats['failed']}")
    print(f"Total size: {total_stats['total_bytes'] // (1024*1024)} MB")
    print("=" * 80)

    if not args.dry_run:
        print(f"\n✅ Sync complete!")
        print(f"📁 Data saved to: {LOCAL_DATA_DIR / args.bucket}")
        print(f"\nNext steps:")
        print(f"   1. View data: make local-view")
        print(f"   2. Browse data: make local-serve")
        print(f"   3. Inspect files: ls -lah local_data/{args.bucket}/bronze/")
    else:
        print(f"\n🔍 Dry run complete! Run without --dry-run to download.")

    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
