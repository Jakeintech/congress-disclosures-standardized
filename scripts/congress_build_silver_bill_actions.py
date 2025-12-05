#!/usr/bin/env python3
"""
Transform Bronze Congress bill_actions to Silver dimension table.

Reads gzipped JSON files from bronze/congress/bill_actions/ and writes consolidated
Parquet files to silver/congress/bill_actions/.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import boto3
import json
import gzip
from io import BytesIO
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def extract_action_data(actions_json: dict, congress: int, bill_type: str, bill_number: int) -> list:
    """Extract relevant fields from raw bill_actions JSON.

    Args:
        actions_json: Raw JSON from Congress API
        congress: Congress number
        bill_type: Bill type (hr, s, hjres, etc.)
        bill_number: Bill number

    Returns:
        List of action dictionaries
    """
    actions = actions_json.get('actions', [])

    records = []
    for idx, action in enumerate(actions):
        bill_id = f"{congress}-{bill_type}-{bill_number}"

        record = {
            'bill_id': bill_id,
            'congress': congress,
            'bill_type': bill_type,
            'bill_number': bill_number,
            'action_date': action.get('actionDate'),
            'action_code': action.get('actionCode'),
            'action_text': action.get('text', '').strip(),
            'action_type': action.get('type'),
            'chamber': action.get('sourceSystem', {}).get('name', '').lower() if action.get('sourceSystem') else None,
            'source_system': action.get('sourceSystem', {}).get('name') if action.get('sourceSystem') else None,
            'action_sequence': idx + 1,  # Sequence number (order in API response)
        }

        # Normalize chamber
        if record['chamber']:
            if 'house' in record['chamber']:
                record['chamber'] = 'house'
            elif 'senate' in record['chamber']:
                record['chamber'] = 'senate'

        if record['action_date']:  # Only include if we have a date
            records.append(record)

    return records


def transform_bronze_to_silver():
    """Read all Bronze bill_actions and write consolidated Silver parquet."""
    s3 = boto3.client('s3')

    # Scan all bill_actions in Bronze
    prefix = 'bronze/congress/bill_actions/'
    logger.info(f"Scanning {prefix}")

    all_actions = []
    paginator = s3.get_paginator('list_objects_v2')

    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
        for obj in page.get('Contents', []):
            key = obj['Key']
            if not key.endswith('.json.gz') and not key.endswith('.json'):
                continue

            # Extract congress, bill_type, bill_number from key
            # Expected format: bronze/congress/bill_actions/congress={N}/bill_type={T}/ingest_date={D}/{number}_actions.json.gz
            parts = key.split('/')
            try:
                congress = None
                bill_type = None
                for part in parts:
                    if part.startswith('congress='):
                        congress = int(part.split('=')[1])
                    elif part.startswith('bill_type='):
                        bill_type = part.split('=')[1]

                filename = parts[-1]
                bill_number = int(filename.split('_')[0])

                if not (congress and bill_type and bill_number):
                    logger.warning(f"Could not extract metadata from key: {key}")
                    continue

            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse key {key}: {e}")
                continue

            try:
                response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
                body = response['Body'].read()

                # Decompress if gzipped
                if key.endswith('.gz'):
                    body = gzip.decompress(body)

                actions_json = json.loads(body)
                action_records = extract_action_data(actions_json, congress, bill_type, bill_number)

                all_actions.extend(action_records)

                if len(action_records) > 0:
                    logger.debug(f"Extracted {len(action_records)} actions from {key}")

            except Exception as e:
                logger.warning(f"Error processing {key}: {e}")
                continue

    if not all_actions:
        logger.warning("No actions found in Bronze layer")
        return

    logger.info(f"Extracted {len(all_actions)} action records from Bronze")

    # Convert to DataFrame
    df = pd.DataFrame(all_actions)

    # Deduplicate by bill_id + action_date + action_text (some bills have duplicate actions)
    df = df.drop_duplicates(subset=['bill_id', 'action_date', 'action_text'], keep='first')

    logger.info(f"After dedup: {len(df)} unique actions")

    # Add metadata
    df['silver_created_at'] = datetime.utcnow().isoformat()

    # Convert date strings to datetime
    if 'action_date' in df.columns:
        df['action_date'] = pd.to_datetime(df['action_date'], errors='coerce')

    # Sort by bill_id and action_date to maintain chronological order
    df = df.sort_values(['bill_id', 'action_date', 'action_sequence'])

    # Write partitioned by congress
    for congress in df['congress'].unique():
        congress_df = df[df['congress'] == congress].copy()
        if congress_df.empty:
            continue

        s3_key = f"silver/congress/bill_actions/congress={congress}/part-0000.parquet"

        buffer = BytesIO()
        congress_df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
        buffer.seek(0)

        s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
        logger.info(f"Wrote {len(congress_df)} records to s3://{BUCKET_NAME}/{s3_key}")

    logger.info(f"\n✅ Silver bill_actions transform complete! Total: {len(df)} actions")
    logger.info(f"   By congress: {df['congress'].value_counts().to_dict()}")
    if 'chamber' in df.columns:
        logger.info(f"   By chamber: {df['chamber'].value_counts().to_dict()}")


if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("Transforming Bronze Congress bill_actions to Silver")
    logger.info("=" * 80)
    transform_bronze_to_silver()
