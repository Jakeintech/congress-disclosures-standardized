#!/usr/bin/env python3
"""
Local Ingestion Script

Downloads and processes Congressional data locally without AWS.
Saves all data to local_data/ directory for inspection.

Usage:
    python3 scripts/local_ingestion.py --year 2025 --limit 10
"""

import os
import sys
import argparse
import requests
import zipfile
import logging
from pathlib import Path
from datetime import datetime
import json
import gzip

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
LOCAL_DATA_DIR = Path(__file__).parent.parent / "local_data"
BUCKET_NAME = "congress-disclosures-standardized"


def setup_local_directories():
    """Create local data directory structure."""
    base_dir = LOCAL_DATA_DIR / BUCKET_NAME

    directories = [
        "bronze/house/financial",
        "bronze/congress/member",
        "bronze/congress/bill",
        "bronze/lobbying/filings",
        "silver/house/financial/documents",
        "silver/house/financial/text",
        "silver/congress/bill_actions",
        "gold/aggregates",
    ]

    for dir_path in directories:
        (base_dir / dir_path).mkdir(parents=True, exist_ok=True)

    logger.info(f"✅ Created local data directories at: {base_dir}")
    return base_dir


def download_house_fd_zip(year: int, base_dir: Path) -> Path:
    """Download House Financial Disclosure ZIP file.

    Args:
        year: Year to download (e.g., 2025)
        base_dir: Base directory for local data

    Returns:
        Path to downloaded ZIP file
    """
    url = f"https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip"
    zip_path = base_dir / f"bronze/house/financial/year={year}/raw_zip/{year}FD.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"📥 Downloading {url}...")

    try:
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0 and downloaded % (1024 * 1024 * 10) == 0:  # Log every 10MB
                        progress = (downloaded / total_size) * 100
                        logger.info(f"   Progress: {progress:.1f}% ({downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB)")

        logger.info(f"✅ Downloaded {zip_path.stat().st_size // (1024*1024)}MB to {zip_path}")
        return zip_path

    except Exception as e:
        logger.error(f"❌ Failed to download: {e}")
        raise


def extract_pdfs_from_zip(zip_path: Path, base_dir: Path, limit: int = None) -> dict:
    """Extract PDFs from House FD ZIP file.

    Args:
        zip_path: Path to ZIP file
        base_dir: Base directory for local data
        limit: Maximum number of PDFs to extract (None for all)

    Returns:
        Dict with extraction statistics
    """
    logger.info(f"📦 Extracting PDFs from {zip_path}...")

    year = int(zip_path.stem.replace('FD', ''))
    stats = {'total': 0, 'extracted': 0, 'by_type': {}}

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Get list of PDF files
            pdf_files = [name for name in zf.namelist() if name.endswith('.pdf')]
            stats['total'] = len(pdf_files)

            logger.info(f"   Found {len(pdf_files)} PDFs in ZIP")

            if limit:
                pdf_files = pdf_files[:limit]
                logger.info(f"   Limiting to {limit} PDFs for testing")

            for pdf_name in pdf_files:
                # Extract filing type from filename
                # Format: {doc_id}.pdf or similar
                doc_id = Path(pdf_name).stem

                # Determine filing type (default to 'P' for testing)
                # In real implementation, would parse XML index
                filing_type = 'P'  # Periodic Transaction Report

                # Create destination path
                pdf_dest = base_dir / f"bronze/house/financial/year={year}/filing_type={filing_type}/pdfs/{doc_id}.pdf"
                pdf_dest.parent.mkdir(parents=True, exist_ok=True)

                # Extract PDF
                with zf.open(pdf_name) as source:
                    with open(pdf_dest, 'wb') as dest:
                        dest.write(source.read())

                stats['extracted'] += 1
                stats['by_type'][filing_type] = stats['by_type'].get(filing_type, 0) + 1

                if stats['extracted'] % 100 == 0:
                    logger.info(f"   Extracted {stats['extracted']} PDFs...")

            logger.info(f"✅ Extracted {stats['extracted']} PDFs")
            logger.info(f"   By type: {stats['by_type']}")

            return stats

    except Exception as e:
        logger.error(f"❌ Failed to extract PDFs: {e}")
        raise


