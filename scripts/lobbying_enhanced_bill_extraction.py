#!/usr/bin/env python3
"""
Enhanced Bill Reference Extraction for Lobbying Activities

Extracts bill references using multiple patterns:
- Explicit bill numbers (H.R. 123, S. 456)
- Public Laws (P.L. 118-50)
- Named Acts ("Give Kids a Chance Act of 2025")
- Generic legislation references (NDAA, Appropriations)

Assigns confidence scores based on specificity.
"""

import argparse
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import io

import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("S3_BUCKET_NAME", "congress-disclosures-standardized")


# ============================================================================
# BILL REFERENCE PATTERNS
# ============================================================================

BILL_PATTERNS = {
    # Explicit bill numbers - highest confidence
    'hr_explicit': {
        'pattern': r'\b(?:H\.?\s*R\.?|HR)\s*\.?\s*(\d+)\b',
        'type': 'hr',
        'confidence': 1.0,
        'extract_number': True
    },
    's_explicit': {
        'pattern': r'\bS\.?\s*(\d+)\b',
        'type': 's',
        'confidence': 1.0,
        'extract_number': True
    },
    'hjres': {
        'pattern': r'\b(?:H\.?\s*J\.?\s*RES|HJRES)\s*\.?\s*(\d+)\b',
        'type': 'hjres',
        'confidence': 1.0,
        'extract_number': True
    },
    'sjres': {
        'pattern': r'\b(?:S\.?\s*J\.?\s*RES|SJRES)\s*\.?\s*(\d+)\b',
        'type': 'sjres',
        'confidence': 1.0,
        'extract_number': True
    },
    'hconres': {
        'pattern': r'\b(?:H\.?\s*CON\.?\s*RES|HCONRES)\s*\.?\s*(\d+)\b',
        'type': 'hconres',
        'confidence': 1.0,
        'extract_number': True
    },
    'sconres': {
        'pattern': r'\b(?:S\.?\s*CON\.?\s*RES|SCONRES)\s*\.?\s*(\d+)\b',
        'type': 'sconres',
        'confidence': 1.0,
        'extract_number': True
    },
    'hres': {
        'pattern': r'\b(?:H\.?\s*RES|HRES)\s*\.?\s*(\d+)\b',
        'type': 'hres',
        'confidence': 1.0,
        'extract_number': True
    },
    'sres': {
        'pattern': r'\b(?:S\.?\s*RES|SRES)\s*\.?\s*(\d+)\b',
        'type': 'sres',
        'confidence': 1.0,
        'extract_number': True
    },
    
    # Public Laws - high confidence
    'public_law': {
        'pattern': r'\bP\.?\s*L\.?\s*(\d+)\s*-\s*(\d+)\b',
        'type': 'public_law',
        'confidence': 0.95,
        'extract_number': False  # Special handling
    },
}

# Named legislation patterns (will extract the act name)
NAMED_ACT_PATTERNS = [
    # Act with year
    (r'\b((?:[A-Z][a-z]+\s+)+Act)\s+of\s+(\d{4})\b', 0.8),
    # Specific common acts
    (r'\b(Infrastructure Investment (?:and|&) Jobs Act)\b', 0.85),
    (r'\b(CHIPS (?:and|&) Science Act)\b', 0.85),
    (r'\b(Inflation Reduction Act)\b', 0.85),
    (r'\b(Tax Cuts and Jobs Act)\b', 0.85),
    (r'\b(American Rescue Plan Act)\b', 0.85),
    (r'\b(CARES Act)\b', 0.85),
]

# Generic legislation references (lower confidence, for tagging only)
GENERIC_LEGISLATION_PATTERNS = [
    (r'\b(National Defense Authorization Act|NDAA)\b', 'ndaa', 0.6),
    (r'\b(Defense Appropriations?\s*(?:bill|Act)?)\b', 'defense_approp', 0.5),
    (r'\b((?:FY\s*\d{2,4}\s+)?(?:Labor|HHS|Energy|Commerce|Agriculture|Transportation|Interior)\s+Appropriations?\s*(?:bill|Act)?)\b', 'approp', 0.5),
    (r'\b(Farm Bill)\b', 'farm_bill', 0.6),
    (r'\b(Highway Bill|Transportation Bill)\b', 'transport_bill', 0.5),
    (r'\b(Tax (?:Reform|Cut|Relief)\s*(?:bill|Act)?)\b', 'tax_bill', 0.5),
]


