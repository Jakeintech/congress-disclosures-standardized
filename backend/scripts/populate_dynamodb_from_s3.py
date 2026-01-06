import boto3
import json
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "congress-disclosures-standardized")
S3_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_SILVER_PREFIX = "silver/house/financial/documents"
DYNAMODB_TABLE = "house_fd_documents"

s3 = boto3.client("s3", region_name=S3_REGION)
dynamodb = boto3.resource("dynamodb", region_name=S3_REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

def list_silver_documents():
    """List all document folders in the silver layer."""
    doc_folders = set()
    paginator = s3.get_paginator("list_objects_v2")
    page_iterator = paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_SILVER_PREFIX)

    for page in page_iterator:
        if "Contents" in page:
            for obj in page["Contents"]:
                key = obj["Key"]
                # Extract doc_id from path like: silver/house/financial/documents/year=2025/10063256/metadata.json
                parts = key.split("/")
                if len(parts) >= 6 and parts[5]:  # doc_id is at index 5
                    year_part = parts[4]  # year=2025
                    doc_id = parts[5]
                    if year_part.startswith("year="):
                        year = int(year_part.split("=")[1])
                        doc_folders.add((doc_id, year, key))
    
    return list(doc_folders)

def populate_dynamodb():
    """Scan S3 and populate DynamoDB."""
    logger.info(f"Scanning {S3_BUCKET}/{S3_SILVER_PREFIX}...")
    doc_data = list_silver_documents()
    logger.info(f"Found {len(doc_data)} unique documents in S3.")
    
    count = 0
    with table.batch_writer() as batch:
        for doc_id, year, sample_key in doc_data:
            try:
                # Try to read metadata.json for this doc_id
                metadata_key = f"silver/house/financial/documents/year={year}/{doc_id}/metadata.json"
                text_key = f"silver/house/financial/documents/year={year}/{doc_id}/text.txt"
                
                metadata = {}
                try:
                    response = s3.get_object(Bucket=S3_BUCKET, Key=metadata_key)
                    metadata = json.loads(response["Body"].read().decode("utf-8"))
                except:
                    pass  # metadata.json might not exist for all docs
                
                item = {
                    "doc_id": doc_id,
                    "year": year,
                    "extraction_status": "success",
                    "text_s3_key": text_key,
                    "text_extraction_timestamp": metadata.get("extraction_timestamp", datetime.utcnow().isoformat()),
                    "pages": metadata.get("pages", 0),
                    "char_count": metadata.get("char_count", 0),
                    "last_updated": datetime.utcnow().isoformat()
                }
                
                batch.put_item(Item=item)
                count += 1
                if count % 100 == 0:
                    logger.info(f"Processed {count}/{len(doc_data)} documents...")
                    
            except Exception as e:
                logger.error(f"Error processing {doc_id} ({year}): {e}")
                
    logger.info(f"DynamoDB population complete. Added {count} documents.")

if __name__ == "__main__":
    populate_dynamodb()
