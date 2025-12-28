#!/usr/bin/env python3
"""
Repair script to move silver layer objects from 'unknown' to correct filing type paths.
"""
import boto3
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime

S3_BUCKET = 'congress-disclosures-standardized'
UNKNOWN_PREFIX = 'silver/objects/unknown/'
SILVER_OBJECTS_PREFIX = 'silver/objects/'

s3 = boto3.client('s3', region_name='us-east-1')

def get_filing_type_map(year):
    """Download and parse XML index to build doc_id -> filing_type map."""
    print(f"Downloading XML index for {year}...")
    try:
        xml_key = f"bronze/house/financial/year={year}/index/{year}FD.xml"
        response = s3.get_object(Bucket=S3_BUCKET, Key=xml_key)
        xml_content = response['Body'].read()
        
        root = ET.fromstring(xml_content)
        mapping = {}
        for member in root.findall('Member'):
            doc_id = member.find('DocID').text
            filing_type = member.find('FilingType').text
            if doc_id and filing_type:
                mapping[doc_id] = filing_type
        
        print(f"Loaded {len(mapping)} filing types from index")
        return mapping
    except Exception as e:
        print(f"Warning: Could not load XML index: {e}")
        return {}

def repair_paths():
    """Move objects from unknown to correct paths."""
    # Load filing types (assuming 2025 for now as per task)
    year = 2025
    filing_type_map = get_filing_type_map(year)
    
    print(f"Scanning {UNKNOWN_PREFIX}...")
    
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=UNKNOWN_PREFIX)
    
    moved_count = 0
    error_count = 0
    skipped_count = 0
    
    for page in pages:
        for obj in page.get('Contents', []):
            old_key = obj['Key']
            
            # Expected format: silver/objects/unknown/{year}/{doc_id}/extraction.json
            parts = old_key.split('/')
            if len(parts) < 6:
                print(f"Skipping malformed key: {old_key}")
                continue
                
            doc_id = parts[-2]
            doc_year = parts[-3]
            
            if doc_year != str(year):
                # If we encounter other years, we might need to load their index
                print(f"Skipping year {doc_year} (only loaded {year})")
                continue

            filing_type = filing_type_map.get(doc_id)
            
            if not filing_type:
                print(f"Could not find filing type for {doc_id}, skipping")
                skipped_count += 1
                continue
                
            # Normalize filing type for path
            filing_type_path = filing_type.replace('/', '_').replace(' ', '_').lower()
            if len(filing_type_path) == 1:
                filing_type_path = f"type_{filing_type_path}"
            
            new_key = f"{SILVER_OBJECTS_PREFIX}{filing_type_path}/{doc_year}/{doc_id}/extraction.json"
            
            if new_key == old_key:
                continue
                
            print(f"Moving {doc_id}: unknown -> {filing_type_path}")
            
            try:
                # Copy
                s3.copy_object(
                    Bucket=S3_BUCKET,
                    Key=new_key,
                    CopySource={'Bucket': S3_BUCKET, 'Key': old_key}
                )
                
                # Delete old
                s3.delete_object(Bucket=S3_BUCKET, Key=old_key)
                
                moved_count += 1
            except Exception as e:
                print(f"Error moving {old_key}: {e}")
                error_count += 1

    print(f"\nRepair Complete!")
    print(f"  Moved: {moved_count}")
    print(f"  Skipped (unknown type): {skipped_count}")
    print(f"  Errors: {error_count}")

if __name__ == '__main__':
    repair_paths()
