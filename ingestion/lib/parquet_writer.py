"""Parquet writing utilities for silver layer tables."""

import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
import pyarrow.parquet as pq
from jsonschema import validate, ValidationError

from .s3_utils import upload_bytes_to_s3, download_bytes_from_s3, s3_object_exists

logger = logging.getLogger(__name__)


def clean_nan_values(record: Dict[str, Any]) -> Dict[str, Any]:
    """Convert NaN values and empty strings to None for JSON schema compatibility.

    Args:
        record: Record dict that may contain NaN values or empty strings

    Returns:
        Cleaned record with NaN/empty string -> None for nullable fields
    """
    import math

    # Fields that should be None instead of empty string
    nullable_string_fields = {
        'pdf_sha256', 'text_s3_key', 'json_s3_key',
        'extraction_error', 'filing_date', 'last_name', 'first_name'
    }

    cleaned = {}
    for key, value in record.items():
        # Handle NaN floats
        if isinstance(value, float) and math.isnan(value):
            cleaned[key] = None
        # Handle empty strings that should be None
        elif key in nullable_string_fields and value == "":
            cleaned[key] = None
        # Recurse into dicts
        elif isinstance(value, dict):
            cleaned[key] = clean_nan_values(value)
        # Recurse into lists
        elif isinstance(value, list):
            cleaned[key] = [
                clean_nan_values(item) if isinstance(item, dict)
                else None if (isinstance(item, float) and math.isnan(item))
                else None if (isinstance(item, str) and item == "" and key in nullable_string_fields)
                else item
                for item in value
            ]
        else:
            cleaned[key] = value
    return cleaned


def validate_record(record: Dict[str, Any], schema: Optional[Dict] = None) -> bool:
    """Validate a record against JSON schema.

    Args:
        record: Record dict to validate
        schema: JSON schema (optional)

    Returns:
        True if valid

    Raises:
        ValidationError: If validation fails
    """
    if schema is None:
        return True

    try:
        # Clean NaN values before validation (NaN is not valid JSON)
        cleaned_record = clean_nan_values(record)
        validate(instance=cleaned_record, schema=schema)
        return True
    except ValidationError as e:
        logger.error(f"Record validation failed: {e.message}")
        raise


