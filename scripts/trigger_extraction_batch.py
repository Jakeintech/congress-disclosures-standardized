import boto3
import json
import os
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
S3_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
PROJECT_NAME = os.getenv("PROJECT_NAME", "congress-disclosures")

# Validate required environment variables
if not AWS_ACCOUNT_ID:
    logger.error("AWS_ACCOUNT_ID environment variable is required")
    import sys
    sys.exit(1)

DYNAMODB_TABLE = "house_fd_documents"
# Queue URL from previous command output
QUEUE_URL = f"https://sqs.{S3_REGION}.amazonaws.com/{AWS_ACCOUNT_ID}/{PROJECT_NAME}-{ENVIRONMENT}-structured-extraction-queue-v2"

dynamodb = boto3.resource("dynamodb", region_name=S3_REGION)
sqs = boto3.client("sqs", region_name=S3_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

def scan_dynamodb_documents():
    """Scan DynamoDB to get all document records."""
    documents = []
    scan_kwargs = {}
    done = False
    
    while not done:
        response = table.scan(**scan_kwargs)
        documents.extend(response.get('Items', []))
        start_key = response.get('LastEvaluatedKey')
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key
        else:
            done = True
            
    return documents

def trigger_extraction():
    """Trigger structured extraction for all documents."""
    logger.info("Scanning DynamoDB for documents...")
    documents = scan_dynamodb_documents()
    logger.info(f"Found {len(documents)} documents to process.")
    
    count = 0
    batch_entries = []
    
    for doc in documents:
        doc_id = doc["doc_id"]
        year = int(doc["year"])
        
        # Create message body
        message_body = {
            "doc_id": doc_id,
            "year": year,
            "extraction_method": "direct_text",
            "has_embedded_text": False,
            "filing_type": doc.get("filing_type", "Unknown")
        }
        
        # Add to batch
        batch_entries.append({
            "Id": doc_id,
            "MessageBody": json.dumps(message_body)
        })
        
        # Send batch of 10
        if len(batch_entries) == 10:
            try:
                sqs.send_message_batch(
                    QueueUrl=QUEUE_URL,
                    Entries=batch_entries
                )
                count += 10
                if count % 100 == 0:
                    logger.info(f"Triggered {count}/{len(documents)} documents...")
            except Exception as e:
                logger.error(f"Failed to send batch: {e}")
            
            batch_entries = []
            time.sleep(0.1)  # Rate limiting
            
    # Send remaining
    if batch_entries:
        try:
            sqs.send_message_batch(
                QueueUrl=QUEUE_URL,
                Entries=batch_entries
            )
            count += len(batch_entries)
        except Exception as e:
            logger.error(f"Failed to send final batch: {e}")
            
    logger.info(f"✅ Successfully triggered extraction for {count} documents.")

if __name__ == "__main__":
    trigger_extraction()
