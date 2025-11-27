#!/usr/bin/env python3
"""
Run Silver pipeline on all Bronze PDFs.

This script triggers extraction for all PDFs in the Bronze layer,
re-processing them with the latest extractors.
"""

import boto3
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

s3 = boto3.client('s3')
sqs = boto3.client('sqs')

BUCKET = 'congress-disclosures-standardized'
QUEUE_URL = None  # Will be discovered

def get_extract_queue_url():
    """Get the extraction queue URL from Terraform output or by name."""
    # Try to get from Terraform output first
    try:
        import subprocess
        import json
        result = subprocess.run(
            ['terraform', 'output', '-json', 'sqs_extraction_queue_url'],
            cwd='infra/terraform',
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            queue_url = json.loads(result.stdout)
            return queue_url
    except:
        pass

    # Fallback: try common queue names
    for queue_name in ['congress-disclosures-development-extract-queue', 'house-fd-extract-queue']:
        try:
            response = sqs.get_queue_url(QueueName=queue_name)
            return response['QueueUrl']
        except:
            continue

    raise Exception("Could not find extraction queue. Run 'make deploy' first.")

def list_bronze_pdfs():
    """List all PDFs in Bronze layer."""
    pdfs = []
    paginator = s3.get_paginator('list_objects_v2')

    # List from bronze/house/financial/ prefix
    pages = paginator.paginate(
        Bucket=BUCKET,
        Prefix='bronze/house/financial/'
    )

    for page in pages:
        for obj in page.get('Contents', []):
            key = obj['Key']
            if key.endswith('.pdf'):
                pdfs.append(key)

    return pdfs

def send_to_extraction_queue(pdf_key):
    """Send a PDF to the extraction queue."""
    # Extract doc_id and year from path
    # Format: bronze/house/financial/year=YYYY/filing_type=X/pdfs/DOCID.pdf
    parts = pdf_key.split('/')
    year = None
    doc_id = None

    for part in parts:
        if part.startswith('year='):
            year = int(part.split('=')[1])
        if part.endswith('.pdf'):
            doc_id = part.replace('.pdf', '')

    if not year or not doc_id:
        print(f"⚠️  Skipping {pdf_key} - couldn't parse year/doc_id")
        return False

    message = {
        'doc_id': doc_id,
        'year': year,
        's3_pdf_key': pdf_key
    }

    try:
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(message)
        )
        return True
    except Exception as e:
        print(f"❌ Error sending {doc_id}: {e}")
        return False

def main():
    """Main execution."""
    import argparse
    global QUEUE_URL

    parser = argparse.ArgumentParser(description='Run Silver pipeline on all Bronze PDFs')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')
    parser.add_argument('--limit', type=int, help='Limit number of PDFs to process (for testing)')
    args = parser.parse_args()

    print("=" * 60)
    print("Silver Pipeline Runner")
    print("=" * 60)

    # Get queue URL
    try:
        QUEUE_URL = get_extract_queue_url()
        print(f"✓ Found extraction queue: {QUEUE_URL}")
    except Exception as e:
        print(f"❌ Error finding queue: {e}")
        print("Make sure infrastructure is deployed (make deploy)")
        return 1

    # List all PDFs
    print("\nListing Bronze PDFs...")
    pdfs = list_bronze_pdfs()

    # Apply limit if specified
    if args.limit:
        pdfs = pdfs[:args.limit]
        print(f"✓ Found {len(pdfs)} PDFs in Bronze layer (limited to {args.limit})")
    else:
        print(f"✓ Found {len(pdfs)} PDFs in Bronze layer")

    if not pdfs:
        print("No PDFs found. Run 'make ingest-year YEAR=2025' first.")
        return 1

    # Ask for confirmation unless --yes flag
    if not args.yes:
        print(f"\nThis will queue {len(pdfs)} PDFs for re-extraction.")
        print("This is safe - it will re-process files with the latest extractors.")
        response = input("Continue? [y/N]: ")

        if response.lower() != 'y':
            print("Cancelled.")
            return 0
    else:
        print(f"\nProcessing {len(pdfs)} PDFs (--yes flag specified)...")

    # Send to queue
    print("\nQueueing PDFs for extraction...")
    success_count = 0

    for i, pdf_key in enumerate(pdfs, 1):
        if send_to_extraction_queue(pdf_key):
            success_count += 1
            if i % 50 == 0:
                print(f"  Queued {i}/{len(pdfs)} PDFs...")

    print(f"\n✓ Queued {success_count}/{len(pdfs)} PDFs successfully")
    print(f"\nMonitor progress:")
    print(f"  make check-extraction-queue    # Check queue status")
    print(f"  make logs-extract              # Tail extraction logs")

    return 0

if __name__ == '__main__':
    sys.exit(main())
