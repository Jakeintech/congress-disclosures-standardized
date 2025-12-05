"""Lambda handler for fetching entities from Congress.gov API.

This Lambda (triggered by SQS):
1. Receives SQS message with entity type and ID
2. Fetches entity from Congress.gov API using CongressAPIClient
3. Compresses response as gzip JSON
4. Uploads to Bronze S3 with metadata
5. Optionally queues subresource fetch jobs (for bills)

Supports multiple API keys for 5x parallel throughput.
"""

import gzip
import json
import logging
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import boto3
from botocore.exceptions import ClientError

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import shared libraries
from lib.congress_api_client import (  # noqa: E402
    CongressAPIClient,
    CongressAPIError,
    CongressAPIRateLimitError,
    CongressAPINotFoundError,
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Environment variables
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")
CONGRESS_API_BASE_URL = os.environ.get("CONGRESS_API_BASE_URL")
INGEST_VERSION = os.environ.get("EXTRACTION_VERSION", "1.0.0")
CONGRESS_SILVER_QUEUE_URL = os.environ.get("CONGRESS_SILVER_QUEUE_URL")
CONGRESS_FETCH_QUEUE_URL = os.environ.get("CONGRESS_FETCH_QUEUE_URL")
CONGRESS_API_KEY_SSM_PATH = os.environ.get(
    "CONGRESS_API_KEY_SSM_PATH",
    "/congress-disclosures-standardized/development/congress-api-key"
)

# Initialize clients
s3_client = boto3.client("s3")
sqs_client = boto3.client("sqs")
ssm_client = boto3.client("ssm")

# Global cache for API keys (loaded once per Lambda cold start)
_API_KEYS: List[str] = []


def load_api_keys() -> List[str]:
    """Load all Congress API keys from SSM Parameter Store.
    
    Returns list of API keys for rotation.
    """
    global _API_KEYS
    
    if _API_KEYS:
        return _API_KEYS
    
    # Try to load keys 1-5
    base_path = CONGRESS_API_KEY_SSM_PATH.rstrip("-key")
    keys = []
    
    # Load primary key
    try:
        response = ssm_client.get_parameter(
            Name=CONGRESS_API_KEY_SSM_PATH,
            WithDecryption=True
        )
        keys.append(response["Parameter"]["Value"])
        logger.info("Loaded primary API key")
    except Exception as e:
        logger.error(f"Failed to load primary API key: {e}")
    
    # Load additional keys (2-5)
    for i in range(2, 6):
        try:
            response = ssm_client.get_parameter(
                Name=f"{base_path}-key-{i}",
                WithDecryption=True
            )
            keys.append(response["Parameter"]["Value"])
            logger.info(f"Loaded API key {i}")
        except ssm_client.exceptions.ParameterNotFound:
            pass  # Key doesn't exist, skip
        except Exception as e:
            logger.warning(f"Failed to load API key {i}: {e}")
    
    _API_KEYS = keys
    logger.info(f"Loaded {len(_API_KEYS)} API keys for rotation")
    return _API_KEYS


def get_random_api_key() -> str:
    """Get a random API key for load balancing across rate limits."""
    keys = load_api_keys()
    if not keys:
        raise ValueError("No API keys available")
    return random.choice(keys)



def get_bronze_s3_key(entity_type: str, entity_id: str, ingest_date: str, **kwargs) -> str:
    """Generate Bronze S3 key for an entity.

    Args:
        entity_type: Entity type (member, bill, house_vote, etc.)
        entity_id: Entity ID (bioguide_id, bill_number, vote_number, etc.)
        ingest_date: Ingest date (YYYY-MM-DD format)
        **kwargs: Additional partition keys (congress, bill_type, chamber, session, etc.)

    Returns:
        S3 key following Hive partitioning pattern

    Example:
        >>> get_bronze_s3_key("member", "A000360", "2025-12-04", chamber="house")
        'bronze/congress/member/chamber=house/ingest_date=2025-12-04/A000360.json.gz'
    """
    # Base prefix
    prefix = f"bronze/congress/{entity_type}"

    # Add entity-specific partitions
    if entity_type == "member":
        chamber = kwargs.get("chamber", "unknown")
        prefix += f"/chamber={chamber}"
    elif entity_type in ["bill", "bill_actions", "bill_cosponsors", "bill_committees",
                          "bill_subjects", "bill_titles", "bill_summaries", "bill_related_bills"]:
        congress = kwargs.get("congress")
        bill_type = kwargs.get("bill_type")
        if congress and bill_type:
            prefix += f"/congress={congress}/bill_type={bill_type}"
    elif entity_type in ["house_vote", "senate_vote"]:
        congress = kwargs.get("congress")
        session = kwargs.get("session")
        if congress and session:
            prefix += f"/congress={congress}/session={session}"
    elif entity_type == "committee":
        chamber = kwargs.get("chamber", "unknown")
        prefix += f"/chamber={chamber}"

    # Add ingest_date partition
    prefix += f"/ingest_date={ingest_date}"

    # Add filename (entity_id with suffix for bill subresources)
    if entity_type.startswith("bill_") and entity_type != "bill":
        # Bill subresources: {bill_number}_{subresource}.json.gz
        subresource = entity_type.replace("bill_", "")
        filename = f"{entity_id}_{subresource}.json.gz"
    else:
        filename = f"{entity_id}.json.gz"

    return f"{prefix}/{filename}"


def upload_to_bronze(
    entity_type: str,
    entity_id: str,
    api_response: Dict[str, Any],
    api_url: str,
    http_status: int,
    **partition_keys
) -> str:
    """Upload API response to Bronze S3 with compression and metadata.

    Args:
        entity_type: Entity type
        entity_id: Entity ID
        api_response: Raw API response (dict)
        api_url: API endpoint URL
        http_status: HTTP status code
        **partition_keys: Partition key values (congress, bill_type, chamber, etc.)

    Returns:
        S3 key where file was uploaded

    Raises:
        ClientError: If S3 upload fails
    """
    ingest_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ingest_timestamp = datetime.now(timezone.utc).isoformat()

    # Generate S3 key
    s3_key = get_bronze_s3_key(entity_type, entity_id, ingest_date, **partition_keys)

    # Compress JSON with gzip
    json_bytes = json.dumps(api_response, indent=2).encode("utf-8")
    gzipped_bytes = gzip.compress(json_bytes)

    # S3 metadata
    metadata = {
        "ingest-timestamp": ingest_timestamp,
        "api-url": api_url,
        "http-status": str(http_status),
        "source-system": "congress-api",
        "entity-type": entity_type,
        "entity-id": entity_id,
        "ingest-version": INGEST_VERSION,
    }

    # Add partition keys to metadata
    for key, value in partition_keys.items():
        if value is not None:
            metadata[key] = str(value)

    # Upload to S3
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=gzipped_bytes,
            ContentType="application/json",
            ContentEncoding="gzip",
            Metadata=metadata,
        )
        logger.info(
            f"Uploaded to Bronze: s3://{S3_BUCKET}/{s3_key} "
            f"({len(gzipped_bytes)} bytes compressed from {len(json_bytes)} bytes)"
        )
        return s3_key
    except ClientError as e:
        logger.error(f"Failed to upload to S3: {e}")
        raise


