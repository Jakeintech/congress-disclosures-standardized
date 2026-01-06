#!/usr/bin/env python3
"""
Bulk tag Bronze layer PDFs with metadata.
"""

import boto3
import argparse
import logging
import sys
import os
import io
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add ingestion/lib to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ingestion/lib')))
from metadata_tagger import tag_bronze_pdf, calculate_quality_score

try:
    import pypdf
except ImportError:
    pypdf = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

S3_BUCKET = 'congress-disclosures-standardized'

def get_xml_metadata(year, s3_client):
    """
    Parse XML index to get metadata for all docs.
    """
    key = f'bronze/house/financial/year={year}/index/{year}FD.xml'
    logger.info(f"Fetching index from s3://{S3_BUCKET}/{key}")
    
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        xml_content = response['Body'].read()
        root = ET.fromstring(xml_content)
        
        metadata_map = {}
        for member in root.findall('Member'):
            doc_id = member.find('DocID').text
            
            # Extract fields
            meta = {
                'filing_type': member.find('FilingType').text,
                'member_name': f"{member.find('Last').text}, {member.find('First').text}",
                'state_district': member.find('StateDst').text,
                'year': member.find('Year').text,
                'filing_date': member.find('FilingDate').text
            }
            metadata_map[doc_id] = meta
            
        return metadata_map
    except Exception as e:
        logger.error(f"Failed to load XML index: {e}")
        return {}

def analyze_pdf(s3_client, bucket, key):
    """
    Download and analyze PDF for page count and text layer.
    """
    if not pypdf:
        return 0, False
        
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        pdf_bytes = io.BytesIO(response['Body'].read())
        
        reader = pypdf.PdfReader(pdf_bytes)
        page_count = len(reader.pages)
        
        # Check for text layer on first page
        has_text = False
        if page_count > 0:
            text = reader.pages[0].extract_text()
            if text and len(text.strip()) > 50:
                has_text = True
                
        return page_count, has_text
    except Exception as e:
        logger.warning(f"Failed to analyze PDF {key}: {e}")
        return 0, False

def process_file(s3_client, key, metadata_map, dry_run):
    """
    Process a single file: analyze and tag.
    """
    filename = key.split('/')[-1]
    doc_id = filename.replace('.pdf', '')
    
    if doc_id not in metadata_map:
        logger.warning(f"No metadata for {doc_id}")
        return False
        
    meta = metadata_map[doc_id]
    
    # Analyze PDF (skip if dry run to save time/bandwidth, or implement if needed)
    # For this script, let's assume we want to analyze even in dry run to show what score would be
    # But downloading 1600 PDFs is heavy.
    # Let's skip analysis in dry run unless specified?
    # Or just do it.
    
    page_count = 0
    has_text = False
    
    if not dry_run:
        page_count, has_text = analyze_pdf(s3_client, S3_BUCKET, key)
    
    # Calculate score
    score = calculate_quality_score(
        has_text, 
        page_count, 
        meta.get('filing_date', ''), 
        meta.get('member_name', '')
    )
    
    tags = {
        'filing_type': meta['filing_type'],
        'member_name': meta['member_name'],
        'state_district': meta['state_district'],
        'quality_score': str(score),
        'page_count': str(page_count),
        'has_text_layer': str(has_text).lower()
    }
    
    if dry_run:
        logger.info(f"[DRY RUN] Would tag {key} with {tags}")
        return True
        
    return tag_bronze_pdf(s3_client, S3_BUCKET, key, tags)

def main():
    parser = argparse.ArgumentParser(description='Bulk tag Bronze layer PDFs')
    parser.add_argument('--year', type=int, required=True, help='Year to process')
    parser.add_argument('--dry-run', action='store_true', help='Dry run')
    
    args = parser.parse_args()
    
    s3 = boto3.client('s3')
    
    # 1. Get metadata
    metadata_map = get_xml_metadata(args.year, s3)
    logger.info(f"Loaded metadata for {len(metadata_map)} documents")
    
    # 2. List PDFs
    prefix = f'bronze/house/financial/year={args.year}/'
    paginator = s3.get_paginator('list_objects_v2')
    
    tasks = []
    
    logger.info(f"Scanning {prefix}...")
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        if 'Contents' not in page:
            continue
            
        for obj in page['Contents']:
            key = obj['Key']
            if key.endswith('.pdf'):
                tasks.append(key)
                
    logger.info(f"Found {len(tasks)} PDFs to process")
    
    # 3. Process
    success_count = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_file, s3, key, metadata_map, args.dry_run) for key in tasks]
        
        for future in as_completed(futures):
            if future.result():
                success_count += 1
                
    logger.info(f"Tagging complete. {success_count}/{len(tasks)} files processed.")

if __name__ == '__main__':
    main()
