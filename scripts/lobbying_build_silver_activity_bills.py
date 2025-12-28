#!/usr/bin/env python3
"""Build Silver lobbying activity_bills table from Bronze LDA data.

Uses NLP extraction to identify bill references in lobbying descriptions.
This is the bridge between lobbying data and bills data.
"""

import argparse
import gzip
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.lib.bill_reference_extractor import extract_bill_references_from_filing
from ingestion.lib.bill_reference_extractor_enhanced import extract_bill_references_from_filing_enhanced

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("S3_BUCKET_NAME", "congress-disclosures-standardized")
S3_BRONZE_PREFIX = os.environ.get("S3_BRONZE_PREFIX", "bronze")
S3_SILVER_PREFIX = os.environ.get("S3_SILVER_PREFIX", "silver")


def list_bronze_filings(s3_client: boto3.client, year: int) -> List[str]:
    """List all filing JSON files in Bronze for a given year."""
    prefix = f"{S3_BRONZE_PREFIX}/lobbying/filings/year={year}/"
    logger.info(f"Listing Bronze filings from s3://{S3_BUCKET}/{prefix}")

    filings = []
    paginator = s3_client.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".json.gz"):
                filings.append(key)

    logger.info(f"Found {len(filings)} filing files")
    return filings


def extract_bill_references(s3_client: boto3.client, year: int, use_enhanced: bool = True) -> pd.DataFrame:
    """Extract bill references from all activity descriptions.

    Args:
        s3_client: Boto3 S3 client
        year: Filing year
        use_enhanced: Use enhanced extractor with fuzzy matching (default: True)
    """
    filing_keys = list_bronze_filings(s3_client, year)

    if not filing_keys:
        logger.warning(f"No filings found for year {year}")
        return pd.DataFrame()

    all_references = []
    filings_with_bills = 0

    extraction_method = "enhanced" if use_enhanced else "basic"
    logger.info(f"Using {extraction_method} bill reference extractor")

    for idx, key in enumerate(filing_keys, 1):
        if idx % 100 == 0:
            logger.info(f"Processing filing {idx}/{len(filing_keys)}")

        try:
            obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
            compressed_data = obj["Body"].read()
            json_data = gzip.decompress(compressed_data)
            filing_data = json.loads(json_data)

            filing_year = filing_data.get("filing_year")
            filing_uuid = filing_data.get("filing_uuid")

            # Extract bill references using NLP
            if use_enhanced:
                references = extract_bill_references_from_filing_enhanced(
                    filing_data,
                    filing_year,
                    s3_bucket=S3_BUCKET,
                    use_fuzzy=True
                )
            else:
                references = extract_bill_references_from_filing(filing_data, filing_year)

            if references:
                filings_with_bills += 1
                for ref in references:
                    ref["filing_uuid"] = filing_uuid
                    ref["filing_year"] = filing_year
                    ref["dt_extracted"] = datetime.utcnow().isoformat()
                    all_references.append(ref)

        except Exception as e:
            logger.error(f"Error processing {key}: {e}")
            continue

    df = pd.DataFrame(all_references)
    logger.info(
        f"Extracted {len(df)} bill references from {filings_with_bills} filings "
        f"({filings_with_bills/len(filing_keys)*100:.1f}% of filings mention bills)"
    )
    return df


def write_silver_table(df: pd.DataFrame, year: int) -> None:
    """Write DataFrame to Silver Parquet table."""
    if df.empty:
        logger.warning("No data to write")
        return

    s3_key = f"{S3_SILVER_PREFIX}/lobbying/activity_bills/year={year}/activity_bills.parquet"
    logger.info(f"Writing Silver table to s3://{S3_BUCKET}/{s3_key}")

    table = pa.Table.from_pandas(df)

    with pa.BufferOutputStream() as out_stream:
        pq.write_table(table, out_stream, compression="snappy")
        buffer = out_stream.getvalue()

        s3_client = boto3.client("s3")
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=buffer.to_pybytes(),
            ContentType="application/x-parquet",
        )

    logger.info(f"Wrote {len(df)} bill reference records to {s3_key}")


def main():
    parser = argparse.ArgumentParser(description="Build Silver lobbying activity_bills table")
    parser.add_argument("--year", type=int, required=True, help="Filing year")
    parser.add_argument("--enhanced", action="store_true", default=True,
                        help="Use enhanced extractor with fuzzy matching (default: True)")
    parser.add_argument("--basic", dest="enhanced", action="store_false",
                        help="Use basic regex-only extractor")
    args = parser.parse_args()

    logger.info(f"Building Silver activity_bills table for year {args.year}")

    s3_client = boto3.client("s3")
    df = extract_bill_references(s3_client, args.year, use_enhanced=args.enhanced)

    if df.empty:
        logger.warning("No bill references extracted")
        # Don't exit with error - some years might have no bill references
    else:
        write_silver_table(df, args.year)

        logger.info(f"\n{'='*60}")
        logger.info("SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total bill references: {len(df)}")
        logger.info(f"Unique bills: {df['bill_id'].nunique()}")
        logger.info(f"Average confidence: {df['confidence'].mean():.2f}")
        logger.info(f"High confidence (>0.9): {(df['confidence'] > 0.9).sum()}")
        logger.info(f"\nTop bills mentioned:")
        for bill_id, count in df['bill_id'].value_counts().head(10).items():
            logger.info(f"  {bill_id}: {count} mentions")


if __name__ == "__main__":
    main()
