#!/usr/bin/env python3
"""
Build Bronze Layer Manifest
Parses the existing XML index and creates a lightweight JSON manifest for quick lookups.
This should be run after Bronze ingestion to avoid repeated tag queries.
"""
import boto3
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter, defaultdict

def build_manifest_from_xml(year=2025):
    """Parse Bronze XML index and create structured manifest."""
    s3 = boto3.client('s3')
    bucket = 'congress-disclosures-standardized'
    
    # Download XML index
    xml_key = f'bronze/house/financial/year={year}/index/{year}FD.xml'
    print(f"Downloading {xml_key}...")
    
    try:
        response = s3.get_object(Bucket=bucket, Key=xml_key)
        xml_content = response['Body'].read()
    except Exception as e:
        print(f"Error downloading XML: {e}")
        return None
    
    # Parse XML
    print("Parsing XML...")
    root = ET.fromstring(xml_content)
    
    # Extract filing data - each <Member> element is a filing
    filings_by_type = defaultdict(list)
    filing_counts = Counter()
    total = 0
    
    for member in root.findall('.//Member'):
        doc_id = member.find('DocID')
        filing_type_elem = member.find('FilingType')
        filing_date_elem = member.find('FilingDate')
        
        if doc_id is None or filing_type_elem is None:
            continue
            
        doc_id_text = doc_id.text
        filing_type = filing_type_elem.text or 'UNKNOWN'
        filing_date = filing_date_elem.text if filing_date_elem is not None else None
        
        filings_by_type[filing_type].append({
            'doc_id': doc_id_text,
            'filing_date': filing_date,
            'year': year
        })
        filing_counts[filing_type] += 1
        total += 1
    
    # Build manifest
    manifest = {
        'year': year,
        'total_filings': total,
        'filing_type_counts': dict(filing_counts),
        'filing_types': {}
    }
    
    for filing_type, filings in filings_by_type.items():
        manifest['filing_types'][filing_type] = {
            'count': len(filings),
            'doc_ids': [f['doc_id'] for f in filings]
        }
    
    # Save locally
    output_dir = Path(f'data/bronze/house/financial/year={year}/index')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'manifest.json'
    
    with open(output_file, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\nManifest saved to {output_file}")
    
    # Upload to S3
    manifest_key = f'bronze/house/financial/year={year}/index/manifest.json'
    s3.put_object(
        Bucket=bucket,
        Key=manifest_key,
        Body=json.dumps(manifest, indent=2),
        ContentType='application/json'
    )
    
    print(f"Manifest uploaded to s3://{bucket}/{manifest_key}")
    
    # Print summary
    print("\n" + "="*60)
    print(f"FILING TYPE DISTRIBUTION ({year})")
    print("="*60)
    for filing_type, count in filing_counts.most_common():
        pct = (count / total) * 100
        print(f"{filing_type:10s} : {count:4d} ({pct:5.1f}%)")
    print("="*60)
    print(f"Total Filings: {total}")
    
    return manifest

def main():
    """Main entry point for pipeline runner."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, default=2025)
    args = parser.parse_args()

    manifest = build_manifest_from_xml(args.year)

    if manifest:
        print("\n✅ Bronze manifest created successfully!")
        print(f"\nTo list Type A doc IDs:")
        print(f"  jq '.filing_types.A.doc_ids[]' data/bronze/house/financial/year={args.year}/index/manifest.json")
        return 0
    return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
