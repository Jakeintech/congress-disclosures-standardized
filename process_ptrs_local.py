#!/usr/bin/env python3
"""Process PTRs locally through complete pipeline."""

import sys
import os

# Add paths FIRST before any other imports
repo_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(repo_root, 'ingestion'))
sys.path.insert(0, os.path.join(repo_root, 'scripts'))

import json
import io
import boto3
import pandas as pd
import requests
import tempfile
from pathlib import Path

# Now import local modules
from lib.extractors.ptr_extractor import PTRExtractor
from lib.terraform_config import get_aws_config

config = get_aws_config()
S3_BUCKET = config.get('s3_bucket_id')
S3_REGION = config.get('s3_region', 'us-east-1')

s3_client = boto3.client('s3', region_name=S3_REGION)

# Load bronze CSV
csv_path = '/Users/jake/Downloads/congress-disclosures-2025-11-25.csv'
bronze_df = pd.read_csv(csv_path)
ptrs_df = bronze_df[bronze_df['Filing Type'] == 'P'].copy()
ptrs_df['doc_id'] = ptrs_df['Document ID'].astype(str)

# Get limit from command line
limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

# Filter to PTRs
ptr_docs = ptrs_df if limit is None else ptrs_df.head(limit)

print(f'Processing {len(ptr_docs)} PTRs...')
print()

results = []
for idx, row in ptr_docs.iterrows():
    doc_id = row['doc_id']
    year = 2025

    print(f"[{idx+1}/{len(ptr_docs)}] Processing {doc_id}: {row['First Name']} {row['Last Name']}")

    pdf_key = f'bronze/house/financial/disclosures/year={year}/doc_id={doc_id}/{doc_id}.pdf'
    structured_key = f'silver/house/financial/structured/year={year}/doc_id={doc_id}/structured.json'

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
        pdf_path = Path(tmp_pdf.name)

        try:
            # Try bronze first
            try:
                s3_client.download_file(S3_BUCKET, pdf_key, str(pdf_path))
                print(f'  ✓ Found in bronze')
            except:
                # Download from House
                house_url = f'https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}/{doc_id}.pdf'
                response = requests.get(house_url, timeout=30)
                response.raise_for_status()
                pdf_path.write_bytes(response.content)
                # Upload to bronze
                s3_client.put_object(
                    Bucket=S3_BUCKET,
                    Key=pdf_key,
                    Body=response.content,
                    ContentType='application/pdf'
                )
                print(f'  ✓ Downloaded ({len(response.content):,} bytes)')

            # Extract
            extractor = PTRExtractor(pdf_path=str(pdf_path))
            structured_data = extractor.extract_with_fallback()
            structured_data['filing_id'] = doc_id

            trans_count = len(structured_data.get('transactions', []))
            confidence = structured_data['extraction_metadata']['confidence_score']

            # Upload structured.json
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=structured_key,
                Body=json.dumps(structured_data, indent=2),
                ContentType='application/json'
            )

            print(f'  ✅ {trans_count} transactions, confidence: {confidence:.1%}')
            results.append({
                'doc_id': doc_id,
                'name': f"{row['First Name']} {row['Last Name']}",
                'transactions': trans_count,
                'confidence': confidence
            })

        except Exception as e:
            print(f'  ❌ Error: {e}')
            results.append({
                'doc_id': doc_id,
                'name': f"{row['First Name']} {row['Last Name']}",
                'error': str(e)
            })
        finally:
            if pdf_path.exists():
                pdf_path.unlink()

print()
print('='*80)
print('PROCESSING SUMMARY')
print('='*80)
success = [r for r in results if 'transactions' in r]
errors = [r for r in results if 'error' in r]
total_trans = sum(r.get('transactions', 0) for r in success)
avg_conf = sum(r.get('confidence', 0) for r in success) / len(success) if success else 0

print(f'Total processed: {len(results)}')
print(f'  ✅ Success: {len(success)}')
print(f'  ❌ Errors: {len(errors)}')
print(f'  📊 Total transactions: {total_trans}')
print(f'  🎯 Average confidence: {avg_conf:.1%}')
print()

if success:
    print('Top members by transaction count:')
    sorted_success = sorted(success, key=lambda x: x.get('transactions', 0), reverse=True)
    for r in sorted_success[:10]:
        print(f'  {r["name"]}: {r["transactions"]} transactions')
print()

if errors:
    print(f'Errors ({len(errors)}):')
    for r in errors[:5]:
        print(f'  {r["doc_id"]} ({r["name"]}): {r["error"]}')
    if len(errors) > 5:
        print(f'  ... and {len(errors)-5} more')

print()
print('Next: Run scripts/generate_ptr_transactions.py to create full table')
