#!/usr/bin/env python3
"""
Trigger ingestion of bill subresources (cosponsors, actions, committees, etc.) from Congress.gov API.

This script:
1. Reads all bills from Bronze layer
2. Queues subresource fetch jobs to SQS for each bill
3. Allows filtering by congress number

Usage:
    python3 scripts/trigger_bill_subresource_ingestion.py --congress 118
    python3 scripts/trigger_bill_subresource_ingestion.py --congress 119 --limit 10  # Test mode
"""

import argparse
import boto3
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
CONGRESS_FETCH_QUEUE_URL = os.environ.get('CONGRESS_FETCH_QUEUE_URL')


def get_bills_from_bronze(congress: int, limit: int = None) -> list:
    """Scan Bronze layer for bills in a congress.

    Args:
        congress: Congress number to scan
        limit: Optional limit on number of bills to process

    Returns:
        List of (congress, bill_type, bill_number) tuples
    """
    s3 = boto3.client('s3')
    prefix = f'bronze/congress/bill/congress={congress}/'

    logger.info(f"Scanning Bronze bills in congress {congress}...")

    bills = []
    paginator = s3.get_paginator('list_objects_v2')

    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
        for obj in page.get('Contents', []):
            key = obj['Key']
            if not (key.endswith('.json.gz') or key.endswith('.json')):
                continue

            # Extract bill_type and bill_number from key
            # Format: bronze/congress/bill/congress=118/bill_type=hr/ingest_date=2025-12-04/118-hr-1096.json.gz
            parts = key.split('/')
            try:
                bill_type = None
                for part in parts:
                    if part.startswith('bill_type='):
                        bill_type = part.split('=')[1]
                        break

                filename = parts[-1].replace('.json.gz', '').replace('.json', '')
                # Filename format: {congress}-{bill_type}-{bill_number}
                file_parts = filename.split('-')
                if len(file_parts) >= 3:
                    bill_number = int(file_parts[2])
                    bills.append((congress, bill_type, bill_number))

            except (ValueError, IndexError) as e:
                logger.debug(f"Could not parse {key}: {e}")
                continue

            if limit and len(bills) >= limit:
                break

        if limit and len(bills) >= limit:
            break

    logger.info(f"Found {len(bills)} bills in congress {congress}")
    return bills


def queue_subresource_jobs(bills: list) -> int:
    """Queue subresource fetch jobs for bills.

    Args:
        bills: List of (congress, bill_type, bill_number) tuples

    Returns:
        Number of messages queued
    """
    if not CONGRESS_FETCH_QUEUE_URL:
        logger.error("CONGRESS_FETCH_QUEUE_URL environment variable not set")
        logger.error("Please set it to your SQS queue URL for congress API fetching")
        return 0

    sqs = boto3.client('sqs')

    subresources = [
        'bill_actions',
        'bill_cosponsors',
        'bill_committees',
        'bill_subjects',
    ]

    total_queued = 0

    # Process in batches of 10 (SQS limit)
    for i in range(0, len(bills), 10):
        batch_bills = bills[i:i+10]
        messages = []

        for congress, bill_type, bill_number in batch_bills:
            for subresource in subresources:
                message = {
                    'entity_type': subresource,
                    'entity_id': str(bill_number),
                    'congress': congress,
                    'bill_type': bill_type,
                    'bill_number': bill_number,
                    'endpoint': f"/bill/{congress}/{bill_type}/{bill_number}/{subresource.replace('bill_', '')}",
                }
                messages.append({
                    'Id': f"{subresource}-{congress}-{bill_type}-{bill_number}",
                    'MessageBody': json.dumps(message),
                })

                if len(messages) >= 10:
                    try:
                        sqs.send_message_batch(
                            QueueUrl=CONGRESS_FETCH_QUEUE_URL,
                            Entries=messages,
                        )
                        total_queued += len(messages)
                        logger.info(f"Queued batch of {len(messages)} subresource jobs (total: {total_queued})")
                        messages = []
                    except Exception as e:
                        logger.error(f"Failed to queue batch: {e}")

        # Send remaining messages
        if messages:
            try:
                sqs.send_message_batch(
                    QueueUrl=CONGRESS_FETCH_QUEUE_URL,
                    Entries=messages,
                )
                total_queued += len(messages)
                logger.info(f"Queued final batch of {len(messages)} jobs (total: {total_queued})")
            except Exception as e:
                logger.error(f"Failed to queue final batch: {e}")

    return total_queued


def main():
    parser = argparse.ArgumentParser(
        description='Trigger bill subresource ingestion from Congress.gov API'
    )
    parser.add_argument(
        '--congress',
        type=int,
        required=True,
        help='Congress number to process (e.g., 118, 119)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of bills to process (for testing)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Count bills but do not queue jobs'
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info(f"Triggering bill subresource ingestion for Congress {args.congress}")
    if args.limit:
        logger.info(f"  Limit: {args.limit} bills (test mode)")
    if args.dry_run:
        logger.info("  Mode: DRY RUN (no jobs will be queued)")
    logger.info("=" * 80)

    # Get bills from Bronze
    bills = get_bills_from_bronze(args.congress, args.limit)

    if not bills:
        logger.warning(f"No bills found in Bronze for congress {args.congress}")
        logger.info("Have you ingested bills yet? Run: python3 scripts/ingest_congress_bills.py")
        return

    logger.info(f"\nFound {len(bills)} bills to process")
    logger.info(f"Will queue {len(bills) * 4} subresource jobs (4 per bill)")

    if args.dry_run:
        logger.info("\nDry run complete - no jobs queued")
        return

    # Queue subresource jobs
    total_queued = queue_subresource_jobs(bills)

    logger.info("=" * 80)
    logger.info(f"✅ Queued {total_queued} subresource fetch jobs")
    logger.info(f"   Bills processed: {len(bills)}")
    logger.info(f"   Subresources per bill: 4 (actions, cosponsors, committees, subjects)")
    logger.info("=" * 80)
    logger.info("\nNext steps:")
    logger.info("  1. Monitor Lambda logs: make logs-congress-fetch")
    logger.info("  2. Check SQS queue: aws sqs get-queue-attributes --queue-url $CONGRESS_FETCH_QUEUE_URL")
    logger.info("  3. Once ingested, build Silver layer: make build-congress-silver-bills")
    logger.info("  4. Build Gold layer: make build-congress-gold")


if __name__ == '__main__':
    main()
