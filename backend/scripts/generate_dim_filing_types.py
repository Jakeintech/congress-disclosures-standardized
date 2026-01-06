#!/usr/bin/env python3
"""
Generate dim_filing_types dimension table (static seed data).
"""

import pandas as pd
import boto3
import os
from pathlib import Path

# Filing type master data from House Clerk documentation
FILING_TYPES = [
    {
        'filing_type_key': 1,
        'filing_type_code': 'P',
        'filing_type_name': 'Periodic Transaction Report',
        'form_type': 'PTR',
        'description': 'Report of securities transactions by Members and covered staff. Required within 45 days of transaction notification.',
        'frequency': 'As-needed',
        'is_transaction_report': True,
        'requires_structured_extraction': True,
        'typical_page_count_low': 2,
        'typical_page_count_high': 15
    },
    {
        'filing_type_key': 2,
        'filing_type_code': 'A',
        'filing_type_name': 'Annual Report',
        'form_type': 'Form A',
        'description': 'Annual Financial Disclosure Statement. Required by May 15 for Members and certain staff.',
        'frequency': 'Annual',
        'is_transaction_report': False,
        'requires_structured_extraction': True,
        'typical_page_count_low': 15,
        'typical_page_count_high': 50
    },
    {
        'filing_type_key': 3,
        'filing_type_code': 'C',
        'filing_type_name': 'Candidate Report',
        'form_type': 'Form B',
        'description': 'New Candidate or New Employee Financial Disclosure Statement. Required within 30 days of candidacy or employment.',
        'frequency': 'One-time',
        'is_transaction_report': False,
        'requires_structured_extraction': True,
        'typical_page_count_low': 15,
        'typical_page_count_high': 50
    },
    {
        'filing_type_key': 4,
        'filing_type_code': 'T',
        'filing_type_name': 'Termination Report',
        'form_type': 'Form A',
        'description': 'Final Financial Disclosure Statement filed upon termination of office or employment.',
        'frequency': 'One-time',
        'is_transaction_report': False,
        'requires_structured_extraction': True,
        'typical_page_count_low': 15,
        'typical_page_count_high': 50
    },
    {
        'filing_type_key': 5,
        'filing_type_code': 'X',
        'filing_type_name': 'Extension Request',
        'form_type': 'Other',
        'description': 'Request for extension of filing deadline. May grant up to 90 additional days.',
        'frequency': 'As-needed',
        'is_transaction_report': False,
        'requires_structured_extraction': False,
        'typical_page_count_low': 1,
        'typical_page_count_high': 3
    },
    {
        'filing_type_key': 6,
        'filing_type_code': 'D',
        'filing_type_name': 'Duplicate Filing',
        'form_type': 'Other',
        'description': 'Duplicate or corrected copy of previously filed report.',
        'frequency': 'As-needed',
        'is_transaction_report': False,
        'requires_structured_extraction': False,
        'typical_page_count_low': 1,
        'typical_page_count_high': 50
    },
    {
        'filing_type_key': 7,
        'filing_type_code': 'E',
        'filing_type_name': 'Electronic Copy',
        'form_type': 'Other',
        'description': 'Electronic version of paper filing.',
        'frequency': 'As-needed',
        'is_transaction_report': False,
        'requires_structured_extraction': False,
        'typical_page_count_low': 1,
        'typical_page_count_high': 50
    },
    {
        'filing_type_key': 8,
        'filing_type_code': 'N',
        'filing_type_name': 'New Filer Notification',
        'form_type': 'Other',
        'description': 'Notification that individual is a new filer.',
        'frequency': 'One-time',
        'is_transaction_report': False,
        'requires_structured_extraction': False,
        'typical_page_count_low': 1,
        'typical_page_count_high': 2
    },
    {
        'filing_type_key': 9,
        'filing_type_code': 'B',
        'filing_type_name': 'Blind Trust Report',
        'form_type': 'Other',
        'description': 'Qualified Blind Trust or Qualified Diversified Trust documentation.',
        'frequency': 'As-needed',
        'is_transaction_report': False,
        'requires_structured_extraction': False,
        'typical_page_count_low': 5,
        'typical_page_count_high': 20
    },
    {
        'filing_type_key': 10,
        'filing_type_code': 'F',
        'filing_type_name': 'Final Amendment',
        'form_type': 'Other',
        'description': 'Final amendment to previously filed report.',
        'frequency': 'As-needed',
        'is_transaction_report': False,
        'requires_structured_extraction': False,
        'typical_page_count_low': 1,
        'typical_page_count_high': 50
    },
    {
        'filing_type_key': 11,
        'filing_type_code': 'G',
        'filing_type_name': 'Gift Travel Report',
        'form_type': 'Other',
        'description': 'Report of travel paid by private source.',
        'frequency': 'As-needed',
        'is_transaction_report': False,
        'requires_structured_extraction': False,
        'typical_page_count_low': 2,
        'typical_page_count_high': 5
    },
    {
        'filing_type_key': 12,
        'filing_type_code': 'U',
        'filing_type_name': 'Unknown/Other',
        'form_type': 'Other',
        'description': 'Filing type not classified or unknown.',
        'frequency': 'As-needed',
        'is_transaction_report': False,
        'requires_structured_extraction': False,
        'typical_page_count_low': 1,
        'typical_page_count_high': 50
    }
]

def main():
    print("Generating dim_filing_types dimension table...")

    df = pd.DataFrame(FILING_TYPES)

    print(f"Generated {len(df)} filing type records")
    print("\nFiling types:")
    for _, row in df.iterrows():
        print(f"  {row['filing_type_code']}: {row['filing_type_name']}")

    # Save locally
    output_dir = Path('data/gold/dimensions/dim_filing_types')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save as Parquet (no partitioning - static table)
    output_file = output_dir / 'part-0000.parquet'
    df.to_parquet(
        output_file,
        engine='pyarrow',
        compression='snappy',
        index=False
    )
    print(f"\nWrote to: {output_file}")

    # Also save CSV for reference
    csv_file = output_dir / 'dim_filing_types.csv'
    df.to_csv(csv_file, index=False)
    print(f"CSV: {csv_file}")

    # Upload to S3 if bucket is configured
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

    try:
        s3 = boto3.client('s3')

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            df.to_parquet(tmp.name, engine='pyarrow', compression='snappy', index=False)

            s3_key = 'gold/house/financial/dimensions/dim_filing_types/part-0000.parquet'
            s3.upload_file(tmp.name, bucket_name, s3_key)
            print(f"\n✅ Uploaded to s3://{bucket_name}/{s3_key}")

            os.unlink(tmp.name)

    except Exception as e:
        print(f"\n⚠️  Could not upload to S3: {e}")

    print("\n✅ dim_filing_types generation complete!")

if __name__ == '__main__':
    main()
