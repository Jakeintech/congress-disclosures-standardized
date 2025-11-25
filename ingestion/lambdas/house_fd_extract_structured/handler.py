"""Lambda handler for extracting structured data from House FD PDFs.

This Lambda (triggered by S3 event when text.txt is created):
1. Downloads PDF from bronze layer
2. Analyzes PDF format and template type
3. Uses appropriate extractor (PTRExtractor for PTRs)
4. Generates structured.json with comprehensive audit trail
5. Uploads to silver/structured layer
"""

import json
import logging
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import shared libraries and extractors
from lib import s3_utils  # noqa: E402
from lib.extractors.pdf_analyzer import PDFAnalyzer, TemplateType  # noqa: E402
from lib.extractors.ptr_extractor import PTRExtractor  # noqa: E402
import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Environment variables
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")
S3_BRONZE_PREFIX = os.environ.get("S3_BRONZE_PREFIX", "bronze")
S3_SILVER_PREFIX = os.environ.get("S3_SILVER_PREFIX", "silver")
EXTRACTION_VERSION = os.environ.get("EXTRACTION_VERSION", "1.0.0")


def lambda_handler(event, context):
    """Lambda handler for structured extraction."""
    logger.info(f"Event: {json.dumps(event)}")

    # Parse S3 event (triggered by text.txt upload)
    for record in event.get("Records", []):
        try:
            # Get S3 object info
            s3_event = record.get("s3", {})
            bucket = s3_event.get("bucket", {}).get("name")
            text_key = s3_event.get("object", {}).get("key")

            logger.info(f"Processing: s3://{bucket}/{text_key}")

            # Extract doc_id and year from silver text path
            # Expected: silver/house/financial/text/year=YYYY/doc_id=XXXXXXXX/text.txt
            parts = text_key.split("/")
            year = None
            doc_id = None

            for part in parts:
                if part.startswith("year="):
                    year = int(part.split("=")[1])
                elif part.startswith("doc_id="):
                    doc_id = part.split("=")[1]

            if not doc_id or not year:
                logger.error(f"Could not parse doc_id/year from key: {text_key}")
                continue

            # Process document
            result = process_document(bucket, doc_id, year)

            if result["status"] == "success":
                logger.info(f"✅ Successfully extracted structured data for {doc_id}")
                logger.info(f"  Template: {result['template_type']}")
                logger.info(f"  Confidence: {result['confidence']}")
                if "transaction_count" in result:
                    logger.info(f"  Transactions: {result['transaction_count']}")
            else:
                logger.warning(f"⚠️  Extraction partially successful: {result['message']}")

        except Exception as e:
            logger.error(f"Error processing record: {e}")
            import traceback
            traceback.print_exc()
            # Continue processing other records

    return {"statusCode": 200, "body": json.dumps({"message": "Processing complete"})}


def process_document(bucket: str, doc_id: str, year: int) -> Dict[str, Any]:
    """Process a document to extract structured data.

    Args:
        bucket: S3 bucket name
        doc_id: Document ID
        year: Filing year

    Returns:
        Dict with processing result
    """
    s3_client = boto3.client("s3")

    # Construct S3 keys
    pdf_key = f"{S3_BRONZE_PREFIX}/house/financial/disclosures/year={year}/doc_id={doc_id}/{doc_id}.pdf"
    structured_key = f"{S3_SILVER_PREFIX}/house/financial/structured/year={year}/doc_id={doc_id}/structured.json"

    logger.info(f"Processing document {doc_id}")
    logger.info(f"  PDF: s3://{bucket}/{pdf_key}")
    logger.info(f"  Output: s3://{bucket}/{structured_key}")

    # Download PDF to temp file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
        pdf_path = Path(tmp_pdf.name)

        try:
            logger.info("Downloading PDF from bronze layer...")
            s3_client.download_file(bucket, pdf_key, str(pdf_path))
            logger.info(f"Downloaded {pdf_path.stat().st_size} bytes")

            # Analyze PDF to determine template type
            logger.info("Analyzing PDF format and template...")
            analyzer = PDFAnalyzer(pdf_path=str(pdf_path))
            analysis = analyzer.analyze()

            template_type = analysis["template_type"]
            pdf_format = analysis["pdf_format"]

            logger.info(f"  Template: {template_type.value if isinstance(template_type, TemplateType) else template_type}")
            logger.info(f"  Format: {pdf_format.value if hasattr(pdf_format, 'value') else pdf_format}")
            logger.info(f"  Requires OCR: {analysis['requires_ocr']}")

            # Extract structured data based on template type
            structured_data = None
            extraction_status = "unsupported"

            if template_type == TemplateType.PTR:
                logger.info("Extracting PTR structured data...")
                extractor = PTRExtractor(pdf_path=str(pdf_path))
                structured_data = extractor.extract_with_fallback()
                structured_data["filing_id"] = doc_id
                extraction_status = "success"

            elif template_type == TemplateType.FORM_A:
                logger.warning("Form A extraction not yet implemented")
                extraction_status = "pending_implementation"

            elif template_type == TemplateType.FORM_B:
                logger.warning("Form B extraction not yet implemented")
                extraction_status = "pending_implementation"

            else:
                logger.warning(f"Unknown template type: {template_type}")
                extraction_status = "unknown_template"

            # Upload structured data if extraction successful
            if structured_data:
                logger.info("Uploading structured.json to silver layer...")

                # Convert to JSON
                json_data = json.dumps(structured_data, indent=2)

                # Upload to S3
                s3_client.put_object(
                    Bucket=bucket,
                    Key=structured_key,
                    Body=json_data,
                    ContentType="application/json",
                    Metadata={
                        "doc_id": doc_id,
                        "year": str(year),
                        "template_type": str(template_type.value if isinstance(template_type, TemplateType) else template_type),
                        "extraction_method": structured_data["extraction_metadata"]["extraction_method"],
                        "confidence_score": str(structured_data["extraction_metadata"]["confidence_score"]),
                    }
                )

                logger.info(f"✅ Uploaded structured.json ({len(json_data)} bytes)")

                return {
                    "status": extraction_status,
                    "doc_id": doc_id,
                    "year": year,
                    "template_type": template_type.value if isinstance(template_type, TemplateType) else str(template_type),
                    "confidence": structured_data["extraction_metadata"]["confidence_score"],
                    "transaction_count": len(structured_data.get("transactions", [])),
                    "s3_key": structured_key,
                }
            else:
                logger.warning(f"No structured data extracted (status: {extraction_status})")
                return {
                    "status": extraction_status,
                    "doc_id": doc_id,
                    "year": year,
                    "template_type": str(template_type.value if isinstance(template_type, TemplateType) else template_type),
                    "message": f"Extraction not supported for {template_type}",
                }

        except Exception as e:
            logger.error(f"Error processing document: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "doc_id": doc_id,
                "year": year,
                "error": str(e),
            }
        finally:
            # Clean up temp file
            if pdf_path.exists():
                pdf_path.unlink()


if __name__ == "__main__":
    # Test locally
    test_event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "congress-disclosures-standardized"},
                    "object": {"key": "silver/house/financial/text/year=2025/doc_id=20026590/text.txt"},
                }
            }
        ]
    }

    # Set environment for local testing
    os.environ["S3_BUCKET_NAME"] = "congress-disclosures-standardized"
    os.environ["S3_REGION"] = "us-east-1"

    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
