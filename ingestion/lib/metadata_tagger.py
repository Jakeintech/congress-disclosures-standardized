"""
Metadata tagging library for Bronze layer PDFs.
"""

import logging
import boto3
import re
from datetime import datetime

logger = logging.getLogger(__name__)

def tag_bronze_pdf(s3_client, bucket, key, metadata):
    """
    Apply metadata tags to an S3 object.
    
    Args:
        s3_client: boto3 S3 client
        bucket: S3 bucket name
        key: S3 object key
        metadata: Dictionary of metadata to apply (will be prefixed with x-amz-meta- if not present, 
                  but boto3 put_object_tagging uses 'TagSet')
                  
    NOTE: S3 Object Metadata (System/User defined) is immutable after creation unless copied.
    S3 Object Tags are mutable.
    The requirement says "Metadata Tagging", which usually refers to Object Metadata (HeadObject).
    However, if we want to update existing objects without copying, we must use Object Tags (PutObjectTagging).
    
    The session file says: "Verify: S3 object metadata includes all tags".
    And "Task 2.7: Update ingestion Lambda to tag on upload".
    
    If we use Object Metadata (x-amz-meta-*), we must set it during PutObject or CopyObject.
    For existing files, we must CopyObject to itself to update metadata.
    
    Let's support both or clarify.
    "Blob tag schema" implies Object Tags?
    "x-amz-meta-filing-type" implies Object Metadata.
    
    The BRONZE_SCHEMA.md I created lists `x-amz-meta-*`. So it's Object Metadata.
    To update existing files, we need to CopyObject.
    """
    try:
        # For existing objects, we need to copy to update metadata
        # First, get existing metadata to preserve other fields if needed
        head = s3_client.head_object(Bucket=bucket, Key=key)
        existing_meta = head.get('Metadata', {})
        
        # Merge new metadata
        new_meta = existing_meta.copy()
        new_meta.update(metadata)
        
        # Copy object to itself with new metadata
        s3_client.copy_object(
            Bucket=bucket,
            Key=key,
            CopySource={'Bucket': bucket, 'Key': key},
            Metadata=new_meta,
            MetadataDirective='REPLACE',
            ContentType=head.get('ContentType', 'application/pdf')
        )
        logger.info(f"Updated metadata for {key}")
        return True
    except Exception as e:
        logger.error(f"Failed to tag {key}: {e}")
        return False

def calculate_quality_score(has_text_layer, page_count, filing_date, member_name):
    """
    Calculate quality score (0.0 - 1.0).
    
    Logic:
    - has_text_layer (50%): 0.5 if True
    - page_count (20%): 0.2 if < 30, else 0.1 if < 100, else 0.0
    - recent_date (15%): 0.15 if > 2020
    - valid_member_name (15%): 0.15 if present and not "Unknown"
    """
    score = 0.0
    
    if has_text_layer:
        score += 0.5
        
    if page_count < 30:
        score += 0.2
    elif page_count < 100:
        score += 0.1
        
    # Parse year from filing_date (assuming YYYY-MM-DD or similar)
    try:
        year = int(str(filing_date)[:4])
        if year >= 2020:
            score += 0.15
    except:
        pass
        
    if member_name and member_name.lower() != 'unknown':
        score += 0.15
        
    return round(score, 2)

def extract_metadata_from_xml(xml_content, doc_id):
    """
    Extract metadata for a specific DocID from the XML index content.
    """
    # This might be slow if parsing full XML for every call.
    # Better to parse once and pass dict.
    # But for this function signature, let's assume we might use it for single lookups.
    pass