def queue_subresource_jobs(
    entity_type: str,
    entity_id: str,
    congress: int,
    bill_type: str,
    bill_number: int,
) -> None:
    """Queue subresource fetch jobs for a bill.

    For bills, we need to fetch additional subresources:
    - actions, cosponsors, committees, subjects, titles, summaries, related bills

    Args:
        entity_type: Must be "bill"
        entity_id: Bill ID (e.g., "118-hr-1")
        congress: Congress number
        bill_type: Bill type
        bill_number: Bill number
    """
    if entity_type != "bill" or not CONGRESS_FETCH_QUEUE_URL:
        return  # Only queue subresources for bills

    subresources = [
        "bill_actions",
        "bill_cosponsors",
        "bill_committees",
        "bill_subjects",
        "bill_titles",
    ]

    messages = []
    for subresource in subresources:
        message = {
            "entity_type": subresource,
            "entity_id": str(bill_number),
            "congress": congress,
            "bill_type": bill_type,
            "bill_number": bill_number,
            "endpoint": f"/bill/{congress}/{bill_type}/{bill_number}/{subresource.replace('bill_', '')}",
        }
        messages.append({
            "Id": f"{subresource}-{bill_number}",
            "MessageBody": json.dumps(message),
        })

    # Send in batches of 10 (SQS limit)
    for i in range(0, len(messages), 10):
        batch = messages[i:i+10]
        try:
            sqs_client.send_message_batch(
                QueueUrl=CONGRESS_FETCH_QUEUE_URL,
                Entries=batch,
            )
            logger.info(f"Queued {len(batch)} subresource jobs for bill {entity_id}")
        except Exception as e:
            logger.error(f"Failed to queue subresource jobs: {e}")


