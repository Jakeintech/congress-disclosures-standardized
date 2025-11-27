#!/usr/bin/env python3
"""
Build fact_filings table by joining silver layer data.

Joins:
- silver/filings (filing metadata)
- silver/documents (extraction metadata)
- silver/structured (counts of extracted data)
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import boto3
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_silver_filings(bucket_name: str) -> pd.DataFrame:
    """Load silver/filings."""
    s3 = boto3.client('s3')
    logger.info("Loading silver/filings...")

    prefix = 'silver/house/financial/filings/'
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    dfs = []
    for page in pages:
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.parquet'):
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
                    s3.download_file(bucket_name, obj['Key'], tmp.name)
                    df = pd.read_parquet(tmp.name)
                    dfs.append(df)
                    os.unlink(tmp.name)

    result = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    logger.info(f"Loaded {len(result):,} filings")
    return result


def load_silver_documents(bucket_name: str) -> pd.DataFrame:
    """Load silver/documents."""
    s3 = boto3.client('s3')
    logger.info("Loading silver/documents...")

    prefix = 'silver/house/financial/documents/'
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    dfs = []
    for page in pages:
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.parquet'):
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
                    s3.download_file(bucket_name, obj['Key'], tmp.name)
                    df = pd.read_parquet(tmp.name)
                    dfs.append(df)
                    os.unlink(tmp.name)

    result = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    logger.info(f"Loaded {len(result):,} document records")
    return result


def load_dim_members(bucket_name: str) -> pd.DataFrame:
    """Load dim_members for lookup."""
    s3 = boto3.client('s3')
    logger.info("Loading dim_members...")

    prefix = 'gold/house/financial/dimensions/dim_members/'
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    dfs = []
    for page in pages:
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.parquet'):
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
                    s3.download_file(bucket_name, obj['Key'], tmp.name)
                    df = pd.read_parquet(tmp.name)
                    dfs.append(df)
                    os.unlink(tmp.name)

    result = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    logger.info(f"Loaded {len(result):,} members")
    return result


def lookup_member_key(members_df: pd.DataFrame, first_name: str, last_name: str, state_district: str) -> int:
    """Lookup member_key."""
    if members_df.empty:
        return None

    matches = members_df[
        (members_df['first_name'].str.upper() == str(first_name).upper()) &
        (members_df['last_name'].str.upper() == str(last_name).upper()) &
        (members_df['state_district'] == state_district)
    ]

    if len(matches) > 0:
        return int(matches.iloc[0]['member_key'])

    # Fallback: name only
    matches = members_df[
        (members_df['first_name'].str.upper() == str(first_name).upper()) &
        (members_df['last_name'].str.upper() == str(last_name).upper())
    ]

    return int(matches.iloc[0]['member_key']) if len(matches) > 0 else None


def build_fact_filings(filings_df: pd.DataFrame, documents_df: pd.DataFrame, members_df: pd.DataFrame) -> pd.DataFrame:
    """Build fact_filings by joining silver data."""
    logger.info("Building fact_filings...")

    # Join filings + documents
    merged = filings_df.merge(
        documents_df,
        on=['doc_id', 'year'],
        how='left',
        suffixes=('', '_doc')
    )

    # Derive pdf_type from has_embedded_text
    def determine_pdf_type(row):
        if pd.isna(row.get('has_embedded_text')):
            return 'unknown'
        elif row['has_embedded_text']:
            return 'text'
        else:
            return 'image'

    merged['pdf_type'] = merged.apply(determine_pdf_type, axis=1)

    # Lookup member_key
    logger.info("Looking up member_keys...")
    merged['member_key'] = merged.apply(
        lambda row: lookup_member_key(members_df, row['first_name'], row['last_name'], row['state_district']),
        axis=1
    )

    # Build fact records
    logger.info("Building fact records...")
    records = []

    for _, row in merged.iterrows():
        # Parse filing_date to date_key
        try:
            filing_date = pd.to_datetime(row['filing_date'])
            filing_date_key = int(filing_date.strftime('%Y%m%d'))
        except:
            filing_date_key = None

        # Build PDF URL
        doc_id = row['doc_id']
        year = row['year']
        pdf_url = f"https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{doc_id}.pdf"

        # Calculate confidence score based on extraction quality
        extraction_status = row.get('extraction_status', 'pending')
        pdf_type = row.get('pdf_type', 'unknown')
        char_count = row.get('char_count', 0)

        # Simple confidence heuristic
        if extraction_status == 'success' and pdf_type == 'text' and char_count > 100:
            overall_confidence = 0.95
        elif extraction_status == 'success' and pdf_type == 'text':
            overall_confidence = 0.85
        elif extraction_status == 'success' and pdf_type == 'image' and char_count > 100:
            overall_confidence = 0.75  # OCR is less reliable
        elif extraction_status == 'success':
            overall_confidence = 0.60
        elif extraction_status == 'pending':
            overall_confidence = None
        else:
            overall_confidence = 0.30  # Failed extraction

        record = {
            'member_key': row.get('member_key'),
            'filing_type_key': 1 if row['filing_type'] == 'P' else 2,  # Simplification
            'filing_date_key': filing_date_key,
            'doc_id': doc_id,
            'year': year,
            'pdf_url': pdf_url,
            'pdf_pages': row.get('pages', 0),
            'pdf_file_size_bytes': row.get('pdf_file_size_bytes', 0),
            'pdf_sha256': row.get('pdf_sha256', ''),
            'transaction_count': 0,  # Would need to count from structured.json
            'asset_count': 0,
            'liability_count': 0,
            'position_count': 0,
            'agreement_count': 0,
            'expected_deadline_date': None,
            'days_late': None,
            'is_timely_filed': True,  # Assume true for now
            'is_amendment': False,
            'original_filing_doc_id': None,
            'extraction_method': row.get('extraction_method', 'pypdf'),
            'extraction_status': extraction_status,
            'pdf_type': pdf_type,
            'overall_confidence': overall_confidence,
            'has_extracted_data': extraction_status == 'success',
            'has_structured_data': False,  # Would need to check structured.json exists
            'requires_manual_review': (pdf_type == 'image' or (extraction_status == 'success' and char_count < 100)),
            'textract_pages_used': row.get('textract_pages_used', 0) if pd.notna(row.get('textract_pages_used')) else 0,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

        records.append(record)

    df = pd.DataFrame(records)
    df['filing_key'] = range(1, len(df) + 1)

    return df


def write_to_gold(df: pd.DataFrame, bucket_name: str):
    """Write fact_filings to gold layer."""
    logger.info("Writing to gold layer...")

    output_dir = Path('data/gold/facts/fact_filings')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Partition by year
    for year in df['year'].unique():
        year_df = df[df['year'] == year]
        year_output_dir = output_dir / f'year={year}'
        year_output_dir.mkdir(parents=True, exist_ok=True)

        output_file = year_output_dir / 'part-0000.parquet'
        year_df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
        logger.info(f"  Wrote {year}: {len(year_df)} records -> {output_file}")

    # Upload to S3
    s3 = boto3.client('s3')
    for year in df['year'].unique():
        year_df = df[df['year'] == year]

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            year_df.to_parquet(tmp.name, engine='pyarrow', compression='snappy', index=False)
            s3_key = f'gold/house/financial/facts/fact_filings/year={year}/part-0000.parquet'
            s3.upload_file(tmp.name, bucket_name, s3_key)
            logger.info(f"  Uploaded to s3://{bucket_name}/{s3_key}")
            os.unlink(tmp.name)


def main():
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

    logger.info("=" * 80)
    logger.info("Building fact_filings")
    logger.info("=" * 80)

    filings_df = load_silver_filings(bucket_name)
    documents_df = load_silver_documents(bucket_name)
    members_df = load_dim_members(bucket_name)

    fact_df = build_fact_filings(filings_df, documents_df, members_df)

    logger.info(f"\nSummary:")
    logger.info(f"  Total filings: {len(fact_df)}")
    logger.info(f"  With member_key: {fact_df['member_key'].notna().sum()}")
    logger.info(f"  By extraction method: {fact_df['extraction_method'].value_counts().to_dict()}")
    logger.info(f"  By PDF type: {fact_df['pdf_type'].value_counts().to_dict()}")

    write_to_gold(fact_df, bucket_name)
    logger.info("\n✅ fact_filings build complete!")


if __name__ == '__main__':
    main()
