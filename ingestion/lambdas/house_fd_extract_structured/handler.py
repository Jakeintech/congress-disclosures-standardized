import json
import logging
import os
import boto3
import sys
from urllib.parse import unquote_plus
from datetime import datetime
import time
import io
import pypdf

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS Clients
s3 = boto3.client('s3')
textract = boto3.client('textract')
sqs = boto3.client('sqs')
dynamodb = boto3.client('dynamodb')

# Environment Variables
S3_BRONZE_PREFIX = os.environ.get('S3_BRONZE_PREFIX', 'bronze')
S3_SILVER_PREFIX = os.environ.get('S3_SILVER_PREFIX', 'silver')
TEXTRACT_SNS_TOPIC_ARN = os.environ.get('TEXTRACT_SNS_TOPIC_ARN')
TEXTRACT_ROLE_ARN = os.environ.get('TEXTRACT_ROLE_ARN')


def handler(event, context):
    """
    Lambda handler for processing House Financial Disclosure PDFs.
    
    This function handles two types of events:
    1. S3 Event: Triggered when a new PDF is uploaded to Bronze bucket.
       - Starts async Textract job
    2. SQS Event: Triggered when Textract job completes (via SNS -> SQS).
       - Gets Textract results
       - Extracts structured data
       - Saves to Silver bucket
    """
    logger.info(f"Received event: {json.dumps(event)}")

    # Handle S3 Events (New PDF uploaded)
    if 'Records' in event and 's3' in event['Records'][0]:
        return handle_s3_event(event)
    
    # Handle SQS Events (Textract completion)
    elif 'Records' in event and 'body' in event['Records'][0]:
        return handle_sqs_event(event)
    
    else:
        logger.warning("Unknown event type")
        return {"statusCode": 400, "body": "Unknown event type"}


def handle_s3_event(event):
    """Handle new PDF upload to S3."""
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        
        logger.info(f"Processing new file: s3://{bucket}/{key}")
        
        # Parse key to get metadata
        # Expected format: bronze/house/financial/year=YYYY/filing_type=Type/pdfs/DOCID.pdf
        try:
            parts = key.split('/')
            filename = parts[-1]
            doc_id = filename.replace('.pdf', '')
            
            # Extract year and filing_type from path if available
            year = None
            filing_type = None
            
            for part in parts:
                if part.startswith('year='):
                    year = int(part.split('=')[1])
                elif part.startswith('filing_type='):
                    filing_type = part.split('=')[1]
            
            if not year:
                # Fallback for old structure
                # bronze/house/financial/year=YYYY/pdfs/YYYY/DOCID.pdf
                # or bronze/house/financial/year=YYYY/pdfs/DOCID.pdf
                if 'year=' in key:
                    year_part = [p for p in parts if p.startswith('year=')][0]
                    year = int(year_part.split('=')[1])
                else:
                    year = datetime.now().year # Fallback
            
            logger.info(f"Identified doc_id={doc_id}, year={year}, filing_type={filing_type}")
            
            # 1. Try Code-Based Extraction First (Fast, Cheap)
            try:
                logger.info("Attempting code-based extraction first...")
                
                # Download PDF bytes
                response = s3.get_object(Bucket=bucket, Key=key)
                pdf_bytes = response['Body'].read()
                
                # Extract text using pypdf
                pdf_file = io.BytesIO(pdf_bytes)
                reader = pypdf.PdfReader(pdf_file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                
                # Determine extractor based on filing type
                extractor = get_extractor_for_type(filing_type)
                
                if extractor:
                    # Attempt extraction
                    structured_data = extractor.extract_from_text(text)
                    
                    # Check confidence
                    confidence = structured_data.get("metadata", {}).get("confidence_score", 0.0)
                    textract_recommended = structured_data.get("data_quality", {}).get("textract_recommended", False)
                    
                    if confidence >= 0.85 and not textract_recommended:
                        logger.info(f"Code-based extraction successful (Confidence: {confidence}). Skipping Textract.")
                        
                        # Save to Silver
                        save_structured_data(bucket, doc_id, year, filing_type, structured_data)
                        return {"statusCode": 200, "body": "Processed with code-based extraction"}
                    else:
                        logger.info(f"Code-based extraction confidence low ({confidence}). Falling back to Textract.")
                else:
                    logger.info(f"No specific extractor for type {filing_type}. Falling back to Textract.")
                    
            except Exception as e:
                logger.error(f"Code-based extraction failed: {e}", exc_info=True)
                # Continue to Textract fallback
            
            # 2. Fallback to Textract (Slow, Expensive)
            logger.info("Starting Textract job...")
            response = textract.start_document_analysis(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': key
                    }
                },
                FeatureTypes=['TABLES', 'FORMS'],
                NotificationChannel={
                    'SNSTopicArn': TEXTRACT_SNS_TOPIC_ARN,
                    'RoleArn': TEXTRACT_ROLE_ARN
                },
                JobTag=doc_id
            )
            
            job_id = response['JobId']
            logger.info(f"Started Textract Job: {job_id}")
            
        except Exception as e:
            logger.error(f"Error processing S3 event: {e}")
            raise e
            
    return {"statusCode": 200, "body": "S3 event processed"}


