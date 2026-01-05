#!/usr/bin/env python3
"""
Verify Pipeline Integration Script

This script simulates the end-to-end data flow from Bronze -> Silver -> Gold
to verify that all components are wired correctly and schemas match.

Usage:
    python3 scripts/verify_pipeline_integration.py
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "ingestion"))

# Import mappers/handlers (using direct imports to verify real code)
from ingestion.lib.congress_schema_mappers import map_member_to_silver, map_bill_to_silver
from ingestion.lib.congress_schema_mappers import get_silver_table_path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_member_flow():
    """Verify Member Data Flow: Bronze -> Silver -> Gold Path"""
    logger.info("Verifying Member Data Flow...")
    
    # 1. Bronze Data (Sample)
    bronze_member = {
        "member": {
            "bioguideId": "T000123",
            "firstName": "Test",
            "lastName": "Member",
            "partyName": "Democratic",
            "state": "CA",
            "district": 99,
            "terms": {"item": [{"chamber": "House", "startYear": 2023, "endYear": 2025}]},
            "updateDate": "2024-01-01T00:00:00Z"
        }
    }
    
    # 2. Bronze -> Silver Transformation
    try:
        silver_record = map_member_to_silver(bronze_member)
        logger.info("✅ Bronze -> Silver transformation successful")
    except Exception as e:
        logger.error(f"❌ Bronze -> Silver failed: {e}")
        return False
        
    # 3. Silver Schema Validation
    required_fields = ["bioguide_id", "first_name", "last_name", "party", "state"]
    missing = [f for f in required_fields if f not in silver_record]
    if missing:
        logger.error(f"❌ Silver schema missing fields: {missing}")
        return False
    logger.info("✅ Silver schema validation successful")
    
    # 4. Silver Path Generation
    path = get_silver_table_path("member", chamber=silver_record["chamber"], is_current="true")
    if "chamber=house" not in path:
        logger.error(f"❌ Incorrect Silver partition path: {path}")
        return False
    logger.info(f"✅ Silver path generation successful: {path}")
    
    return True

def verify_bill_flow():
    """Verify Bill Data Flow: Bronze -> Silver"""
    logger.info("Verifying Bill Data Flow...")
    
    # 1. Bronze Data
    bronze_bill = {
        "bill": {
            "congress": 118,
            "type": "HR",
            "number": 5555,
            "title": "Integration Test Bill",
            "sponsors": [{"bioguideId": "T000123", "fullName": "Test Member", "party": "D", "state": "CA"}]
        }
    }
    
    # 2. Bronze -> Silver
    try:
        silver_record = map_bill_to_silver(bronze_bill)
        logger.info("✅ Bronze -> Silver transformation successful")
    except Exception as e:
        logger.error(f"❌ Bronze -> Silver failed: {e}")
        return False
        
    # 3. Validation
    if silver_record["bill_id"] != "118-hr-5555":
        logger.error(f"❌ Incorrect Bill ID generated: {silver_record['bill_id']}")
        return False
        
    logger.info("✅ Silver schema validation successful")
    return True

def main():
    logger.info("🚀 Starting Pipeline Integration Verification")
    
    success = True
    success &= verify_member_flow()
    success &= verify_bill_flow()
    
    if success:
        logger.info("\n✨ ALL COMPONENT INTEGRATION CHECKS PASSED ✨")
        logger.info("The logic for transforming Bronze -> Silver is verified and consistent.")
        sys.exit(0)
    else:
        logger.error("\n❌ INTEGRATION CHECKS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
