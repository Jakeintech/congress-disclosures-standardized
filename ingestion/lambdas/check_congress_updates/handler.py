"""
Check Congress Updates Lambda - STORY-047

Checks Congress.gov API for new bills and members data.
Uses DynamoDB watermarking for incremental updates.
"""
import json
import os
import logging
import urllib.request
import urllib.parse
import boto3
from datetime import datetime, timedelta, timezone
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Environment variables
CONGRESS_API_KEY = os.environ.get('CONGRESS_API_KEY', '')
WATERMARK_TABLE = os.environ.get('WATERMARK_TABLE_NAME', 'congress-disclosures-pipeline-watermarks')
LOOKBACK_YEARS = int(os.environ.get('LOOKBACK_YEARS', '5'))

# AWS clients
dynamodb = boto3.resource('dynamodb')


def get_watermark(data_type: str) -> dict:
    """Get watermark for Congress.gov data type from DynamoDB."""
    table = dynamodb.Table(WATERMARK_TABLE)
    
    try:
        response = table.get_item(
            Key={
                'table_name': 'congress_gov',
                'watermark_type': data_type  # 'bills' or 'members'
            }
        )
        return response.get('Item', {})
    except Exception as e:
        logger.warning(f"Error getting watermark for {data_type}: {e}")
        return {}


def update_watermark(data_type: str, last_update_date: str, record_count: int):
    """Update watermark in DynamoDB."""
    table = dynamodb.Table(WATERMARK_TABLE)
    
    try:
        table.put_item(
            Item={
                'table_name': 'congress_gov',
                'watermark_type': data_type,
                'last_update_date': last_update_date,
                'record_count': Decimal(str(record_count)),
                'updated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
        )
        logger.info(f"Updated watermark for {data_type}: {last_update_date}")
    except Exception as e:
        logger.error(f"Error updating watermark: {e}")
        raise


def check_congress_api(endpoint: str, params: dict) -> dict:
    """
    Query Congress.gov API.
    
    Args:
        endpoint: API endpoint (e.g., 'bill', 'member')
        params: Query parameters
        
    Returns:
        API response as dict
    """
    base_url = "https://api.congress.gov/v3"
    
    # Add API key to params
    params['api_key'] = CONGRESS_API_KEY
    params['format'] = 'json'
    
    # Build URL
    query_string = urllib.parse.urlencode(params)
    url = f"{base_url}/{endpoint}?{query_string}"
    
    try:
        request = urllib.request.Request(url)
        request.add_header('User-Agent', 'Mozilla/5.0 (compatible; CongressDisclosures/1.0)')
        
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
            
    except urllib.error.HTTPError as e:
        if e.code == 429:
            # Rate limited - return empty result
            logger.warning("Congress.gov API rate limit hit (HTTP 429)")
            return {'pagination': {'count': 0}}
        else:
            logger.error(f"HTTP error querying Congress.gov API: {e}")
            raise
    except Exception as e:
        logger.error(f"Error querying Congress.gov API: {e}")
        raise


def lambda_handler(event, context):
    """
    Check if new Congress.gov data is available.
    
    STORY-004: Implements watermarking with Congress.gov API.
    STORY-047: Created initial check_congress_updates Lambda.
    
    Args:
        event: { "data_type": "bills" or "members" }
        
    Returns:
        {
            "has_new_data": true/false,
            "data_type": "bills",
            "from_date": "2024-01-01T00:00:00Z",
            "to_date": "2025-12-14T10:30:00Z",  # Only when has_new_data=true
            "record_count": 150,                # Only when has_new_data=true
            "bills_count": 150,                  # Alias for record_count (STORY-004)
            "is_initial_load": true,             # true when watermark_status="new"
            "watermark_status": "new|incremental",
            "checked_at": "2025-12-14T10:30:00Z"
        }
    """
    data_type = event.get('data_type', 'bills')
    current_year = datetime.now().year
    
    logger.info(f"Checking for Congress.gov updates: {data_type}")
    
    # Get existing watermark
    watermark = get_watermark(data_type)
    
    if watermark and watermark.get('last_update_date'):
        # Incremental update - use watermark date
        from_date = watermark['last_update_date']
        watermark_status = "incremental"
        logger.info(f"Found watermark for {data_type}: {from_date}")
    else:
        # First ingestion - use 5-year lookback
        from_date = f"{current_year - LOOKBACK_YEARS}-01-01T00:00:00Z"
        watermark_status = "new"
        logger.info(f"No watermark found for {data_type} - using {LOOKBACK_YEARS}-year lookback: {from_date}")
    
    try:
        # Query Congress.gov API to check for new data
        if data_type == 'bills':
            # Check for bills updated since watermark
            response = check_congress_api('bill', {
                'fromDateTime': from_date,
                'limit': 1  # Just check if any exist
            })
        elif data_type == 'members':
            # Check for member updates
            response = check_congress_api('member', {
                'fromDateTime': from_date,
                'limit': 1
            })
        else:
            raise ValueError(f"Unknown data_type: {data_type}")
        
        # Check if new data exists
        record_count = response.get('pagination', {}).get('count', 0)
        has_new_data = record_count > 0
        
        if has_new_data:
            logger.info(f"Found {record_count} new {data_type} records since {from_date}")
            
            # Update watermark to current time
            current_time = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            update_watermark(data_type, current_time, record_count)
            
            return {
                "has_new_data": True,
                "data_type": data_type,
                "from_date": from_date,
                "to_date": current_time,
                "record_count": record_count,
                "bills_count": record_count,  # Alias for compatibility with STORY-004
                "is_initial_load": watermark_status == "new",
                "watermark_status": watermark_status,
                "checked_at": current_time
            }
        else:
            logger.info(f"No new {data_type} records since {from_date}")
            return {
                "has_new_data": False,
                "data_type": data_type,
                "from_date": from_date,
                "is_initial_load": watermark_status == "new",
                "watermark_status": watermark_status,
                "checked_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
            
    except Exception as e:
        logger.error(f"Error checking Congress.gov updates: {e}")
        # Don't fail pipeline on API errors - return no new data
        return {
            "has_new_data": False,
            "data_type": data_type,
            "error": str(e),
            "checked_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }
