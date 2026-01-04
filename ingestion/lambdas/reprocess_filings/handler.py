"""
Selective Reprocessing Lambda (STORY-055)

Reprocess filings with improved extractor versions to iteratively improve data quality
without reprocessing the entire dataset.

Input:
{
    "filing_type": "type_p",           # Required
    "year_range": [2024, 2025],        # Required
    "extractor_version": "1.1.0",      # Required
    "comparison_mode": true,           # Optional (default: true)
    "dry_run": false,                  # Optional (default: false)
    "batch_size": 100,                 # Optional (default: 100)
    "overwrite": false                 # Optional (default: false)
}

Output:
{
    "status": "completed",
    "summary": {...},
    "comparison": {...},
    "s3_paths": {...}
}
"""

import json
import logging
import os
import gzip
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import boto3
from botocore.exceptions import ClientError

# Setup logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.client('dynamodb')

# Environment variables
S3_BUCKET = os.environ['S3_BUCKET_NAME']
DYNAMODB_VERSIONS_TABLE = os.environ.get('DYNAMODB_VERSIONS_TABLE', 'congress-disclosures-extraction-versions')
SNS_ALERTS_ARN = os.environ.get('SNS_ALERTS_ARN')

# Import extractor classes
from lib.extractors.type_p_ptr.extractor import PTRExtractor
from lib.extractors.type_a_b_annual.extractor import TypeABAnnualExtractor
from lib.extractors.type_t_termination.extractor import TypeTTerminationExtractor
from lib.extractors.type_x_extension_request.extractor import TypeXExtensionRequestExtractor
from lib.extractors.type_d_campaign_notice.extractor import TypeDCampaignNoticeExtractor
from lib.extractors.type_w_withdrawal_notice.extractor import TypeWWithdrawalNoticeExtractor

# Import utilities
from lib.version_utils import ExtractionVersionRegistry, compare_versions
from lib.version_comparison import QualityMetricsCalculator, generate_comparison_report


# Extractor mapping
EXTRACTOR_MAP = {
    'type_p': PTRExtractor,
    'type_a': TypeABAnnualExtractor,
    'type_b': TypeABAnnualExtractor,
    'type_t': TypeTTerminationExtractor,
    'type_x': TypeXExtensionRequestExtractor,
    'type_d': TypeDCampaignNoticeExtractor,
    'type_w': TypeWWithdrawalNoticeExtractor,
}


