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
import time
from typing import Any, Dict, List, Optional, Generator

import boto3
from botocore.exceptions import ClientError


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
dynamodb = boto3.resource("dynamodb")
watermarks_table = dynamodb.Table("congress-disclosures-pipeline-watermarks")



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

def get_checkpoint(checkpoint_id: str) -> int:
    """Get last processed offset from DynamoDB."""
    try:
        response = watermarks_table.get_item(
            Key={
                "table_name": "congress_pipeline",
                "watermark_type": checkpoint_id
            }
        )
        if "Item" in response:
            offset = int(response["Item"].get("offset", 0))
            logger.info(f"Found checkpoint for {checkpoint_id}: offset={offset}")
            return offset
    except ClientError as e:
        logger.warning(f"Failed to read checkpoint {checkpoint_id}: {e}")
    return 0

def save_checkpoint(checkpoint_id: str, offset: int, metadata: Dict[str, Any] = None):
    """Save current offset to DynamoDB."""
    import time  # Defensive import
    try:
        item = {
            "table_name": "congress_pipeline",
            "watermark_type": checkpoint_id,
            "offset": offset,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "ttl": int(time.time()) + (7 * 24 * 3600)  # 7 days retention
        }
        if metadata:
            item.update(metadata)
        
        watermarks_table.put_item(Item=item)
        logger.info(f"Saved checkpoint {checkpoint_id}: offset={offset}")
    except ClientError as e:
        logger.error(f"Failed to save checkpoint {checkpoint_id}: {e}")

def hash_checkpoint_id(entity_type: str, congress: Optional[int] = None, 
                      bill_type: Optional[str] = None, mode: str = "full") -> str:
    """Generate unique checkpoint ID."""
    parts = ["ingest", entity_type, mode]
    if congress:
        parts.append(str(congress))
    if bill_type:
        parts.append(bill_type)
    return "_".join(parts)


def queue_fetch_jobs(jobs: List[Dict[str, Any]], queue_url: str) -> int:
    """Send fetch jobs to SQS in batches of 10.
    
    Args:
        jobs: List of job dicts to queue
        queue_url: SQS queue URL
        
    Returns:
        Number of successfully queued jobs
    """
    queued = 0
    sqs = boto3.client('sqs')
    
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
            response = sqs.send_message_batch(QueueUrl=queue_url, Entries=entries)
            queued += len(entries) - len(response.get('Failed', []))
            
            if 'Failed' in response:
                for failed in response['Failed']:
                    logger.error(f"Failed to queue job {failed['Id']}: {failed.get('Message')}")
        except Exception as e:
            logger.error(f"Error queuing batch: {e}")
    
    return queued


def build_member_jobs_generator(
    client: CongressAPIClient, 
    limit: Optional[int] = None,
    start_offset: int = 0
) -> Generator[Dict[str, Any], None, None]:
    """Yield fetch jobs for members."""
    logger.info(f"Fetching member list starting at offset {start_offset}...")
    
    for member in client.list_members(limit=limit, start_offset=start_offset):
        bioguide_id = member.get("bioguideId")
        if not bioguide_id:
            continue
        
        chamber = "unknown"
        terms = member.get("terms", {}).get("item", [])
        if terms:
            latest_term = terms[-1] if isinstance(terms, list) else terms
            chamber = latest_term.get("chamber", "unknown").lower()
        
        yield {
            "entity_type": "member",
            "entity_id": bioguide_id,
            "endpoint": f"/member/{bioguide_id}",
            "chamber": chamber
        }

def build_bill_jobs_generator(
    client: CongressAPIClient,
    congress: int,
    bill_type: Optional[str] = None,
    limit: Optional[int] = None,
    start_offset: int = 0
) -> Generator[Dict[str, Any], None, None]:
    """Yield fetch jobs for bills."""
    logger.info(f"Fetching bills for Congress {congress} starting at offset {start_offset}...")
    
    for bill in client.list_bills(congress=congress, bill_type=bill_type, limit=limit, start_offset=start_offset):
        bill_number = bill.get("number")
        b_type = bill.get("type", "").lower()
        
        if not bill_number or not b_type:
            continue
        
        bill_id = f"{congress}-{b_type}-{bill_number}"
        
        yield {
            "entity_type": "bill",
            "entity_id": bill_id,
            "endpoint": f"/bill/{congress}/{b_type}/{bill_number}",
            "congress": congress,
            "bill_type": b_type,
            "bill_number": int(bill_number)
        }

