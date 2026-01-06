#!/usr/bin/env python3
"""Audit extraction results and generate comprehensive statistics."""
import boto3
import json
import pandas as pd

s3 = boto3.client('s3')
BUCKET = 'congress-disclosures-standardized'

results = {'P': [], 'C': [], 'A': [], 'X': [], 'T': [], 'Unknown': []}

# List all structured JSON files
prefix = 'silver/objects/type_p/2025/'
paginator = s3.get_paginator('list_objects_v2')

for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
    for obj in page.get('Contents', []):
        key = obj['Key']
        if key.endswith('.json'):
            filing_type = key.split('filing_type=')[1].split('/')[0]
            try:
                response = s3.get_object(Bucket=BUCKET, Key=key)
                data = json.loads(response['Body'].read())
                stats = {
                    'doc_id': data.get('doc_id'),
                    'confidence': data.get('confidence_score', 0),
                    'ocr_followup': data.get('requires_additional_ocr', False),
                    'missing': len(data.get('missing_fields', [])),
                    'has_name': bool(data.get('document_header', {}).get('filer_name')),
                    'has_date': bool(data.get('document_header', {}).get('filing_date')),
                    'transactions': len(data.get('transactions', [])) if 'transactions' in data else None,
                }
                results[filing_type].append(stats)
            except Exception as e:
                print(f"Error {key}: {e}")

# Generate report
print("\n" + "=" * 80)
print("EXTRACTION AUDIT REPORT")
print("=" * 80)

for ft, records in results.items():
    if not records:
        continue
    df = pd.DataFrame(records)
    print(f"\n{'─' * 80}\nFiling Type: {ft} ({len(records)} docs)\n{'─' * 80}")
    print(f"Confidence: avg={df['confidence'].mean():.1%} med={df['confidence'].median():.1%}")
    print(f"OCR Follow-up Recommended: {df['ocr_followup'].sum()} ({df['ocr_followup'].mean():.1%})")
    print(f"Has Name: {df['has_name'].sum()} ({df['has_name'].mean():.1%})")
    print(f"Has Date: {df['has_date'].sum()} ({df['has_date'].mean():.1%})")
    if df['transactions'].notna().any():
        print(f"Transactions: total={df['transactions'].sum()} avg={df['transactions'].mean():.1f}")
