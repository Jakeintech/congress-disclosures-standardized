#!/usr/bin/env python3
"""
Analyze bills and generate industry impact tags.

Reads bills from Silver dim_bill layer, applies industry classification,
extracts tickers, and writes results to Gold bill_industry_tags table.

Output: gold/congress/bill_industry_tags/congress={congress}/
Schema: bill_id, industry, ticker, confidence_score, extraction_method, matched_keywords
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import boto3
from io import BytesIO
from datetime import datetime
import logging
import argparse
from typing import List, Dict

# Import our classification libraries
from backend.lib.ingestion.industry_classifier import IndustryClassifier, load_sp500_tickers
from backend.lib.ingestion.ticker_industry_mapper import TickerIndustryMapper

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


def read_parquet_from_s3(s3_client, prefix: str) -> pd.DataFrame:
    """Read all Parquet files from an S3 prefix."""
    logger.info(f"Reading from s3://{BUCKET_NAME}/{prefix}")

    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
    if 'Contents' not in response:
        logger.warning(f"No files found in {prefix}")
        return pd.DataFrame()

    dfs = []
    for obj in response['Contents']:
        if obj['Key'].endswith('.parquet'):
            logger.debug(f"  Reading {obj['Key']}")
            response_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=obj['Key'])
            df = pd.read_parquet(BytesIO(response_obj['Body'].read()))
            dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)


def analyze_bill(
    bill: pd.Series,
    classifier: IndustryClassifier,
    known_tickers: set,
    ticker_mapper: TickerIndustryMapper
) -> List[Dict]:
    """
    Analyze a single bill for industry impact.

    Returns list of industry tag records.
    """
    # Extract bill data
    bill_id = bill.get('bill_id')
    title = bill.get('title', '')
    summary = bill.get('summary', '')
    policy_area = bill.get('policy_area', '')

    # Handle subjects (could be list or string)
    subjects = bill.get('subjects', [])
    if isinstance(subjects, str):
        subjects = [subjects] if subjects else []
    elif pd.isna(subjects):
        subjects = []

    # Classify the bill
    classification = classifier.classify_bill(
        title=title,
        summary=summary,
        policy_area=policy_area,
        subjects=subjects,
        known_tickers=known_tickers
    )

    records = []

    # Process industry tags
    for tag in classification['industry_tags']:
        # Get tickers associated with this industry
        industry_tickers = ticker_mapper.tickers_for_industry(tag['industry'])

        # Filter to only tickers mentioned in the bill
        mentioned_tickers = [
            t['ticker'] for t in classification['tickers']
            if t['ticker'] in industry_tickers
        ]

        record = {
            'bill_id': bill_id,
            'congress': bill.get('congress'),
            'bill_type': bill.get('bill_type'),
            'bill_number': bill.get('bill_number'),
            'industry': tag['industry'],
            'confidence_score': tag['confidence'],
            'extraction_method': ','.join(tag['methods']),
            'matched_keywords': ','.join(tag['matched_keywords'][:10]),  # Limit to 10
            'tickers': ','.join(mentioned_tickers) if mentioned_tickers else None,
            'has_ticker_mention': len(mentioned_tickers) > 0,
            'created_at': datetime.utcnow().isoformat()
        }
        records.append(record)

    # If no industry tags but tickers were found, create generic tags based on ticker industries
    if not records and classification['tickers']:
        ticker_industries = set()
        for ticker_info in classification['tickers']:
            ticker = ticker_info['ticker']
            industries = ticker_mapper.get_all_industries(ticker)
            ticker_industries.update(industries)

        for industry in ticker_industries:
            records.append({
                'bill_id': bill_id,
                'congress': bill.get('congress'),
                'bill_type': bill.get('bill_type'),
                'bill_number': bill.get('bill_number'),
                'industry': industry,
                'confidence_score': 1.0,  # High confidence for ticker-based
                'extraction_method': 'ticker_mention',
                'matched_keywords': '',
                'tickers': ','.join([t['ticker'] for t in classification['tickers']]),
                'has_ticker_mention': True,
                'created_at': datetime.utcnow().isoformat()
            })

    return records


def analyze_bills(congress_filter: int = None, min_confidence: float = 0.0) -> pd.DataFrame:
    """
    Analyze all bills and generate industry tags.

    Args:
        congress_filter: Only analyze specific congress (e.g., 118, 119)
        min_confidence: Minimum confidence threshold (0.0-1.0)

    Returns:
        DataFrame with industry tags
    """
    s3 = boto3.client('s3')

    # Load bills from Silver
    logger.info("Loading bills from Silver layer...")
    bills_df = read_parquet_from_s3(s3, 'silver/congress/dim_bill/')

    if bills_df.empty:
        logger.error("No bills found in Silver layer")
        return pd.DataFrame()

    logger.info(f"Loaded {len(bills_df)} bills")

    # Filter by congress if specified
    if congress_filter:
        bills_df = bills_df[bills_df['congress'] == congress_filter]
        logger.info(f"Filtered to {len(bills_df)} bills for congress {congress_filter}")

    # Initialize classifier and mapper
    logger.info("Initializing industry classifier...")
    classifier = IndustryClassifier()
    known_tickers = load_sp500_tickers()
    ticker_mapper = TickerIndustryMapper()

    # Analyze each bill
    logger.info("Analyzing bills for industry impact...")
    all_records = []

    for idx, bill in bills_df.iterrows():
        if idx % 100 == 0:
            logger.info(f"  Processed {idx}/{len(bills_df)} bills...")

        try:
            records = analyze_bill(bill, classifier, known_tickers, ticker_mapper)
            all_records.extend(records)
        except Exception as e:
            logger.error(f"Error analyzing bill {bill.get('bill_id')}: {e}")
            continue

    if not all_records:
        logger.warning("No industry tags generated")
        return pd.DataFrame()

    # Convert to DataFrame
    df = pd.DataFrame(all_records)

    # Apply confidence filter
    if min_confidence > 0:
        df = df[df['confidence_score'] >= min_confidence]
        logger.info(f"Filtered to {len(df)} tags with confidence >= {min_confidence}")

    logger.info(f"\nGenerated {len(df)} industry tags for {df['bill_id'].nunique()} bills")

    return df


def write_gold_parquet_partitioned(df: pd.DataFrame, prefix: str, partition_col: str):
    """Write DataFrame to Gold layer partitioned by column."""
    s3 = boto3.client('s3')

    if partition_col not in df.columns:
        logger.error(f"Partition column '{partition_col}' not found in DataFrame")
        return

    # Write partitioned by congress
    for partition_value in sorted(df[partition_col].unique()):
        partition_df = df[df[partition_col] == partition_value].copy()
        s3_key = f"{prefix}/{partition_col}={partition_value}/part-0000.parquet"

        buffer = BytesIO()
        partition_df.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
        buffer.seek(0)

        s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
        logger.info(f"Wrote {len(partition_df)} records to s3://{BUCKET_NAME}/{s3_key}")


def main():
    parser = argparse.ArgumentParser(description='Analyze bills for industry impact')
    parser.add_argument(
        '--congress',
        type=int,
        help='Analyze specific congress only (e.g., 118, 119)'
    )
    parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.0,
        help='Minimum confidence threshold (0.0-1.0, default: 0.0)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: analyze first 10 bills only'
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("Bill Industry Impact Analysis")
    logger.info("=" * 80)

    # Analyze bills
    df = analyze_bills(
        congress_filter=args.congress,
        min_confidence=args.min_confidence
    )

    if df.empty:
        logger.error("No data to write")
        return

    # Test mode: limit output
    if args.test:
        logger.info("TEST MODE: Limiting to first 100 records")
        df = df.head(100)

    # Print summary statistics
    logger.info("\n" + "=" * 80)
    logger.info("Summary Statistics")
    logger.info("=" * 80)
    logger.info(f"Total industry tags: {len(df)}")
    logger.info(f"Bills with tags: {df['bill_id'].nunique()}")
    logger.info(f"Average tags per bill: {len(df) / df['bill_id'].nunique():.2f}")
    logger.info(f"\nTags by industry:")
    for industry, count in df['industry'].value_counts().items():
        pct = (count / len(df)) * 100
        logger.info(f"  {industry}: {count} ({pct:.1f}%)")

    logger.info(f"\nConfidence distribution:")
    logger.info(f"  High (>0.7): {(df['confidence_score'] > 0.7).sum()}")
    logger.info(f"  Medium (0.4-0.7): {((df['confidence_score'] >= 0.4) & (df['confidence_score'] <= 0.7)).sum()}")
    logger.info(f"  Low (<0.4): {(df['confidence_score'] < 0.4).sum()}")

    logger.info(f"\nBills with ticker mentions: {df['has_ticker_mention'].sum()}")

    if 'congress' in df.columns:
        logger.info(f"\nBy congress: {df['congress'].value_counts().to_dict()}")

    # Write to Gold layer
    logger.info("\nWriting to Gold layer...")
    write_gold_parquet_partitioned(
        df,
        'gold/congress/bill_industry_tags',
        'congress'
    )

    logger.info("\n✅ Bill industry analysis complete!")
    logger.info(f"Output: s3://{BUCKET_NAME}/gold/congress/bill_industry_tags/")


if __name__ == '__main__':
    main()
