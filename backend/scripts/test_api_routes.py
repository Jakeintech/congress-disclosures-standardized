#!/usr/bin/env python3
"""
Test script for API routes.
"""
import requests
import json
import os

# Base URL from Terraform output (hardcoded for now based on previous output)
API_BASE_URL = "https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com"

def test_get_filings():
    print("\nTesting GET /v1/filings...")
    url = f"{API_BASE_URL}/v1/filings"
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Count: {len(data.get('data', []))}")
            return data.get('data', [])
        else:
            print(f"Error: {response.text}")
            return []
    except Exception as e:
        print(f"Exception: {e}")
        return []

def test_get_filing(doc_id):
    print(f"\nTesting GET /v1/filings/{doc_id}...")
    url = f"{API_BASE_URL}/v1/filings/{doc_id}"
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Success!")
            # Check for structured data
            if data.get('structured_data'):
                print("✅ Structured data found")
                print(f"  Filing Type: {data['structured_data'].get('filing_type')}")
                print(f"  Bronze Key: {data['structured_data'].get('bronze_pdf_s3_key')}")
            else:
                print("❌ Structured data MISSING")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

def main():
    # 1. List filings to get a valid doc_id
    filings = test_get_filings()
    
    if filings:
        # 2. Test get_filing with a valid doc_id
        # Try to find one that we know we migrated (e.g., Type P)
        target_doc = None
        for doc in filings:
            if doc.get('filing_type') == 'P':
                target_doc = doc
                break
        
        if not target_doc:
            target_doc = filings[0]
            
        doc_id = target_doc['doc_id']
        test_get_filing(doc_id)
    else:
        print("Skipping get_filing test due to empty list")

if __name__ == "__main__":
    main()
