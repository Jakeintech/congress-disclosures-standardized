"""Lambda handler for ingesting Senate LDA (Lobbying Disclosure Act) filings.

This Lambda:
1. Fetches from lda.senate.gov/api/v1/filings/?filing_year=YYYY
2. Paginates through all results (API returns 100/page)
3. Writes raw JSON to bronze/lobbying/filings/year=YYYY/filing_uuid={uuid}.json.gz
4. Queues SQS jobs for bill extraction (parse descriptions for bill references)
"""

import gzip
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
import requests
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Environment variables
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")
S3_BRONZE_PREFIX = os.environ.get("S3_BRONZE_PREFIX", "bronze")
SQS_QUEUE_URL = os.environ.get("LDA_EXTRACTION_QUEUE_URL")

# AWS clients
s3_client = boto3.client("s3")
sqs_client = boto3.client("sqs")

# LDA API base URL
LDA_API_BASE_URL = "https://lda.senate.gov/api/v1"


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler.

    Args:
        event: Lambda event with parameters
        context: Lambda context

    Returns:
        Dict with status and stats

    Example event:
        {
            "filing_year": 2024,
            "filing_type": "FILING",  # or "CONTRIBUTION"
            "skip_existing": false
        }
    """
    try:
        # Extract parameters from event
        filing_year = event.get("filing_year")
        if not filing_year:
            raise ValueError("Missing required parameter: filing_year")

        filing_year = int(filing_year)
        filing_type = event.get("filing_type", "FILING")  # FILING or CONTRIBUTION
        skip_existing = event.get("skip_existing", False)

        logger.info(
            f"Starting LDA {filing_type} ingestion for year {filing_year}"
        )

        if filing_type == "FILING":
            result = ingest_filings(filing_year, skip_existing)
        elif filing_type == "CONTRIBUTION":
            result = ingest_contributions(filing_year, skip_existing)
        else:
            raise ValueError(f"Invalid filing_type: {filing_type}")

        result["status"] = "success"
        result["filing_year"] = filing_year
        result["filing_type"] = filing_type
        result["timestamp"] = datetime.now(timezone.utc).isoformat()

        logger.info(f"Ingestion complete: {result}")
        return result

    except Exception as e:
        logger.error(f"Error in lambda_handler: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def ingest_filings(filing_year: int, skip_existing: bool) -> Dict[str, Any]:
    """Ingest LDA filings for a given year.

    Args:
        filing_year: Year to ingest (e.g., 2024)
        skip_existing: If True, skip filings that already exist in S3

    Returns:
        Dict with ingestion statistics
    """
    url = f"{LDA_API_BASE_URL}/filings/"
    params = {"filing_year": filing_year}

    filings_ingested = 0
    filings_skipped = 0
    pages_processed = 0
    sqs_messages_sent = 0

    while url:
        logger.info(f"Fetching page {pages_processed + 1}: {url}")

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            logger.info(f"Processing {len(results)} filings from page {pages_processed + 1}")

            for filing in results:
                filing_uuid = filing.get("filing_uuid")
                if not filing_uuid:
                    logger.warning("Skipping filing without filing_uuid")
                    continue

                # Check if filing already exists
                s3_key = (
                    f"{S3_BRONZE_PREFIX}/lobbying/filings/"
                    f"year={filing_year}/filing_uuid={filing_uuid}.json.gz"
                )

                if skip_existing and check_s3_object_exists(s3_key):
                    logger.debug(f"Skipping existing filing: {filing_uuid}")
                    filings_skipped += 1
                    continue

                # Upload filing to S3
                upload_filing_to_s3(filing, s3_key, filing_year)
                filings_ingested += 1

                # Queue for bill extraction if there are lobbying activities
                if filing.get("lobbying_activities"):
                    queue_bill_extraction(filing_uuid, filing_year)
                    sqs_messages_sent += 1

            pages_processed += 1

            # Get next page URL
            url = data.get("next")
            if url:
                params = {}  # Next URL already contains query params
                time.sleep(0.1)  # Rate limiting

        except requests.RequestException as e:
            logger.error(f"Error fetching filings: {e}")
            raise

    return {
        "filings_ingested": filings_ingested,
        "filings_skipped": filings_skipped,
        "pages_processed": pages_processed,
        "sqs_messages_sent": sqs_messages_sent,
    }


def ingest_contributions(filing_year: int, skip_existing: bool) -> Dict[str, Any]:
    """Ingest LDA contributions (LD-203) for a given year.

    Args:
        filing_year: Year to ingest (e.g., 2024)
        skip_existing: If True, skip contributions that already exist in S3

    Returns:
        Dict with ingestion statistics
    """
    url = f"{LDA_API_BASE_URL}/contributions/"
    params = {"filing_year": filing_year}

    contributions_ingested = 0
    contributions_skipped = 0
    pages_processed = 0

    while url:
        logger.info(f"Fetching contributions page {pages_processed + 1}: {url}")

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            logger.info(
                f"Processing {len(results)} contributions from page {pages_processed + 1}"
            )

            for contribution in results:
                contribution_id = contribution.get("id")
                if not contribution_id:
                    logger.warning("Skipping contribution without id")
                    continue

                # Check if contribution already exists
                s3_key = (
                    f"{S3_BRONZE_PREFIX}/lobbying/contributions/"
                    f"year={filing_year}/contribution_id={contribution_id}.json.gz"
                )

                if skip_existing and check_s3_object_exists(s3_key):
                    logger.debug(f"Skipping existing contribution: {contribution_id}")
                    contributions_skipped += 1
                    continue

                # Upload contribution to S3
                upload_contribution_to_s3(contribution, s3_key, filing_year)
                contributions_ingested += 1

            pages_processed += 1

            # Get next page URL
            url = data.get("next")
            if url:
                params = {}  # Next URL already contains query params
                time.sleep(0.1)  # Rate limiting

        except requests.RequestException as e:
            logger.error(f"Error fetching contributions: {e}")
            raise

    return {
        "contributions_ingested": contributions_ingested,
        "contributions_skipped": contributions_skipped,
        "pages_processed": pages_processed,
    }


def upload_filing_to_s3(filing: Dict[str, Any], s3_key: str, filing_year: int) -> None:
    """Upload filing JSON to S3 with gzip compression.

    Args:
        filing: Filing data dict
        s3_key: S3 key to upload to
        filing_year: Filing year for metadata
    """
    try:
        # Compress JSON
        json_bytes = json.dumps(filing, indent=2).encode("utf-8")
        compressed = gzip.compress(json_bytes)

        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=compressed,
            ContentType="application/json",
            ContentEncoding="gzip",
            Metadata={
                "filing-year": str(filing_year),
                "filing-uuid": filing.get("filing_uuid", ""),
                "ingestion-timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.debug(f"Uploaded filing to s3://{S3_BUCKET}/{s3_key}")

    except ClientError as e:
        logger.error(f"Error uploading filing to S3: {e}")
        raise


def upload_contribution_to_s3(
    contribution: Dict[str, Any], s3_key: str, filing_year: int
) -> None:
    """Upload contribution JSON to S3 with gzip compression.

    Args:
        contribution: Contribution data dict
        s3_key: S3 key to upload to
        filing_year: Filing year for metadata
    """
    try:
        # Compress JSON
        json_bytes = json.dumps(contribution, indent=2).encode("utf-8")
        compressed = gzip.compress(json_bytes)

        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=compressed,
            ContentType="application/json",
            ContentEncoding="gzip",
            Metadata={
                "filing-year": str(filing_year),
                "contribution-id": str(contribution.get("id", "")),
                "ingestion-timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.debug(f"Uploaded contribution to s3://{S3_BUCKET}/{s3_key}")

    except ClientError as e:
        logger.error(f"Error uploading contribution to S3: {e}")
        raise


def check_s3_object_exists(s3_key: str) -> bool:
    """Check if an S3 object exists.

    Args:
        s3_key: S3 key to check

    Returns:
        True if object exists, False otherwise
    """
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise


def queue_bill_extraction(filing_uuid: str, filing_year: int) -> None:
    """Queue a filing for bill reference extraction.

    Args:
        filing_uuid: UUID of the filing
        filing_year: Year of the filing
    """
    if not SQS_QUEUE_URL:
        logger.warning("SQS_QUEUE_URL not set, skipping queue operation")
        return

    try:
        message = {
            "filing_uuid": filing_uuid,
            "filing_year": filing_year,
            "extraction_type": "bill_references",
        }

        sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message),
            MessageAttributes={
                "filing_uuid": {"StringValue": filing_uuid, "DataType": "String"},
                "filing_year": {"StringValue": str(filing_year), "DataType": "Number"},
            },
        )

        logger.debug(f"Queued bill extraction for filing {filing_uuid}")

    except ClientError as e:
        logger.error(f"Error sending SQS message: {e}")
        # Don't raise - extraction can be run separately
