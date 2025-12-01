import boto3
import os
import sys
import random
import json
import logging
from io import BytesIO

# Add project root to path
sys.path.append(os.getcwd())

from ingestion.lib.extractors.type_p_ptr.extractor import PTRExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

s3 = boto3.client('s3')
BUCKET = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

def list_ptr_pdfs(limit=20):
    """List Type P PDFs using manifest."""
    logger.info("Reading manifest to find Type P filings...")
    
    try:
        response = s3.get_object(Bucket=BUCKET, Key="website/api/v1/documents/manifest.json")
        manifest_data = json.loads(response['Body'].read())
        
        # Manifest structure: {"filings": [...]} or just [...]
        filings = manifest_data.get('filings', []) if isinstance(manifest_data, dict) else manifest_data
        
        # Filter for Type P and Year 2025
        ptr_filings = [
            f for f in filings 
            if f.get('filing_type') == 'P' and str(f.get('year')) == '2025'
        ]
        
        logger.info(f"Found {len(ptr_filings)} Type P filings in manifest for 2025")
        
        # Construct S3 keys
        pdf_keys = []
        for f in ptr_filings[:limit*2]: # Get more than limit to shuffle
            doc_id = f.get('doc_id')
            year = f.get('year')
            # Path: bronze/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf
            key = f"bronze/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf"
            pdf_keys.append(key)
            
        return pdf_keys
        
    except Exception as e:
        logger.error(f"Failed to read manifest: {e}")
        return []

def test_extraction(s3_key):
    """Download PDF and run extraction."""
    logger.info(f"Testing extraction for {s3_key}")
    
    try:
        # Download PDF
        response = s3.get_object(Bucket=BUCKET, Key=s3_key)
        pdf_bytes = response['Body'].read()
        
        # Initialize extractor
        extractor = PTRExtractor(pdf_bytes=pdf_bytes)
        
        # Run extraction
        result = extractor.extract_with_fallback()
        
        # Analyze result
        transactions = result.get('transactions', [])
        confidence = result.get('confidence_score', 0)
        method = result.get('extraction_metadata', {}).get('extraction_method', 'unknown')
        
        logger.info(f"Result for {s3_key}:")
        logger.info(f"  Transactions: {len(transactions)}")
        logger.info(f"  Confidence: {confidence:.2f}")
        logger.info(f"  Method: {method}")
        
        if len(transactions) == 0:
            logger.warning(f"  ZERO TRANSACTIONS FOUND!")
            # print extracted text preview
            if hasattr(extractor, 'text') and extractor.text:
                print(f"  Text preview: {extractor.text[:500]}")
            else:
                print("  Text is empty/None")
            
        return {
            "key": s3_key,
            "transactions": len(transactions),
            "confidence": confidence,
            "method": method
        }
        
    except Exception as e:
        logger.error(f"Extraction failed for {s3_key}: {e}")
        return {
            "key": s3_key,
            "error": str(e)
        }

def main():
    keys = list_ptr_pdfs(limit=50)
    if not keys:
        logger.error("No PDFs found!")
        return
        
    # Test specific failed doc
    sample_keys = ["bronze/house/financial/year=2025/pdfs/2025/20030439.pdf"]
        
    results = []
    for key in sample_keys:
        results.append(test_extraction(key))
        
    # Summary
    print("\n\n=== SUMMARY ===")
    for r in results:
        if 'error' in r:
            print(f"❌ {r['key']}: ERROR - {r['error']}")
        else:
            status = "✅" if r['transactions'] > 0 else "⚠️"
            print(f"{status} {r['key']}: {r['transactions']} txns, Conf: {r['confidence']:.2f}, Method: {r['method']}")

if __name__ == "__main__":
    main()
