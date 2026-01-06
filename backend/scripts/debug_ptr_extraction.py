import sys
import os
import boto3
import logging
import json
from pathlib import Path

# Add ingestion to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.lib.ingestion.extractors.type_p_ptr.extractor import PTRExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("S3_BUCKET_NAME", "congress-disclosures-standardized")

def debug_extraction(doc_id: str, year: int):
    s3 = boto3.client("s3")
    
    # Path: bronze/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf
    s3_key = f"bronze/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf"
    
    print(f"Downloading {s3_key}...")
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
        pdf_bytes = response['Body'].read()
        print(f"Downloaded {len(pdf_bytes)} bytes")
    except Exception as e:
        print(f"Failed to download PDF: {e}")
        return

    extractor = PTRExtractor(pdf_bytes=pdf_bytes)
    
    print("\nRunning extraction...")
    try:
        result = extractor.extract_with_fallback()
        print("\nExtraction Result:")
        print(json.dumps(result, indent=2, default=str))
        
        # Print extracted text for debugging
        print("\n--- Extracted Text Start ---")
        print(extractor.text)
        print("--- Extracted Text End ---\n")
        
        transactions = result.get('transactions', [])
        print(f"\nFound {len(transactions)} transactions")
        
    except Exception as e:
        print(f"\nExtraction Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # doc_id = "9115689" # From missing list
    doc_id = sys.argv[1] if len(sys.argv) > 1 else "9115689"
    year = 2025
    debug_extraction(doc_id, year)
