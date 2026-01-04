#!/usr/bin/env python3
"""
Lambda handler for validating Gold dimension tables.

Ensures all dimension tables exist and are valid before building fact tables.
This prevents orphaned foreign keys and referential integrity issues.
"""

import os
import logging
from typing import Dict, List, Any
import boto3
import pyarrow.parquet as pq
from io import BytesIO

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Initialize AWS clients
s3_client = boto3.client('s3')

# Environment variables
BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

# Required dimensions with their S3 paths and primary keys
REQUIRED_DIMENSIONS = [
    {
        'name': 'dim_members',
        'path': 'gold/house/financial/dimensions/dim_members/dim_members.parquet',
        'primary_key': 'member_key'
    },
    {
        'name': 'dim_assets',
        'path': 'gold/house/financial/dimensions/dim_assets/part-0000.parquet',
        'primary_key': 'asset_key'
    },
    {
        'name': 'dim_bills',
        'path': 'gold/congress/dimensions/dim_bills/dim_bills.parquet',
        'primary_key': 'bill_key'
    },
    {
        'name': 'dim_lobbyists',
        'path': 'gold/lobbying/dimensions/dim_lobbyists/dim_lobbyists.parquet',
        'primary_key': 'lobbyist_key'
    },
    {
        'name': 'dim_dates',
        'path': 'gold/house/financial/dimensions/dim_dates/dim_dates.parquet',
        'primary_key': 'date_key'
    }
]


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Validate that all dimension tables exist and are valid.

    Args:
        event: Lambda event (not used)
        context: Lambda context

    Returns:
        {
            'validation_passed': bool,
            'dimensions_validated': int,
            'dimensions_passed': int,
            'dimensions_failed': int,
            'failures': List[str],
            'details': List[Dict[str, Any]]
        }
    """
    logger.info("Starting dimension validation")
    
    results = []
    failures = []

    for dim in REQUIRED_DIMENSIONS:
        try:
            logger.info(f"Validating dimension: {dim['name']}")
            result = validate_dimension(dim)
            results.append(result)

            if not result['passed']:
                error_msg = f"{dim['name']}: {result['error']}"
                failures.append(error_msg)
                logger.error(error_msg)
            else:
                logger.info(f"✓ {dim['name']}: {result['row_count']} rows, no duplicates")

        except Exception as e:
            error_msg = f"{dim['name']}: Unexpected error - {str(e)}"
            failures.append(error_msg)
            logger.error(error_msg, exc_info=True)
            results.append({
                'dimension': dim['name'],
                'passed': False,
                'error': str(e)
            })

    validation_passed = len(failures) == 0

    response = {
        'validation_passed': validation_passed,
        'dimensions_validated': len(REQUIRED_DIMENSIONS),
        'dimensions_passed': len([r for r in results if r['passed']]),
        'dimensions_failed': len(failures),
        'failures': failures,
        'details': results
    }

    # Log summary
    if validation_passed:
        logger.info(f"✓ All {len(REQUIRED_DIMENSIONS)} dimensions validated successfully")
    else:
        logger.error(f"✗ Validation failed: {len(failures)} dimension(s) have issues")
        for failure in failures:
            logger.error(f"  - {failure}")

    return response


def validate_dimension(dim: Dict[str, str]) -> Dict[str, Any]:
    """
    Validate a single dimension table.

    Checks:
    1. File exists in S3
    2. Table has at least 1 row
    3. Primary key has no duplicates

    Args:
        dim: Dictionary with 'name', 'path', and 'primary_key'

    Returns:
        {
            'dimension': str,
            'passed': bool,
            'row_count': int (if passed),
            'has_duplicates': bool (if passed),
            'error': str | None
        }
    """
    dim_name = dim['name']
    s3_path = dim['path']
    primary_key = dim['primary_key']

    # Step 1: Check if file exists
    try:
        s3_client.head_object(Bucket=BUCKET, Key=s3_path)
    except s3_client.exceptions.NoSuchKey:
        return {
            'dimension': dim_name,
            'passed': False,
            'error': f"File not found: s3://{BUCKET}/{s3_path}"
        }
    except Exception as e:
        return {
            'dimension': dim_name,
            'passed': False,
            'error': f'Error checking file existence: {str(e)}'
        }

    # Step 2: Read Parquet and count rows
    try:
        obj = s3_client.get_object(Bucket=BUCKET, Key=s3_path)
        table = pq.read_table(BytesIO(obj['Body'].read()))
        row_count = len(table)

        if row_count == 0:
            return {
                'dimension': dim_name,
                'passed': False,
                'row_count': 0,
                'error': 'Dimension table is empty (0 rows)'
            }

        # Step 3: Check for duplicate primary keys
        pk_column = table[primary_key].to_pylist()
        unique_count = len(set(pk_column))
        has_duplicates = unique_count < row_count

        if has_duplicates:
            return {
                'dimension': dim_name,
                'passed': False,
                'row_count': row_count,
                'has_duplicates': True,
                'error': f'Duplicate primary keys found: {row_count} rows but only {unique_count} unique keys'
            }

        # All checks passed
        return {
            'dimension': dim_name,
            'passed': True,
            'row_count': row_count,
            'has_duplicates': False,
            'error': None
        }

    except KeyError as e:
        return {
            'dimension': dim_name,
            'passed': False,
            'error': f'Primary key column "{primary_key}" not found in table: {str(e)}'
        }
    except Exception as e:
        return {
            'dimension': dim_name,
            'passed': False,
            'error': f'Error reading Parquet: {str(e)}'
        }
