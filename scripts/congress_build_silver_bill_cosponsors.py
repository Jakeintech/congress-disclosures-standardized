#!/usr/bin/env python3
"""
Transform Bronze Congress bill_cosponsors to Silver dimension table.

Reads gzipped JSON files from bronze/congress/bill_cosponsors/ and writes consolidated
Parquet files to silver/congress/bill_cosponsors/.
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


def extract_cosponsor_data(cosponsors_json: dict, congress: int, bill_type: str, bill_number: int) -> list:
    """Extract relevant fields from raw bill_cosponsors JSON.

    Args:
        cosponsors_json: Raw JSON from Congress API
        congress: Congress number
        bill_type: Bill type (hr, s, hjres, etc.)
        bill_number: Bill number

    Returns:
        List of cosponsor dictionaries
    """
    cosponsors = cosponsors_json.get('cosponsors', [])

    records = []
    for cosponsor in cosponsors:
        bill_id = f"{congress}-{bill_type}-{bill_number}"

        record = {
            'bill_id': bill_id,
            'congress': congress,
            'bill_type': bill_type,
            'bill_number': bill_number,
            'bioguide_id': cosponsor.get('bioguideId'),
            'full_name': cosponsor.get('fullName'),
            'sponsorship_date': cosponsor.get('sponsorshipDate'),
            'is_original_cosponsor': cosponsor.get('isOriginalCosponsor', False),
            'state': cosponsor.get('state'),
            'district': cosponsor.get('district'),
            'party': cosponsor.get('party'),
        }

        if record['bioguide_id']:  # Only include if we have a bioguide ID
            records.append(record)

    return records


def transform_bronze_to_silver():
    """Read all Bronze bill_cosponsors and write consolidated Silver parquet."""
    s3 = boto3.client('s3')

    # Scan all bill_cosponsors in Bronze
    prefix = 'bronze/congress/bill_cosponsors/'
    logger.info(f"Scanning {prefix}")

    all_cosponsors = []
    paginator = s3.get_paginator('list_objects_v2')

    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
        for obj in page.get('Contents', []):
            key = obj['Key']
            if not key.endswith('.json.gz') and not key.endswith('.json'):
                continue

            # Extract congress, bill_type, bill_number from key
            # Expected format: bronze/congress/bill_cosponsors/congress={N}/bill_type={T}/ingest_date={D}/{number}_cosponsors.json.gz
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

                cosponsors_json = json.loads(body)
                cosponsor_records = extract_cosponsor_data(cosponsors_json, congress, bill_type, bill_number)

                all_cosponsors.extend(cosponsor_records)

                if len(cosponsor_records) > 0:
                    logger.debug(f"Extracted {len(cosponsor_records)} cosponsors from {key}")

            except Exception as e:
                logger.warning(f"Error processing {key}: {e}")
                continue

    if not all_cosponsors:
        logger.warning("No cosponsors found in Bronze layer")
        return

    logger.info(f"Extracted {len(all_cosponsors)} cosponsor records from Bronze")

    # Convert to DataFrame
    df = pd.DataFrame(all_cosponsors)

    # Deduplicate by bill_id + bioguide_id (keep latest)
    df = df.drop_duplicates(subset=['bill_id', 'bioguide_id'], keep='last')

    logger.info(f"After dedup: {len(df)} unique cosponsor relationships")

    # Add metadata
    df['silver_created_at'] = datetime.utcnow().isoformat()

    # Convert date strings to datetime
    if 'sponsorship_date' in df.columns:
        df['sponsorship_date'] = pd.to_datetime(df['sponsorship_date'], errors='coerce')

    # Write partitioned by congress
    for congress in df['congress'].unique():
        congress_df = df[df['congress'] == congress].copy()
        if congress_df.empty:
            continue

        s3_key = f"silver/congress/bill_cosponsors/congress={congress}/part-0000.parquet"

        buffer = BytesIO()
        congress_df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
        buffer.seek(0)

        s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
        logger.info(f"Wrote {len(congress_df)} records to s3://{BUCKET_NAME}/{s3_key}")

    logger.info(f"\n✅ Silver bill_cosponsors transform complete! Total: {len(df)} relationships")
    logger.info(f"   By congress: {df['congress'].value_counts().to_dict()}")
    logger.info(f"   Original cosponsors: {df['is_original_cosponsor'].sum()}")


if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("Transforming Bronze Congress bill_cosponsors to Silver")
    logger.info("=" * 80)
    transform_bronze_to_silver()
