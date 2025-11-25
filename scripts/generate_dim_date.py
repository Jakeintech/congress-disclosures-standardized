#!/usr/bin/env python3
"""
Generate dim_date dimension table (2008-2030).

This creates a standard date dimension with calendar attributes, fiscal year,
and congressional session metadata.
"""

import pandas as pd
from datetime import datetime, timedelta
import boto3
import os
from pathlib import Path

# Federal holidays (simplified - major holidays only)
FEDERAL_HOLIDAYS = {
    "New Year's Day": (1, 1),
    "Independence Day": (7, 4),
    "Veterans Day": (11, 11),
    "Christmas Day": (12, 25),
}

def get_congressional_session(date):
    """Calculate congressional session number and year."""
    # 118th Congress: Jan 3, 2023 - Jan 3, 2025
    # 119th Congress: Jan 3, 2025 - Jan 3, 2027
    # Each congress is 2 years starting in odd years

    year = date.year
    month = date.month
    day = date.day

    # Congress starts Jan 3 of odd years
    if month == 1 and day < 3:
        # Before Jan 3, use previous congress
        session_start_year = year - 2 if year % 2 == 1 else year - 1
    else:
        session_start_year = year if year % 2 == 1 else year - 1

    # Session number: 1st congress was 1789-1791, so calculate from there
    session = ((session_start_year - 1789) // 2) + 1

    # Session year (1 or 2)
    session_year = 1 if year == session_start_year else 2

    return session, session_year

def get_fiscal_year(date):
    """Calculate US government fiscal year (Oct 1 - Sep 30)."""
    if date.month >= 10:
        return date.year + 1
    return date.year

def get_fiscal_quarter(date):
    """Calculate fiscal quarter (Q1=Oct-Dec, Q2=Jan-Mar, Q3=Apr-Jun, Q4=Jul-Sep)."""
    month = date.month
    if month in [10, 11, 12]:
        return 1
    elif month in [1, 2, 3]:
        return 2
    elif month in [4, 5, 6]:
        return 3
    else:  # 7, 8, 9
        return 4

def is_holiday(date):
    """Check if date is a federal holiday."""
    month_day = (date.month, date.day)

    # Check fixed holidays
    if month_day in FEDERAL_HOLIDAYS.values():
        return True

    # Martin Luther King Jr Day: 3rd Monday in January
    if date.month == 1 and date.weekday() == 0:
        if 15 <= date.day <= 21:
            return True

    # Presidents Day: 3rd Monday in February
    if date.month == 2 and date.weekday() == 0:
        if 15 <= date.day <= 21:
            return True

    # Memorial Day: Last Monday in May
    if date.month == 5 and date.weekday() == 0:
        if date.day > 24:
            return True

    # Labor Day: 1st Monday in September
    if date.month == 9 and date.weekday() == 0:
        if date.day <= 7:
            return True

    # Thanksgiving: 4th Thursday in November
    if date.month == 11 and date.weekday() == 3:
        if 22 <= date.day <= 28:
            return True

    return False

def get_holiday_name(date):
    """Get name of holiday if date is a holiday."""
    if not is_holiday(date):
        return None

    month_day = (date.month, date.day)

    # Check fixed holidays
    for name, md in FEDERAL_HOLIDAYS.items():
        if month_day == md:
            return name

    # Variable holidays
    if date.month == 1 and date.weekday() == 0 and 15 <= date.day <= 21:
        return "Martin Luther King Jr Day"
    if date.month == 2 and date.weekday() == 0 and 15 <= date.day <= 21:
        return "Presidents Day"
    if date.month == 5 and date.weekday() == 0 and date.day > 24:
        return "Memorial Day"
    if date.month == 9 and date.weekday() == 0 and date.day <= 7:
        return "Labor Day"
    if date.month == 11 and date.weekday() == 3 and 22 <= date.day <= 28:
        return "Thanksgiving Day"

    return None

def generate_dim_date(start_date='2008-01-01', end_date='2030-12-31'):
    """Generate date dimension table."""

    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    dates = []
    current = start

    while current <= end:
        congressional_session, session_year = get_congressional_session(current)

        date_record = {
            'date_key': int(current.strftime('%Y%m%d')),
            'full_date': current.strftime('%Y-%m-%d'),
            'year': current.year,
            'quarter': (current.month - 1) // 3 + 1,
            'month': current.month,
            'week_of_year': current.isocalendar()[1],
            'day_of_year': current.timetuple().tm_yday,
            'day_of_month': current.day,
            'day_of_week': current.isoweekday(),  # 1=Monday, 7=Sunday
            'day_name': current.strftime('%A'),
            'month_name': current.strftime('%B'),
            'is_weekend': current.weekday() >= 5,
            'is_holiday': is_holiday(current),
            'holiday_name': get_holiday_name(current),
            'fiscal_year': get_fiscal_year(current),
            'fiscal_quarter': get_fiscal_quarter(current),
            'congressional_session': congressional_session,
            'congressional_session_year': session_year
        }

        dates.append(date_record)
        current += timedelta(days=1)

    return pd.DataFrame(dates)

def main():
    print("Generating dim_date dimension table (2008-2030)...")

    # Generate date dimension
    df = generate_dim_date()

    print(f"Generated {len(df):,} date records")
    print(f"Date range: {df['full_date'].min()} to {df['full_date'].max()}")
    print(f"Years: {df['year'].min()} to {df['year'].max()}")
    print(f"Congressional sessions: {df['congressional_session'].min()} to {df['congressional_session'].max()}")
    print(f"Holidays: {df['is_holiday'].sum():,}")

    # Save locally
    output_dir = Path('data/gold/dimensions/dim_date')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Partition by year and save as Parquet
    for year in df['year'].unique():
        year_df = df[df['year'] == year]
        year_output_dir = output_dir / f'year={year}'
        year_output_dir.mkdir(parents=True, exist_ok=True)

        output_file = year_output_dir / 'part-0000.parquet'
        year_df.to_parquet(
            output_file,
            engine='pyarrow',
            compression='snappy',
            index=False
        )
        print(f"  Wrote {year}: {len(year_df)} records -> {output_file}")

    # Also save consolidated CSV for reference
    csv_file = output_dir / 'dim_date_full.csv'
    df.to_csv(csv_file, index=False)
    print(f"\nConsolidated CSV: {csv_file}")

    # Upload to S3 if bucket is configured
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')

    try:
        s3 = boto3.client('s3')

        for year in df['year'].unique():
            year_df = df[df['year'] == year]

            # Write to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
                year_df.to_parquet(tmp.name, engine='pyarrow', compression='snappy', index=False)

                s3_key = f'gold/house/financial/dimensions/dim_date/year={year}/part-0000.parquet'
                s3.upload_file(tmp.name, bucket_name, s3_key)
                print(f"  Uploaded to s3://{bucket_name}/{s3_key}")

                os.unlink(tmp.name)

        print(f"\n✅ Successfully uploaded dim_date to S3: s3://{bucket_name}/gold/house/financial/dimensions/dim_date/")

    except Exception as e:
        print(f"\n⚠️  Could not upload to S3: {e}")
        print("Run with AWS credentials configured to upload to S3")

    print("\n✅ dim_date generation complete!")

if __name__ == '__main__':
    main()
