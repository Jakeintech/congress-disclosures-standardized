#!/usr/bin/env python3
"""
Rebuild silver_documents.json manifest from DynamoDB.
Ensures 100% accuracy by reading directly from the source of truth.
"""
import json
import boto3
from decimal import Decimal

def decimal_default(obj):
    """JSON encoder for Decimal types."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError

def rebuild_silver_manifest():
    """Scan DynamoDB and rebuild silver_documents.json."""
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    s3 = boto3.client('s3', region_name='us-east-1')
    
    table = dynamodb.Table('house_fd_documents')
    
    print("Scanning DynamoDB table...")
    documents = []
    
    # Scan table (handles pagination automatically)
    scan_kwargs = {}
    done = False
    start_key = None
    
    while not done:
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key
        response = table.scan(**scan_kwargs)
        documents.extend(response.get('Items', []))
        start_key = response.get('LastEvaluatedKey', None)
        done = start_key is None
        print(f"  Scanned {len(documents)} documents so far...")
    
    print(f"Total documents scanned: {len(documents)}")
    
    # Calculate stats
    total_pages = sum(int(d.get('pages') or 0) for d in documents)
    total_chars = sum(int(d.get('char_count') or 0) for d in documents)
    
    extraction_stats = {
        'success': sum(1 for d in documents if d.get('extraction_status') == 'success'),
        'pending': sum(1 for d in documents if d.get('extraction_status') == 'pending'),
        'failed': sum(1 for d in documents if d.get('extraction_status') == 'failed'),
    }
    
    # Build manifest
    manifest = {
        'generated_at': '2025-11-26T04:24:00Z',  # UTC timestamp
        'total_documents': len(documents),
        'stats': {
            'total_documents': len(documents),
            'total_pages': total_pages,
            'extraction_stats': extraction_stats
        },
        'documents': documents
    }
    
    # Write to local file
    output_path = 'website/data/silver_documents_v2.json'
    with open(output_path, 'w') as f:
        json.dump(manifest, f, default=decimal_default, indent=2)
    
    print(f"Wrote manifest to {output_path}")
    print(f"  Total documents: {len(documents)}")
    print(f"  Extraction stats: {extraction_stats}")
    
    # Upload to S3
    print("Uploading to S3...")
    s3.upload_file(
        output_path,
        'congress-disclosures-standardized',
        'website/data/silver_documents_v2.json',
        ExtraArgs={'CacheControl': 'no-cache', 'ContentType': 'application/json'}
    )
    print("✅ Manifest uploaded to S3")
    
    return manifest

def main():
    """Main entry point."""
    rebuild_silver_manifest()
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
