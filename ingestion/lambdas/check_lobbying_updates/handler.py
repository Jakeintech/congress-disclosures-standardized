"""
Check Lobbying Updates Lambda - STORY-005

Checks the Senate LDA database for new lobbying disclosure filings.
Uses S3 object existence for watermarking (simpler than SHA256 for XML files).
"""
import json
import os
import logging
import boto3
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Environment variables
S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
LOOKBACK_YEARS = int(os.environ.get('LOOKBACK_YEARS', '5'))

# AWS clients
s3 = boto3.client('s3')


def check_bronze_exists(year: int, quarter: str) -> bool:
    """Check if Bronze data already exists for year/quarter."""
    prefix = f"bronze/lobbying/year={year}/quarter={quarter}/"
    
    try:
        response = s3.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=prefix,
            MaxKeys=1
        )
        exists = response.get('KeyCount', 0) > 0
        if exists:
            logger.info(f"Bronze data exists for {year}/{quarter}")
        return exists
    except Exception as e:
        logger.warning(f"Error checking Bronze for {year}/{quarter}: {e}")
        return False


def lambda_handler(event, context):
    """
    Check if new Lobbying Disclosure Act (LDA) filings are available.
    
    STORY-005: Implements watermarking by checking Bronze S3 existence.
    
    Args:
        event: { "year": 2024, "quarter": "Q1" or "all" }
        
    Returns:
        {
            "has_new_filings": true/false,
            "year": 2024,
            "quarters_to_process": ["Q1", "Q2"],
            "xml_sources": [...]
        }
    """
    year = event.get('year', datetime.now().year)
    quarter = event.get('quarter', 'all')
    current_year = datetime.now().year
    
    logger.info(f"Checking for LDA updates for year {year}, quarter {quarter}")
    logger.info("VERSION: API-BASED-INGESTION v3 - Normalized Inputs")
    
    # STORY-005: Validate year is within lookback window
    if year < (current_year - LOOKBACK_YEARS):
        logger.warning(f"Year {year} is outside {LOOKBACK_YEARS}-year lookback window")
        return {
            "has_new_filings": False,
            "year": year,
            "error": f"Year outside lookback window (current - {LOOKBACK_YEARS} years)",
            "checked_at": datetime.utcnow().isoformat() + "Z"
        }
    
    # STORY-005: Validate quarter
    valid_quarters = ['Q1', 'Q2', 'Q3', 'Q4', 'all']
    if quarter not in valid_quarters:
        logger.error(f"Invalid quarter: {quarter}")
        return {
            "has_new_filings": False,
            "year": year,
            "error": f"Invalid quarter. Must be one of: {valid_quarters}",
            "checked_at": datetime.utcnow().isoformat() + "Z"
        }
    
    # Senate LDA XML URL patterns
    quarters = ['Q1', 'Q2', 'Q3', 'Q4'] if quarter == 'all' else [quarter.upper()]
    
    xml_sources = []
    quarters_to_process = []
    
    for q in quarters:
        # STORY-005: Check if Bronze data already exists (watermarking)
        if check_bronze_exists(year, q):
            logger.info(f"Skipping {year}/{q} - Bronze data already exists")
            continue
        
        # No Bronze data - need to process this quarter
        quarters_to_process.append(q)
    
    try:
        has_new_filings = len(quarters_to_process) > 0
        
        # Prepare API ingestion tasks
        # The worker lambda handles the entire year and pagination via API
        ingest_tasks = []
        
        # We always schedule the main filing ingest if we found new quarters OR if force (implied)
        if has_new_filings:
            ingest_tasks.append({
                "filing_year": year,
                "filing_type": "FILING",
                "entity_type": None
            })
            # Optionally schedule contributions too? Let's add it.
            ingest_tasks.append({
                "filing_year": year,
                "filing_type": "CONTRIBUTION",
                "entity_type": None
            })
        
            # STORY-UPDATE: Ensure we capture ALL reference data (Lobbyists, Registrants, Clients)
            # These endpoints don't strictly depend on year but good to refresh periodically.
            # We pass year just to satisfy the strict ItemSelector, though it might be ignored by the logic.
            ingest_tasks.append({"filing_year": year, "filing_type": None, "entity_type": "LOBBYIST"})
            ingest_tasks.append({"filing_year": year, "filing_type": None, "entity_type": "REGISTRANT"})
            ingest_tasks.append({"filing_year": year, "filing_type": None, "entity_type": "CLIENT"})

        return {
            "has_new_filings": has_new_filings,
            "year": year,
            "quarter": quarter,
            "quarters_to_process": quarters_to_process,
            "ingest_tasks": ingest_tasks,
            "checked_at": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error checking LDA updates: {e}")
        raise

