#!/usr/bin/env python3
"""
Migrate Bronze layer to new structure with filing_type partitioning.
Old: bronze/house/financial/year={YEAR}/pdfs/{DocID}.pdf
New: bronze/house/financial/year={YEAR}/filing_type={TYPE}/pdfs/{DocID}.pdf
"""

import boto3
import argparse
import logging
import xml.etree.ElementTree as ET
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

S3_BUCKET = 'congress-disclosures-standardized'

def get_filing_type_map(year, s3_client):
    """
    Read the XML index for the given year and build a map of DocID -> FilingType.
    """
    try:
        # The XML index is typically at bronze/house/financial/year={YEAR}/index.xml
        # But based on previous knowledge, it might be raw downloads.
        # Let's assume we can fetch the index from a known location or we might need to find it.
        # For this script, we'll look for the index file in the bronze layer.
        
        # NOTE: In a real scenario, we might need to download the XML from the Clerk's site if not present.
        # For now, let's assume it's available or we can infer from the filename if we had a local DB.
        # Since we are in the bronze layer, we should have the index.
        
        key = f'bronze/house/financial/year={year}/index/{year}FD.xml'
        
        logger.info(f"Fetching index from s3://{S3_BUCKET}/{key}")
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        xml_content = response['Body'].read()
        
        root = ET.fromstring(xml_content)
        
        mapping = {}
        for member in root.findall('Member'):
            doc_id = member.find('DocID').text
            filing_type = member.find('FilingType').text
            mapping[doc_id] = filing_type
            
        logger.info(f"Loaded {len(mapping)} entries from index")
        return mapping
        
    except Exception as e:
        logger.error(f"Failed to load filing type map: {e}")
        # Fallback or exit? For migration, we need this.
        # If the XML is not there, we might need to look at a different path or fail.
        # Let's try the zip file path style if the direct XML isn't there?
        # Or maybe it's in the raw folder.
        sys.exit(1)

def migrate_file(s3_client, old_key, new_key, dry_run):
    """
    Copy a single file to the new location.
    """
    if dry_run:
        logger.info(f"[DRY RUN] Would copy {old_key} -> {new_key}")
        return True
    
    try:
        # Copy object
        s3_client.copy_object(
            Bucket=S3_BUCKET,
            CopySource={'Bucket': S3_BUCKET, 'Key': old_key},
            Key=new_key
        )
        logger.info(f"Copied {old_key} -> {new_key}")
        return True
    except Exception as e:
        logger.error(f"Failed to copy {old_key}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Migrate Bronze layer structure')
    parser.add_argument('--year', type=int, required=True, help='Year to migrate')
    parser.add_argument('--dry-run', action='store_true', help='Print actions without executing')
    parser.add_argument('--execute', action='store_true', help='Execute the migration')
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        parser.error("Must specify either --dry-run or --execute")
        
    s3 = boto3.client('s3')
    
    # 1. Get Filing Type Map
    filing_type_map = get_filing_type_map(args.year, s3)
    
    # 2. List existing PDFs
    prefix = f'bronze/house/financial/year={args.year}/pdfs/'
    paginator = s3.get_paginator('list_objects_v2')
    
    tasks = []
    
    logger.info(f"Scanning {prefix}...")
    
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        if 'Contents' not in page:
            continue
            
        for obj in page['Contents']:
            old_key = obj['Key']
            filename = old_key.split('/')[-1]
            
            # Skip if it's not a PDF or if it's already in a subdirectory (if run multiple times)
            if not filename.endswith('.pdf'):
                continue
                
            doc_id = filename.replace('.pdf', '')
            
            if doc_id in filing_type_map:
                filing_type = filing_type_map[doc_id]
                new_key = f'bronze/house/financial/year={args.year}/filing_type={filing_type}/pdfs/{filename}'
                
                # Check if we are essentially moving it to the same place (shouldn't happen with this logic but good to be safe)
                if old_key != new_key:
                    tasks.append((old_key, new_key))
            else:
                logger.warning(f"DocID {doc_id} not found in index, skipping or moving to 'U'?")
                # Optional: Move to 'U' (Unknown)
                new_key = f'bronze/house/financial/year={args.year}/filing_type=U/pdfs/{filename}'
                tasks.append((old_key, new_key))

    logger.info(f"Found {len(tasks)} files to migrate")
    
    # 3. Execute Migration
    success_count = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(migrate_file, s3, old, new, args.dry_run) for old, new in tasks]
        
        for future in as_completed(futures):
            if future.result():
                success_count += 1
                
    logger.info(f"Migration complete. {success_count}/{len(tasks)} files processed.")

if __name__ == '__main__':
    main()
