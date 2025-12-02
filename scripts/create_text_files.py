#!/usr/bin/env python3
"""
Create uncompressed text.txt files in the documents/ path from compressed raw_text.txt.gz files.
This makes text files accessible at the expected URL structure.
"""
import boto3
import gzip
import json
from io import BytesIO

S3_BUCKET = "congress-disclosures-standardized"
S3_REGION = "us-east-1"

s3 = boto3.client("s3", region_name=S3_REGION)

def get_documents_from_dynamodb():
    """Get list of documents from DynamoDB."""
    dynamodb = boto3.resource("dynamodb", region_name=S3_REGION)
    table = dynamodb.Table("house_fd_documents")
    
    print("📥 Loading documents from DynamoDB...")
    documents = []
    scan_kwargs = {}
    
    while True:
        response = table.scan(**scan_kwargs)
        documents.extend(response.get("Items", []))
        
        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
    
    print(f"✅ Loaded {len(documents)} documents")
    return documents

def find_text_file(doc_id, year):
    """Find the compressed text file for a document."""
    # Try different extraction methods
    extraction_methods = ["direct_text", "ocr_text", "pypdf"]
    
    for method in extraction_methods:
        text_key = (
            f"silver/house/financial/text/"
            f"extraction_method={method}/year={year}/"
            f"doc_id={doc_id}/raw_text.txt.gz"
        )
        
        try:
            s3.head_object(Bucket=S3_BUCKET, Key=text_key)
            return text_key
        except s3.exceptions.ClientError:
            continue
    
    return None

def create_text_file(doc_id, year):
    """Create uncompressed text.txt file in documents/ path."""
    # Find source compressed file
    source_key = find_text_file(doc_id, year)
    if not source_key:
        return False
    
    # Destination path
    dest_key = f"silver/house/financial/documents/year={year}/{doc_id}/text.txt"
    
    try:
        # Download and decompress
        print(f"  Processing {doc_id}...")
        response = s3.get_object(Bucket=S3_BUCKET, Key=source_key)
        compressed_data = response["Body"].read()
        text_content = gzip.decompress(compressed_data).decode("utf-8")
        
        # Upload uncompressed text
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=dest_key,
            Body=text_content.encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
            CacheControl="max-age=3600",
            Metadata={
                "doc_id": doc_id,
                "year": str(year),
                "source": source_key
            }
        )
        
        return True
    except Exception as e:
        print(f"  ⚠️  Error processing {doc_id}: {e}")
        return False

def main():
    print("🚀 Creating uncompressed text.txt files...")
    print("=" * 60)
    
    # Get all documents
    documents = get_documents_from_dynamodb()
    
    # Process each document
    success_count = 0
    skipped_count = 0
    
    for doc in documents:
        doc_id = str(doc.get("doc_id", ""))
        year = int(doc.get("year", 2025))
        
        # Check if text.txt already exists
        dest_key = f"silver/house/financial/documents/year={year}/{doc_id}/text.txt"
        try:
            s3.head_object(Bucket=S3_BUCKET, Key=dest_key)
            skipped_count += 1
            continue
        except s3.exceptions.ClientError:
            pass
        
        # Create text file
        if create_text_file(doc_id, year):
            success_count += 1
        
        # Progress update
        if (success_count + skipped_count) % 100 == 0:
            print(f"  Progress: {success_count} created, {skipped_count} skipped")
    
    print("=" * 60)
    print(f"✅ Complete!")
    print(f"  Created: {success_count} text.txt files")
    print(f"  Skipped: {skipped_count} (already exist)")
    print(f"  Total: {len(documents)} documents")

if __name__ == "__main__":
    main()
