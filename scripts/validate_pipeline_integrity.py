#!/usr/bin/env python3
"""
Pipeline Integrity Validator

This script performs a comprehensive check of the pipeline's health:
1.  **Bronze Integrity**: Verifies that every filing in the XML manifest exists as a PDF in S3.
2.  **DLQ Status**: Checks if any messages are stuck in the Dead Letter Queue.
3.  **Extraction Status**: (Optional) Checks if Silver layer has corresponding records.

Usage:
    python scripts/validate_pipeline_integrity.py [--year 2025]
"""

import argparse
import boto3
import sys
import xml.etree.ElementTree as ET
from botocore.exceptions import ClientError

# Configuration
BUCKET_NAME = "congress-disclosures-standardized"
DLQ_NAME = "congress-disclosures-development-extract-dlq"

s3 = boto3.client('s3')
sqs = boto3.client('sqs')

def get_xml_manifest(year):
    """Retrieves and parses the XML manifest from S3."""
    key = f"bronze/house/financial/year={year}/index/{year}FD.xml"
    print(f"📥 Fetching manifest: s3://{BUCKET_NAME}/{key}")
    
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        xml_content = response['Body'].read()
        return ET.fromstring(xml_content)
    except ClientError as e:
        print(f"❌ Failed to retrieve manifest: {e}")
        return None
    except ET.ParseError as e:
        print(f"❌ Failed to parse XML: {e}")
        return None

def get_s3_pdfs(year):
    """Lists all PDF DocIDs present in the Bronze layer for the given year."""
    # Use a broad prefix to capture all possible PDF locations under the year.
    prefix = f"bronze/house/financial/year={year}/"
    print(f"🔎 Scanning S3 prefix: s3://{BUCKET_NAME}/{prefix}")

    pdfs = set()
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix)
    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                key = obj['Key']
                if not key.lower().endswith('.pdf'):
                    continue
                # Extract doc_id from the filename (last component) without extension
                filename = key.split('/')[-1]
                doc_id = filename.replace('.pdf', '')
                pdfs.add(doc_id)
    print(f"✓ Found {len(pdfs)} PDFs in S3 under year {year}")
    return pdfs

def check_s3_tags(bucket, key, expected_tags):
    """Verifies that an S3 object has the expected tags."""
    try:
        response = s3.get_object_tagging(Bucket=bucket, Key=key)
        actual_tags = {t['Key']: t['Value'] for t in response['TagSet']}
        
        missing_tags = []
        mismatched_tags = []
        
        for k, v in expected_tags.items():
            if k not in actual_tags:
                missing_tags.append(k)
            elif actual_tags[k] != v:
                mismatched_tags.append(f"{k}: expected '{v}', got '{actual_tags[k]}'")
        
        if missing_tags or mismatched_tags:
            return False, f"Missing: {missing_tags}, Mismatched: {mismatched_tags}"
        return True, "OK"
    except ClientError as e:
        return False, f"Error fetching tags: {e}"

def check_silver_layer(year, doc_ids):
    """Checks if Silver layer text exists for the given DocIDs."""
    print(f"🔎 Checking Silver layer for {len(doc_ids)} documents...")
    
    missing_silver = []
    # Check a sample if too many, or all if reasonable. Let's check all for now but be mindful of API costs.
    # Actually, listing the prefix is cheaper than head_object for every file.
    
    prefix = f"silver/house/financial/text/year={year}/"
    silver_docs = set()
    
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix)
    
    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                # Key format: silver/.../doc_id=12345/raw_text.txt.gz
                parts = obj['Key'].split('/')
                for part in parts:
                    if part.startswith('doc_id='):
                        silver_docs.add(part.split('=')[1])
    
    missing_silver = doc_ids - silver_docs
    return missing_silver

    
    return not errors_found

