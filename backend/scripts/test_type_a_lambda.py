#!/usr/bin/env python3
"""
Trigger extraction for Type A filings by invoking Lambda directly.
Simpler approach than SQS queue.
"""
import boto3
import json
from pathlib import Path

def main():
    # Load Bronze manifest
    manifest_path = Path('data/bronze/house/financial/year=2025/index/manifest.json')
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    type_a_docs = manifest.get('filing_types', {}).get('A', {}).get('doc_ids', [])
    print(f"Found {len(type_a_docs)} Type A filings to re-extract")
    
    if not type_a_docs:
        print("No Type A filings found in manifest")
        return
    
    # Test with first 3 docs
    test_docs = type_a_docs[:3]
    print(f"\nTesting with {len(test_docs)} documents first: {test_docs}")
    
    lambda_client = boto3.client('lambda')
    
    for doc_id in test_docs:
        payload = {
            'Records': [{
                'body': json.dumps({
                    'doc_id': doc_id,
                    'year': 2025,
                    'filing_type': 'A',
                    's3_bucket': 'congress-disclosures-standardized',
                    's3_pdf_key': f'bronze/house/financial/year=2025/pdfs/2025/{doc_id}.pdf',
                    's3_text_key': f'bronze/house/financial/year=2025/raw_text/{doc_id}.txt'
                })
            }]
        }
        
        print(f"\n  Invoking Lambda for doc_id={doc_id}...")
        try:
            response = lambda_client.invoke(
                FunctionName='congress-disclosures-development-extract-structured-code',
                InvocationType='RequestResponse',  # Synchronous
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            if 'errorMessage' in result:
                print(f"  ✗ Error: {result['errorMessage']}")
            else:
                print(f"  ✓ Success: {result.get('statusCode', 'unknown status')}")
                
        except Exception as e:
            print(f"  ✗ Exception: {e}")
    
    print(f"\n✅ Test extraction complete!")
    print("Check Silver layer: silver/objects/type_a/2025/")

if __name__ == '__main__':
    main()
