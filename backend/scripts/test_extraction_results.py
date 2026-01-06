#!/usr/bin/env python3
"""
Test extraction results and output a table of samples for each filing type.

This script:
1. Queries Silver layer for extracted documents
2. Groups by filing type
3. Validates extraction quality
4. Outputs summary table with sample doc_ids
"""

import boto3
import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, List
import sys

s3 = boto3.client('s3')

BUCKET = 'congress-disclosures-standardized'
SILVER_PREFIX = 'silver/house/financial/documents'

def get_extraction_samples():
    """Get sample extracted documents from Silver layer."""
    samples_by_type = defaultdict(list)

    # List all Parquet files in Silver/documents
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(
        Bucket=BUCKET,
        Prefix=SILVER_PREFIX
    )

    doc_count = 0
    for page in pages:
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.parquet'):
                # Download and parse Parquet
                try:
                    response = s3.get_object(Bucket=BUCKET, Key=obj['Key'])
                    # For now, just track that we found files
                    doc_count += 1
                except Exception as e:
                    print(f"Error reading {obj['Key']}: {e}", file=sys.stderr)

    return samples_by_type, doc_count

def check_structured_extractions():
    """Check structured extraction JSON files in Silver layer."""
    structured_prefix = 'silver/house/financial/structured'

    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(
        Bucket=BUCKET,
        Prefix=structured_prefix,
        MaxKeys=100  # Limit for testing
    )

    samples_by_type = defaultdict(lambda: {'count': 0, 'samples': [], 'success': 0, 'failed': 0})

    for page in pages:
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.json'):
                try:
                    # Download JSON
                    response = s3.get_object(Bucket=BUCKET, Key=obj['Key'])
                    data = json.loads(response['Body'].read())

                    filing_type = data.get('filing_type', 'Unknown')
                    doc_id = data.get('doc_id', 'Unknown')
                    confidence = data.get('metadata', {}).get('confidence_score', 0)

                    samples_by_type[filing_type]['count'] += 1

                    if confidence >= 0.7:
                        samples_by_type[filing_type]['success'] += 1
                    else:
                        samples_by_type[filing_type]['failed'] += 1

                    # Keep first 3 samples
                    if len(samples_by_type[filing_type]['samples']) < 3:
                        samples_by_type[filing_type]['samples'].append({
                            'doc_id': doc_id,
                            'confidence': confidence,
                            's3_key': obj['Key']
                        })

                except Exception as e:
                    print(f"Error reading {obj['Key']}: {e}", file=sys.stderr)

    return samples_by_type

def print_results_table(samples_by_type):
    """Print formatted table of extraction results."""
    print("\n" + "="*100)
    print("EXTRACTION RESULTS BY FILING TYPE")
    print("="*100)
    print(f"{'Filing Type':<25} {'Count':>8} {'Success':>8} {'Failed':>8} {'Rate':>8} {'Sample Doc IDs':<30}")
    print("-"*100)

    total_count = 0
    total_success = 0
    total_failed = 0

    # Sort by count descending
    for filing_type in sorted(samples_by_type.keys(), key=lambda x: samples_by_type[x]['count'], reverse=True):
        data = samples_by_type[filing_type]
        count = data['count']
        success = data['success']
        failed = data['failed']
        rate = (success / count * 100) if count > 0 else 0

        total_count += count
        total_success += success
        total_failed += failed

        # Get sample doc_ids
        sample_ids = ', '.join([s['doc_id'] for s in data['samples'][:3]])

        print(f"{filing_type:<25} {count:>8} {success:>8} {failed:>8} {rate:>7.1f}% {sample_ids:<30}")

    print("-"*100)
    overall_rate = (total_success / total_count * 100) if total_count > 0 else 0
    print(f"{'TOTAL':<25} {total_count:>8} {total_success:>8} {total_failed:>8} {overall_rate:>7.1f}%")
    print("="*100)

def main():
    """Main execution."""
    print("Checking Silver layer extraction results...")
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Check structured extractions
    samples_by_type = check_structured_extractions()

    if not samples_by_type:
        print("\n⚠️  No structured extractions found yet in Silver layer.")
        print("   Extractions may still be in progress.")
        print("   Check queue status with: make check-extraction-queue")
        return 1

    # Print results
    print_results_table(samples_by_type)

    # Print detailed samples
    print("\n" + "="*100)
    print("SAMPLE DETAILS")
    print("="*100)

    for filing_type, data in sorted(samples_by_type.items()):
        if data['samples']:
            print(f"\n{filing_type}:")
            for sample in data['samples']:
                print(f"  - Doc ID: {sample['doc_id']}")
                print(f"    Confidence: {sample['confidence']:.2f}")
                print(f"    S3 Key: {sample['s3_key']}")

    print("\n✓ Extraction validation complete")
    return 0

if __name__ == '__main__':
    sys.exit(main())