def write_parquet_to_s3(
    records: List[Dict[str, Any]],
    bucket: str,
    s3_key: str,
    schema: Optional[Dict] = None,
    partition_cols: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Write records to Parquet file in S3.

    Args:
        records: List of record dicts
        bucket: S3 bucket name
        s3_key: S3 key for Parquet file
        schema: Optional JSON schema for validation
        partition_cols: Optional columns to partition by (not used for single file write)

    Returns:
        Dict with write details (s3_key, row_count, file_size)

    Raises:
        ValidationError: If any record fails validation
        Exception: If write fails
    """
    if not records:
        raise ValueError("No records to write")

    # Validate all records if schema provided
    if schema:
        for i, record in enumerate(records):
            try:
                validate_record(record, schema)
            except ValidationError as e:
                logger.error(f"Record {i} validation failed: {e}")
                raise

    try:
        # Convert to pandas DataFrame
        df = pd.DataFrame(records)

        # Write to Parquet in memory
        buffer = io.BytesIO()
        df.to_parquet(
            buffer,
            engine="pyarrow",
            compression="snappy",  # Good balance of speed and compression
            index=False,
        )

        parquet_bytes = buffer.getvalue()

        # Upload to S3
        logger.info(
            f"Writing {len(records)} records "
            f"({len(parquet_bytes)} bytes) to {s3_key}"
        )

        result = upload_bytes_to_s3(
            data=parquet_bytes,
            bucket=bucket,
            s3_key=s3_key,
            metadata={
                "row_count": str(len(records)),
                "columns": ",".join(df.columns.tolist()),
                "write_timestamp": datetime.now(timezone.utc).isoformat(),
            },
            content_type="application/octet-stream",
        )

        result["row_count"] = len(records)
        result["columns"] = df.columns.tolist()

        logger.info(f"Successfully wrote {len(records)} records to {s3_key}")

        return result

    except Exception as e:
        logger.error(f"Failed to write Parquet to S3: {e}")
        raise


def read_parquet_from_s3(bucket: str, s3_key: str) -> List[Dict[str, Any]]:
    """Read Parquet file from S3 as list of dicts.

    Args:
        bucket: S3 bucket name
        s3_key: S3 key of Parquet file

    Returns:
        List of record dicts

    Raises:
        Exception: If read fails
    """
    try:
        logger.info(f"Reading Parquet from s3://{bucket}/{s3_key}")

        parquet_bytes = download_bytes_from_s3(bucket, s3_key)

        # Read Parquet from bytes
        buffer = io.BytesIO(parquet_bytes)
        df = pd.read_parquet(buffer, engine="pyarrow")

        records = df.to_dict("records")

        logger.info(f"Read {len(records)} records from {s3_key}")

        return records

    except Exception as e:
        logger.error(f"Failed to read Parquet from S3: {e}")
        raise


def upsert_parquet_records(
    new_records: List[Dict[str, Any]],
    bucket: str,
    s3_key: str,
    key_columns: List[str],
    schema: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Upsert records into existing Parquet file.

    Reads existing file (if exists), merges with new records based on key columns,
    and writes back.

    Args:
        new_records: New records to upsert
        bucket: S3 bucket name
        s3_key: S3 key of Parquet file
        key_columns: Columns that form the primary key
        schema: Optional JSON schema for validation

    Returns:
        Dict with upsert details

    Raises:
        ValidationError: If validation fails
        Exception: If upsert fails
    """
    if not new_records:
        raise ValueError("No records to upsert")

    if not key_columns:
        raise ValueError("Must specify key_columns for upsert")

    try:
        # Read existing records if file exists
        existing_records = []
        if s3_object_exists(bucket, s3_key):
            logger.info(f"Reading existing records from {s3_key}")
            existing_records = read_parquet_from_s3(bucket, s3_key)

        # Convert to DataFrames
        existing_df = (
            pd.DataFrame(existing_records) if existing_records else pd.DataFrame()
        )
        new_df = pd.DataFrame(new_records)

        # Perform upsert (merge with 'right' to keep new records)
        if not existing_df.empty:
            # Drop duplicates from new_df based on key columns (keep last)
            new_df = new_df.drop_duplicates(subset=key_columns, keep="last")

            # Merge: keep all new records, update existing
            merged_df = pd.concat([existing_df, new_df]).drop_duplicates(
                subset=key_columns, keep="last"
            )
        else:
            merged_df = new_df

        # Fill NaN values for required fields with schema defaults
        # This handles old records that don't have new required fields
        if "requires_additional_ocr" in merged_df.columns:
            merged_df["requires_additional_ocr"] = merged_df["requires_additional_ocr"].fillna(False)
        if "extraction_month" in merged_df.columns:
            # For old records without extraction_month, use current month (project just started)
            from datetime import date
            current_month = date.today().strftime("%Y-%m")
            merged_df["extraction_month"] = merged_df["extraction_month"].fillna(current_month)

        # Convert back to records
        merged_records = merged_df.to_dict("records")

        # Write back to S3
        result = write_parquet_to_s3(
            records=merged_records,
            bucket=bucket,
            s3_key=s3_key,
            schema=schema,
        )

        result["upsert_stats"] = {
            "existing_count": len(existing_records),
            "new_count": len(new_records),
            "final_count": len(merged_records),
            "updated_count": len(
                new_records
            ),  # Simplified - could track actual updates
        }

        logger.info(
            f"Upsert complete: {len(existing_records)} existing + "
            f"{len(new_records)} new = {len(merged_records)} final"
        )

        return result

    except Exception as e:
        logger.error(f"Failed to upsert Parquet records: {e}")
        raise


def append_parquet_records(
    new_records: List[Dict[str, Any]],
    bucket: str,
    s3_key: str,
    schema: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Append records to existing Parquet file.

    Args:
        new_records: New records to append
        bucket: S3 bucket name
        s3_key: S3 key of Parquet file
        schema: Optional JSON schema for validation

    Returns:
        Dict with append details

    Raises:
        Exception: If append fails
    """
    if not new_records:
        raise ValueError("No records to append")

    try:
        # Read existing records if file exists
        existing_records = []
        if s3_object_exists(bucket, s3_key):
            logger.info(f"Reading existing records from {s3_key}")
            existing_records = read_parquet_from_s3(bucket, s3_key)

        # Combine records
        all_records = existing_records + new_records

        # Write back
        result = write_parquet_to_s3(
            records=all_records,
            bucket=bucket,
            s3_key=s3_key,
            schema=schema,
        )

        result["append_stats"] = {
            "existing_count": len(existing_records),
            "appended_count": len(new_records),
            "final_count": len(all_records),
        }

        logger.info(
            f"Append complete: {len(existing_records)} existing + "
            f"{len(new_records)} appended = {len(all_records)} final"
        )

        return result

    except Exception as e:
        logger.error(f"Failed to append Parquet records: {e}")
        raise


def create_partitioned_path(
    base_path: str,
    partition_values: Dict[str, Any],
    filename: str = "part-0000.parquet",
) -> str:
    """Create partitioned S3 path.

    Args:
        base_path: Base S3 path (e.g., 'silver/house/financial/filings')
        partition_values: Dict of partition column names to values
        filename: Parquet filename

    Returns:
        Full partitioned S3 path

    Example:
        >>> create_partitioned_path(
        ...     'silver/house/financial/filings',
        ...     {'year': 2025, 'month': 5},
        ...     'part-0000.parquet'
        ... )
        'silver/house/financial/filings/year=2025/month=5/part-0000.parquet'
    """
    # Build partition path components
    partition_parts = [f"{k}={v}" for k, v in sorted(partition_values.items())]

    # Combine all parts
    parts = [base_path] + partition_parts + [filename]

    # Join with forward slashes
    return "/".join(parts)


def get_parquet_stats(bucket: str, s3_key: str) -> Dict[str, Any]:
    """Get statistics about a Parquet file without loading all data.

    Args:
        bucket: S3 bucket name
        s3_key: S3 key of Parquet file

    Returns:
        Dict with stats (row_count, columns, file_size, etc.)

    Raises:
        Exception: If stats retrieval fails
    """
    try:
        logger.info(f"Getting Parquet stats for s3://{bucket}/{s3_key}")

        parquet_bytes = download_bytes_from_s3(bucket, s3_key)
        buffer = io.BytesIO(parquet_bytes)

        # Read Parquet metadata
        parquet_file = pq.ParquetFile(buffer)

        metadata = parquet_file.metadata
        schema = parquet_file.schema_arrow

        stats = {
            "s3_key": s3_key,
            "bucket": bucket,
            "file_size_bytes": len(parquet_bytes),
            "row_count": metadata.num_rows,
            "num_row_groups": metadata.num_row_groups,
            "columns": [field.name for field in schema],
            "column_types": {field.name: str(field.type) for field in schema},
            "compression": metadata.row_group(0).column(0).compression
            if metadata.num_row_groups > 0
            else None,
        }

        logger.info(
            f"Parquet stats: {stats['row_count']} rows, {len(stats['columns'])} columns"
        )

        return stats

    except Exception as e:
        logger.error(f"Failed to get Parquet stats: {e}")
        raise


def normalize_datetime_fields(
    records: List[Dict[str, Any]], datetime_fields: List[str]
) -> List[Dict[str, Any]]:
    """Normalize datetime fields to ISO format strings.

    Args:
        records: List of record dicts
        datetime_fields: List of field names that should be datetime

    Returns:
        Records with normalized datetime fields
    """
    normalized_records = []

    for record in records:
        normalized = record.copy()

        for field in datetime_fields:
            if field in normalized and normalized[field] is not None:
                value = normalized[field]

                # Convert to datetime if not already
                if isinstance(value, str):
                    # Already a string, ensure ISO format
                    try:
                        dt = pd.to_datetime(value)
                        normalized[field] = dt.isoformat()
                    except Exception:
                        logger.warning(f"Could not parse datetime: {value}")

                elif isinstance(value, (datetime, pd.Timestamp)):
                    normalized[field] = value.isoformat()

        normalized_records.append(normalized)

    return normalized_records
