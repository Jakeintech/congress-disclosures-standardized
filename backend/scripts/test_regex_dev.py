import json
import logging
import sys
from backend.lib.ingestion.extractors.type_t_termination.extractor import TypeTTerminationExtractor

# Configure logging
logging.basicConfig(level=logging.INFO)

def main():
    extractor = TypeTTerminationExtractor()
    
    with open('analysis/sample_text/Type_T_Termination.txt', 'r') as f:
        text = f.read()
        
    result = extractor.extract_from_text(text)
    
    print(json.dumps(result, indent=2, default=str))
    
    print(f"\nFiler Name: {result['filer_info']['full_name']}")
    print(f"Termination Date: {result['termination_date']}")
    print(f"Liability Count: {result['filing_metadata']['liability_count']}")

if __name__ == "__main__":
    main()
