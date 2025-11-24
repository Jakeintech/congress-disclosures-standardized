"""Lambda handler for converting House FD index to silver layer.

This Lambda:
1. Downloads XML index from bronze layer
2. Parses XML into structured records
3. Validates against JSON schema
4. Writes to Parquet in silver layer (upsert mode)
5. Initializes house_fd_documents records with pending status
"""

import json
import logging
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import shared libraries
from lib import s3_utils, parquet_writer, manifest_generator

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Environment variables
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")
S3_BRONZE_PREFIX = os.environ.get("S3_BRONZE_PREFIX", "bronze")
S3_SILVER_PREFIX = os.environ.get("S3_SILVER_PREFIX", "silver")
EXTRACTION_VERSION = os.environ.get("EXTRACTION_VERSION", "1.0.0")

# Load JSON schemas
SCHEMAS_DIR = Path(__file__).parent / "schemas"
with open(SCHEMAS_DIR / "house_fd_filings.json") as f:
    FILINGS_SCHEMA = json.load(f)
with open(SCHEMAS_DIR / "house_fd_documents.json") as f:
    DOCUMENTS_SCHEMA = json.load(f)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler.

    Args:
        event: Lambda event with 'year' parameter
        context: Lambda context

    Returns:
        Dict with status and stats

    Example event:
        {
            "year": 2025
        }
    """
    try:
        # Extract year from event
        year = event.get("year")
        if not year:
            raise ValueError("Missing required parameter: year")

        year = int(year)

        logger.info(f"Starting index-to-silver for year {year}")

        # Step 1: Download XML index from bronze
        logger.info(f"Step 1: Downloading XML index from bronze")
        xml_s3_key = f"{S3_BRONZE_PREFIX}/house/financial/year={year}/index/{year}FD.xml"
        xml_content = s3_utils.download_bytes_from_s3(S3_BUCKET, xml_s3_key)

        # Step 2: Parse XML into records
        logger.info(f"Step 2: Parsing XML index")
        filing_records = parse_xml_index(xml_content, year, xml_s3_key)

        logger.info(f"Parsed {len(filing_records)} filing records")

        # Step 3: Write house_fd_filings to silver
        logger.info(f"Step 3: Writing house_fd_filings to silver")
        filings_s3_key = f"{S3_SILVER_PREFIX}/house/financial/filings/year={year}/part-0000.parquet"

        filings_result = parquet_writer.upsert_parquet_records(
            new_records=filing_records,
            bucket=S3_BUCKET,
            s3_key=filings_s3_key,
            key_columns=["year", "doc_id"],
            schema=FILINGS_SCHEMA,
        )

        # Step 4: Initialize house_fd_documents records
        logger.info(f"Step 4: Initializing house_fd_documents records")
        document_records = initialize_document_records(filing_records)

        documents_s3_key = f"{S3_SILVER_PREFIX}/house/financial/documents/year={year}/part-0000.parquet"

        documents_result = parquet_writer.upsert_parquet_records(
            new_records=document_records,
            bucket=S3_BUCKET,
            s3_key=documents_s3_key,
            key_columns=["year", "doc_id"],
            schema=DOCUMENTS_SCHEMA,
        )

        # Step 5: Generate manifest.json for website
        logger.info(f"Step 5: Generating manifest.json for website")
        try:
            manifest_result = manifest_generator.update_manifest_incremental(
                new_filings=filing_records,
                s3_bucket=S3_BUCKET,
                s3_key="manifest.json",
            )
            logger.info(f"Manifest generated: {manifest_result['filings_count']} filings")
        except Exception as e:
            logger.warning(f"Failed to generate manifest: {str(e)}")
            manifest_result = {"error": str(e)}

        result = {
            "status": "success",
            "year": year,
            "filings_written": filings_result["row_count"],
            "documents_initialized": documents_result["row_count"],
            "filings_s3_key": filings_s3_key,
            "documents_s3_key": documents_s3_key,
            "manifest": manifest_result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Index-to-silver complete: {json.dumps(result)}")

        return result

    except Exception as e:
        logger.error(f"Index-to-silver failed: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def parse_xml_index(xml_bytes: bytes, year: int, xml_s3_key: str) -> List[Dict[str, Any]]:
    """Parse House FD XML index into structured records.

    Args:
        xml_bytes: XML content as bytes
        year: Filing year
        xml_s3_key: S3 key of XML file

    Returns:
        List of filing record dicts

    Raises:
        ET.ParseError: If XML is malformed
    """
    records = []

    # Parse XML
    root = ET.fromstring(xml_bytes)

    # Process each <Member> element
    for member in root.findall(".//Member"):
        doc_id = member.findtext("DocID", "").strip()

        if not doc_id:
            logger.warning(f"Skipping member with no DocID")
            continue

        # Extract fields
        record = {
            "doc_id": doc_id,
            "year": year,
            "filing_date": member.findtext("FilingDate", "").strip(),
            "filing_type": member.findtext("FilingType", "").strip(),
            "prefix": member.findtext("Prefix", "").strip() or None,
            "first_name": member.findtext("First", "").strip(),
            "last_name": member.findtext("Last", "").strip(),
            "suffix": member.findtext("Suffix", "").strip() or None,
            "state_district": member.findtext("StateDst", "").strip(),
            "raw_xml_path": xml_s3_key,
            "raw_txt_path": xml_s3_key.replace(".xml", ".txt"),
            "pdf_s3_key": f"{S3_BRONZE_PREFIX}/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf",
            "bronze_ingest_ts": datetime.now(timezone.utc).isoformat(),
            "silver_ingest_ts": datetime.now(timezone.utc).isoformat(),
            "source_system": "house_fd",
        }

        # Convert filing_date to ISO format (from MM/DD/YYYY)
        if record["filing_date"]:
            try:
                date_obj = datetime.strptime(record["filing_date"], "%m/%d/%Y")
                record["filing_date"] = date_obj.strftime("%Y-%m-%d")
            except ValueError:
                logger.warning(f"Could not parse filing_date: {record['filing_date']}")

        records.append(record)

    return records


def initialize_document_records(filing_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Initialize house_fd_documents records from filing records.

    Creates pending extraction records for each PDF.

    Args:
        filing_records: List of filing records

    Returns:
        List of document records
    """
    document_records = []

    for filing in filing_records:
        doc_id = filing["doc_id"]
        year = filing["year"]
        pdf_s3_key = filing["pdf_s3_key"]

        # Initialize with pending status
        # Actual metadata (pages, file_size, hash) will be populated by extract Lambda
        document_record = {
            "doc_id": doc_id,
            "year": year,
            "pdf_s3_key": pdf_s3_key,
            "pdf_sha256": "",  # Will be populated by extract Lambda
            "pdf_file_size_bytes": 0,  # Will be populated
            "pages": 0,  # Will be populated
            "has_embedded_text": False,  # Will be determined
            "extraction_method": "pending",
            "extraction_status": "pending",
            "extraction_version": EXTRACTION_VERSION,
            "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            "extraction_error": None,
            "extraction_duration_seconds": None,
            "text_s3_key": None,
            "json_s3_key": None,
            "textract_job_id": None,
            "char_count": None,
        }

        document_records.append(document_record)

    return document_records
