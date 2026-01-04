"""
Check House FD Updates Lambda - STORY-003

Checks the House Clerk website for new financial disclosure filings.
Uses SHA256-based watermarking to prevent duplicate processing.
"""
import json
import os
import logging
import urllib.request
import hashlib
import boto3
from datetime import datetime, timezone
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Environment variables
WATERMARK_TABLE = os.environ.get('WATERMARK_TABLE_NAME', 'congress-disclosures-pipeline-watermarks')
LOOKBACK_YEARS = int(os.environ.get('LOOKBACK_YEARS', '5'))

# AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')


def get_watermark(year: int) -> dict:
    """Get watermark for a specific year from DynamoDB."""
    table = dynamodb.Table(WATERMARK_TABLE)
    
    try:
        response = table.get_item(
            Key={
                'table_name': 'house_fd',
                'watermark_type': f'year_{year}'
            }
        )
        return response.get('Item', {})
    except Exception as e:
        logger.warning(f"Error getting watermark for year {year}: {e}")
        return {}


def update_watermark(year: int, sha256: str, last_modified: str, content_length: int):
    """Update watermark in DynamoDB."""
    table = dynamodb.Table(WATERMARK_TABLE)
    
    try:
        table.put_item(
            Item={
                'table_name': 'house_fd',
                'watermark_type': f'year_{year}',
                'sha256': sha256,
                'last_modified': last_modified,
                'content_length': Decimal(str(content_length)),
                'updated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
        )
        logger.info(f"Updated watermark for year {year}: {sha256[:16]}...")
    except Exception as e:
        logger.error(f"Error updating watermark: {e}")
        raise


def compute_sha256_from_url(url: str) -> str:
    """Compute SHA256 hash of remote file without downloading entire file."""
    request = urllib.request.Request(url)
    request.add_header('User-Agent', 'Mozilla/5.0 (compatible; CongressDisclosures/1.0)')
    
    sha256_hash = hashlib.sha256()
    
    # Download in chunks to compute hash
    with urllib.request.urlopen(request, timeout=60) as response:
        while True:
            chunk = response.read(8192)  # 8KB chunks
            if not chunk:
                break
            sha256_hash.update(chunk)
    
    return sha256_hash.hexdigest()


def lambda_handler(event, context):
    """
    Check if new House Financial Disclosure filings are available.
    
    STORY-003: Implements watermarking with SHA256 comparison.
    
    Args:
        event: { "year": 2025 }
        
    Returns:
        {
            "has_new_filings": true/false,
            "year": 2025,
            "zip_url": "https://...",
            "sha256": "abc123...",
            "watermark_status": "new|unchanged|updated"
        }
    """
    year = event.get('year', datetime.now().year)
    current_year = datetime.now().year
    
    logger.info(f"Checking for House FD updates for year {year}")
    
    # STORY-003: Validate year is within lookback window
    if year < (current_year - LOOKBACK_YEARS):
        logger.warning(f"Year {year} is outside {LOOKBACK_YEARS}-year lookback window")
        return {
            "has_new_filings": False,
            "year": year,
            "error": f"Year outside lookback window (current - {LOOKBACK_YEARS} years)",
            "checked_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }
    
    # House Clerk FD ZIP URL pattern
    zip_url = f"https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip"
    
    try:
        # HEAD request to check if file exists and get metadata
        request = urllib.request.Request(zip_url, method='HEAD')
        request.add_header('User-Agent', 'Mozilla/5.0 (compatible; CongressDisclosures/1.0)')
        
        with urllib.request.urlopen(request, timeout=30) as response:
            last_modified = response.headers.get('Last-Modified', '')
            content_length = int(response.headers.get('Content-Length', '0'))
            
            logger.info(f"ZIP available: {zip_url}")
            logger.info(f"Last-Modified: {last_modified}")
            logger.info(f"Content-Length: {content_length} bytes")
        
        # STORY-003: Get existing watermark
        watermark = get_watermark(year)
        
        if watermark:
            logger.info(f"Found existing watermark for year {year}")
            
            # Quick check: if content length changed, definitely new
            if watermark.get('content_length') != content_length:
                logger.info(f"Content length changed: {watermark.get('content_length')} -> {content_length}")
                # Compute new SHA256 and update watermark
                sha256 = compute_sha256_from_url(zip_url)
                update_watermark(year, sha256, last_modified, content_length)
                
                return {
                    "has_new_filings": True,
                    "year": year,
                    "zip_url": zip_url,
                    "sha256": sha256,
                    "last_modified": last_modified,
                    "content_length": content_length,
                    "watermark_status": "updated",
                    "checked_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                }
            
            # Content length same, check SHA256
            logger.info("Content length unchanged, computing SHA256...")
            sha256 = compute_sha256_from_url(zip_url)
            
            if sha256 == watermark.get('sha256'):
                logger.info(f"SHA256 matches watermark: {sha256[:16]}... - No new filings")
                return {
                    "has_new_filings": False,
                    "year": year,
                    "zip_url": zip_url,
                    "sha256": sha256,
                    "watermark_status": "unchanged",
                    "checked_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                }
            else:
                logger.info(f"SHA256 differs: {watermark.get('sha256', '')[:16]}... -> {sha256[:16]}...")
                update_watermark(year, sha256, last_modified, content_length)
                
                return {
                    "has_new_filings": True,
                    "year": year,
                    "zip_url": zip_url,
                    "sha256": sha256,
                    "last_modified": last_modified,
                    "content_length": content_length,
                    "watermark_status": "updated",
                    "checked_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                }
        else:
            # No watermark exists - first ingestion
            logger.info(f"No watermark found for year {year} - first ingestion")
            sha256 = compute_sha256_from_url(zip_url)
            update_watermark(year, sha256, last_modified, content_length)
            
            return {
                "has_new_filings": True,
                "year": year,
                "zip_url": zip_url,
                "sha256": sha256,
                "last_modified": last_modified,
                "content_length": content_length,
                "watermark_status": "new",
                "checked_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
            
    except urllib.error.HTTPError as e:
        if e.code == 404:
            logger.warning(f"No ZIP file found for year {year} (HTTP 404)")
            return {
                "has_new_filings": False,
                "year": year,
                "zip_url": zip_url,
                "error": "File not found (404)",
                "checked_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
        else:
            logger.error(f"HTTP error checking {zip_url}: {e}")
            raise
    
    except urllib.error.URLError as e:
        logger.error(f"Network error (timeout/connection): {e}")
        # Don't fail pipeline on network errors - return no new filings
        return {
            "has_new_filings": False,
            "year": year,
            "zip_url": zip_url,
            "error": f"Network error: {str(e)}",
            "checked_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }
            
    except Exception as e:
        logger.error(f"Error checking House FD updates: {e}")
        raise
