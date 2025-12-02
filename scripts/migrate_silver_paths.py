#!/usr/bin/env python3
"""
Migration script to:
1. Move silver layer objects to Hive-style paths (filing_type=X/year=Y/doc_id=Z).
2. Inject 'bronze_metadata' and 'bronze_pdf_s3_key' into the JSON.
"""
import boto3
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime

S3_BUCKET = 'congress-disclosures-standardized'
SILVER_OBJECTS_PREFIX = 'silver/objects/'

s3 = boto3.client('s3', region_name='us-east-1')

def get_bronze_metadata_map(year):
    """Download and parse XML index to build doc_id -> metadata map."""
    print(f"Downloading XML index for {year}...")
    try:
        xml_key = f"bronze/house/financial/year={year}/index/{year}FD.xml"
        response = s3.get_object(Bucket=S3_BUCKET, Key=xml_key)
        xml_content = response['Body'].read()
        
        root = ET.fromstring(xml_content)
        mapping = {}
        for member in root.findall('Member'):
            doc_id = member.find('DocID').text
            if not doc_id:
                continue
                
            mapping[doc_id] = {
                'filer_name': f"{member.find('First').text} {member.find('Last').text}",
                'filing_date': member.find('FilingDate').text,
                'state_district': member.find('StateDst').text,
                'filing_type': member.find('FilingType').text
            }
        
        print(f"Loaded metadata for {len(mapping)} documents")
        return mapping
    except Exception as e:
        print(f"Warning: Could not load XML index: {e}")
        return {}

def migrate_paths():
    """Move objects to Hive-style paths and update content."""
    year = 2025
    metadata_map = get_bronze_metadata_map(year)
    
    # List all objects in silver/objects/
    # Note: We need to handle both old paths (type_p/...) and potentially already migrated ones if re-run
    print(f"Scanning {SILVER_OBJECTS_PREFIX}...")
    
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=SILVER_OBJECTS_PREFIX)
    
    processed_count = 0
    moved_count = 0
    error_count = 0
    
    for page in pages:
        for obj in page.get('Contents', []):
            old_key = obj['Key']
            
            # Skip if already in Hive format (filing_type=...)
            if 'filing_type=' in old_key:
                continue
                
            # Expected format: silver/objects/{type_folder}/{year}/{doc_id}/extraction.json
            # e.g., silver/objects/type_p/2025/12345/extraction.json
            parts = old_key.split('/')
            
            # Basic validation
            if len(parts) < 6 or not old_key.endswith('extraction.json'):
                continue
                
            type_folder = parts[2] # type_p or unknown
            doc_year = parts[3]
            doc_id = parts[4]
            
            if doc_year != str(year):
                continue

            # Determine filing type
            filing_type = None
            if type_folder.startswith('type_'):
                filing_type = type_folder.replace('type_', '').upper()
            
            # Lookup metadata
            metadata = metadata_map.get(doc_id, {})
            
            # Fallback for filing type if unknown in path
            if not filing_type and metadata.get('filing_type'):
                filing_type = metadata['filing_type']
            
            if not filing_type:
                print(f"Skipping {doc_id}: Could not determine filing type")
                continue
                
            # Construct new Hive-style path
            # silver/objects/filing_type={type}/year={year}/doc_id={doc_id}/extraction.json
            
            # Normalize filing type for path (e.g., P -> type_p)
            filing_type_path = filing_type.replace('/', '_').replace(' ', '_').lower()
            if len(filing_type_path) == 1:
                filing_type_path = f"type_{filing_type_path}"
                
            new_key = f"{SILVER_OBJECTS_PREFIX}filing_type={filing_type_path}/year={doc_year}/doc_id={doc_id}/extraction.json"
            
            print(f"Migrating {doc_id} -> {new_key}")
            
            try:
                # Read existing content
                resp = s3.get_object(Bucket=S3_BUCKET, Key=old_key)
                data = json.loads(resp['Body'].read())
                
                # Update content
                changed = False
                
                # 1. Add bronze_metadata
                if 'bronze_metadata' not in data:
                    data['bronze_metadata'] = {
                        'filer_name': metadata.get('filer_name'),
                        'filing_date': metadata.get('filing_date'),
                        'state_district': metadata.get('state_district')
                    }
                    changed = True
                    
                # 2. Add bronze_pdf_s3_key
                if 'bronze_pdf_s3_key' not in data:
                    data['bronze_pdf_s3_key'] = f"bronze/house/financial/year={doc_year}/pdfs/{doc_year}/{doc_id}.pdf"
                    changed = True
                
                # Write to new location
                s3.put_object(
                    Bucket=S3_BUCKET,
                    Key=new_key,
                    Body=json.dumps(data, indent=2),
                    ContentType='application/json'
                )
                
                # Delete old object
                s3.delete_object(Bucket=S3_BUCKET, Key=old_key)
                
                moved_count += 1
                
            except Exception as e:
                print(f"Error processing {old_key}: {e}")
                error_count += 1
                
            processed_count += 1

    print(f"\nMigration Complete!")
    print(f"  Processed: {processed_count}")
    print(f"  Moved: {moved_count}")
    print(f"  Errors: {error_count}")

if __name__ == '__main__':
    migrate_paths()