def lambda_handler(event, context):
    """
    Selectively reprocess filings with improved extractor version.
    
    Args:
        event: Reprocessing configuration
        context: Lambda context
        
    Returns:
        Reprocessing results with quality comparison
    """
    logger.info(f"Reprocessing request: {json.dumps(event)}")
    
    # Validate input
    try:
        validate_reprocessing_request(event)
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }
    
    filing_type = event['filing_type']
    year_range = event['year_range']
    new_version = event['extractor_version']
    comparison_mode = event.get('comparison_mode', True)
    dry_run = event.get('dry_run', False)
    batch_size = event.get('batch_size', 100)
    overwrite = event.get('overwrite', False)
    
    # Initialize version registry
    version_registry = ExtractionVersionRegistry(DYNAMODB_VERSIONS_TABLE, dynamodb)
    
    # Step 1: Get list of PDFs to reprocess from Bronze
    logger.info(f"Finding PDFs for {filing_type} in years {year_range[0]}-{year_range[1]}")
    pdfs_to_reprocess = get_bronze_pdfs(
        filing_type=filing_type,
        year_range=year_range
    )
    
    logger.info(f"Found {len(pdfs_to_reprocess)} PDFs to reprocess")
    
    if dry_run:
        return {
            'status': 'dry_run',
            'pdfs_found': len(pdfs_to_reprocess),
            'filing_type': filing_type,
            'year_range': year_range,
            'extractor_version': new_version
        }
    
    # Step 2: Get baseline quality metrics (from current production version)
    baseline_metrics = None
    baseline_version = None
    
    if comparison_mode:
        extractor_class = get_extractor_class_name(filing_type)
        production_version_info = version_registry.get_production_version(extractor_class)
        
        if production_version_info:
            baseline_version = production_version_info['extractor_version']
            logger.info(f"Current production version: {baseline_version}")
            
            # Calculate baseline metrics from existing extractions
            baseline_prefix = f"silver/house/financial/objects/filing_type={filing_type}/extractor_version={baseline_version}/"
            calculator = QualityMetricsCalculator()
            
            try:
                baseline_metrics = calculator.calculate_from_s3_extractions(
                    s3_client=s3,
                    bucket=S3_BUCKET,
                    prefix=baseline_prefix,
                    limit=min(len(pdfs_to_reprocess), 1000)  # Sample up to 1000 for comparison
                )
                logger.info(f"Baseline metrics calculated: avg confidence = {baseline_metrics.get('avg_confidence_score', 0):.2%}")
            except Exception as e:
                logger.warning(f"Could not calculate baseline metrics: {e}")
        else:
            logger.info(f"No production version found for {extractor_class}, skipping comparison")
    
    # Step 3: Reprocess PDFs in batches
    results = []
    total_batches = (len(pdfs_to_reprocess) + batch_size - 1) // batch_size
    
    for batch_num, i in enumerate(range(0, len(pdfs_to_reprocess), batch_size), 1):
        batch = pdfs_to_reprocess[i:i + batch_size]
        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} PDFs)")
        
        batch_results = process_batch(
            pdfs=batch,
            filing_type=filing_type,
            extractor_version=new_version,
            overwrite=overwrite
        )
        results.extend(batch_results)
        
        # Log progress
        success_count = len([r for r in batch_results if r.get('status') == 'success'])
        logger.info(f"Batch {batch_num} complete: {success_count}/{len(batch)} succeeded")
    
    # Step 4: Calculate new quality metrics
    calculator = QualityMetricsCalculator()
    new_metrics = calculator.calculate_metrics(results)
    
    logger.info(f"New metrics calculated: avg confidence = {new_metrics.get('avg_confidence_score', 0):.2%}")
    
    # Step 5: Generate comparison report
    comparison = None
    report_key = None
    
    if comparison_mode and baseline_metrics and baseline_version:
        comparison = generate_comparison_report(
            baseline_metrics=baseline_metrics,
            new_metrics=new_metrics,
            baseline_version=baseline_version,
            new_version=new_version
        )
        
        # Store comparison report in S3
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        report_key = f"reports/reprocessing/{filing_type}_{baseline_version}_to_{new_version}_{timestamp}.json"
        
        try:
            s3.put_object(
                Bucket=S3_BUCKET,
                Key=report_key,
                Body=json.dumps(comparison, indent=2).encode('utf-8'),
                ContentType='application/json'
            )
            logger.info(f"Comparison report saved to s3://{S3_BUCKET}/{report_key}")
        except Exception as e:
            logger.error(f"Failed to save comparison report: {e}")
    
    # Step 6: Update version registry
    extractor_class = get_extractor_class_name(filing_type)
    try:
        version_registry.register_version(
            extractor_class=extractor_class,
            extractor_version=new_version,
            quality_metrics=new_metrics,
            changelog=f"Reprocessed {len(results)} filings for {filing_type}",
            is_production=False  # Don't auto-promote, require manual promotion
        )
        logger.info(f"Registered version {extractor_class} v{new_version} in registry")
    except Exception as e:
        logger.error(f"Failed to register version: {e}")
    
    # Calculate processing time
    processing_time = context.get_remaining_time_in_millis() / 1000 if context else 0
    
    # Build response
    response = {
        'status': 'completed',
        'summary': {
            'pdfs_reprocessed': len(results),
            'extractions_succeeded': len([r for r in results if r.get('status') == 'success']),
            'extractions_failed': len([r for r in results if r.get('status') == 'failed']),
            'processing_time_seconds': processing_time,
            'filing_type': filing_type,
            'year_range': year_range,
            'extractor_version': new_version
        },
        'comparison': comparison,
        's3_paths': {
            'new_version': f"silver/house/financial/objects/filing_type={filing_type}/extractor_version={new_version}/",
            'comparison_report': f"s3://{S3_BUCKET}/{report_key}" if report_key else None
        }
    }
    
    logger.info(f"Reprocessing complete: {response['summary']}")
    
    return response


def validate_reprocessing_request(event: Dict[str, Any]) -> None:
    """Validate reprocessing request parameters.
    
    Args:
        event: Request event dict
        
    Raises:
        ValueError: If request is invalid
    """
    required_fields = ['filing_type', 'year_range', 'extractor_version']
    
    for field in required_fields:
        if field not in event:
            raise ValueError(f"Missing required field: {field}")
    
    filing_type = event['filing_type']
    if filing_type not in EXTRACTOR_MAP:
        raise ValueError(f"Unsupported filing type: {filing_type}. Supported: {list(EXTRACTOR_MAP.keys())}")
    
    year_range = event['year_range']
    if not isinstance(year_range, list) or len(year_range) != 2:
        raise ValueError("year_range must be a list of [start_year, end_year]")
    
    if year_range[0] > year_range[1]:
        raise ValueError("Invalid year range: start_year must be <= end_year")
    
    # Validate version format (basic check)
    version = event['extractor_version']
    if not version or not all(c.isdigit() or c == '.' for c in version):
        raise ValueError(f"Invalid extractor_version format: {version}")


