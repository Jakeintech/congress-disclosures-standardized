import json
import logging
import os
import sys
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Import extractors
from backend.lib.ingestion.extractors.type_a_b_annual.extractor import TypeABAnnualExtractor
from backend.lib.ingestion.extractors.type_p_ptr.extractor import PTRExtractor
from backend.lib.ingestion.extractors.type_d_campaign_notice.extractor import TypeDCampaignNoticeExtractor
from backend.lib.ingestion.extractors.type_w_withdrawal_notice.extractor import TypeWWithdrawalNoticeExtractor
from backend.lib.ingestion.extractors.type_x_extension_request.extractor import TypeXExtensionRequestExtractor
from backend.lib.ingestion.extractors.type_t_termination.extractor import TypeTTerminationExtractor

def verify_extractor(name: str, extractor_class, sample_file: str, expected_fields: list):
    """Verify a single extractor."""
    logger.info(f"Verifying {name}...")
    
    file_path = f"analysis/sample_text/{sample_file}"
    if not os.path.exists(file_path):
        logger.error(f"Sample file not found: {file_path}")
        return False
        
    try:
        with open(file_path, 'r') as f:
            text = f.read()
            
        extractor = extractor_class()
        result = extractor.extract_from_text(text)
        
        # Check for expected fields
        missing = []
        for field in expected_fields:
            if field not in result and field not in result.get('filer_info', {}) and field not in result.get('metadata', {}):
                missing.append(field)
                
        if missing:
            logger.error(f"Missing expected fields for {name}: {missing}")
            return False
            
        logger.info(f"✅ {name} passed. Confidence: {result.get('metadata', {}).get('confidence_score', 'N/A')}")
        return True
        
    except Exception as e:
        logger.error(f"❌ {name} failed with error: {e}")
        return False

def main():
    tests = [
        {
            "name": "Type A (Annual)",
            "class": TypeABAnnualExtractor,
            "file": "Type_A_Annual.txt",
            "expected": ["filer_info", "schedule_a", "schedule_d"]
        },
        {
            "name": "Type P (PTR)",
            "class": PTRExtractor,
            "file": "Type_P_PTR.txt",
            "expected": ["filer_info", "transactions"]
        },
        {
            "name": "Type D (Campaign Notice)",
            "class": TypeDCampaignNoticeExtractor,
            "file": "Type_D_Campaign.txt",
            "expected": ["filer_info", "signature"]
        },
        {
            "name": "Type W (Withdrawal)",
            "class": TypeWWithdrawalNoticeExtractor,
            "file": "Type_W_Withdrawal.txt",
            "expected": ["filer_info", "withdrawal_date"]
        },
        {
            "name": "Type X (Extension)",
            "class": TypeXExtensionRequestExtractor,
            "file": "Type_X_Extension.txt",
            "expected": ["filer_info", "extension_details"]
        },
        {
            "name": "Type T (Termination)",
            "class": TypeTTerminationExtractor,
            "file": "Type_T_Termination.txt",
            "expected": ["filer_info", "termination_date"]
        }
    ]
    
    passed = 0
    failed = 0
    
    print("\n=== Starting Verification ===\n")
    
    for test in tests:
        if verify_extractor(test["name"], test["class"], test["file"], test["expected"]):
            passed += 1
        else:
            failed += 1
            
    print(f"\n=== Verification Complete ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
