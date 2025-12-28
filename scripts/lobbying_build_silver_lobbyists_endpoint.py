#!/usr/bin/env python3
"""Build Silver lobbying lobbyists table from endpoint Bronze.

Reads lobbyist items stored under bronze/lobbying/lobbyists/ and writes a year-partitioned Parquet.
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("S3_BUCKET_NAME", "congress-disclosures-standardized")
S3_BRONZE_PREFIX = os.environ.get("S3_BRONZE_PREFIX", "bronze")
S3_SILVER_PREFIX = os.environ.get("S3_SILVER_PREFIX", "silver")


def read_lobbyists_endpoint(s3_client: boto3.client) -> pd.DataFrame:
    prefix = f"{S3_BRONZE_PREFIX}/lobbying/lobbyists/"
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
                lob = json.loads(data)
                lid = lob.get("id")
                if lid is None:
                    continue
                rows.append({
                    "lobbyist_id": lid,
                    "prefix": lob.get("prefix"),
                    "first_name": lob.get("first_name"),
                    "middle_name": lob.get("middle_name"),
                    "last_name": lob.get("last_name"),
                    "suffix": lob.get("suffix"),
                    "has_covered_position": lob.get("has_covered_position"),
                    "covered_offices": lob.get("covered_offices"),
                    "dt_updated": datetime.utcnow().isoformat(),
                })
                total += 1
            except Exception as e:
                logger.warning(f"Failed to read {key}: {e}")
    logger.info(f"Read {total} lobbyists from endpoint Bronze")
    return pd.DataFrame(rows)


def write_silver(df: pd.DataFrame, year: int) -> None:
    if df.empty:
        logger.warning("No lobbyists to write")
        return
    s3_key = f"{S3_SILVER_PREFIX}/lobbying/lobbyists/year={year}/lobbyists.parquet"
    table = pa.Table.from_pandas(df)
    with pa.BufferOutputStream() as out:
        pq.write_table(table, out, compression="snappy")
        buf = out.getvalue()
        boto3.client("s3").put_object(Bucket=S3_BUCKET, Key=s3_key, Body=buf.to_pybytes(), ContentType="application/x-parquet")
    logger.info(f"Wrote {len(df)} lobbyists to s3://{S3_BUCKET}/{s3_key}")


def main():
    ap = argparse.ArgumentParser(description="Build Silver lobbyists from endpoint Bronze")
    ap.add_argument("--year", type=int, required=True)
    args = ap.parse_args()
    s3 = boto3.client("s3")
    df = read_lobbyists_endpoint(s3)
    write_silver(df, args.year)


if __name__ == "__main__":
    main()