def handle_sqs_event(event):
    """Handle SQS message (Textract completion)."""
    for record in event['Records']:
        body = json.loads(record['body'])
        message = json.loads(body['Message'])
        
        job_id = message['JobId']
        status = message['Status']
        doc_id = message['JobTag'] # We used doc_id as JobTag
        
        logger.info(f"Processing Textract completion for JobId={job_id}, DocId={doc_id}, Status={status}")
        
        if status == 'SUCCEEDED':
            try:
                # Get full Textract results
                blocks = get_textract_results(job_id)
                
                # We need to reconstruct the S3 key to know the year/filing_type
                # Since we don't have it in the SQS message, we have to find the PDF
                # Or we could have stored it in DynamoDB when starting the job.
                # For now, let's search for the PDF in Bronze to get metadata
                
                # Try to find year from doc_id (often contains year) or search S3
                # This is a bit inefficient, ideally we pass metadata through
                year = 2024 # Default
                filing_type = None
                
                # Attempt to find the file to get metadata
                pdf_key = find_pdf_in_bronze(doc_id)
                if pdf_key:
                    parts = pdf_key.split('/')
                    for part in parts:
                        if part.startswith('year='):
                            year = int(part.split('=')[1])
                        elif part.startswith('filing_type='):
                            filing_type = part.split('=')[1]
                
                # Parse blocks
                structured_data = parse_textract_blocks(doc_id, year, filing_type, blocks)
                
                # Save to Silver
                # We need the bucket name, assume same as Bronze prefix
                bucket = os.environ.get('S3_BUCKET_NAME') 
                save_structured_data(bucket, doc_id, year, filing_type, structured_data)
                
            except Exception as e:
                logger.error(f"Error processing Textract results: {e}")
                raise e
        else:
            logger.error(f"Textract job failed: {status}")
            
    return {"statusCode": 200, "body": "SQS event processed"}


def get_extractor_for_type(filing_type):
    """Get the appropriate extractor class for the filing type."""
    sys.path.insert(0, '/opt/python')  # Lambda layer path
    
    try:
        if filing_type in ["Annual Report", "Candidate Report", "Form A", "Form B", "A", "B", "N"]:
            from ingestion.lib.extractors.type_a_b_annual.extractor import TypeABAnnualExtractor
            return TypeABAnnualExtractor()
            
        elif filing_type in ["Periodic Transaction Report", "PTR", "P"]:
            # PTR is handled by a separate pipeline usually, but if routed here:
            from ingestion.lib.extractors.ptr_extractor import PTRExtractor
            return PTRExtractor()
            
        elif filing_type in ["Extension Request", "Extension", "X"]:
            from ingestion.lib.extractors.type_x_extension_request.extractor import TypeXExtensionRequestExtractor
            return TypeXExtensionRequestExtractor()
            
        elif filing_type in ["Campaign Notice", "D"]:
            from ingestion.lib.extractors.type_d_campaign_notice.extractor import TypeDCampaignNoticeExtractor
            return TypeDCampaignNoticeExtractor()
            
        elif filing_type in ["Withdrawal Notice", "W"]:
            from ingestion.lib.extractors.type_w_withdrawal_notice.extractor import TypeWWithdrawalNoticeExtractor
            return TypeWWithdrawalNoticeExtractor()
            
        elif filing_type in ["Termination Report", "Termination", "T"]:
            from ingestion.lib.extractors.type_t_termination.extractor import TypeTTerminationExtractor
            return TypeTTerminationExtractor()
            
    except ImportError as e:
        logger.warning(f"Could not import extractor for {filing_type}: {e}")
        return None
        
    return None


