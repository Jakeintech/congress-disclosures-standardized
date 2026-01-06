"""SCD Type 2 CDC handler for Congress member history tracking.

Implements Slowly Changing Dimension Type 2 logic for tracking historical
changes to member attributes (party, state, district).

Example:
    from backend.lib.ingestion.congress_cdc_handler import apply_scd_type2

    result = apply_scd_type2(
        bucket="congress-disclosures-standardized",
        s3_key="silver/congress/dim_member/chamber=house/is_current=true/part-0000.parquet",
        new_member_df=df,
        pk_column="bioguide_id",
        tracked_columns=["party", "state", "district"]
    )
"""

import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from .s3_utils import s3_object_exists
from .parquet_writer import read_parquet_from_s3, write_parquet_to_s3

logger = logging.getLogger(__name__)


def apply_scd_type2(
    bucket: str,
    s3_key: str,
    new_records: List[Dict[str, Any]],
    pk_column: str = "bioguide_id",
    tracked_columns: Optional[List[str]] = None,
    sk_column: str = "member_sk",
) -> Dict[str, Any]:
    """Apply SCD Type 2 logic to member records.

    Compares new records to existing history and:
    - Creates new records for new members (effective_date=today, is_current=True)
    - Closes old records if tracked columns changed (end_date=today, is_current=False)
    - Inserts new version for changed records (effective_date=today, is_current=True)
    - Skips unchanged records

    Args:
        bucket: S3 bucket name
        s3_key: S3 key for Silver member Parquet (is_current=true partition)
        new_records: New member records from Bronze
        pk_column: Natural key column (default: bioguide_id)
        tracked_columns: Columns to track for changes (default: party, state, district)
        sk_column: Surrogate key column name (default: member_sk)

    Returns:
        Dict with SCD2 update statistics:
        - inserted: Count of new members
        - updated: Count of changed members (2 records: old closed + new inserted)
        - skipped: Count of unchanged members
        - final_count: Total records in final table
    """
    if tracked_columns is None:
        tracked_columns = ["party", "state", "district"]

    if not new_records:
        logger.warning("No records provided for SCD Type 2 processing")
        return {"inserted": 0, "updated": 0, "skipped": 0, "final_count": 0}

    today = date.today()
    now = datetime.now(timezone.utc).isoformat()

    # Load existing history
    existing_records = []
    existing_current = {}  # pk -> current record

    if s3_object_exists(bucket, s3_key):
        existing_records = read_parquet_from_s3(bucket, s3_key)
        # Build index of current records by PK
        for rec in existing_records:
            if rec.get("is_current", False):
                pk = rec.get(pk_column)
                if pk:
                    existing_current[pk] = rec

    logger.info(f"Loaded {len(existing_records)} existing records ({len(existing_current)} current)")

    # Track statistics
    stats = {"inserted": 0, "updated": 0, "skipped": 0}
    output_records = list(existing_records)  # Start with all existing

    for new_rec in new_records:
        pk = new_rec.get(pk_column)
        if not pk:
            logger.warning(f"Record missing PK column {pk_column}: {new_rec}")
            continue

        if pk in existing_current:
            # Check if tracked columns changed
            old_rec = existing_current[pk]
            changed = False

            for col in tracked_columns:
                old_val = old_rec.get(col)
                new_val = new_rec.get(col)
                # Normalize for comparison
                if old_val != new_val:
                    logger.info(f"{pk_column}={pk}: {col} changed from '{old_val}' to '{new_val}'")
                    changed = True
                    break

            if changed:
                # Close old record
                for i, rec in enumerate(output_records):
                    if rec.get(pk_column) == pk and rec.get("is_current", False):
                        output_records[i]["end_date"] = str(today)
                        output_records[i]["is_current"] = False
                        break

                # Insert new version
                new_version = _create_scd_record(
                    new_rec, sk_column, pk_column, today, now
                )
                output_records.append(new_version)
                stats["updated"] += 1

            else:
                # No change - skip
                stats["skipped"] += 1

        else:
            # New member - insert
            new_version = _create_scd_record(
                new_rec, sk_column, pk_column, today, now
            )
            output_records.append(new_version)
            stats["inserted"] += 1

    # Write back to S3
    if output_records:
        write_parquet_to_s3(
            records=output_records,
            bucket=bucket,
            s3_key=s3_key,
        )

    stats["final_count"] = len(output_records)
    logger.info(f"SCD Type 2 complete: {stats}")

    return stats


def _create_scd_record(
    source_record: Dict[str, Any],
    sk_column: str,
    pk_column: str,
    effective_date: date,
    ingest_ts: str,
) -> Dict[str, Any]:
    """Create a new SCD Type 2 record with surrogate key and effective dates.

    Args:
        source_record: Source record to copy
        sk_column: Surrogate key column name
        pk_column: Natural key column name
        effective_date: Effective date for this version
        ingest_ts: Silver ingestion timestamp

    Returns:
        New record with SCD2 columns populated
    """
    record = dict(source_record)

    # Generate surrogate key
    record[sk_column] = str(uuid.uuid4())

    # Set SCD2 dates
    record["effective_date"] = str(effective_date)
    record["end_date"] = None
    record["is_current"] = True
    record["silver_ingest_ts"] = ingest_ts

    return record


def get_current_members(bucket: str, base_path: str = "silver/congress/dim_member") -> pd.DataFrame:
    """Load all current member records across chambers.

    Args:
        bucket: S3 bucket name
        base_path: Base Silver path for dim_member

    Returns:
        DataFrame with all current member records
    """
    all_records = []

    for chamber in ["house", "senate"]:
        s3_key = f"{base_path}/chamber={chamber}/is_current=true/part-0000.parquet"
        if s3_object_exists(bucket, s3_key):
            records = read_parquet_from_s3(bucket, s3_key)
            all_records.extend(records)

    return pd.DataFrame(all_records)
