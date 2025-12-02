#!/usr/bin/env python3
"""Backfill S3 metadata for Bronze PDFs that have already been processed.

This script queries the Silver layer to find all extracted documents and adds
metadata to the corresponding Bronze PDFs to track Textract usage.
"""

import boto3
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Configuration
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "congress-disclosures-standardized")
S3_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BRONZE_PREFIX = "bronze"
S3_SILVER_PREFIX = "silver"
EXTRACTION_VERSION = "1.1.0"  # Updated version with metadata tracking

s3 = boto3.client("s3", region_name=S3_REGION)
dynamodb = boto3.resource("dynamodb", region_name=S3_REGION)
table = dynamodb.Table("house_fd_documents")

def get_all_extracted_documents():
    """Scan DynamoDB to get all documents that have been extracted."""
    documents = []
    scan_kwargs = {}
    
    logger.info("Scanning DynamoDB for extracted documents...")
    
    while True:
        response = table.scan(**scan_kwargs)
        for item in response.get('Items', []):
            # Only include documents that have text_s3_key (successfully extracted)
            if item.get('text_s3_key'):
                documents.append(item)
        
        if 'LastEvaluatedKey' in response:
            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
        else:
            break
    
    logger.info(f"Found {len(documents)} extracted documents")
    return documents

def update_bronze_metadata(doc_id, year, extraction_info):
    """Update Bronze PDF metadata for a single document."""
    try:
        # Construct Bronze PDF key
        bronze_key = f"{S3_BRONZE_PREFIX}/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf"
        
        # Check if PDF exists
        try:
            s3.head_object(Bucket=S3_BUCKET, Key=bronze_key)
        except s3.exceptions.NoSuchKey:
            logger.warning(f"Bronze PDF not found: {bronze_key}")
            return False
        
        # Prepare metadata (all values must be strings, handle None)
        metadata = {
            "extraction-processed": "true",
            "extraction-version": EXTRACTION_VERSION,
            "extraction-timestamp": str(extraction_info.get('extraction_timestamp') or datetime.utcnow().isoformat()),
            "extraction-method": str(extraction_info.get('extraction_method') or 'unknown'),
            "extraction-pages": str(extraction_info.get('pages') or '0'),
            "text-location": str(extraction_info.get('text_s3_key') or ''),
        }
        
        # Add structured location if available
        json_key = extraction_info.get('json_s3_key')
        if json_key:
            metadata["structured-location"] = str(json_key)
        
        # Copy object to itself with new metadata
        copy_source = {"Bucket": S3_BUCKET, "Key": bronze_key}
        
        s3.copy_object(
            Bucket=S3_BUCKET,
            Key=bronze_key,
            CopySource=copy_source,
            Metadata=metadata,
            MetadataDirective="REPLACE"
        )
        
        return True
        
    except Exception as e:
        import traceback
        logger.error(f"Failed to update metadata for {doc_id}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        logger.error(f"Extraction info: {extraction_info}")
        return False

def main():
    """Main backfill process."""
    logger.info("Starting Bronze PDF metadata backfill...")
    
    # Get all extracted documents
    documents = get_all_extracted_documents()
    
    if not documents:
        logger.warning("No extracted documents found!")
        return
    
    # Update metadata for each document
    success_count = 0
    fail_count = 0
    
    for i, doc in enumerate(documents, 1):
        doc_id = doc['doc_id']
        year = int(doc['year'])
        
        if i % 100 == 0:
            logger.info(f"Progress: {i}/{len(documents)} documents processed...")
        
        extraction_info = {
            'extraction_timestamp': doc.get('extraction_timestamp'),
            'extraction_method': doc.get('extraction_method'),
            'pages': doc.get('pages'),
            'text_s3_key': doc.get('text_s3_key'),
            'json_s3_key': doc.get('json_s3_key')
        }
        
        if update_bronze_metadata(doc_id, year, extraction_info):
            success_count += 1
        else:
            fail_count += 1
    
    logger.info(f"\n✅ Backfill complete!")
    logger.info(f"   Successfully updated: {success_count} PDFs")
    logger.info(f"   Failed: {fail_count} PDFs")

if __name__ == "__main__":
    main()
