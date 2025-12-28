#!/usr/bin/env python3
"""Quick check of Silver layer extraction samples."""

import boto3
import json
from collections import defaultdict

s3 = boto3.client('s3')

def check_silver_structured():
    """Check structured extraction JSON files."""
    samples_by_type = defaultdict(lambda: {'count': 0, 'samples': []})

    # List structured JSON files (limit to reasonable number)
    response = s3.list_objects_v2(
        Bucket='congress-disclosures-standardized',
        Prefix='silver/house/financial/structured/year=2025/',
        MaxKeys=100
    )

    for obj in response.get('Contents', []):
        if obj['Key'].endswith('.json'):
            try:
                # Get just the object metadata, not full content
                head = s3.head_object(
                    Bucket='congress-disclosures-standardized',
                    Key=obj['Key']
                )

                # Extract doc_id from filename
                # Format: silver/.../doc_id=XXXXX.json
                doc_id = obj['Key'].split('doc_id=')[1].replace('.json', '') if 'doc_id=' in obj['Key'] else 'unknown'

                # For now just count files
                samples_by_type['All']['count'] += 1
                if len(samples_by_type['All']['samples']) < 5:
                    samples_by_type['All']['samples'].append(doc_id)

            except Exception as e:
                print(f"Error checking {obj['Key']}: {e}")

    return samples_by_type

def main():
    print("="*80)
    print("SILVER LAYER EXTRACTION CHECK")
    print("="*80)

    samples = check_silver_structured()

    if not samples:
        print("\n⚠️  No extractions found in Silver layer yet")
        print("   Pipeline may still be processing")
        return

    for filing_type, data in samples.items():
        print(f"\n{filing_type}:")
        print(f"  Files found: {data['count']}")
        if data['samples']:
            print(f"  Sample doc_ids: {', '.join(data['samples'][:5])}")

    print("\n✓ Check complete")

if __name__ == '__main__':
    main()
