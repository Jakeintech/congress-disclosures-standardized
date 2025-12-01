#!/usr/bin/env python3
"""
Count filing types in Bronze layer using S3 object tags.
"""
import boto3
from collections import Counter
import json

s3 = boto3.client('s3')
bucket = 'congress-disclosures-standardized'
prefix = 'bronze/house/financial/year=2025/pdfs/'

filing_types = Counter()
total = 0
errors = 0

print(f"Scanning {bucket}/{prefix}...")

paginator = s3.get_paginator('list_objects_v2')
for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
    if 'Contents' not in page:
        continue
        
    for obj in page['Contents']:
        key = obj['Key']
        if not key.endswith('.pdf'):
            continue
            
        total += 1
        try:
            response = s3.get_object_tagging(Bucket=bucket, Key=key)
            tags = {tag['Key']: tag['Value'] for tag in response['TagSet']}
            filing_type = tags.get('filing_type', 'UNKNOWN')
            filing_types[filing_type] += 1
            
            if total % 100 == 0:
                print(f"  Processed {total} PDFs...")
                
        except Exception as e:
            errors += 1
            if errors < 5:
                print(f"  Error on {key}: {e}")

print("\n" + "="*60)
print(f"FILING TYPE DISTRIBUTION (2025)")
print("="*60)
for filing_type, count in filing_types.most_common():
    pct = (count / total) * 100
    print(f"{filing_type:10s} : {count:4d} ({pct:5.1f}%)")
print("="*60)
print(f"Total PDFs: {total}")
print(f"Errors: {errors}")
