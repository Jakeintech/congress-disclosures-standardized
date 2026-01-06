"""Lambda handler for ingesting Senate LDA (Lobbying Disclosure Act) filings.

This Lambda:
1. Fetches from lda.senate.gov/api/v1/filings/?filing_year=YYYY
2. Paginates through all results (API returns 100/page)
3. Writes raw JSON to bronze/lobbying/filings/year=YYYY/filing_uuid={uuid}.json.gz
4. Queues SQS jobs for bill extraction (parse descriptions for bill references)
"""

import gzip
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Environment variables
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")
S3_BRONZE_PREFIX = os.environ.get("S3_BRONZE_PREFIX", "bronze")
SQS_QUEUE_URL = os.environ.get("LDA_EXTRACTION_QUEUE_URL")

# AWS clients
s3_client = boto3.client("s3")
sqs_client = boto3.client("sqs")

# LDA API base URL
LDA_API_BASE_URL = os.environ.get("LDA_API_BASE_URL", "https://lda.senate.gov/api/v1")

# HTTP session defaults to reduce 429s and transient failures
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


def _requests_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=6,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(REQUEST_HEADERS)
    return session


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler.

    Args:
        event: Lambda event with parameters
        context: Lambda context

    Returns:
        Dict with status and stats

    Example event:
        {
            "filing_year": 2024,
            "filing_type": "FILING",  # or "CONTRIBUTION"
            "skip_existing": false
        }
    """
    try:
        # Extract parameters from event
        filing_year = event.get("filing_year")
        filing_type = event.get("filing_type")  # legacy path: FILING or CONTRIBUTION
        entity_type = event.get("entity_type")  # new path: REGISTRANT, CLIENT, LOBBYIST, CONSTANTS
        skip_existing = event.get("skip_existing", False)

        if not filing_type and not entity_type:
            raise ValueError("Missing required parameter: filing_type or entity_type")

        if filing_type:
            if not filing_year:
                raise ValueError("Missing required parameter: filing_year")
            filing_year = int(filing_year)

        # Optional pagination controls for chunked invocation
        page = event.get("page")  # single page
        page_start = event.get("page_start")
        page_end = event.get("page_end")
        max_pages = event.get("max_pages")  # max pages to process in this invocation
        page_size = int(event.get("page_size", 100))

        logger.info(
            f"Starting LDA {filing_type} ingestion for year {filing_year}"
        )

        if filing_type == "FILING":
            result = ingest_filings(
                int(filing_year),
                skip_existing,
                page=page,
                page_start=page_start,
                page_end=page_end,
                max_pages=max_pages,
                page_size=page_size,
            )
        elif filing_type == "CONTRIBUTION":
            result = ingest_contributions(
                int(filing_year),
                skip_existing,
                page=page,
                page_start=page_start,
                page_end=page_end,
                max_pages=max_pages,
                page_size=page_size,
            )
        elif entity_type:
            et = str(entity_type).upper()
            if et == "REGISTRANT":
                result = ingest_registrants(skip_existing=skip_existing, page=page, page_start=page_start, page_end=page_end, max_pages=max_pages, page_size=page_size)
            elif et == "CLIENT":
                result = ingest_clients(skip_existing=skip_existing, page=page, page_start=page_start, page_end=page_end, max_pages=max_pages, page_size=page_size)
            elif et == "LOBBYIST":
                result = ingest_lobbyists(skip_existing=skip_existing, page=page, page_start=page_start, page_end=page_end, max_pages=max_pages, page_size=page_size)
            elif et == "CONSTANTS":
                result = ingest_constants()
            else:
                raise ValueError(f"Invalid entity_type: {entity_type}")
        else:
            raise ValueError(f"Invalid filing_type: {filing_type}")

        result["status"] = "success"
        if filing_year:
            result["filing_year"] = filing_year
        if filing_type:
            result["filing_type"] = filing_type
        if entity_type:
            result["entity_type"] = entity_type
        result["timestamp"] = datetime.now(timezone.utc).isoformat()

        logger.info(f"Ingestion complete: {result}")
        return result

    except Exception as e:
        logger.error(f"Error in lambda_handler: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def ingest_filings(
    filing_year: int,
    skip_existing: bool,
    page: Optional[int] = None,
    page_start: Optional[int] = None,
    page_end: Optional[int] = None,
    max_pages: Optional[int] = None,
    page_size: int = 100,
) -> Dict[str, Any]:
    """Ingest LDA filings for a given year.

    Args:
        filing_year: Year to ingest (e.g., 2024)
        skip_existing: If True, skip filings that already exist in S3

    Returns:
        Dict with ingestion statistics
    """
    base_url = f"{LDA_API_BASE_URL}/filings/"
    session = _requests_session()

    filings_ingested = 0
    filings_skipped = 0
    pages_processed = 0
    sqs_messages_sent = 0

    def fetch_page(pn: int) -> Dict[str, Any]:
        params = {"filing_year": filing_year, "page": pn, "page_size": page_size}
        for attempt in range(8):
            try:
                resp = session.get(base_url, params=params, timeout=30)
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else min(60, 1.5 ** attempt)
                    logger.warning(f"429 on page {pn}. Backing off {wait:.1f}s (attempt {attempt+1})")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                wait = min(60, 1.5 ** attempt)
                logger.warning(f"HTTP error on page {pn}: {e}. Retrying in {wait:.1f}s")
                time.sleep(wait)
        raise RuntimeError(f"Failed to fetch page {pn} after retries")

    # Determine page iteration plan
    if page is not None:
        pages = [int(page)]
    else:
        start = int(page_start) if page_start is not None else 1
        end = int(page_end) if page_end is not None else None
        pages = []
        pn = start
        while True:
            if end is not None and pn > end:
                break
            if max_pages is not None and len(pages) >= int(max_pages):
                break
            pages.append(pn)
            pn += 1

    if not pages:
        # Fallback to original crawler if no page bounds provided
        pn = 1
        while True:
            data = fetch_page(pn)
            results = data.get("results", [])
            logger.info(f"Processing {len(results)} filings from page {pn}")
            for filing in results:
                filing_uuid = filing.get("filing_uuid")
                if not filing_uuid:
                    logger.warning("Skipping filing without filing_uuid")
                    continue

                # Check if filing already exists
                s3_key = (
                    f"{S3_BRONZE_PREFIX}/lobbying/filings/"
                    f"year={filing_year}/filing_uuid={filing_uuid}.json.gz"
                )

                if skip_existing and check_s3_object_exists(s3_key):
                    logger.debug(f"Skipping existing filing: {filing_uuid}")
                    filings_skipped += 1
                    continue

                # Upload filing to S3
                upload_filing_to_s3(filing, s3_key, filing_year)
                filings_ingested += 1

                # Queue for bill extraction if there are lobbying activities
                if filing.get("lobbying_activities"):
                    queue_bill_extraction(filing_uuid, filing_year)
                    sqs_messages_sent += 1

            pages_processed += 1
            pn += 1
            if max_pages is not None and pages_processed >= int(max_pages):
                break
            if not data.get("next"):
                break
            time.sleep(0.1)
    else:
        # Explicit page list mode
        for pn in pages:
            data = fetch_page(pn)
            results = data.get("results", [])
            logger.info(f"Processing {len(results)} filings from page {pn}")
            for filing in results:
                filing_uuid = filing.get("filing_uuid")
                if not filing_uuid:
                    logger.warning("Skipping filing without filing_uuid")
                    continue

            pages_processed += 1
            time.sleep(0.05)

    return {
        "filings_ingested": filings_ingested,
        "filings_skipped": filings_skipped,
        "pages_processed": pages_processed,
        "sqs_messages_sent": sqs_messages_sent,
    }


def ingest_contributions(
    filing_year: int,
    skip_existing: bool,
    page: Optional[int] = None,
    page_start: Optional[int] = None,
    page_end: Optional[int] = None,
    max_pages: Optional[int] = None,
    page_size: int = 100,
) -> Dict[str, Any]:
    """Ingest LDA contributions (LD-203) for a given year.

    Args:
        filing_year: Year to ingest (e.g., 2024)
        skip_existing: If True, skip contributions that already exist in S3

    Returns:
        Dict with ingestion statistics
    """
    base_url = f"{LDA_API_BASE_URL}/contributions/"
    session = _requests_session()

    contributions_ingested = 0
    contributions_skipped = 0
    pages_processed = 0

    def fetch_page(pn: int) -> Dict[str, Any]:
        params = {"filing_year": filing_year, "page": pn, "page_size": page_size}
        for attempt in range(8):
            try:
                resp = session.get(base_url, params=params, timeout=30)
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else min(60, 1.5 ** attempt)
                    logger.warning(f"429 on contributions page {pn}. Backing off {wait:.1f}s (attempt {attempt+1})")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                wait = min(60, 1.5 ** attempt)
                logger.warning(f"HTTP error on contributions page {pn}: {e}. Retrying in {wait:.1f}s")
                time.sleep(wait)
        raise RuntimeError(f"Failed to fetch contributions page {pn} after retries")

    # Determine page iteration plan
    if page is not None:
        pages = [int(page)]
    else:
        start = int(page_start) if page_start is not None else 1
        end = int(page_end) if page_end is not None else None
        pages = []
        pn = start
        while True:
            if end is not None and pn > end:
                break
            if max_pages is not None and len(pages) >= int(max_pages):
                break
            pages.append(pn)
            pn += 1

    if not pages:
        pn = 1
        while True:
            data = fetch_page(pn)
            results = data.get("results", [])
            logger.info(f"Processing {len(results)} contributions from page {pn}")
            for contribution in results:
                contribution_id = contribution.get("id")
                if not contribution_id:
                    logger.warning("Skipping contribution without id")
                    continue

                # Check if contribution already exists
                s3_key = (
                    f"{S3_BRONZE_PREFIX}/lobbying/contributions/"
                    f"year={filing_year}/contribution_id={contribution_id}.json.gz"
                )

                if skip_existing and check_s3_object_exists(s3_key):
                    logger.debug(f"Skipping existing contribution: {contribution_id}")
                    contributions_skipped += 1
                    continue

                # Upload contribution to S3
                upload_contribution_to_s3(contribution, s3_key, filing_year)
                contributions_ingested += 1

            pages_processed += 1
            pn += 1
            if max_pages is not None and pages_processed >= int(max_pages):
                break
            if not data.get("next"):
                break
            time.sleep(0.1)
    else:
        for pn in pages:
            data = fetch_page(pn)
            results = data.get("results", [])
            logger.info(f"Processing {len(results)} contributions from page {pn}")
            for contribution in results:
                contribution_id = contribution.get("id")
                if not contribution_id:
                    logger.warning("Skipping contribution without id")
                    continue

            pages_processed += 1
            time.sleep(0.05)

    return {
        "contributions_ingested": contributions_ingested,
        "contributions_skipped": contributions_skipped,
        "pages_processed": pages_processed,
    }


def _gzip_bytes(obj: Dict[str, Any]) -> bytes:
    data = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    return gzip.compress(data)


def ingest_entity_list(
    base_url: str,
    key_fn,
    s3_prefix: str,
    skip_existing: bool = False,
    page: Optional[int] = None,
    page_start: Optional[int] = None,
    page_end: Optional[int] = None,
    max_pages: Optional[int] = None,
    page_size: int = 100,
) -> Dict[str, Any]:
    session = _requests_session()
    s3 = s3_client
    ingested = 0
    skipped = 0
    processed_pages = 0

    def fetch_page(pn: int) -> Dict[str, Any]:
        params = {"page": pn, "page_size": page_size}
        for attempt in range(8):
            try:
                resp = session.get(base_url, params=params, timeout=30)
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else min(60, 1.5 ** attempt)
                    logger.warning(f"429 on entity page {pn}. Backoff {wait:.1f}s")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                wait = min(60, 1.5 ** attempt)
                logger.warning(f"HTTP error on entity page {pn}: {e}. Retrying in {wait:.1f}s")
                time.sleep(wait)
        raise RuntimeError(f"Failed to fetch entity page {pn}")

    # Determine pages
    if page is not None:
        pages = [int(page)]
    else:
        start = int(page_start) if page_start is not None else 1
        end = int(page_end) if page_end is not None else None
        pages = []
        pn = start
        while True:
            if end is not None and pn > end:
                break
            if max_pages is not None and len(pages) >= int(max_pages):
                break
            pages.append(pn)
            pn += 1

    # If no explicit pages, crawl until next is null or max_pages reached
    if not pages:
        pn = 1
        while True:
            data = fetch_page(pn)
            results = data.get("results", [])
            for item in results:
                key, exists_key = key_fn(item)
                if skip_existing:
                    try:
                        s3.head_object(Bucket=S3_BUCKET, Key=exists_key)
                        skipped += 1
                        continue
                    except ClientError:
                        pass
                gz = _gzip_bytes(item)
                s3.put_object(Bucket=S3_BUCKET, Key=key, Body=gz, ContentType="application/gzip",
                              Metadata={"source": LDA_API_BASE_URL, "ingest_ts": datetime.now(timezone.utc).isoformat()})
                ingested += 1
            processed_pages += 1
            pn += 1
            if max_pages is not None and processed_pages >= int(max_pages):
                break
            if not data.get("next"):
                break
            time.sleep(0.1)
    else:
        for pn in pages:
            data = fetch_page(pn)
            results = data.get("results", [])
            for item in results:
                key, exists_key = key_fn(item)
                if skip_existing:
                    try:
                        s3.head_object(Bucket=S3_BUCKET, Key=exists_key)
                        skipped += 1
                        continue
                    except ClientError:
                        pass
                gz = _gzip_bytes(item)
                s3.put_object(Bucket=S3_BUCKET, Key=key, Body=gz, ContentType="application/gzip",
                              Metadata={"source": LDA_API_BASE_URL, "ingest_ts": datetime.now(timezone.utc).isoformat()})
                ingested += 1
            processed_pages += 1
            time.sleep(0.05)

    return {"ingested": ingested, "skipped": skipped, "pages_processed": processed_pages}


def ingest_registrants(
    skip_existing: bool = False,
    page: Optional[int] = None,
    page_start: Optional[int] = None,
    page_end: Optional[int] = None,
    max_pages: Optional[int] = None,
    page_size: int = 100,
) -> Dict[str, Any]:
    logger.info("Starting LDA REGISTRANT ingestion")
    def key_fn(item: Dict[str, Any]):
        rid = item.get("id")
        key = f"{S3_BRONZE_PREFIX}/lobbying/registrants/registrant_id={rid}.json.gz"
        return key, key
    return ingest_entity_list(
        base_url=f"{LDA_API_BASE_URL}/registrants/",
        key_fn=key_fn,
        s3_prefix=f"{S3_BRONZE_PREFIX}/lobbying/registrants/",
        skip_existing=skip_existing,
        page=page,
        page_start=page_start,
        page_end=page_end,
        max_pages=max_pages,
        page_size=page_size,
    )


def ingest_clients(
    skip_existing: bool = False,
    page: Optional[int] = None,
    page_start: Optional[int] = None,
    page_end: Optional[int] = None,
    max_pages: Optional[int] = None,
    page_size: int = 100,
) -> Dict[str, Any]:
    logger.info("Starting LDA CLIENT ingestion")
    def key_fn(item: Dict[str, Any]):
        cid = item.get("id")
        key = f"{S3_BRONZE_PREFIX}/lobbying/clients/client_id={cid}.json.gz"
        return key, key
    return ingest_entity_list(
        base_url=f"{LDA_API_BASE_URL}/clients/",
        key_fn=key_fn,
        s3_prefix=f"{S3_BRONZE_PREFIX}/lobbying/clients/",
        skip_existing=skip_existing,
        page=page,
        page_start=page_start,
        page_end=page_end,
        max_pages=max_pages,
        page_size=page_size,
    )


def ingest_lobbyists(
    skip_existing: bool = False,
    page: Optional[int] = None,
    page_start: Optional[int] = None,
    page_end: Optional[int] = None,
    max_pages: Optional[int] = None,
    page_size: int = 100,
) -> Dict[str, Any]:
    logger.info("Starting LDA LOBBYIST ingestion")
    def key_fn(item: Dict[str, Any]):
        lid = item.get("id")
        key = f"{S3_BRONZE_PREFIX}/lobbying/lobbyists/lobbyist_id={lid}.json.gz"
        return key, key
    return ingest_entity_list(
        base_url=f"{LDA_API_BASE_URL}/lobbyists/",
        key_fn=key_fn,
        s3_prefix=f"{S3_BRONZE_PREFIX}/lobbying/lobbyists/",
        skip_existing=skip_existing,
        page=page,
        page_start=page_start,
        page_end=page_end,
        max_pages=max_pages,
        page_size=page_size,
    )


def ingest_constants() -> Dict[str, Any]:
    logger.info("Starting LDA CONSTANTS ingestion")
    session = _requests_session()
    snapshot = datetime.now(timezone.utc).date().isoformat()
    consts = {
        "filingtypes": f"{LDA_API_BASE_URL}/constants/filing/filingtypes/",
        "lobbyingactivityissues": f"{LDA_API_BASE_URL}/constants/filing/lobbyingactivityissues/",
        "governmententities": f"{LDA_API_BASE_URL}/constants/filing/governmententities/",
        "countries": f"{LDA_API_BASE_URL}/constants/general/countries/",
        "states": f"{LDA_API_BASE_URL}/constants/general/states/",
        "prefixes": f"{LDA_API_BASE_URL}/constants/lobbyist/prefixes/",
        "suffixes": f"{LDA_API_BASE_URL}/constants/lobbyist/suffixes/",
        "itemtypes": f"{LDA_API_BASE_URL}/constants/contribution/itemtypes/",
    }
    ingested = 0
    for name, url in consts.items():
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            obj = resp.json()
            gz = _gzip_bytes(obj)
            key = f"{S3_BRONZE_PREFIX}/lobbying/constants/{name}/snapshot_date={snapshot}/snapshot.json.gz"
            s3_client.put_object(Bucket=S3_BUCKET, Key=key, Body=gz, ContentType="application/gzip",
                                 Metadata={"source": LDA_API_BASE_URL, "ingest_ts": datetime.now(timezone.utc).isoformat()})
            ingested += 1
        except Exception as e:
            logger.error(f"Failed constants {name}: {e}")
    return {"constants_ingested": ingested}


def upload_filing_to_s3(filing: Dict[str, Any], s3_key: str, filing_year: int) -> None:
    """Upload filing JSON to S3 with gzip compression.

    Args:
        filing: Filing data dict
        s3_key: S3 key to upload to
        filing_year: Filing year for metadata
    """
    try:
        # Compress JSON
        json_bytes = json.dumps(filing, indent=2).encode("utf-8")
        compressed = gzip.compress(json_bytes)

        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=compressed,
            ContentType="application/json",
            ContentEncoding="gzip",
            Metadata={
                "filing-year": str(filing_year),
                "filing-uuid": filing.get("filing_uuid", ""),
                "ingestion-timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.debug(f"Uploaded filing to s3://{S3_BUCKET}/{s3_key}")

    except ClientError as e:
        logger.error(f"Error uploading filing to S3: {e}")
        raise


def upload_contribution_to_s3(
    contribution: Dict[str, Any], s3_key: str, filing_year: int
) -> None:
    """Upload contribution JSON to S3 with gzip compression.

    Args:
        contribution: Contribution data dict
        s3_key: S3 key to upload to
        filing_year: Filing year for metadata
    """
    try:
        # Compress JSON
        json_bytes = json.dumps(contribution, indent=2).encode("utf-8")
        compressed = gzip.compress(json_bytes)

        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=compressed,
            ContentType="application/json",
            ContentEncoding="gzip",
            Metadata={
                "filing-year": str(filing_year),
                "contribution-id": str(contribution.get("id", "")),
                "ingestion-timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.debug(f"Uploaded contribution to s3://{S3_BUCKET}/{s3_key}")

    except ClientError as e:
        logger.error(f"Error uploading contribution to S3: {e}")
        raise


def check_s3_object_exists(s3_key: str) -> bool:
    """Check if an S3 object exists.

    Args:
        s3_key: S3 key to check

    Returns:
        True if object exists, False otherwise
    """
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise


def queue_bill_extraction(filing_uuid: str, filing_year: int) -> None:
    """Queue a filing for bill reference extraction.

    Args:
        filing_uuid: UUID of the filing
        filing_year: Year of the filing
    """
    if not SQS_QUEUE_URL:
        logger.warning("SQS_QUEUE_URL not set, skipping queue operation")
        return

    try:
        message = {
            "filing_uuid": filing_uuid,
            "filing_year": filing_year,
            "extraction_type": "bill_references",
        }

        sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message),
            MessageAttributes={
                "filing_uuid": {"StringValue": filing_uuid, "DataType": "String"},
                "filing_year": {"StringValue": str(filing_year), "DataType": "Number"},
            },
        )

        logger.info(f"Queued bill extraction for filing {filing_uuid}")

    except ClientError as e:
        logger.error(f"Error sending SQS message: {e}")
        # Don't raise - extraction can be run separately
