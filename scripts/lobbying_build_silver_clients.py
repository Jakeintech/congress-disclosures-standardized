#!/usr/bin/env python3
"""Build Silver lobbying clients dimension table from Bronze LDA data.

Extracts and normalizes client (organizations hiring lobbyists) data.
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


def extract_clients(s3_client: boto3.client, year: int) -> pd.DataFrame:
    """Extract unique clients from all filings."""
    filing_keys = list_bronze_filings(s3_client, year)

    if not filing_keys:
        logger.warning(f"No filings found for year {year}")
        return pd.DataFrame()

    clients_dict = {}

    for idx, key in enumerate(filing_keys, 1):
        if idx % 100 == 0:
            logger.info(f"Processing filing {idx}/{len(filing_keys)}")

        try:
            obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
            compressed_data = obj["Body"].read()
            json_data = gzip.decompress(compressed_data)
            filing_data = json.loads(json_data)

            client = filing_data.get("client", {})
            if not client or not client.get("id"):
                continue

            client_id = client["id"]

            if client_id not in clients_dict:
                clients_dict[client_id] = {
                    "client_id": client_id,
                    "name": client.get("name"),
                    "description": client.get("description"),
                    "status": client.get("status"),
                    "status_display": client.get("status_display"),
                    "state": client.get("state"),
                    "state_display": client.get("state_display"),
                    "country": client.get("country"),
                    "country_display": client.get("country_display"),
                    "ppb_state": client.get("ppb_state"),
                    "ppb_country": client.get("ppb_country"),
                    "contact_name": client.get("contact_name"),
                    "senate_id": client.get("senate_id"),
                    "dt_updated": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            logger.error(f"Error processing {key}: {e}")
            continue

    df = pd.DataFrame(list(clients_dict.values()))
    logger.info(f"Extracted {len(df)} unique clients")
    return df


def read_endpoint_clients(s3_client: boto3.client) -> pd.DataFrame:
    """Read clients directly from Bronze endpoint dir, if present."""
    prefix = f"{S3_BRONZE_PREFIX}/lobbying/clients/"
    rows: List[Dict[str, Any]] = []
    total = 0
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj.get("Key", "")
            if not key.endswith(".json.gz"):
                continue
            try:
                o = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
                data = gzip.decompress(o["Body"].read())
                cli = json.loads(data)
                cid = cli.get("id")
                if cid is None:
                    continue
                rows.append({
                    "client_id": cid,
                    "name": cli.get("name"),
                    "status": cli.get("status"),
                    "status_display": cli.get("status_display"),
                    "address": cli.get("address"),
                    "address_2": cli.get("address_2"),
                    "city": cli.get("city"),
                    "state": cli.get("state"),
                    "state_display": cli.get("state_display"),
                    "zip": cli.get("zip"),
                    "country": cli.get("country"),
                    "country_display": cli.get("country_display"),
                    "ppb_state": cli.get("ppb_state"),
                    "ppb_country": cli.get("ppb_country"),
                    "contact_name": cli.get("contact_name"),
                    "senate_id": cli.get("senate_id"),
                    "dt_updated": datetime.utcnow().isoformat(),
                })
                total += 1
            except Exception as e:
                logger.warning(f"Failed to read {key}: {e}")
    if total:
        logger.info(f"Read {total} clients from endpoint Bronze")
    return pd.DataFrame(rows)


def write_silver_table(df: pd.DataFrame) -> None:
    """Write DataFrame to Silver Parquet table."""
    if df.empty:
        logger.warning("No data to write")
        return

    s3_key = f"{S3_SILVER_PREFIX}/lobbying/clients/clients.parquet"
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

    logger.info(f"Wrote {len(df)} clients to {s3_key}")


def main():
    parser = argparse.ArgumentParser(description="Build Silver lobbying clients table")
    parser.add_argument("--year", type=int, required=True, help="Filing year")
    args = parser.parse_args()

    logger.info(f"Building Silver clients table for year {args.year}")

    s3_client = boto3.client("s3")
    df = extract_clients(s3_client, args.year)
    ep = read_endpoint_clients(s3_client)
    if not ep.empty:
        if df.empty:
            df = ep
        else:
            df = df.merge(ep, on="client_id", how="outer", suffixes=("", "_ep"))
            for col in [
                "name","status","status_display","address","address_2","city","state","state_display","zip","country","country_display","ppb_state","ppb_country","contact_name","senate_id"
            ]:
                epcol = f"{col}_ep"
                if epcol in df.columns:
                    df[col] = df[epcol].where(df[epcol].notna(), df[col])
            df = df[[c for c in df.columns if not c.endswith("_ep")]]
    if df.empty:
        logger.error("No clients extracted (neither from filings nor endpoint)")
        sys.exit(1)

    write_silver_table(df)

    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total clients: {len(df)}")
    logger.info(f"By status: {df['status_display'].value_counts().to_dict()}")
    logger.info(f"Top states: {df['state'].value_counts().head(10).to_dict()}")


if __name__ == "__main__":
    main()