def queue_silver_transform(entity_type: str, bronze_s3_key: str, **partition_keys) -> None:
    """Queue Bronze-to-Silver transform job.

    Args:
        entity_type: Entity type
        bronze_s3_key: S3 key of Bronze file
        **partition_keys: Partition key values
    """
    if not CONGRESS_SILVER_QUEUE_URL:
        logger.warning("CONGRESS_SILVER_QUEUE_URL not set, skipping Silver transform queue")
        return

    message = {
        "entity_type": entity_type,
        "bronze_s3_key": bronze_s3_key,
        **partition_keys,
    }

    try:
        sqs_client.send_message(
            QueueUrl=CONGRESS_SILVER_QUEUE_URL,
            MessageBody=json.dumps(message),
        )
        logger.info(f"Queued Silver transform for {bronze_s3_key}")
    except Exception as e:
        logger.error(f"Failed to queue Silver transform: {e}")


def process_fetch_job(message_body: Dict[str, Any]) -> None:
    """Process a single fetch job from SQS.

    Args:
        message_body: SQS message body with:
            - entity_type: Entity type (member, bill, house_vote, etc.)
            - entity_id: Entity ID (bioguide_id, bill_number, etc.)
            - endpoint: API endpoint path (e.g., "/member/A000360")
            - Additional partition keys (congress, bill_type, chamber, session)

    Raises:
        CongressAPIError: If API request fails
    """
    entity_type = message_body["entity_type"]
    entity_id = message_body.get("entity_id")
    endpoint = message_body.get("endpoint")

    # Extract partition keys
    congress = message_body.get("congress")
    bill_type = message_body.get("bill_type")
    bill_number = message_body.get("bill_number")
    chamber = message_body.get("chamber")
    session = message_body.get("session")

    logger.info(
        f"Fetching {entity_type}: entity_id={entity_id}, "
        f"congress={congress}, bill_type={bill_type}, chamber={chamber}"
    )

    # Initialize API client with random key for load balancing
    api_key = get_random_api_key()
    client = CongressAPIClient(
        api_key=api_key,
        base_url=CONGRESS_API_BASE_URL,
    )

    # Fetch entity from API
    try:
        # Use endpoint if provided, otherwise construct based on entity type
        if endpoint:
            api_response = client._make_request(endpoint)
            api_url = f"{client.base_url}{endpoint}"
        else:
            # Route to correct API method based on entity type
            if entity_type == "member":
                api_response = client.get_member(entity_id)
                api_url = f"{client.base_url}/member/{entity_id}"
            elif entity_type == "bill":
                api_response = client.get_bill(congress, bill_type, bill_number)
                api_url = f"{client.base_url}/bill/{congress}/{bill_type}/{bill_number}"
            elif entity_type == "house_vote":
                session = session or 1
                api_response = client.get_house_vote(congress, session, int(entity_id))
                api_url = f"{client.base_url}/vote/{congress}/house/{entity_id}"
            elif entity_type == "senate_vote":
                session = session or 1
                api_response = client.get_senate_vote(congress, session, int(entity_id))
                api_url = f"{client.base_url}/vote/{congress}/senate/{entity_id}"
            elif entity_type == "committee":
                api_response = client.get_committee(chamber, entity_id)
                api_url = f"{client.base_url}/committee/{chamber}/{entity_id}"
            elif entity_type == "bill_actions":
                api_response = client.get_bill_actions(congress, bill_type, bill_number)
                api_url = f"{client.base_url}/bill/{congress}/{bill_type}/{bill_number}/actions"
            elif entity_type == "bill_cosponsors":
                api_response = client.get_bill_cosponsors(congress, bill_type, bill_number)
                api_url = f"{client.base_url}/bill/{congress}/{bill_type}/{bill_number}/cosponsors"
            elif entity_type == "bill_committees":
                api_response = client.get_bill_committees(congress, bill_type, bill_number)
                api_url = f"{client.base_url}/bill/{congress}/{bill_type}/{bill_number}/committees"
            elif entity_type == "bill_subjects":
                api_response = client.get_bill_subjects(congress, bill_type, bill_number)
                api_url = f"{client.base_url}/bill/{congress}/{bill_type}/{bill_number}/subjects"
            elif entity_type == "bill_titles":
                api_response = client.get_bill_titles(congress, bill_type, bill_number)
                api_url = f"{client.base_url}/bill/{congress}/{bill_type}/{bill_number}/titles"
            else:
                raise ValueError(f"Unknown entity_type: {entity_type}")

        http_status = 200

    except CongressAPINotFoundError as e:
        logger.warning(f"Entity not found: {entity_id}, {e}")
        raise  # Re-raise to trigger retry/DLQ
    except CongressAPIRateLimitError as e:
        logger.error(f"Rate limit exceeded: {e}")
        raise  # Re-raise to trigger retry
    except CongressAPIError as e:
        logger.error(f"API error: {e}")
        raise

    # Upload to Bronze
    partition_keys = {
        "congress": congress,
        "bill_type": bill_type,
        "chamber": chamber,
        "session": session,
    }
    bronze_s3_key = upload_to_bronze(
        entity_type=entity_type,
        entity_id=entity_id or str(bill_number),
        api_response=api_response,
        api_url=api_url,
        http_status=http_status,
        **{k: v for k, v in partition_keys.items() if v is not None},
    )

    # Queue subresource jobs if this is a bill
    if entity_type == "bill":
        queue_subresource_jobs(entity_type, entity_id, congress, bill_type, bill_number)

    # Queue Silver transform
    queue_silver_transform(entity_type, bronze_s3_key, **partition_keys)

    logger.info(f"Successfully processed {entity_type}: {entity_id}")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler (triggered by SQS).

    Args:
        event: SQS event with batch of messages
        context: Lambda context

    Returns:
        Dict with batch item failures for SQS

    Example event:
        {
            "Records": [
                {
                    "messageId": "...",
                    "body": "{\"entity_type\": \"member\", \"entity_id\": \"A000360\", \"endpoint\": \"/member/A000360\"}"
                }
            ]
        }
    """
    batch_item_failures = []

    for record in event.get("Records", []):
        try:
            # Parse SQS message
            message_body = json.loads(record["body"])

            # Process fetch job
            process_fetch_job(message_body)

        except Exception as e:
            logger.error(f"Failed to process record: {str(e)}", exc_info=True)

            # Add to batch failures (SQS will retry)
            batch_item_failures.append({"itemIdentifier": record["messageId"]})

    # Return batch failures for SQS partial batch response
    return {"batchItemFailures": batch_item_failures}
