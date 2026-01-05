#!/usr/bin/env python3
"""
Wrapper script to invoke build_fact_lobbying Lambda function.

This script invokes the Lambda function that builds the Gold layer
fact_lobbying table from Bronze/Silver lobbying disclosure data.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import boto3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add lib paths for terraform config
sys.path.insert(0, str(Path(__file__).parent.parent / "ingestion"))
sys.path.insert(0, str(Path(__file__).parent))

from lib.terraform_config import get_aws_config


def invoke_lambda(lambda_client: boto3.client, function_name: str, payload: dict) -> dict:
    """Invoke Lambda function and return response."""
    logger.info(f"Invoking Lambda: {function_name}")
    logger.info(f"Payload: {json.dumps(payload)}")
    
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        status_code = response['StatusCode']
        response_payload = json.loads(response['Payload'].read().decode('utf-8'))
        
        logger.info(f"Lambda invocation status: {status_code}")
        logger.info(f"Response: {json.dumps(response_payload, indent=2)}")
        
        if status_code != 200:
            logger.error(f"Lambda invocation failed with status {status_code}")
            return None
            
        return response_payload
        
    except Exception as e:
        logger.error(f"Error invoking Lambda: {e}", exc_info=True)
        return None


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Build fact_lobbying table by invoking Lambda function'
    )
    parser.add_argument(
        '--year',
        type=int,
        help='Optional: Filter to specific year'
    )
    parser.add_argument(
        '--bucket',
        type=str,
        help='Optional: Override S3 bucket name'
    )
    parser.add_argument(
        '--function-name',
        type=str,
        help='Optional: Override Lambda function name'
    )
    args = parser.parse_args()
    
    # Get AWS configuration
    config = get_aws_config()
    region = config.get("s3_region", "us-east-1")
    project_name = config.get("project_name", "congress-disclosures")
    environment = config.get("environment", "development")
    bucket_name = args.bucket or config.get("s3_bucket_id")
    
    if not bucket_name:
        logger.error("S3 bucket name not configured")
        sys.exit(1)
    
    # Determine Lambda function name
    function_name = args.function_name or f"{project_name}-{environment}-build-fact-lobbying"
    
    logger.info("=" * 80)
    logger.info("Build fact_lobbying Gold Table")
    logger.info("=" * 80)
    logger.info(f"Environment: {environment}")
    logger.info(f"Region: {region}")
    logger.info(f"Bucket: {bucket_name}")
    logger.info(f"Lambda: {function_name}")
    
    # Create Lambda client
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Build payload
    payload = {
        'bucket_name': bucket_name
    }
    
    if args.year:
        payload['year'] = args.year
        logger.info(f"Filtering to year: {args.year}")
    
    # Invoke Lambda
    result = invoke_lambda(lambda_client, function_name, payload)
    
    if not result:
        logger.error("❌ Lambda invocation failed")
        sys.exit(1)
    
    # Check result status
    if result.get('statusCode') == 200 and result.get('status') == 'success':
        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ SUCCESS: fact_lobbying table built")
        logger.info("=" * 80)
        logger.info(f"Records processed: {result.get('records_processed', 0):,}")
        logger.info(f"Files written: {len(result.get('files_written', []))}")
        logger.info(f"Years: {result.get('years', [])}")
        
        for file_path in result.get('files_written', []):
            logger.info(f"  ✓ {file_path}")
        
        sys.exit(0)
    else:
        logger.error("=" * 80)
        logger.error("❌ FAILED: fact_lobbying table build failed")
        logger.error("=" * 80)
        logger.error(f"Error: {result.get('error', 'Unknown error')}")
        logger.error(f"Error type: {result.get('error_type', 'Unknown')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
