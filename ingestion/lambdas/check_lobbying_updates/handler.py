"""
Check Lobbying Updates Lambda

Checks the Senate LDA database for new lobbying disclosure filings.
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
    Check if new Lobbying Disclosure Act (LDA) filings are available.
    
    Args:
        event: { "year": 2024, "quarter": "Q1" or "all" }
        
    Returns:
        {
            "has_new_filings": true/false,
            "year": 2024,
            "quarter": "Q1",
            "xml_urls": [...],
            "last_modified": "2025-01-15T10:30:00Z"
        }
    """
    year = event.get('year', datetime.now().year)
    quarter = event.get('quarter', 'all')
    
    logger.info(f"Checking for LDA updates for year {year}, quarter {quarter}")
    
    # Senate LDA XML URL patterns
    base_url = "https://lda.senate.gov/filings/public/filing/xml/"
    
    quarters = ['Q1', 'Q2', 'Q3', 'Q4'] if quarter == 'all' else [quarter.upper()]
    
    xml_urls = []
    for q in quarters:
        # Pattern: lobbying disclosures are available at various endpoints
        # Main bulk download: https://lda.senate.gov/system/public-disclosures/
        url = f"https://lda.senate.gov/system/public-disclosures/{year}/{q}/"
        xml_urls.append({
            "quarter": q,
            "url": url
        })
    
    try:
        # For now, always return true to allow processing
        # TODO: Implement actual check against watermark table
        
        logger.info(f"LDA data sources identified for {year}: {len(xml_urls)} quarters")
        
        return {
            "has_new_filings": True,
            "year": year,
            "quarter": quarter,
            "quarters_to_process": quarters,
            "xml_sources": xml_urls,
            "checked_at": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error checking LDA updates: {e}")
        raise