def extract_bill_references(text: str, activity_id: str, filing_uuid: str, 
                           filing_year: int, issue_code: str) -> List[Dict]:
    """Extract all bill references from text with confidence scores."""
    if not text or pd.isna(text):
        return []
    
    references = []
    text = str(text)
    
    # 1. Extract explicit bill numbers
    for pattern_name, config in BILL_PATTERNS.items():
        matches = re.finditer(config['pattern'], text, re.IGNORECASE)
        for match in matches:
            if config['extract_number']:
                bill_num = match.group(1)
                bill_type = config['type']
                
                # Create bill IDs for both 118th and 119th Congress
                references.append({
                    'activity_id': activity_id,
                    'filing_uuid': filing_uuid,
                    'filing_year': filing_year,
                    'general_issue_code': issue_code,
                    'reference_type': 'explicit_bill',
                    'bill_type': bill_type,
                    'bill_number': int(bill_num),
                    'bill_id_119': f"119-{bill_type}-{bill_num}",
                    'bill_id_118': f"118-{bill_type}-{bill_num}",
                    'raw_reference': match.group(0).strip(),
                    'confidence': config['confidence']
                })
            elif pattern_name == 'public_law':
                congress_num = match.group(1)
                law_num = match.group(2)
                references.append({
                    'activity_id': activity_id,
                    'filing_uuid': filing_uuid,
                    'filing_year': filing_year,
                    'general_issue_code': issue_code,
                    'reference_type': 'public_law',
                    'bill_type': 'public_law',
                    'bill_number': int(law_num),
                    'bill_id_119': f"pl-{congress_num}-{law_num}",
                    'bill_id_118': f"pl-{congress_num}-{law_num}",
                    'raw_reference': match.group(0).strip(),
                    'confidence': config['confidence']
                })
    
    # 2. Extract named acts
    for pattern, confidence in NAMED_ACT_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            act_name = match.group(1) if match.lastindex >= 1 else match.group(0)
            year = match.group(2) if match.lastindex >= 2 else None
            
            references.append({
                'activity_id': activity_id,
                'filing_uuid': filing_uuid,
                'filing_year': filing_year,
                'general_issue_code': issue_code,
                'reference_type': 'named_act',
                'bill_type': 'named_act',
                'bill_number': int(year) if year else 0,
                'bill_id_119': f"act-{act_name[:30].lower().replace(' ', '-')}",
                'bill_id_118': f"act-{act_name[:30].lower().replace(' ', '-')}",
                'raw_reference': match.group(0).strip(),
                'confidence': confidence
            })
    
    # 3. Extract generic legislation references
    for pattern, ref_type, confidence in GENERIC_LEGISLATION_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            references.append({
                'activity_id': activity_id,
                'filing_uuid': filing_uuid,
                'filing_year': filing_year,
                'general_issue_code': issue_code,
                'reference_type': 'generic_legislation',
                'bill_type': ref_type,
                'bill_number': 0,
                'bill_id_119': f"generic-{ref_type}",
                'bill_id_118': f"generic-{ref_type}",
                'raw_reference': match.group(0).strip()[:100],
                'confidence': confidence
            })
    
    # Deduplicate by raw_reference
    seen = set()
    unique_refs = []
    for ref in references:
        key = (ref['activity_id'], ref['raw_reference'].lower())
        if key not in seen:
            seen.add(key)
            unique_refs.append(ref)
    
    return unique_refs


def main():
    parser = argparse.ArgumentParser(description="Enhanced bill extraction from lobbying activities")
    parser.add_argument("--year", type=int, default=2025, help="Filing year")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to S3")
    args = parser.parse_args()
    
    logger.info(f"Enhanced bill extraction for year {args.year}")
    
    s3 = boto3.client('s3')
    
    # Load activities
    logger.info("Loading silver activities...")
    obj = s3.get_object(
        Bucket=S3_BUCKET, 
        Key=f'silver/lobbying/activities/year={args.year}/activities.parquet'
    )
    activities_df = pd.read_parquet(io.BytesIO(obj['Body'].read()))
    logger.info(f"Loaded {len(activities_df)} activities")
    
    # Extract bill references
    logger.info("Extracting bill references...")
    all_refs = []
    
    for i, row in activities_df.iterrows():
        refs = extract_bill_references(
            text=row.get('description', ''),
            activity_id=row['activity_id'],
            filing_uuid=row['filing_uuid'],
            filing_year=row['filing_year'],
            issue_code=row['general_issue_code']
        )
        all_refs.extend(refs)
        
        if (i + 1) % 500 == 0:
            logger.info(f"Processed {i+1}/{len(activities_df)} activities, {len(all_refs)} refs found")
    
    if not all_refs:
        logger.warning("No bill references extracted!")
        return
    
    # Create DataFrame
    refs_df = pd.DataFrame(all_refs)
    
    # Summary statistics
    logger.info(f"\n{'='*60}")
    logger.info("EXTRACTION SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total references: {len(refs_df)}")
    logger.info(f"Unique activities with refs: {refs_df['activity_id'].nunique()}")
    logger.info(f"Coverage: {refs_df['activity_id'].nunique() / len(activities_df) * 100:.1f}% of activities")
    
    logger.info(f"\nBy reference type:")
    for ref_type, count in refs_df['reference_type'].value_counts().items():
        logger.info(f"  {ref_type}: {count}")
    
    logger.info(f"\nBy bill type:")
    for bill_type, count in refs_df['bill_type'].value_counts().head(10).items():
        logger.info(f"  {bill_type}: {count}")
    
    logger.info(f"\nTop raw references:")
    for ref, count in refs_df['raw_reference'].value_counts().head(15).items():
        logger.info(f"  {ref}: {count}")
    
    logger.info(f"\nConfidence distribution:")
    for conf, count in refs_df['confidence'].value_counts().sort_index(ascending=False).items():
        logger.info(f"  {conf}: {count}")
    
    if args.dry_run:
        logger.info("\n[DRY RUN] Not writing to S3")
        return
    
    # Write to S3
    logger.info(f"\nWriting to silver/lobbying/activity_bills/year={args.year}/...")
    buffer = io.BytesIO()
    table = pa.Table.from_pandas(refs_df)
    pq.write_table(table, buffer)
    buffer.seek(0)
    
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=f'silver/lobbying/activity_bills/year={args.year}/activity_bills.parquet',
        Body=buffer.getvalue()
    )
    logger.info("Done!")


if __name__ == "__main__":
    main()
