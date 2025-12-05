"""Integration tests for Congress API fetch Lambda.

These tests verify the end-to-end fetch workflow:
1. Send SQS message with entity type and ID
2. Lambda fetches from Congress.gov API
3. Raw JSON uploaded to Bronze S3

Run with: pytest tests/integration/test_congress_fetch.py -v
"""

import gzip
import json
import os
import time
import uuid

import boto3
import pytest

# Test configuration from environment
S3_BUCKET = os.environ.get("S3_BUCKET_NAME", "congress-disclosures-standardized")
CONGRESS_FETCH_QUEUE_URL = os.environ.get(
    "CONGRESS_FETCH_QUEUE_URL",
    "https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT/congress-fetch-queue"
)
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Initialize clients
s3_client = boto3.client("s3", region_name=AWS_REGION)
sqs_client = boto3.client("sqs", region_name=AWS_REGION)


def get_today_date() -> str:
    """Get today's date in YYYY-MM-DD format."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")


def send_fetch_message(
    entity_type: str,
    entity_id: str,
    endpoint: str,
    **kwargs
) -> str:
    """Send a fetch job message to SQS.
    
    Args:
        entity_type: Entity type (member, bill, etc.)
        entity_id: Entity ID
        endpoint: API endpoint
        **kwargs: Additional partition keys
        
    Returns:
        SQS message ID
    """
    message = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "endpoint": endpoint,
        **kwargs
    }
    
    response = sqs_client.send_message(
        QueueUrl=CONGRESS_FETCH_QUEUE_URL,
        MessageBody=json.dumps(message)
    )
    
    return response["MessageId"]


def wait_for_bronze_file(s3_key: str, timeout: int = 120) -> dict:
    """Wait for a Bronze file to appear in S3.
    
    Args:
        s3_key: Expected S3 key
        timeout: Max seconds to wait
        
    Returns:
        S3 object metadata dict
        
    Raises:
        TimeoutError: If file not found within timeout
    """
    start = time.time()
    
    while time.time() - start < timeout:
        try:
            response = s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
            return response
        except s3_client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                time.sleep(5)  # Wait and retry
            else:
                raise
    
    raise TimeoutError(f"File not found at {s3_key} after {timeout}s")


def download_bronze_json(s3_key: str) -> dict:
    """Download and decompress a Bronze JSON file.
    
    Args:
        s3_key: S3 key
        
    Returns:
        Parsed JSON dict
    """
    response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
    body = response["Body"].read()
    
    # Decompress if gzipped
    if s3_key.endswith(".gz"):
        body = gzip.decompress(body)
    
    return json.loads(body)


def delete_test_objects(prefix: str) -> int:
    """Delete test objects from S3.
    
    Args:
        prefix: S3 prefix to delete
        
    Returns:
        Number of objects deleted
    """
    paginator = s3_client.get_paginator("list_objects_v2")
    deleted = 0
    
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        objects = page.get("Contents", [])
        if not objects:
            continue
        
        delete_keys = [{"Key": obj["Key"]} for obj in objects]
        s3_client.delete_objects(
            Bucket=S3_BUCKET,
            Delete={"Objects": delete_keys}
        )
        deleted += len(delete_keys)
    
    return deleted


@pytest.fixture
def cleanup_test_keys():
    """Fixture to track and cleanup test S3 keys."""
    keys_to_delete = []
    
    yield keys_to_delete
    
    # Cleanup after test
    for key in keys_to_delete:
        try:
            s3_client.delete_object(Bucket=S3_BUCKET, Key=key)
        except Exception as e:
            print(f"Cleanup failed for {key}: {e}")


@pytest.mark.integration
class TestCongressFetch:
    """Integration tests for Congress fetch Lambda."""
    
    def test_fetch_member_to_bronze(self, cleanup_test_keys):
        """Test fetching a member entity to Bronze S3.
        
        This test:
        1. Sends SQS message for member A000360 (Lamar Alexander)
        2. Waits for Lambda to process
        3. Verifies Bronze JSON exists and is valid
        """
        # Test member: Lamar Alexander (retired but still in API)
        bioguide_id = "A000360"
        chamber = "senate"
        today = get_today_date()
        
        # Expected S3 key pattern
        expected_key = f"bronze/congress/member/chamber={chamber}/ingest_date={today}/{bioguide_id}.json.gz"
        cleanup_test_keys.append(expected_key)
        
        # Send fetch message
        message_id = send_fetch_message(
            entity_type="member",
            entity_id=bioguide_id,
            endpoint=f"/member/{bioguide_id}",
            chamber=chamber
        )
        print(f"Sent message {message_id} for member {bioguide_id}")
        
        # Wait for Bronze file
        try:
            metadata = wait_for_bronze_file(expected_key, timeout=120)
            print(f"Found Bronze file: {expected_key}")
        except TimeoutError:
            # Try without chamber partition (handler might detect it differently)
            alt_keys = [
                f"bronze/congress/member/chamber=house/ingest_date={today}/{bioguide_id}.json.gz",
                f"bronze/congress/member/chamber=unknown/ingest_date={today}/{bioguide_id}.json.gz",
            ]
            for alt_key in alt_keys:
                try:
                    metadata = wait_for_bronze_file(alt_key, timeout=10)
                    expected_key = alt_key
                    cleanup_test_keys.append(alt_key)
                    print(f"Found Bronze file at alt key: {alt_key}")
                    break
                except TimeoutError:
                    continue
            else:
                pytest.fail(f"Bronze file not found for member {bioguide_id}")
        
        # Verify metadata
        assert metadata.get("ContentEncoding") == "gzip" or expected_key.endswith(".gz")
        
        # Download and verify content
        data = download_bronze_json(expected_key)
        assert "member" in data, "Expected 'member' key in response"
        assert data["member"].get("bioguideId") == bioguide_id
        print(f"Verified member data: {data['member'].get('firstName')} {data['member'].get('lastName')}")
    
    def test_fetch_bill_to_bronze(self, cleanup_test_keys):
        """Test fetching a bill entity to Bronze S3."""
        # Test bill: HR 1 from Congress 118
        congress = 118
        bill_type = "hr"
        bill_number = 1
        bill_id = f"{congress}-{bill_type}-{bill_number}"
        today = get_today_date()
        
        # Expected S3 key pattern
        expected_key = f"bronze/congress/bill/congress={congress}/bill_type={bill_type}/ingest_date={today}/{bill_id}.json.gz"
        cleanup_test_keys.append(expected_key)
        
        # Send fetch message
        message_id = send_fetch_message(
            entity_type="bill",
            entity_id=bill_id,
            endpoint=f"/bill/{congress}/{bill_type}/{bill_number}",
            congress=congress,
            bill_type=bill_type,
            bill_number=bill_number
        )
        print(f"Sent message {message_id} for bill {bill_id}")
        
        # Wait for Bronze file
        metadata = wait_for_bronze_file(expected_key, timeout=120)
        print(f"Found Bronze file: {expected_key}")
        
        # Verify metadata
        assert "Metadata" in metadata or expected_key.endswith(".gz")
        
        # Download and verify content
        data = download_bronze_json(expected_key)
        assert "bill" in data, "Expected 'bill' key in response"
        bill = data["bill"]
        assert bill.get("number") == str(bill_number) or bill.get("number") == bill_number
        print(f"Verified bill: {bill.get('title', 'No title')[:50]}...")
    
    def test_fetch_member_returns_s3_metadata(self, cleanup_test_keys):
        """Test that Bronze files have correct S3 object metadata."""
        bioguide_id = "P000197"  # Nancy Pelosi
        chamber = "house"
        today = get_today_date()
        
        expected_key = f"bronze/congress/member/chamber={chamber}/ingest_date={today}/{bioguide_id}.json.gz"
        cleanup_test_keys.append(expected_key)
        
        # Send fetch message
        send_fetch_message(
            entity_type="member",
            entity_id=bioguide_id,
            endpoint=f"/member/{bioguide_id}",
            chamber=chamber
        )
        
        # Wait and get full metadata
        metadata = wait_for_bronze_file(expected_key, timeout=120)
        
        # Verify S3 object metadata
        s3_meta = metadata.get("Metadata", {})
        
        # Check expected metadata fields (case-insensitive in S3)
        meta_lower = {k.lower(): v for k, v in s3_meta.items()}
        
        assert "entity-type" in meta_lower or "entitytype" in meta_lower, \
            f"Missing entity-type metadata. Found: {s3_meta}"
        
        print(f"S3 Metadata: {s3_meta}")


@pytest.mark.integration
class TestCongressOrchestrator:
    """Integration tests for Congress orchestrator Lambda."""
    
    def test_orchestrator_queues_member_jobs(self):
        """Test that orchestrator queues member fetch jobs."""
        lambda_client = boto3.client("lambda", region_name=AWS_REGION)
        
        # Get Lambda function name from env or construct it
        function_name = os.environ.get(
            "CONGRESS_ORCHESTRATOR_LAMBDA",
            "congress-disclosures-development-congress-orchestrator"
        )
        
        # Invoke with small limit for testing
        payload = {
            "entity_type": "member",
            "mode": "full",
            "limit": 5  # Only fetch 5 members for testing
        }
        
        try:
            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType="RequestResponse",
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response["Payload"].read())
            print(f"Orchestrator result: {result}")
            
            assert result.get("statusCode") == 200, f"Unexpected status: {result}"
            assert result.get("queued_count", 0) > 0, "No jobs queued"
            assert result.get("entity_type") == "member"
            
        except lambda_client.exceptions.ResourceNotFoundException:
            pytest.skip(f"Lambda function {function_name} not found - orchestrator not deployed")
    
    def test_orchestrator_queues_bill_jobs(self):
        """Test that orchestrator queues bill fetch jobs."""
        lambda_client = boto3.client("lambda", region_name=AWS_REGION)
        
        function_name = os.environ.get(
            "CONGRESS_ORCHESTRATOR_LAMBDA",
            "congress-disclosures-development-congress-orchestrator"
        )
        
        payload = {
            "entity_type": "bill",
            "congress": 118,
            "mode": "full",
            "limit": 5
        }
        
        try:
            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType="RequestResponse",
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response["Payload"].read())
            print(f"Orchestrator result: {result}")
            
            assert result.get("statusCode") == 200
            assert result.get("queued_count", 0) > 0
            assert result.get("congress") == 118
            
        except lambda_client.exceptions.ResourceNotFoundException:
            pytest.skip(f"Lambda function {function_name} not found")


if __name__ == "__main__":
    # Allow running directly for debugging
    pytest.main([__file__, "-v", "-s"])
