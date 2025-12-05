"""Lambda handler for Congress.gov API ingestion orchestration.

This Lambda orchestrates bulk ingestion by:
1. Receiving a payload specifying entity type and scope (e.g., Congress 118 bills)
2. Paginating through Congress.gov list endpoints
3. Queuing individual fetch jobs to SQS in batches

Example invocation:
    {
        "entity_type": "bill",
        "congress": 118,
        "mode": "full"  # or "incremental"
    }

For entity_type="member":
    {
        "entity_type": "member",
        "mode": "full"
    }
"""

import gzip
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

# Add parent path for lib imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.congress_api_client import CongressAPIClient, CongressAPIError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Configuration from environment
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")
CONGRESS_FETCH_QUEUE_URL = os.environ.get("CONGRESS_FETCH_QUEUE_URL")
STATE_PREFIX = "bronze/congress/_state"

# Initialize clients
s3_client = boto3.client("s3")
sqs_client = boto3.client("sqs")
ssm_client = boto3.client("ssm")


def get_api_key() -> str:
    """Get Congress API key from SSM Parameter Store.
    
    Returns:
        API key string
        
    Raises:
        ValueError: If parameter not found
    """
    ssm_path = os.environ.get(
        "CONGRESS_API_KEY_SSM_PATH",
        "/congress-disclosures-standardized/development/congress-api-key"
    )
    try:
        response = ssm_client.get_parameter(Name=ssm_path, WithDecryption=True)
        return response["Parameter"]["Value"]
    except ClientError as e:
        logger.error(f"Failed to get API key from SSM: {e}")
        raise ValueError(f"Congress API key not found at {ssm_path}")


def read_last_ingest_state(entity_type: str, congress: Optional[int] = None) -> Dict[str, Any]:
    """Read last ingest state from S3 marker file.
    
    Args:
        entity_type: Entity type (bill, member, etc.)
        congress: Congress number (optional, for bills)
        
    Returns:
        State dict with last_ingest_date and last_item_count, or empty dict if not found
    """
    # Build state file key
    if congress:
        key = f"{STATE_PREFIX}/{entity_type}_{congress}_last_ingest.json"
    else:
        key = f"{STATE_PREFIX}/{entity_type}_last_ingest.json"
    
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        body = response["Body"].read()
        # Handle gzip if needed
        if key.endswith(".gz"):
            body = gzip.decompress(body)
        return json.loads(body)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            logger.info(f"No state file found at {key}, this is a first run")
            return {}
        raise


def write_last_ingest_state(
    entity_type: str,
    timestamp: str,
    item_count: int,
    congress: Optional[int] = None
) -> None:
    """Write last ingest state to S3 marker file.
    
    Args:
        entity_type: Entity type
        timestamp: ISO timestamp of ingest
        item_count: Number of items queued
        congress: Congress number (optional)
    """
    # Build state file key
    if congress:
        key = f"{STATE_PREFIX}/{entity_type}_{congress}_last_ingest.json"
    else:
        key = f"{STATE_PREFIX}/{entity_type}_last_ingest.json"
    
    state = {
        "last_ingest_date": timestamp,
        "last_item_count": item_count,
        "entity_type": entity_type,
    }
    if congress:
        state["congress"] = congress
    
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=json.dumps(state, indent=2),
        ContentType="application/json"
    )
    logger.info(f"Wrote state to {key}: {state}")


def queue_fetch_jobs(jobs: List[Dict[str, Any]], queue_url: str) -> int:
    """Send fetch jobs to SQS in batches of 10.
    
    Args:
        jobs: List of job dicts to queue
        queue_url: SQS queue URL
        
    Returns:
        Number of successfully queued jobs
    """
    queued = 0
    
    # Process in batches of 10 (SQS limit)
    for i in range(0, len(jobs), 10):
        batch = jobs[i:i+10]
        entries = [
            {
                "Id": str(idx),
                "MessageBody": json.dumps(job)
            }
            for idx, job in enumerate(batch)
        ]
        
        try:
            response = sqs_client.send_message_batch(
                QueueUrl=queue_url,
                Entries=entries
            )
            successful = len(response.get("Successful", []))
            queued += successful
            
            if response.get("Failed"):
                logger.error(f"Failed to queue {len(response['Failed'])} messages: {response['Failed']}")
                
        except ClientError as e:
            logger.error(f"SQS batch send failed: {e}")
            raise
    
    return queued