def build_committee_jobs_generator(
    client: CongressAPIClient,
    limit: Optional[int] = None,
    start_offset: int = 0
) -> Generator[Dict[str, Any], None, None]:
    """Yield fetch jobs for committees."""
    logger.info(f"Fetching committees starting at offset {start_offset}...")
    
    for committee in client.list_committees(limit=limit, start_offset=start_offset):
        committee_code = committee.get("systemCode")
        c_chamber = committee.get("chamber", "").lower()
        
        if not committee_code:
            continue
        
        yield {
            "entity_type": "committee",
            "entity_id": committee_code,
            "endpoint": f"/committee/{c_chamber}/{committee_code}",
            "chamber": c_chamber
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Orchestrator Handler with Watermark Support."""
    import time  # Cleaned up redundant imports if necessary, but keeping simple
    start_time = time.time()
    
    # Parse event
    entity_type = event.get("entity_type")
    year = event.get("year")
    congress = event.get("congress")
    mode = event.get("mode", "full")
    limit = event.get("limit")
    bill_type = event.get("bill_type")
    output_mode = event.get("output_mode", "sqs")
    
    # Calculate congress from year if needed
    if year and not congress:
        try:
            year_int = int(year)
            congress = (year_int - 1789) // 2 + 1
        except (ValueError, TypeError):
            return {"statusCode": 400, "error": f"Invalid year: {year}"}

    if not entity_type:
        return {"statusCode": 400, "error": "entity_type is required"}
    
    logger.info(f"Starting orchestrator: {entity_type}, congress={congress}, mode={mode}")
    
    # Initialize Client
    try:
        api_key = get_api_key()
        client = CongressAPIClient(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize client: {e}")
        return {"statusCode": 500, "error": str(e)}
    
    # Determine Resume State
    checkpoint_id = hash_checkpoint_id(entity_type, congress, bill_type, mode)
    start_offset = 0
    
    # Only resume if explicitly requested OR defaulting to auto-resume mechanism
    # For now, we always try to resume in "full" mode if a checkpoint exists
    if mode == "full":
        start_offset = get_checkpoint(checkpoint_id)
        if start_offset > 0:
            logger.info(f"Resuming from verified checkpoint offset: {start_offset}")

    # Build Generator
    job_generator = None
    try:
        if entity_type == "member":
            job_generator = build_member_jobs_generator(client, limit, start_offset)
        elif entity_type == "bill":
            job_generator = build_bill_jobs_generator(client, congress, bill_type, limit, start_offset)
        elif entity_type == "committee":
            job_generator = build_committee_jobs_generator(client, limit, start_offset)
        else:
            return {"statusCode": 400, "error": f"Unsupported entity_type: {entity_type}"}
    except Exception as e:
        return {"statusCode": 500, "error": f"Generator creation failed: {e}"}

    # Iterate and Process
    processed_count = 0
    queued_count = 0
    batch_jobs = []
    all_jobs_for_manifest = []
    
    try:
        for job in job_generator:
            if output_mode == "s3_manifest":
                all_jobs_for_manifest.append(job)
            else:
                batch_jobs.append(job)
                
            processed_count += 1
            
            # Queue when batch full (SQS only)
            if output_mode == "sqs" and len(batch_jobs) >= 10:
                q = queue_fetch_jobs(batch_jobs, CONGRESS_FETCH_QUEUE_URL)
                queued_count += q
                batch_jobs = []
                
            # Checkpoint every 100 items
            if processed_count % 100 == 0:
                current_offset = start_offset + processed_count
                save_checkpoint(checkpoint_id, current_offset, {"status": "in_progress"})
                
                # Check Time Limit (stop if < 2 mins remains)
                if context and context.get_remaining_time_in_millis() < 120000:
                    logger.warning("Time limit approaching. Stopping and saving state.")
                    break
        
        # Flush remaining SQS
        if output_mode == "sqs" and batch_jobs:
            q = queue_fetch_jobs(batch_jobs, CONGRESS_FETCH_QUEUE_URL)
            queued_count += q

        # Write Manifest if needed
        manifest_key = None
        if output_mode == "s3_manifest":
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            manifest_key = f"manifests/{entity_type}_{congress if congress else 'all'}_{timestamp}.json"
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=manifest_key,
                Body=json.dumps(all_jobs_for_manifest),
                ContentType="application/json"
            )
            logger.info(f"Wrote {len(all_jobs_for_manifest)} jobs to manifest: {manifest_key}")

        # Completion handling
        status = "completed"
        if limit and processed_count >= limit:
             logger.info("Hit limit. Keeping checkpoint for resume.")
             current_offset = start_offset + processed_count
             save_checkpoint(checkpoint_id, current_offset)
             status = "limit_reached"
        else:
             # If we finished naturally (generator exhausted), reset checkpoint
             logger.info("Ingestion complete. Resetting checkpoint.")
             save_checkpoint(checkpoint_id, 0, {"status": "completed"})
             status = "success"

    except Exception as e:
        logger.error(f"Error during ingestion loop: {e}")
        # Save progress before dying
        current_offset = start_offset + processed_count
        save_checkpoint(checkpoint_id, current_offset, {"status": "failed"})
        raise

    result = {
        "statusCode": 200, 
        "status": status,
        "queued_count": queued_count,
        "processed_count": processed_count,
        "start_offset": start_offset,
        "end_offset": start_offset + processed_count,
        "s3_bucket": S3_BUCKET
    }
    
    if manifest_key:
        result["manifest_key"] = manifest_key
        result["jobs_built"] = len(all_jobs_for_manifest)
        
    return result
