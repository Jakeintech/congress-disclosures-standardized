"""Lambda handler for Bronze to Silver transformation.

Triggered by SQS messages from congress-silver-queue.
Transforms Bronze JSON to normalized Silver Parquet.

Message format:
{
    "entity_type": "member|bill|committee|house_vote|senate_vote",
    "bronze_s3_key": "bronze/congress/member/chamber=house/..."
}
"""

import gzip
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import boto3

# Import shared libraries
from lib.s3_utils import download_bytes_from_s3, s3_object_exists
from lib.parquet_writer import upsert_parquet_records
from lib.congress_schema_mappers import (
    map_member_to_silver,
    map_bill_to_silver,
    map_committee_to_silver,
    map_vote_to_silver,
    get_silver_table_path,
)
from lib.congress_cdc_handler import apply_scd_type2

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Environment variables
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for Bronze to Silver transformation.

    Args:
        event: SQS event with Records array
        context: Lambda context

    Returns:
        Dict with batchItemFailures for partial batch errors
    """
    start_time = datetime.now(timezone.utc)
    batch_item_failures = []
    processed_count = 0
    error_count = 0

    records = event.get("Records", [])
    logger.info(f"Processing {len(records)} SQS messages")

    for record in records:
        message_id = record.get("messageId", "unknown")

        try:
            body = json.loads(record.get("body", "{}"))
            entity_type = body.get("entity_type")
            bronze_s3_key = body.get("bronze_s3_key")

            if not entity_type or not bronze_s3_key:
                logger.error(f"Message {message_id}: Missing entity_type or bronze_s3_key")
                batch_item_failures.append({"itemIdentifier": message_id})
                error_count += 1
                continue

            logger.info(f"Processing {entity_type}: {bronze_s3_key}")

            # Process based on entity type
            result = process_entity(entity_type, bronze_s3_key)

            if result.get("error"):
                logger.error(f"Message {message_id}: {result['error']}")
                batch_item_failures.append({"itemIdentifier": message_id})
                error_count += 1
            else:
                processed_count += 1
                logger.info(f"Message {message_id}: Processed {result.get('records_written', 0)} records")

        except Exception as e:
            logger.error(f"Message {message_id}: Unexpected error: {e}", exc_info=True)
            batch_item_failures.append({"itemIdentifier": message_id})
            error_count += 1

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info(
        f"Batch complete: {processed_count} processed, {error_count} errors, "
        f"{duration:.2f}s"
    )

    return {"batchItemFailures": batch_item_failures}


def process_entity(entity_type: str, bronze_s3_key: str) -> Dict[str, Any]:
    """Process a single Bronze entity to Silver.

    Args:
        entity_type: Entity type (member, bill, committee, etc.)
        bronze_s3_key: S3 key for Bronze JSON

    Returns:
        Dict with processing result
    """
    try:
        # Download and decompress Bronze JSON
        if not s3_object_exists(S3_BUCKET, bronze_s3_key):
            return {"error": f"Bronze file not found: {bronze_s3_key}"}

        bronze_bytes = download_bytes_from_s3(S3_BUCKET, bronze_s3_key)

        # Decompress if gzipped
        if bronze_s3_key.endswith(".gz"):
            bronze_bytes = gzip.decompress(bronze_bytes)

        bronze_json = json.loads(bronze_bytes)

        # Route to appropriate handler
        if entity_type == "member":
            return process_member(bronze_json, bronze_s3_key)
        elif entity_type == "bill":
            return process_bill(bronze_json, bronze_s3_key)
        elif entity_type == "committee":
            return process_committee(bronze_json, bronze_s3_key)
        elif entity_type in ("house_vote", "senate_vote"):
            return process_vote(bronze_json, bronze_s3_key, entity_type)
        else:
            return {"error": f"Unsupported entity type: {entity_type}"}

    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}"}
    except Exception as e:
        return {"error": f"Processing failed: {e}"}


def process_member(bronze_json: Dict[str, Any], bronze_s3_key: str) -> Dict[str, Any]:
    """Process member Bronze JSON to Silver with SCD Type 2.

    Args:
        bronze_json: Raw API response
        bronze_s3_key: Source S3 key

    Returns:
        Processing result
    """
    # Map to Silver schema
    silver_record = map_member_to_silver(bronze_json)

    if not silver_record or not silver_record.get("bioguide_id"):
        return {"error": "Failed to map member to Silver schema"}

    chamber = silver_record.get("chamber", "unknown")

    # Get Silver path for current records partition
    silver_key = get_silver_table_path(
        "member",
        chamber=chamber,
        is_current="true"
    )

    # Apply SCD Type 2
    result = apply_scd_type2(
        bucket=S3_BUCKET,
        s3_key=silver_key,
        new_records=[silver_record],
        pk_column="bioguide_id",
        tracked_columns=["party", "state", "district"],
    )

    return {
        "entity_type": "member",
        "bioguide_id": silver_record["bioguide_id"],
        "records_written": result.get("inserted", 0) + result.get("updated", 0),
        "scd_stats": result,
    }


def process_bill(bronze_json: Dict[str, Any], bronze_s3_key: str) -> Dict[str, Any]:
    """Process bill Bronze JSON to Silver.

    Args:
        bronze_json: Raw API response
        bronze_s3_key: Source S3 key

    Returns:
        Processing result
    """
    # Map to Silver schema
    silver_record = map_bill_to_silver(bronze_json)

    if not silver_record or not silver_record.get("bill_id"):
        return {"error": "Failed to map bill to Silver schema"}

    congress = silver_record.get("congress", 0)
    bill_type = silver_record.get("bill_type", "unknown")

    # Get Silver path
    silver_key = get_silver_table_path(
        "bill",
        congress=congress,
        bill_type=bill_type
    )

    # Add ingestion timestamp
    silver_record["silver_ingest_ts"] = datetime.now(timezone.utc).isoformat()

    # Upsert to Silver
    result = upsert_parquet_records(
        new_records=[silver_record],
        bucket=S3_BUCKET,
        s3_key=silver_key,
        key_columns=["bill_id"],
    )

    return {
        "entity_type": "bill",
        "bill_id": silver_record["bill_id"],
        "records_written": 1,
        "upsert_stats": result.get("upsert_stats"),
    }


def process_committee(bronze_json: Dict[str, Any], bronze_s3_key: str) -> Dict[str, Any]:
    """Process committee Bronze JSON to Silver.

    Args:
        bronze_json: Raw API response
        bronze_s3_key: Source S3 key

    Returns:
        Processing result
    """
    # Map to Silver schema
    silver_record = map_committee_to_silver(bronze_json)

    if not silver_record or not silver_record.get("committee_code"):
        return {"error": "Failed to map committee to Silver schema"}

    chamber = silver_record.get("chamber", "unknown")

    # Get Silver path
    silver_key = get_silver_table_path("committee", chamber=chamber)

    # Add ingestion timestamp
    silver_record["silver_ingest_ts"] = datetime.now(timezone.utc).isoformat()

    # Upsert to Silver
    result = upsert_parquet_records(
        new_records=[silver_record],
        bucket=S3_BUCKET,
        s3_key=silver_key,
        key_columns=["committee_code"],
    )

    return {
        "entity_type": "committee",
        "committee_code": silver_record["committee_code"],
        "records_written": 1,
        "upsert_stats": result.get("upsert_stats"),
    }


def process_vote(bronze_json: Dict[str, Any], bronze_s3_key: str, entity_type: str) -> Dict[str, Any]:
    """Process vote Bronze JSON to Silver.

    Args:
        bronze_json: Raw API response
        bronze_s3_key: Source S3 key
        entity_type: house_vote or senate_vote

    Returns:
        Processing result
    """
    # Map to Silver schema (returns list of per-member vote records)
    silver_records = map_vote_to_silver(bronze_json)

    if not silver_records:
        return {"error": "Failed to map vote to Silver schema"}

    # Get partition values from first record
    first = silver_records[0]
    congress = first.get("congress", 0)
    session = first.get("session", 1)

    # Get Silver path
    silver_key = get_silver_table_path(
        entity_type,
        congress=congress,
        session=session
    )

    # Upsert to Silver
    result = upsert_parquet_records(
        new_records=silver_records,
        bucket=S3_BUCKET,
        s3_key=silver_key,
        key_columns=["vote_id", "bioguide_id"],
    )

    return {
        "entity_type": entity_type,
        "vote_id": first.get("vote_id"),
        "records_written": len(silver_records),
        "upsert_stats": result.get("upsert_stats"),
    }
