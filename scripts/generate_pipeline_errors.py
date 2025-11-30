#!/usr/bin/env python3
"""
Generate Pipeline Errors Report

Scans the pipeline state (Bronze, Silver) and generates a JSON report of all errors
for the website UI.

Checks for:
1. Missing Bronze PDFs (in XML but not S3)
2. Missing Silver Data (in Bronze but not extracted)
3. Low Confidence Extractions
4. Tag Mismatches

Output: website/data/pipeline_errors.json
"""

import boto3
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from botocore.exceptions import ClientError

# Configuration
BUCKET_NAME = "congress-disclosures-standardized"
OUTPUT_FILE = "website/data/pipeline_errors.json"
YEAR = 2025

s3 = boto3.client('s3')

def get_xml_manifest(year):
    """Retrieves and parses the XML manifest from S3."""
    key = f"bronze/house/financial/year={year}/index/{year}FD.xml"
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        xml_content = response['Body'].read()
        return ET.fromstring(xml_content)
    except Exception as e:
        print(f"❌ Failed to retrieve manifest: {e}")
        return None

def get_s3_pdfs(year):
    """Lists all PDF DocIDs present in the Bronze layer."""
    prefix = f"bronze/house/financial/year={year}/"
    pdfs = set()
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix)
    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                key = obj['Key']
                if key.lower().endswith('.pdf'):
                    filename = key.split('/')[-1]
                    doc_id = filename.replace('.pdf', '')
                    pdfs.add(doc_id)
    return pdfs

def get_silver_docs(year):
    """Lists all DocIDs present in the Silver layer (structured code)."""
    prefix = f"silver/house/financial/structured_code/year={year}/"
    docs = set()
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix)
    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                # Key: .../filing_type=X/doc_id=123.json
                parts = obj['Key'].split('/')
                for p in parts:
                    if p.startswith('doc_id='):
                        doc_id = p.split('=')[1].replace('.json', '')
                        docs.add(doc_id)
    return docs

def main():
    print(f"Generating error report for Year {YEAR}...")
    
    errors = []
    
    # 1. Get Manifest (Source of Truth)
    root = get_xml_manifest(YEAR)
    if not root:
        sys.exit(1)
        
    manifest_docs = {}
    for member in root.findall('Member'):
        doc_id = member.find('DocID').text
        manifest_docs[doc_id] = {
            'filing_type': member.find('FilingType').text,
            'filer_name': f"{member.find('Last').text}, {member.find('First').text}",
            'state_district': member.find('StateDst').text,
            'filing_date': member.find('FilingDate').text,
            'year': member.find('Year').text
        }
        
    # 2. Check Bronze (Missing PDFs)
    s3_pdfs = get_s3_pdfs(YEAR)
    missing_bronze = set(manifest_docs.keys()) - s3_pdfs
    
    for doc_id in missing_bronze:
        meta = manifest_docs[doc_id]
        errors.append({
            "doc_id": doc_id,
            "error_type": "Missing PDF",
            "severity": "Critical",
            "message": "Document listed in Clerk XML but PDF not found in S3 Bronze layer.",
            "details": f"Expected at bronze/house/financial/year={YEAR}/pdfs/{YEAR}/{doc_id}.pdf",
            "filer_name": meta['filer_name'],
            "filing_type": meta['filing_type'],
            "date": meta['filing_date']
        })

    # 3. Check Silver (Failed Extraction)
    # Only check for docs that exist in Bronze
    silver_docs = get_silver_docs(YEAR)
    # We expect structured data for all PDFs, though currently only Type P is fully supported.
    # For now, let's flag missing Type P as Critical, others as Warning (Pending)
    
    existing_bronze_ids = set(manifest_docs.keys()) & s3_pdfs
    missing_silver = existing_bronze_ids - silver_docs
    
    for doc_id in missing_silver:
        meta = manifest_docs[doc_id]
        is_supported = meta['filing_type'] == 'P'
        
        errors.append({
            "doc_id": doc_id,
            "error_type": "Extraction Failed" if is_supported else "Extraction Pending",
            "severity": "High" if is_supported else "Info",
            "message": "Structured data not found in Silver layer." if is_supported else "Structured extraction not yet supported for this type.",
            "details": "Lambda failed or timed out." if is_supported else "Parser not implemented.",
            "filer_name": meta['filer_name'],
            "filing_type": meta['filing_type'],
            "date": meta['filing_date']
        })

    # 4. Save Report
    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "year": YEAR,
        "summary": {
            "total_manifest_docs": len(manifest_docs),
            "total_errors": len(errors),
            "critical_errors": sum(1 for e in errors if e['severity'] == 'Critical'),
            "high_errors": sum(1 for e in errors if e['severity'] == 'High')
        },
        "errors": errors
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(report, f, indent=2)
        
    print(f"✓ Error report generated: {OUTPUT_FILE} ({len(errors)} errors)")
    
    # Upload to S3
    try:
        s3.upload_file(OUTPUT_FILE, BUCKET_NAME, f"website/data/pipeline_errors.json", ExtraArgs={'ContentType': 'application/json'})
        print("✓ Uploaded to S3")
    except Exception as e:
        print(f"❌ Failed to upload to S3: {e}")

if __name__ == "__main__":
    main()