def build_member_jobs(client: CongressAPIClient, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Build fetch jobs for all members.
    
    Args:
        client: Congress API client
        limit: Optional limit on number of members
        
    Returns:
        List of job dicts
    """
    jobs = []
    
    logger.info("Fetching member list from Congress.gov API...")
    
    for member in client.list_members(limit=limit):
        bioguide_id = member.get("bioguideId")
        if not bioguide_id:
            logger.warning(f"Member missing bioguideId: {member}")
            continue
        
        # Determine chamber from terms
        chamber = "unknown"
        terms = member.get("terms", {}).get("item", [])
        if terms:
            latest_term = terms[-1] if isinstance(terms, list) else terms
            chamber = latest_term.get("chamber", "unknown").lower()
        
        job = {
            "entity_type": "member",
            "entity_id": bioguide_id,
            "endpoint": f"/member/{bioguide_id}",
            "chamber": chamber
        }
        jobs.append(job)
        
        if len(jobs) % 100 == 0:
            logger.info(f"Built {len(jobs)} member jobs...")
    
    return jobs


def build_bill_jobs(
    client: CongressAPIClient,
    congress: int,
    bill_type: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Build fetch jobs for bills.
    
    Args:
        client: Congress API client
        congress: Congress number
        bill_type: Optional bill type filter (hr, s, hjres, sjres)
        limit: Optional limit on number of bills
        
    Returns:
        List of job dicts
    """
    jobs = []
    
    logger.info(f"Fetching bill list for Congress {congress}...")
    
    for bill in client.list_bills(congress=congress, bill_type=bill_type, limit=limit):
        bill_number = bill.get("number")
        b_type = bill.get("type", "").lower()
        
        if not bill_number or not b_type:
            logger.warning(f"Bill missing number or type: {bill}")
            continue
        
        bill_id = f"{congress}-{b_type}-{bill_number}"
        
        job = {
            "entity_type": "bill",
            "entity_id": bill_id,
            "endpoint": f"/bill/{congress}/{b_type}/{bill_number}",
            "congress": congress,
            "bill_type": b_type,
            "bill_number": int(bill_number)
        }
        jobs.append(job)
        
        if len(jobs) % 100 == 0:
            logger.info(f"Built {len(jobs)} bill jobs...")
    
    return jobs


def build_committee_jobs(
    client: CongressAPIClient,
    chamber: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Build fetch jobs for committees.
    
    Args:
        client: Congress API client
        chamber: Optional chamber filter (house, senate, joint)
        limit: Optional limit
        
    Returns:
        List of job dicts
    """
    jobs = []
    
    logger.info("Fetching committee list...")
    
    for committee in client.list_committees(chamber=chamber, limit=limit):
        committee_code = committee.get("systemCode")
        c_chamber = committee.get("chamber", "").lower()
        
        if not committee_code:
            logger.warning(f"Committee missing systemCode: {committee}")
            continue
        
        job = {
            "entity_type": "committee",
            "entity_id": committee_code,
            "endpoint": f"/committee/{c_chamber}/{committee_code}",
            "chamber": c_chamber
        }
        jobs.append(job)
    
    return jobs


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for orchestrating Congress.gov data ingestion.
    
    Args:
        event: Invocation payload with:
            - entity_type: "bill", "member", or "committee"
            - congress: Congress number (for bills)
            - bill_type: Optional bill type filter (hr, s, hjres, sjres)
            - mode: "full" or "incremental" (default: full)
            - limit: Optional limit for testing
        context: Lambda context
        
    Returns:
        Summary dict with queued_count, duration_seconds, etc.
    """
    import time
    start_time = time.time()
    
    # Parse event
    entity_type = event.get("entity_type")
    congress = event.get("congress")
    bill_type = event.get("bill_type")
    mode = event.get("mode", "full")
    limit = event.get("limit")
    
    if not entity_type:
        return {
            "statusCode": 400,
            "error": "entity_type is required"
        }
    
    logger.info(f"Starting orchestrator: entity_type={entity_type}, congress={congress}, mode={mode}, limit={limit}")
    
    # Check required env vars
    if not S3_BUCKET:
        return {"statusCode": 500, "error": "S3_BUCKET_NAME not configured"}
    if not CONGRESS_FETCH_QUEUE_URL:
        return {"statusCode": 500, "error": "CONGRESS_FETCH_QUEUE_URL not configured"}
    
    # Get API key and initialize client
    try:
        api_key = get_api_key()
        client = CongressAPIClient(api_key=api_key)
    except (ValueError, ClientError) as e:
        logger.error(f"Failed to initialize API client: {e}")
        return {"statusCode": 500, "error": str(e)}
    
    # Read state for incremental mode
    last_state = {}
    if mode == "incremental":
        last_state = read_last_ingest_state(entity_type, congress)
        logger.info(f"Incremental mode, last state: {last_state}")
        # TODO: Filter API calls by updateDate > last_ingest_date
    
    # Build fetch jobs based on entity type
    jobs = []
    try:
        if entity_type == "member":
            jobs = build_member_jobs(client, limit=limit)
        elif entity_type == "bill":
            if not congress:
                return {"statusCode": 400, "error": "congress is required for bill entity type"}
            jobs = build_bill_jobs(client, congress, bill_type, limit=limit)
        elif entity_type == "committee":
            jobs = build_committee_jobs(client, limit=limit)
        else:
            return {"statusCode": 400, "error": f"Unsupported entity_type: {entity_type}"}
    except CongressAPIError as e:
        logger.error(f"API error building jobs: {e}")
        return {"statusCode": 500, "error": f"Congress API error: {e}"}
    
    logger.info(f"Built {len(jobs)} fetch jobs")
    
    # Queue all jobs
    queued_count = 0
    if jobs:
        queued_count = queue_fetch_jobs(jobs, CONGRESS_FETCH_QUEUE_URL)
        logger.info(f"Queued {queued_count}/{len(jobs)} jobs to fetch queue")
    
    # Write state
    now = datetime.now(timezone.utc).isoformat()
    write_last_ingest_state(entity_type, now, queued_count, congress)
    
    # Calculate duration
    duration = time.time() - start_time
    
    result = {
        "statusCode": 200,
        "entity_type": entity_type,
        "mode": mode,
        "jobs_built": len(jobs),
        "queued_count": queued_count,
        "duration_seconds": round(duration, 2)
    }
    if congress:
        result["congress"] = congress
    
    logger.info(f"Orchestrator complete: {result}")
    return result
