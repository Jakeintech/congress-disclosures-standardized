"""
Check House FD Updates Lambda

Checks the House Clerk website for new financial disclosure filings.
Returns whether new filings are available for processing.
"""
import json
import os
import logging
import urllib.request
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))


def lambda_handler(event, context):
    """
    Check if new House Financial Disclosure filings are available.
    
    Args:
        event: { "year": 2025 }
        
    Returns:
        {
            "has_new_filings": true/false,
            "year": 2025,
            "zip_url": "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/2025FD.zip",
            "last_modified": "2025-01-15T10:30:00Z"
        }
    """
    year = event.get('year', datetime.now().year)
    
    logger.info(f"Checking for House FD updates for year {year}")
    
    # House Clerk FD ZIP URL pattern
    zip_url = f"https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip"
    
    try:
        # HEAD request to check if file exists and get last modified
        request = urllib.request.Request(zip_url, method='HEAD')
        request.add_header('User-Agent', 'Mozilla/5.0 (compatible; CongressDisclosures/1.0)')
        
        with urllib.request.urlopen(request, timeout=30) as response:
            last_modified = response.headers.get('Last-Modified', '')
            content_length = response.headers.get('Content-Length', '0')
            
            logger.info(f"ZIP available: {zip_url}")
            logger.info(f"Last-Modified: {last_modified}")
            logger.info(f"Content-Length: {content_length} bytes")
            
            # TODO: Compare with watermark to determine if truly new
            # For now, always return true to process
            
            return {
                "has_new_filings": True,
                "year": year,
                "zip_url": zip_url,
                "last_modified": last_modified,
                "content_length": int(content_length) if content_length else 0,
                "checked_at": datetime.utcnow().isoformat() + "Z"
            }
            
    except urllib.error.HTTPError as e:
        if e.code == 404:
            logger.warning(f"No ZIP file found for year {year}")
            return {
                "has_new_filings": False,
                "year": year,
                "zip_url": zip_url,
                "error": f"File not found (404)",
                "checked_at": datetime.utcnow().isoformat() + "Z"
            }
        else:
            logger.error(f"HTTP error checking {zip_url}: {e}")
            raise
            
    except Exception as e:
        logger.error(f"Error checking House FD updates: {e}")
        raise
