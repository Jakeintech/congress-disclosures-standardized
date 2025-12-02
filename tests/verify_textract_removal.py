import sys
import os
from pathlib import Path
import logging

# Add lambda package to path
sys.path.insert(0, "/Users/jake/Documents/GitHub/congress-disclosures-standardized/ingestion/lambdas/house_fd_extract_structured_code/package")

# Mock boto3 to ensure it's not used for Textract
import boto3
from unittest.mock import MagicMock

# Spy on boto3.client
original_client = boto3.client
def mock_client(service_name, *args, **kwargs):
    if service_name == 'textract':
        raise RuntimeError("Textract client initialization attempted! Textract should be removed.")
    return original_client(service_name, *args, **kwargs)

boto3.client = mock_client

try:
    from lib import pdf_extractor
    from lib.extraction import ExtractionPipeline
    print("Successfully imported modules.")
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

# Check pdf_extractor attributes
if hasattr(pdf_extractor, 'get_textract_client'):
    print("FAILURE: get_textract_client still exists in pdf_extractor")
    sys.exit(1)

if hasattr(pdf_extractor, 'extract_text_textract_sync'):
    print("FAILURE: extract_text_textract_sync still exists in pdf_extractor")
    sys.exit(1)

print("SUCCESS: Textract methods removed from pdf_extractor.")

# Test extraction pipeline with a dummy file (won't actually run extraction if file doesn't exist, but checks init)
try:
    pipeline = ExtractionPipeline()
    print("Successfully initialized ExtractionPipeline.")
except Exception as e:
    print(f"Failed to initialize ExtractionPipeline: {e}")
    sys.exit(1)

print("Verification complete: Textract dependencies appear to be removed.")
