#!/usr/bin/env python3
"""
Compute agg_document_quality aggregate table.

This tracks document quality metrics by member to identify those submitting
hard-to-process PDFs (image-based scans vs text-based PDFs).

Metrics tracked:
- % image-based PDFs (KEY METRIC for identifying suspicious patterns)
- Average extraction confidence
- Manual review rates
- Data completeness
- Document quality score (0-100)
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import boto3
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Thresholds from .env
MIN_CONFIDENCE_SCORE = float(os.environ.get('MIN_CONFIDENCE_SCORE', '0.85'))
IMAGE_PDF_WARNING_THRESHOLD = float(os.environ.get('IMAGE_PDF_WARNING_THRESHOLD', '0.30'))
QUALITY_WEIGHT_CONFIDENCE = float(os.environ.get('QUALITY_WEIGHT_CONFIDENCE', '0.4'))
QUALITY_WEIGHT_FORMAT = float(os.environ.get('QUALITY_WEIGHT_FORMAT', '0.3'))
QUALITY_WEIGHT_COMPLETENESS = float(os.environ.get('QUALITY_WEIGHT_COMPLETENESS', '0.3'))


def load_fact_filings(bucket_name: str) -> pd.DataFrame:
    """Load fact_filings from gold layer."""
    s3 = boto3.client('s3')

    logger.info("Loading fact_filings...")

    prefix = 'gold/house/financial/facts/fact_filings/'
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    dfs = []
    for page in pages:
        if 'Contents' not in page:
            continue

        for obj in page['Contents']:
            if obj['Key'].endswith('.parquet'):
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
                    s3.download_file(bucket_name, obj['Key'], tmp.name)
                    df = pd.read_parquet(tmp.name)
                    dfs.append(df)
                    os.unlink(tmp.name)

    if not dfs:
        logger.warning("No fact_filings found! Returning empty DataFrame.")
        return pd.DataFrame(columns=[
            'member_key', 'filing_type_key', 'filing_date_key', 'doc_id', 'year',
            'pdf_url', 'pdf_pages', 'pdf_file_size_bytes', 'pdf_sha256',
            'transaction_count', 'asset_count', 'liability_count', 'position_count',
            'agreement_count', 'expected_deadline_date', 'days_late', 'is_timely_filed',
            'is_amendment', 'original_filing_doc_id', 'extraction_method',
            'extraction_status', 'pdf_type', 'overall_confidence', 'has_extracted_data',
            'has_structured_data', 'requires_manual_review', 'textract_pages_used',
            'created_at', 'updated_at', 'filing_date'
        ])

    all_filings = pd.concat(dfs, ignore_index=True)
    logger.info(f"Loaded {len(all_filings):,} filings")

    return all_filings


def load_dim_members(bucket_name: str) -> pd.DataFrame:
    """Load dim_members for lookup."""
    s3 = boto3.client('s3')

    prefix = 'gold/house/financial/dimensions/dim_members/'
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    dfs = []
    for page in pages:
        if 'Contents' not in page:
            continue

        for obj in page['Contents']:
            if obj['Key'].endswith('.parquet'):
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp:
                    s3.download_file(bucket_name, obj['Key'], tmp.name)
                    df = pd.read_parquet(tmp.name)
                    dfs.append(df)
                    os.unlink(tmp.name)

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def compute_document_quality_by_member(
    filings_df: pd.DataFrame,
    period_start: str,
    period_end: str
) -> pd.DataFrame:
    """Compute document quality metrics by member for a period."""

    # Filter to period - handle NaN values
    filings_df['filing_date'] = pd.to_datetime(
        filings_df['filing_date_key'].fillna(0).astype(int).astype(str),
        format='%Y%m%d',
        errors='coerce'
    )
    period_filings = filings_df[
        (filings_df['filing_date'] >= period_start) &
        (filings_df['filing_date'] <= period_end)
    ]

    logger.info(f"Computing quality metrics for {len(period_filings):,} filings in period {period_start} to {period_end}")

    # Group by member_key
    quality_metrics = []

    for member_key, member_filings in period_filings.groupby('member_key'):
        # Total counts
        total_filings = len(member_filings)
        ptr_filings = len(member_filings[member_filings['filing_type_key'] == 1])
        annual_filings = len(member_filings[member_filings['filing_type_key'].isin([2, 3, 4])])

        # PDF type breakdown
        text_pdf_count = len(member_filings[member_filings['pdf_type'] == 'text'])
        image_pdf_count = len(member_filings[member_filings['pdf_type'] == 'image'])
        hybrid_pdf_count = len(member_filings[member_filings['pdf_type'] == 'hybrid'])

        image_pdf_pct = image_pdf_count / total_filings if total_filings > 0 else 0.0

        # Confidence metrics
        avg_confidence = member_filings['overall_confidence'].mean()
        min_confidence = member_filings['overall_confidence'].min()
        low_confidence_count = len(member_filings[member_filings['overall_confidence'] < MIN_CONFIDENCE_SCORE])

        # Manual review
        manual_review_count = len(member_filings[member_filings['requires_manual_review'] == True])

        # Extraction failures
        extraction_failure_count = len(member_filings[member_filings['extraction_status'] == 'failed'])

        # Data completeness (would need to calculate from structured data)
        avg_data_completeness_pct = 100.0  # Placeholder - calculate from structured metadata

        # Zero transaction filings (PTRs with 0 transactions extracted)
        zero_transaction_count = len(member_filings[
            (member_filings['filing_type_key'] == 1) &
            (member_filings['transaction_count'] == 0)
        ])

        # Quality score calculation
        # quality_score = (avg_confidence * WEIGHT_CONFIDENCE + (1 - image_pdf_pct) * WEIGHT_FORMAT + avg_completeness * WEIGHT_COMPLETENESS) * 100
        quality_score = (
            (avg_confidence if pd.notna(avg_confidence) else 0.0) * QUALITY_WEIGHT_CONFIDENCE +
            (1 - image_pdf_pct) * QUALITY_WEIGHT_FORMAT +
            (avg_data_completeness_pct / 100.0) * QUALITY_WEIGHT_COMPLETENESS
        ) * 100

        # Quality category
        if quality_score >= 90:
            quality_category = 'Excellent'
        elif quality_score >= 75:
            quality_category = 'Good'
        elif quality_score >= 60:
            quality_category = 'Fair'
        else:
            quality_category = 'Poor'

        # Flag hard to process
        is_hard_to_process = image_pdf_pct > IMAGE_PDF_WARNING_THRESHOLD

        # Quality trend (would compare to previous period)
        quality_trend = 'Insufficient Data'  # Placeholder

        # Days since last filing
        last_filing_date = member_filings['filing_date'].max()
        days_since_last_filing = (datetime.now() - last_filing_date).days

        # Textract usage
        textract_pages_used = member_filings['textract_pages_used'].sum()

        # Build record
        record = {
            'member_key': member_key,
            'period_start_date': period_start,
            'period_end_date': period_end,
            'total_filings': total_filings,
            'ptr_filings': ptr_filings,
            'annual_filings': annual_filings,
            'text_pdf_count': text_pdf_count,
            'image_pdf_count': image_pdf_count,
            'hybrid_pdf_count': hybrid_pdf_count,
            'image_pdf_pct': image_pdf_pct,
            'avg_confidence_score': avg_confidence,
            'min_confidence_score': min_confidence,
            'low_confidence_count': low_confidence_count,
            'manual_review_count': manual_review_count,
            'extraction_failure_count': extraction_failure_count,
            'avg_data_completeness_pct': avg_data_completeness_pct,
            'zero_transaction_filing_count': zero_transaction_count,
            'quality_score': quality_score,
            'quality_category': quality_category,
            'is_hard_to_process': is_hard_to_process,
            'quality_trend': quality_trend,
            'days_since_last_filing': days_since_last_filing,
            'textract_pages_used': int(textract_pages_used)
        }

        quality_metrics.append(record)

    if not quality_metrics:
        return pd.DataFrame(columns=[
            'member_key', 'period_start_date', 'period_end_date', 'total_filings',
            'ptr_filings', 'annual_filings', 'text_pdf_count', 'image_pdf_count',
            'hybrid_pdf_count', 'image_pdf_pct', 'avg_confidence_score',
            'min_confidence_score', 'low_confidence_count', 'manual_review_count',
            'extraction_failure_count', 'avg_data_completeness_pct',
            'zero_transaction_filing_count', 'quality_score', 'quality_category',
            'is_hard_to_process', 'quality_trend', 'days_since_last_filing',
            'textract_pages_used'
        ])

    return pd.DataFrame(quality_metrics)


def write_to_gold(df: pd.DataFrame, bucket_name: str):
    """Write agg_document_quality to gold layer."""
    if df.empty:
        logger.warning("DataFrame is empty, skipping write to gold layer.")
        return

    logger.info("Writing to gold layer...")

    # Save locally
    output_dir = Path('data/gold/aggregates/agg_document_quality')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Partition by year
    df['year'] = pd.to_datetime(df['period_start_date']).dt.year

    for year in df['year'].unique():
        year_df = df[df['year'] == year].drop(columns=['year'])
        year_output_dir = output_dir / f'year={year}'
        year_output_dir.mkdir(parents=True, exist_ok=True)

        output_file = year_output_dir / 'part-0000.parquet'
        year_df.to_parquet(
            output_file,
            engine='pyarrow',
            compression='snappy',
            index=False
        )
        logger.info(f"  Wrote {year}: {len(year_df)} records -> {output_file}")

    # Upload to S3
    s3 = boto3.client('s3')

    for year in df['year'].unique():
        year_df = df[df['year'] == year].drop(columns=['year'])

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            year_df.to_parquet(tmp.name, engine='pyarrow', compression='snappy', index=False)

            s3_key = f'gold/house/financial/aggregates/agg_document_quality/year={year}/part-0000.parquet'
            s3.upload_file(tmp.name, bucket_name, s3_key)
            logger.info(f"  Uploaded to s3://{bucket_name}/{s3_key}")

            os.unlink(tmp.name)


def main():
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

    logger.info("=" * 80)
    logger.info("Computing agg_document_quality")
    logger.info("=" * 80)

    # Define period (monthly aggregates)
    # For demo, compute for 2025 full year
    period_start = '2025-01-01'
    period_end = '2025-12-31'

    # Load fact_filings
    filings_df = load_fact_filings(bucket_name)

    # Compute quality metrics
    quality_df = compute_document_quality_by_member(filings_df, period_start, period_end)

    # Load dim_members for member names
    members_df = load_dim_members(bucket_name)

    # Join for display
    if not members_df.empty:
        display_df = quality_df.merge(
            members_df[['member_key', 'full_name', 'party', 'state_district']],
            on='member_key',
            how='left'
        )

        # Show flagged members
        flagged = display_df[display_df['is_hard_to_process'] == True].sort_values('image_pdf_pct', ascending=False)

        logger.info(f"\n🔍 FLAGGED: {len(flagged)} members with >30% image-based PDFs:")
        for _, row in flagged.head(20).iterrows():
            logger.info(f"  {row['full_name']} ({row['party']}-{row['state_district']}): "
                       f"{row['image_pdf_pct']*100:.1f}% image PDFs, quality score: {row['quality_score']:.1f}")

    # Write to gold layer
    write_to_gold(quality_df, bucket_name)

    logger.info(f"\nSummary:")
    if not quality_df.empty:
        logger.info(f"  Total members: {len(quality_df)}")
        logger.info(f"  Flagged as hard to process: {quality_df['is_hard_to_process'].sum()}")
        logger.info(f"  Average quality score: {quality_df['quality_score'].mean():.1f}")
        logger.info(f"  Quality breakdown: {quality_df['quality_category'].value_counts().to_dict()}")
    else:
        logger.info("  No data to summarize.")

    logger.info("\n✅ agg_document_quality computation complete!")


if __name__ == '__main__':
    main()