def parse_textract_blocks(doc_id, year, filing_type, blocks):
    """Parse Textract blocks into structured data using specific extractors."""
    
    # If filing_type is unknown, try to classify
    if not filing_type:
        filing_type = classify_document_type(blocks)
        logger.info(f"Classified document as: {filing_type}")
    
    extractor = get_extractor_for_type(filing_type)
    
    if extractor:
        # Most extractors now support extract_from_textract
        # But we prefer extract_from_text if possible. 
        # Since we are here, code-based failed or wasn't confident.
        # So we use the Textract-specific method if available
        if hasattr(extractor, 'extract_from_textract'):
            return extractor.extract_from_textract(doc_id, year, blocks)
    
    # Generic fallback if no specific extractor or method
    logger.warning(f"No specific Textract extractor for {filing_type}, using generic.")
    return generic_textract_parse(doc_id, year, blocks)


def save_structured_data(bucket, doc_id, year, filing_type, data):
    """Save structured JSON to Silver layer."""
    if not filing_type:
        filing_type = data.get('filing_type', 'Unknown')
        
    key = f"{S3_SILVER_PREFIX}/house/financial/year={year}/filing_type={filing_type}/json/{doc_id}.json"
    
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data, indent=2),
        ContentType='application/json'
    )
    logger.info(f"Saved structured data to s3://{bucket}/{key}")


def get_textract_results(job_id):
    """Retrieve all blocks from Textract job (handling pagination)."""
    blocks = []
    next_token = None
    
    while True:
        if next_token:
            response = textract.get_document_analysis(JobId=job_id, NextToken=next_token)
        else:
            response = textract.get_document_analysis(JobId=job_id)
            
        blocks.extend(response['Blocks'])
        next_token = response.get('NextToken')
        
        if not next_token:
            break
            
    return blocks


def find_pdf_in_bronze(doc_id):
    """Find PDF key in Bronze bucket given doc_id."""
    # This is a helper to find the file if we lost the path context
    # In a real production system, we'd query a DynamoDB index
    bucket = os.environ.get('S3_BUCKET_NAME')
    prefix = f"{S3_BRONZE_PREFIX}/house/financial/"
    
    # List objects is inefficient but works for fallback
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if 'Contents' in page:
            for obj in page['Contents']:
                if obj['Key'].endswith(f"/{doc_id}.pdf"):
                    return obj['Key']
    return None


def classify_document_type(blocks):
    """Classify document type from Textract blocks."""
    # Simple keyword search on first page
    text = ""
    for block in blocks:
        if block['BlockType'] == 'LINE' and block.get('Page', 1) == 1:
            text += block['Text'] + "\n"
            
    text = text.upper()
    
    if "PERIODIC TRANSACTION REPORT" in text:
        return "PTR"
    elif "EXTENSION REQUEST" in text:
        return "Extension Request"
    elif "CAMPAIGN NOTICE" in text:
        return "Campaign Notice"
    elif "WITHDRAWAL" in text:
        return "Withdrawal Notice"
    elif "TERMINATION" in text:
        return "Termination Report"
    elif "FINANCIAL DISCLOSURE REPORT" in text:
        return "Annual Report"
        
    return "Unknown"


def generic_textract_parse(doc_id, year, blocks):
    """Generic parser for unknown document types."""
    # Just dump the raw text and key-values
    text = ""
    kv_pairs = {}
    
    block_map = {b['Id']: b for b in blocks}
    
    for block in blocks:
        if block['BlockType'] == 'LINE':
            text += block['Text'] + "\n"
        elif block['BlockType'] == 'KEY_VALUE_SET' and 'KEY' in block.get('EntityTypes', []):
            # Extract KV (simplified)
            pass
            
    return {
        "doc_id": doc_id,
        "year": year,
        "filing_type": "Unknown",
        "raw_text": text,
        "metadata": {
            "extraction_method": "generic_textract"
        }
    }