def download_congress_bills(base_dir: Path, limit: int = 10):
    """Download sample bills from Congress.gov API.

    Args:
        base_dir: Base directory for local data
        limit: Number of bills to download
    """
    logger.info(f"📥 Downloading {limit} bills from Congress.gov API...")

    # Congress.gov API
    api_key = os.environ.get('CONGRESS_API_KEY')
    if not api_key:
        logger.warning("⚠️  CONGRESS_API_KEY not set, skipping bill download")
        logger.info("   Get a free API key at: https://api.congress.gov/sign-up/")
        return

    url = "https://api.congress.gov/v3/bill/119"  # 119th Congress
    params = {
        'api_key': api_key,
        'format': 'json',
        'limit': limit
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        bills = data.get('bills', [])
        logger.info(f"   Retrieved {len(bills)} bills")

        for bill in bills:
            bill_type = bill.get('type', '').lower()
            bill_number = bill.get('number')
            congress = bill.get('congress')

            if not all([bill_type, bill_number, congress]):
                continue

            # Save to Bronze
            bill_path = base_dir / f"bronze/congress/bill/congress={congress}/bill_type={bill_type}/ingest_date={datetime.now().strftime('%Y-%m-%d')}/{bill_number}.json.gz"
            bill_path.parent.mkdir(parents=True, exist_ok=True)

            with gzip.open(bill_path, 'wt', encoding='utf-8') as f:
                json.dump(bill, f, indent=2)

            logger.info(f"   Saved {congress}-{bill_type}-{bill_number}")

        logger.info(f"✅ Downloaded {len(bills)} bills to Bronze")

    except Exception as e:
        logger.error(f"⚠️  Failed to download bills: {e}")


def download_lobbying_filings(year: int, base_dir: Path, limit: int = 10):
    """Download sample lobbying filings from LDA API.

    Args:
        year: Year to download
        base_dir: Base directory for local data
        limit: Number of filings to download
    """
    logger.info(f"📥 Downloading {limit} lobbying filings for {year}...")

    url = "https://lda.senate.gov/api/v1/filings/"
    params = {
        'filing_year': year,
        'page_size': limit
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        filings = data.get('results', [])
        logger.info(f"   Retrieved {len(filings)} filings")

        for filing in filings:
            filing_uuid = filing.get('filing_uuid')
            if not filing_uuid:
                continue

            # Save to Bronze
            filing_path = base_dir / f"bronze/lobbying/filings/year={year}/filing_uuid={filing_uuid}.json.gz"
            filing_path.parent.mkdir(parents=True, exist_ok=True)

            with gzip.open(filing_path, 'wt', encoding='utf-8') as f:
                json.dump(filing, f, indent=2)

            logger.info(f"   Saved filing {filing_uuid}")

        logger.info(f"✅ Downloaded {len(filings)} lobbying filings to Bronze")

    except Exception as e:
        logger.error(f"⚠️  Failed to download lobbying filings: {e}")


def create_summary_report(base_dir: Path) -> dict:
    """Generate summary report of local data.

    Args:
        base_dir: Base directory for local data

    Returns:
        Summary statistics dict
    """
    summary = {
        'timestamp': datetime.now().isoformat(),
        'bronze': {},
        'silver': {},
        'gold': {}
    }

    # Count files in each layer
    for layer in ['bronze', 'silver', 'gold']:
        layer_dir = base_dir / layer
        if layer_dir.exists():
            file_count = sum(1 for _ in layer_dir.rglob('*') if _.is_file())
            dir_count = sum(1 for _ in layer_dir.rglob('*') if _.is_dir())
            total_size = sum(f.stat().st_size for f in layer_dir.rglob('*') if f.is_file())

            summary[layer] = {
                'files': file_count,
                'directories': dir_count,
                'total_size_mb': round(total_size / (1024 * 1024), 2)
            }

    # Save summary
    summary_path = base_dir / 'local_data_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Download Congressional data locally for development"
    )
    parser.add_argument(
        '--year',
        type=int,
        default=2025,
        help='Year to download (default: 2025)'
    )
    parser.add_argument(
        '--limit-pdfs',
        type=int,
        default=50,
        help='Maximum PDFs to extract from House FD ZIP (default: 50, 0 for all)'
    )
    parser.add_argument(
        '--limit-bills',
        type=int,
        default=10,
        help='Maximum bills to download (default: 10)'
    )
    parser.add_argument(
        '--limit-lobbying',
        type=int,
        default=10,
        help='Maximum lobbying filings to download (default: 10)'
    )
    parser.add_argument(
        '--skip-house',
        action='store_true',
        help='Skip House Financial Disclosures download'
    )
    parser.add_argument(
        '--skip-bills',
        action='store_true',
        help='Skip Congress bills download'
    )
    parser.add_argument(
        '--skip-lobbying',
        action='store_true',
        help='Skip lobbying filings download'
    )

    args = parser.parse_args()

    # Banner
    print("\n" + "=" * 80)
    print("🏠 LOCAL DATA INGESTION".center(80))
    print("=" * 80)
    print(f"📅 Year: {args.year}")
    print(f"📁 Data directory: {LOCAL_DATA_DIR.absolute()}")
    print("=" * 80 + "\n")

    # Setup directories
    base_dir = setup_local_directories()

    # Download House Financial Disclosures
    if not args.skip_house:
        try:
            zip_path = download_house_fd_zip(args.year, base_dir)
            limit = args.limit_pdfs if args.limit_pdfs > 0 else None
            extract_pdfs_from_zip(zip_path, base_dir, limit=limit)
        except Exception as e:
            logger.error(f"Failed to process House FD data: {e}")

    # Download Congress bills
    if not args.skip_bills:
        try:
            download_congress_bills(base_dir, limit=args.limit_bills)
        except Exception as e:
            logger.error(f"Failed to download bills: {e}")

    # Download lobbying filings
    if not args.skip_lobbying:
        try:
            download_lobbying_filings(args.year, base_dir, limit=args.limit_lobbying)
        except Exception as e:
            logger.error(f"Failed to download lobbying filings: {e}")

    # Generate summary
    summary = create_summary_report(base_dir)

    # Print summary
    print("\n" + "=" * 80)
    print("📊 INGESTION SUMMARY".center(80))
    print("=" * 80)
    for layer in ['bronze', 'silver', 'gold']:
        if layer in summary:
            print(f"\n{layer.upper()}:")
            print(f"   Files: {summary[layer].get('files', 0)}")
            print(f"   Directories: {summary[layer].get('directories', 0)}")
            print(f"   Total size: {summary[layer].get('total_size_mb', 0)} MB")

    print("\n" + "=" * 80)
    print(f"✅ Local ingestion complete!")
    print(f"📁 Data saved to: {base_dir}")
    print(f"\nNext steps:")
    print(f"   1. View data: make local-view")
    print(f"   2. Browse data: make local-serve")
    print(f"   3. Run aggregation: make local-run-aggregate")
    print("=" * 80 + "\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
