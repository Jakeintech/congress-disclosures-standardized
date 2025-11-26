#!/usr/bin/env python3
"""
Backfill script to process all existing Bronze PDFs.
Creates Silver metadata and queues for extraction with error handling.
Uses S3 metadata tagging to avoid reprocessing.
"""
import boto3
import json
import os
from datetime import datetime

S3_BUCKET = 'congress-disclosures-standardized'
BRONZE_PREFIX = 'bronze/house/financial/year=2025/pdfs/2025/'
SILVER_PREFIX = 'silver/house/financial/documents/year=2025/'
SQS_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/464813693153/congress-disclosures-development-extract-queue'

s3 = boto3.client('s3', region_name='us-east-1')
sqs = boto3.client('sqs', region_name='us-east-1')

def has_been_processed(pdf_key):
    """Check if PDF has already been processed via S3 metadata."""
    try:
        response = s3.head_object(Bucket=S3_BUCKET, Key=pdf_key)
        metadata = response.get('Metadata', {})
        return metadata.get('processed') == 'true'
    except:
        return False

def mark_as_processed(pdf_key):
    """Mark PDF as processed in S3 metadata."""
    try:
        s3.copy_object(
            Bucket=S3_BUCKET,
            Key=pdf_key,
            CopySource={'Bucket': S3_BUCKET, 'Key': pdf_key},
            Metadata={'processed': 'true'},
            MetadataDirective='REPLACE'
        )
    except Exception as e:
        print(f"  Warning: Could not tag {pdf_key}: {e}")

def create_silver_metadata(doc_id, year, pdf_key, pdf_size):
    """Create Silver layer metadata file."""
    metadata = {
        'doc_id': doc_id,
        'year': year,
        'pdf_s3_key': pdf_key,
        'pdf_file_size_bytes': pdf_size,
        'created_at': datetime.utcnow().isoformat(),
        'extraction_status': 'queued',
        'pages': None,
        'has_embedded_text': None,
        'extraction_method': None,
        'char_count': None,
        'text_s3_key': None,
        'json_s3_key': None
    }
    
    metadata_key = f"{SILVER_PREFIX}{doc_id}/metadata.json"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=metadata_key,
        Body=json.dumps(metadata, indent=2),
        ContentType='application/json'
    )
    return metadata

def queue_for_extraction(doc_id, year):
    """Queue document for text extraction."""
    message = {
        'doc_id': doc_id,
        'year': year,
        's3_bucket': S3_BUCKET,
        's3_pdf_key': f'bronze/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf'
    }
    
    sqs.send_message(
        QueueUrl=SQS_QUEUE_URL,
        MessageBody=json.dumps(message)
    )

def process_bronze_pdfs():
    """Process all Bronze PDFs that haven't been processed yet."""
    print(f"Scanning Bronze layer: {BRONZE_PREFIX}")
    
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=BRONZE_PREFIX)
    
    total = 0
    processed = 0
    skipped = 0
    errors = 0
    
    for page in pages:
        for obj in page.get('Contents', []):
            pdf_key = obj['Key']
            if not pdf_key.endswith('.pdf'):
                continue
            
            total += 1
            doc_id = os.path.basename(pdf_key).replace('.pdf', '')
            
            # Check if already processed
            if has_been_processed(pdf_key):
                skipped += 1
                if total % 100 == 0:
                    print(f"  Progress: {total} scanned, {processed} queued, {skipped} skipped, {errors} errors")
                continue
            
            try:
                # Create Silver metadata
                metadata = create_silver_metadata(
                    doc_id=doc_id,
                    year=2025,
                    pdf_key=pdf_key,
                    pdf_size=obj['Size']
                )
                
                # Queue for extraction
                queue_for_extraction(doc_id, 2025)
                
                # Mark as processed
                mark_as_processed(pdf_key)
                
                processed += 1
                
                if total % 100 == 0:
                    print(f"  Progress: {total} scanned, {processed} queued, {skipped} skipped, {errors} errors")
                    
            except Exception as e:
                errors += 1
                print(f"  ERROR processing {doc_id}: {e}")
                # Continue with next document - errors are expected
    
    print(f"\n✅ Backfill Complete!")
    print(f"  Total PDFs: {total}")
    print(f"  Newly queued: {processed}")
    print(f"  Already processed: {skipped}")
    print(f"  Errors: {errors}")
    print(f"\nExtraction pipeline now processing {processed} documents...")
    print(f"Monitor queue: aws sqs get-queue-attributes --queue-url {SQS_QUEUE_URL} --attribute-names All --region us-east-1")

if __name__ == '__main__':
    process_bronze_pdfs()