def analyze_extraction_quality(year, sample_size=20):
    """
    Analyzes structured extraction quality by filing type.
    - Counts total processed documents per type (from S3 keys).
    - Calculates average confidence score (by sampling S3 objects).
    """
    print(f"📊 Analyzing Extraction Quality (Sampling {sample_size} docs/type)...")
    
    prefix = f"silver/objects/type_p/{year}/"
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix)
    
    # Group keys by filing type
    # Key format: .../filing_type=P/doc_id=123.json
    files_by_type = {}
    
    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                key = obj['Key']
                # Extract filing_type from key
                parts = key.split('/')
                ftype = "Unknown"
                for p in parts:
                    if p.startswith('filing_type='):
                        ftype = p.split('=')[1]
                        break
                
                if ftype not in files_by_type:
                    files_by_type[ftype] = []
                files_by_type[ftype].append(key)
    
    if not files_by_type:
        print("   ⚠️  No structured data found in Silver layer.")
        return False

    print(f"\n{'Filing Type':<15} | {'Count':<10} | {'Avg Confidence':<15} | {'Sampled':<10}")
    print("-" * 60)
    
    import random
    import json
    
    all_types_ok = True
    
    for ftype, keys in sorted(files_by_type.items()):
        count = len(keys)
        
        # Sample keys for content analysis
        sample_keys = random.sample(keys, min(count, sample_size))
        total_confidence = 0.0
        valid_samples = 0
        
        for key in sample_keys:
            try:
                resp = s3.get_object(Bucket=BUCKET_NAME, Key=key)
                data = json.loads(resp['Body'].read())
                total_confidence += data.get('confidence_score', 0.0)
                valid_samples += 1
            except Exception as e:
                print(f"   ❌ Failed to read {key}: {e}")
        
        avg_conf = (total_confidence / valid_samples) if valid_samples > 0 else 0.0
        
        # Colorize output based on confidence
        conf_str = f"{avg_conf:.1%}"
        if avg_conf < 0.8:
            all_types_ok = False
            conf_str += " ⚠️"
            
        print(f"{ftype:<15} | {count:<10} | {conf_str:<15} | {valid_samples:<10}")

    print("-" * 60)
    return all_types_ok

def get_queue_url(queue_name):
    """Helper to get SQS queue URL."""
    try:
        response = sqs.get_queue_url(QueueName=queue_name)
        return response['QueueUrl']
    except ClientError as e:
        if e.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
            print(f"❌ SQS queue '{queue_name}' does not exist.")
        else:
            print(f"❌ Error getting queue URL for '{queue_name}': {e}")
        return None

def check_lambda_health(lambda_names):
    """Helper: Verify each Lambda is Active and has recent logs."""
    client = boto3.client('lambda')
    all_ok = True
    for name in lambda_names:
        try:
            cfg = client.get_function_configuration(FunctionName=name)
            state = cfg.get('State', 'Unknown')
            if state != 'Active':
                print(f"❌ Lambda {name} not active (state={state})")
                all_ok = False
            else:
                print(f"✅ Lambda {name} is active")
        except Exception as e:
            print(f"❌ Error checking lambda {name}: {e}")
            all_ok = False
    return all_ok

def check_cloudwatch_logs(log_groups):
    """Helper: Check if log streams exist for CloudWatch log groups."""
    logs = boto3.client('logs')
    all_ok = True
    for lg in log_groups:
        try:
            streams = logs.describe_log_streams(logGroupName=lg, orderBy='LastEventTime', descending=True, limit=1)
            if streams.get('logStreams'):
                print(f"✅ Logs present for {lg}")
            else:
                print(f"⚠️  No log streams found for {lg}")
                all_ok = False
        except Exception as e:
            print(f"❌ Error accessing logs for {lg}: {e}")
            all_ok = False
    return all_ok

def check_dlq():
    """Checks both DLQ and main extraction queue for stuck messages."""
    print("🔎 Checking DLQ and main SQS queues...")
    dlq_url = get_queue_url("congress-disclosures-development-extract-dlq")
    main_url = get_queue_url("congress-disclosures-development-extract-queue")
    
    def attrs(url):
        try:
            resp = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=['ApproximateNumberOfMessages','ApproximateNumberOfMessagesNotVisible'])
            return int(resp['Attributes'].get('ApproximateNumberOfMessages',0)), int(resp['Attributes'].get('ApproximateNumberOfMessagesNotVisible',0))
        except Exception as e:
            print(f"❌ Unable to get attributes for {url}: {e}")
            return 0,0
            
    dlq_msg, dlq_vis = attrs(dlq_url) if dlq_url else (0,0)
    main_msg, main_vis = attrs(main_url) if main_url else (0,0)
    
    if dlq_msg or dlq_vis:
        print(f"⚠️  DLQ has {dlq_msg} pending and {dlq_vis} in-flight messages")
        return False
    else:
        print("✅ DLQ is empty")
    
    if main_msg:
        print(f"⚠️  Extraction queue has {main_msg} messages waiting")
        return False
    else:
        print("✅ Extraction queue is empty")
    return True

