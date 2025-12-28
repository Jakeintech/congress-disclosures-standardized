#!/usr/bin/env python3
"""Test Type A/B extractor locally with sample PDF."""
import sys
from pathlib import Path

# Add package lib to path
sys.path.insert(0, str(Path().absolute() / 'ingestion/lambdas/house_fd_extract_structured_code/package'))
sys.path.insert(0, str(Path().absolute() / 'ingestion/lambdas/house_fd_extract_structured_code/package/lib'))

from lib.extractors.type_a_b_annual.extractor import TypeABAnnualExtractor
from lib.pdf_extractor import PDFExtractor

# Extract text from sample PDF
pdf_path = 'data/test_samples/type_a_10063536.pdf'
print(f"Testing with PDF: {pdf_path}")

pdf_extractor = PDFExtractor()
extracted_text, pdf_props = pdf_extractor.extract_text_from_file(pdf_path)

print(f"\\nExtracted {len(extracted_text)} characters of text")

# Run Type A/B extractor
extractor = TypeABAnnualExtractor(doc_id='10063536', year=2025, filing_type='A')
result = extractor.extract_from_text(extracted_text, pdf_props)

# Print results
print(f"\\n{'='*60}")
print("EXTRACTION RESULTS")
print(f"{'='*60}")
print(f"Filer: {result['filer_info'].get('full_name')}")
print(f"Type: {result['filer_info'].get('filer_type')}")
print(f"State/District: {result['filer_info'].get('state_district')}")
print(f"\\nSchedule A (Assets): {len(result.get('schedule_a', []))} items")
print(f"Schedule C (Income): {len(result.get('schedule_c', []))} items") 
print(f"Schedule D (Liabilities): {len(result.get('schedule_d', []))} items")
print(f"Schedule E (Positions): {len(result.get('schedule_e', []))} items")
print(f"\\nConfidence: {result['data_quality']['confidence_score']:.2f}")
print(f"Textract Recommended: {result['data_quality']['textract_recommended']}")

if result.get('schedule_a'):
    print(f"\\n{'='*60}")
    print("SAMPLE ASSETS (first 3)")
    print(f"{'='*60}")
    for i, asset in enumerate(result['schedule_a'][:3], 1):
        print(f"\\n{i}. {asset.get('asset_name')}")
        print(f"   Owner: {asset.get('owner_code')}")
        print(f"   Value: ${asset.get('value_low'):,} - ${asset.get('value_high'):,}")
        print(f"   Type: {asset.get('asset_type')}")
