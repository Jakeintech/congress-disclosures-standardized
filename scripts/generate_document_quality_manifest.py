#!/usr/bin/env python3
"""
Generate document_quality.json manifest for website.

This creates a public JSON file that surfaces document quality metrics,
allowing users to see which members submit hard-to-process PDFs.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import boto3
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_agg_document_quality(bucket_name: str) -> pd.DataFrame:
    """Load agg_document_quality from gold layer."""
    s3 = boto3.client('s3')

    logger.info("Loading agg_document_quality...")

    prefix = 'gold/house/financial/aggregates/agg_document_quality/'
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
        logger.warning("No agg_document_quality found! Returning empty DataFrame.")
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

    return pd.concat(dfs, ignore_index=True)


def load_dim_members(bucket_name: str) -> pd.DataFrame:
    """Load dim_members for member names."""
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


def generate_manifest(quality_df: pd.DataFrame, members_df: pd.DataFrame) -> dict:
    """Generate document quality manifest JSON."""

    # Handle empty quality_df
    if quality_df.empty:
        return {
            'generated_at': pd.Timestamp.now().isoformat(),
            'period_start': None,
            'period_end': None,
            'total_members': 0,
            'flagged_members_count': 0,
            'average_quality_score': 0.0,
            'quality_breakdown': {},
            'members': []
        }

    # Join with member names
    manifest_df = quality_df.merge(
        members_df[['member_key', 'full_name', 'party', 'state', 'state_district', 'bioguide_id']],
        on='member_key',
        how='left'
    )

    # Sort by image_pdf_pct descending (worst first)
    manifest_df = manifest_df.sort_values('image_pdf_pct', ascending=False)

    # Build manifest
    manifest = {
        'generated_at': pd.Timestamp.now().isoformat(),
        'period_start': manifest_df['period_start_date'].iloc[0],
        'period_end': manifest_df['period_end_date'].iloc[0],
        'total_members': len(manifest_df),
        'flagged_members_count': int(manifest_df['is_hard_to_process'].sum()),
        'average_quality_score': float(manifest_df['quality_score'].mean()),
        'quality_breakdown': manifest_df['quality_category'].value_counts().to_dict(),
        'members': []
    }

    # Add member records
    for _, row in manifest_df.iterrows():
        member_record = {
            'member_key': int(row['member_key']),
            'bioguide_id': row.get('bioguide_id'),
            'full_name': row.get('full_name', 'Unknown'),
            'party': row.get('party'),
            'state': row.get('state'),
            'state_district': row.get('state_district'),
            'total_filings': int(row['total_filings']),
            'ptr_filings': int(row['ptr_filings']),
            'text_pdf_count': int(row['text_pdf_count']),
            'image_pdf_count': int(row['image_pdf_count']),
            'hybrid_pdf_count': int(row['hybrid_pdf_count']),
            'image_pdf_pct': round(float(row['image_pdf_pct']) * 100, 1),  # Convert to percentage
            'avg_confidence_score': round(float(row['avg_confidence_score']) if pd.notna(row['avg_confidence_score']) else 0.0, 3),
            'low_confidence_count': int(row['low_confidence_count']),
            'manual_review_count': int(row['manual_review_count']),
            'extraction_failure_count': int(row['extraction_failure_count']),
            'zero_transaction_filing_count': int(row['zero_transaction_filing_count']),
            'quality_score': round(float(row['quality_score']), 1),
            'quality_category': row['quality_category'],
            'is_hard_to_process': bool(row['is_hard_to_process']),
            'days_since_last_filing': int(row['days_since_last_filing']),
            'textract_pages_used': int(row['textract_pages_used'])
        }

        manifest['members'].append(member_record)

    return manifest


def main():
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

    logger.info("=" * 80)
    logger.info("Generating document_quality.json manifest")
    logger.info("=" * 80)

    # Load data
    quality_df = load_agg_document_quality(bucket_name)
    members_df = load_dim_members(bucket_name)

    # Generate manifest
    manifest = generate_manifest(quality_df, members_df)

    logger.info(f"\nManifest summary:")
    logger.info(f"  Total members: {manifest['total_members']}")
    logger.info(f"  Flagged members: {manifest['flagged_members_count']}")
    logger.info(f"  Average quality score: {manifest['average_quality_score']:.1f}")
    logger.info(f"  Quality breakdown: {manifest['quality_breakdown']}")

    # Save locally
    output_dir = Path('website/data')
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / 'document_quality.json'
    with open(output_file, 'w') as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"\nWrote to: {output_file}")

    # Upload to S3 (website bucket)
    s3 = boto3.client('s3')

    try:
        s3_key = 'website/data/document_quality.json'
        s3.upload_file(
            str(output_file),
            bucket_name,
            s3_key,
            ExtraArgs={
                'ContentType': 'application/json'
            }
        )
        logger.info(f"✅ Uploaded to s3://{bucket_name}/{s3_key}")
        logger.info(f"   Public URL: http://{bucket_name}.s3-website-us-east-1.amazonaws.com/website/data/document_quality.json")

    except Exception as e:
        logger.error(f"Error uploading to S3: {e}")

    logger.info("\n✅ Manifest generation complete!")


if __name__ == '__main__':
    main()