def main():
    parser = argparse.ArgumentParser(description="Validate pipeline integrity")
    parser.add_argument("--year", type=int, default=2025, help="Year to validate")
    parser.add_argument("--sample-tags", type=int, default=5, help="Number of files to verify tags for")
    args = parser.parse_args()

    print(f"🚀 Starting validation for Year {args.year}...\n")

    # 0. Check Lambda Health & Logs
    lambdas = [
        "congress-disclosures-development-ingest-zip",
        "congress-disclosures-development-index-to-silver",
        "congress-disclosures-development-extract-document",
        "congress-disclosures-development-extract-structured-code"
    ]
    log_groups = [f"/aws/lambda/{name}" for name in lambdas]
    
    lambda_ok = check_lambda_health(lambdas)
    logs_ok = check_cloudwatch_logs(log_groups)
    print("-" * 40)

    # 1. Check DLQ
    dlq_ok = check_dlq()
    print("-" * 40)

    # 2. Get Manifest
    root = get_xml_manifest(args.year)
    if not root:
        sys.exit(1)

    # 3. Parse Expected DocIDs and Metadata
    expected_docs = {}
    for member in root.findall('Member'):
        doc_id = member.find('DocID').text
        expected_docs[doc_id] = {
            'filing_type': member.find('FilingType').text,
            'filer_name': f"{member.find('Last').text}, {member.find('First').text}",
            'state_district': member.find('StateDst').text,
            'filing_date': member.find('FilingDate').text
        }
    
    print(f"✓ Manifest contains {len(expected_docs)} filings")

    # 4. Get Actual S3 PDFs
    actual_pdfs = get_s3_pdfs(args.year)

    # 5. Compare Bronze Existence
    missing_bronze = set(expected_docs.keys()) - actual_pdfs
    unexpected_bronze = actual_pdfs - set(expected_docs.keys())

    print("-" * 40)
    print("📊 Bronze Layer Validation:")
    
    if not missing_bronze and not unexpected_bronze:
        print("✅ SUCCESS: S3 PDFs match XML manifest exactly.")
    else:
        if missing_bronze:
            print(f"❌ MISSING BRONZE: {len(missing_bronze)} files listed in XML but NOT in S3:")
            for doc_id in list(missing_bronze)[:10]:
                print(f"   - {doc_id}")
        if unexpected_bronze:
            print(f"⚠️  UNEXPECTED BRONZE: {len(unexpected_bronze)} files in S3 but NOT in XML:")
            for doc_id in list(unexpected_bronze)[:10]:
                print(f"   - {doc_id}")

    # 6. Verify Tags (Sample)
    print("-" * 40)
    print(f"🏷️  Verifying Metadata Tags (Sample of {args.sample_tags})...")
    tag_errors = 0
    import random
    sample_ids = random.sample(list(actual_pdfs), min(len(actual_pdfs), args.sample_tags))
    
    for doc_id in sample_ids:
        key = f"bronze/house/financial/year={args.year}/pdfs/{args.year}/{doc_id}.pdf"
        # Note: XML tags might need normalization to match what Lambda applies (e.g., handling None)
        # The Lambda likely applies them exactly as strings.
        expected = expected_docs[doc_id]
        # Filter out None values from expected if Lambda doesn't tag them
        expected = {k: v for k, v in expected.items() if v is not None}
        
        ok, msg = check_s3_tags(BUCKET_NAME, key, expected)
        if not ok:
            print(f"❌ Tag mismatch for {doc_id}: {msg}")
            tag_errors += 1
        else:
            print(f"✓ Tags OK for {doc_id}")
            
    if tag_errors == 0:
        print("✅ Tag validation passed for sample.")

    # 7. Verify Silver Layer (Lambda Execution)
    print("-" * 40)
    print("🥈 Verifying Silver Layer (Extraction Success)...")
    missing_silver = check_silver_layer(args.year, set(expected_docs.keys()))
    
    if not missing_silver:
        print("✅ SUCCESS: All documents have extracted text in Silver layer.")
        print("   (This confirms Ingestion -> SQS -> Extraction flow worked)")
    else:
        print(f"❌ MISSING SILVER: {len(missing_silver)} documents missing from Silver layer:")
        print(f"   (Possible causes: Extraction Lambda failed, SQS latency, or OCR failure)")
        for doc_id in list(missing_silver)[:10]:
            print(f"   - {doc_id}")

    print("-" * 40)

    # 8. Analyze Extraction Quality
    quality_ok = analyze_extraction_quality(args.year)
    print("-" * 40)
    
    # Final Verdict
    if not missing_bronze and dlq_ok and tag_errors == 0 and not missing_silver and lambda_ok and logs_ok and quality_ok:
        print("✨ Pipeline Integrity: HEALTHY")
        sys.exit(0)
    else:
        print("🚨 Pipeline Integrity: ISSUES DETECTED")
        sys.exit(1)

if __name__ == "__main__":
    main()