def get_bronze_pdfs(filing_type: str, year_range: List[int]) -> List[Dict[str, str]]:
    """Get list of PDFs from Bronze layer matching criteria.
    
    Args:
        filing_type: Filing type code (e.g., "type_p")
        year_range: [start_year, end_year]
        
    Returns:
        List of PDF metadata dicts
    """
    pdfs = []
    
    for year in range(year_range[0], year_range[1] + 1):
        # Bronze path structure: bronze/house/financial/year={year}/filing_type={type}/pdfs/
        prefix = f"bronze/house/financial/year={year}/filing_type={filing_type}/pdfs/"
        
        logger.info(f"Scanning {prefix}")
        
        # List all PDFs in Bronze
        paginator = s3.get_paginator('list_objects_v2')
        
        try:
            for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    if key.endswith('.pdf'):
                        doc_id = key.split('/')[-1].replace('.pdf', '')
                        pdfs.append({
                            'doc_id': doc_id,
                            'year': year,
                            'filing_type': filing_type,
                            's3_key': key
                        })
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"No PDFs found in {prefix}")
            else:
                logger.error(f"Error listing PDFs in {prefix}: {e}")
    
    return pdfs


def process_batch(
    pdfs: List[Dict[str, str]],
    filing_type: str,
    extractor_version: str,
    overwrite: bool = False
) -> List[Dict[str, Any]]:
    """Process batch of PDFs with new extractor version.
    
    Args:
        pdfs: List of PDF metadata dicts
        filing_type: Filing type code
        extractor_version: New extractor version
        overwrite: Whether to overwrite existing extractions
        
    Returns:
        List of extraction results
    """
    results = []
    extractor_class = EXTRACTOR_MAP.get(filing_type)
    
    if not extractor_class:
        logger.error(f"No extractor for filing type: {filing_type}")
        return results
    
    for pdf_info in pdfs:
        doc_id = pdf_info['doc_id']
        year = pdf_info['year']
        s3_key = pdf_info['s3_key']
        
        try:
            # Check if already processed (unless overwrite=True)
            if not overwrite:
                existing_key = construct_versioned_path(
                    filing_type=filing_type,
                    extractor_version=extractor_version,
                    year=year,
                    doc_id=doc_id
                )
                
                if s3_object_exists(S3_BUCKET, existing_key):
                    logger.info(f"Skipping {doc_id} (already extracted with v{extractor_version})")
                    continue
            
            # Download PDF from Bronze
            pdf_bytes = download_pdf(s3_key)
            
            # Extract with new version
            extractor = extractor_class(pdf_bytes=pdf_bytes)
            extraction_result = extractor.extract_with_fallback()
            
            # Update version in metadata
            if 'extraction_metadata' not in extraction_result:
                extraction_result['extraction_metadata'] = {}
            
            extraction_result['extraction_metadata']['extractor_version'] = extractor_version
            extraction_result['extraction_metadata']['extractor_class'] = extractor_class.__name__
            extraction_result['extraction_metadata']['reprocessing_timestamp'] = datetime.now(timezone.utc).isoformat()
            
            # Add doc_id and year to result
            extraction_result['doc_id'] = doc_id
            extraction_result['year'] = year
            extraction_result['filing_type'] = filing_type
            
            # Write to Silver with versioned path
            silver_key = construct_versioned_path(
                filing_type=filing_type,
                extractor_version=extractor_version,
                year=year,
                doc_id=doc_id
            )
            
            s3.put_object(
                Bucket=S3_BUCKET,
                Key=silver_key,
                Body=json.dumps(extraction_result, indent=2).encode('utf-8'),
                ContentType='application/json'
            )
            
            logger.info(f"Extracted {doc_id} to {silver_key}")
            
            results.append({
                'doc_id': doc_id,
                'year': year,
                'status': 'success',
                'extraction_metadata': extraction_result.get('extraction_metadata', {})
            })
            
        except Exception as e:
            logger.error(f"Failed to process {doc_id}: {e}", exc_info=True)
            results.append({
                'doc_id': doc_id,
                'year': year,
                'status': 'failed',
                'error': str(e)
            })
    
    return results


def download_pdf(s3_key: str) -> bytes:
    """Download PDF from S3.
    
    Args:
        s3_key: S3 object key
        
    Returns:
        PDF bytes
    """
    response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
    return response['Body'].read()


def s3_object_exists(bucket: str, key: str) -> bool:
    """Check if S3 object exists.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        
    Returns:
        True if object exists
    """
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise


def construct_versioned_path(
    filing_type: str,
    extractor_version: str,
    year: int,
    doc_id: str
) -> str:
    """Construct versioned S3 path for extraction result.
    
    Args:
        filing_type: Filing type code
        extractor_version: Extractor version
        year: Filing year
        doc_id: Document ID
        
    Returns:
        S3 key path
    """
    # Path structure: silver/house/financial/objects/year={year}/filing_type={type}/extractor_version={version}/doc_id={doc_id}/extraction.json
    return f"silver/house/financial/objects/year={year}/filing_type={filing_type}/extractor_version={extractor_version}/doc_id={doc_id}/extraction.json"


def get_extractor_class_name(filing_type: str) -> str:
    """Get extractor class name for filing type.
    
    Args:
        filing_type: Filing type code
        
    Returns:
        Extractor class name
    """
    extractor_class = EXTRACTOR_MAP.get(filing_type)
    return extractor_class.__name__ if extractor_class else "UnknownExtractor"
