"""
Lambda to bootstrap gold-layer dimension seeds (idempotent).

Seeds:
- dim_date (2008–2030, partitioned by year)
- dim_filing_types (static lookup)

Design:
- Checks S3 for existing objects and only writes missing partitions/files
- Uses pandas/pyarrow (provided by AWS SDK for pandas Lambda layer)
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List

import boto3
import pandas as pd


S3_BUCKET = os.environ.get("S3_BUCKET_NAME") or os.environ.get("BUCKET")
S3_PREFIX = "gold/house/financial/dimensions"

_s3 = boto3.client("s3")


def _s3_key_exists(bucket: str, key: str) -> bool:
    try:
        _s3.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False


# ------------------ dim_date ------------------
FEDERAL_HOLIDAYS = {
    "New Year's Day": (1, 1),
    "Independence Day": (7, 4),
    "Veterans Day": (11, 11),
    "Christmas Day": (12, 25),
}


def _get_congressional_session(date: datetime):
    year, month, day = date.year, date.month, date.day
    if month == 1 and day < 3:
        session_start_year = year - 2 if year % 2 == 1 else year - 1
    else:
        session_start_year = year if year % 2 == 1 else year - 1
    session = ((session_start_year - 1789) // 2) + 1
    session_year = 1 if year == session_start_year else 2
    return session, session_year


def _get_fiscal_year(date: datetime) -> int:
    return date.year + 1 if date.month >= 10 else date.year


def _get_fiscal_quarter(date: datetime) -> int:
    m = date.month
    if m in [10, 11, 12]:
        return 1
    if m in [1, 2, 3]:
        return 2
    if m in [4, 5, 6]:
        return 3
    return 4


def _is_holiday(date: datetime) -> bool:
    md = (date.month, date.day)
    if md in FEDERAL_HOLIDAYS.values():
        return True
    if date.month == 1 and date.weekday() == 0 and 15 <= date.day <= 21:
        return True
    if date.month == 2 and date.weekday() == 0 and 15 <= date.day <= 21:
        return True
    if date.month == 5 and date.weekday() == 0 and date.day > 24:
        return True
    if date.month == 9 and date.weekday() == 0 and date.day <= 7:
        return True
    if date.month == 11 and date.weekday() == 3 and 22 <= date.day <= 28:
        return True
    return False


def _get_holiday_name(date: datetime):
    if not _is_holiday(date):
        return None
    md = (date.month, date.day)
    for name, pair in FEDERAL_HOLIDAYS.items():
        if md == pair:
            return name
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


def _generate_dim_date_df(start_date: str = "2008-01-01", end_date: str = "2030-12-31") -> pd.DataFrame:
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    rows: List[Dict] = []
    cur = start
    while cur <= end:
        congress, session_year = _get_congressional_session(cur)
        rows.append(
            {
                "date_key": int(cur.strftime("%Y%m%d")),
                "full_date": cur.strftime("%Y-%m-%d"),
                "year": cur.year,
                "quarter": (cur.month - 1) // 3 + 1,
                "month": cur.month,
                "week_of_year": cur.isocalendar()[1],
                "day_of_year": cur.timetuple().tm_yday,
                "day_of_month": cur.day,
                "day_of_week": cur.isoweekday(),
                "day_name": cur.strftime("%A"),
                "month_name": cur.strftime("%B"),
                "is_weekend": cur.weekday() >= 5,
                "is_holiday": _is_holiday(cur),
                "holiday_name": _get_holiday_name(cur),
                "fiscal_year": _get_fiscal_year(cur),
                "fiscal_quarter": _get_fiscal_quarter(cur),
                "congressional_session": congress,
                "congressional_session_year": session_year,
            }
        )
        cur += timedelta(days=1)
    return pd.DataFrame(rows)


def ensure_dim_date(bucket: str, start_year: int = 2008, end_year: int = 2030) -> Dict:
    df = _generate_dim_date_df(f"{start_year}-01-01", f"{end_year}-12-31")
    created: List[int] = []
    for year in sorted(df["year"].unique()):
        key = f"{S3_PREFIX}/dim_date/year={year}/part-0000.parquet"
        if _s3_key_exists(bucket, key):
            continue
        tmp = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
        try:
            df[df["year"] == year].to_parquet(tmp.name, engine="pyarrow", compression="snappy", index=False)
            _s3.upload_file(tmp.name, bucket, key)
            created.append(year)
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass
    return {"created_years": created, "total_years": int(df["year"].nunique())}


# ------------------ dim_filing_types ------------------
FILING_TYPES = [
    {
        "filing_type_key": 1,
        "filing_type_code": "P",
        "filing_type_name": "Periodic Transaction Report",
        "form_type": "PTR",
        "description": "Report of securities transactions by Members and covered staff. Required within 45 days of transaction notification.",
        "frequency": "As-needed",
        "is_transaction_report": True,
        "requires_structured_extraction": True,
        "typical_page_count_low": 2,
        "typical_page_count_high": 15,
    },
    {
        "filing_type_key": 2,
        "filing_type_code": "A",
        "filing_type_name": "Annual Report",
        "form_type": "Form A",
        "description": "Annual Financial Disclosure Statement. Required by May 15 for Members and certain staff.",
        "frequency": "Annual",
        "is_transaction_report": False,
        "requires_structured_extraction": True,
        "typical_page_count_low": 15,
        "typical_page_count_high": 50,
    },
    {
        "filing_type_key": 3,
        "filing_type_code": "C",
        "filing_type_name": "Candidate Report",
        "form_type": "Form B",
        "description": "New Candidate or New Employee Financial Disclosure Statement. Required within 30 days of candidacy or employment.",
        "frequency": "One-time",
        "is_transaction_report": False,
        "requires_structured_extraction": True,
        "typical_page_count_low": 15,
        "typical_page_count_high": 50,
    },
    {
        "filing_type_key": 4,
        "filing_type_code": "T",
        "filing_type_name": "Termination Report",
        "form_type": "Form A",
        "description": "Final Financial Disclosure Statement filed upon termination of office or employment.",
        "frequency": "One-time",
        "is_transaction_report": False,
        "requires_structured_extraction": True,
        "typical_page_count_low": 15,
        "typical_page_count_high": 50,
    },
    {
        "filing_type_key": 5,
        "filing_type_code": "X",
        "filing_type_name": "Extension Request",
        "form_type": "Other",
        "description": "Request for extension of filing deadline. May grant up to 90 additional days.",
        "frequency": "As-needed",
        "is_transaction_report": False,
        "requires_structured_extraction": False,
        "typical_page_count_low": 1,
        "typical_page_count_high": 3,
    },
    {
        "filing_type_key": 6,
        "filing_type_code": "D",
        "filing_type_name": "Duplicate Filing",
        "form_type": "Other",
        "description": "Duplicate or corrected copy of previously filed report.",
        "frequency": "As-needed",
        "is_transaction_report": False,
        "requires_structured_extraction": False,
        "typical_page_count_low": 1,
        "typical_page_count_high": 50,
    },
    {
        "filing_type_key": 7,
        "filing_type_code": "E",
        "filing_type_name": "Electronic Copy",
        "form_type": "Other",
        "description": "Electronic version of paper filing.",
        "frequency": "As-needed",
        "is_transaction_report": False,
        "requires_structured_extraction": False,
        "typical_page_count_low": 1,
        "typical_page_count_high": 50,
    },
    {
        "filing_type_key": 8,
        "filing_type_code": "N",
        "filing_type_name": "New Filer Notification",
        "form_type": "Other",
        "description": "Notification that individual is a new filer.",
        "frequency": "One-time",
        "is_transaction_report": False,
        "requires_structured_extraction": False,
        "typical_page_count_low": 1,
        "typical_page_count_high": 2,
    },
    {
        "filing_type_key": 9,
        "filing_type_code": "B",
        "filing_type_name": "Blind Trust Report",
        "form_type": "Other",
        "description": "Qualified Blind Trust or Qualified Diversified Trust documentation.",
        "frequency": "As-needed",
        "is_transaction_report": False,
        "requires_structured_extraction": False,
        "typical_page_count_low": 5,
        "typical_page_count_high": 20,
    },
    {
        "filing_type_key": 10,
        "filing_type_code": "F",
        "filing_type_name": "Final Amendment",
        "form_type": "Other",
        "description": "Final amendment to previously filed report.",
        "frequency": "As-needed",
        "is_transaction_report": False,
        "requires_structured_extraction": False,
        "typical_page_count_low": 1,
        "typical_page_count_high": 50,
    },
    {
        "filing_type_key": 11,
        "filing_type_code": "G",
        "filing_type_name": "Gift Travel Report",
        "form_type": "Other",
        "description": "Report of travel paid by private source.",
        "frequency": "As-needed",
        "is_transaction_report": False,
        "requires_structured_extraction": False,
        "typical_page_count_low": 2,
        "typical_page_count_high": 5,
    },
    {
        "filing_type_key": 12,
        "filing_type_code": "U",
        "filing_type_name": "Unknown/Other",
        "form_type": "Other",
        "description": "Filing type not classified or unknown.",
        "frequency": "As-needed",
        "is_transaction_report": False,
        "requires_structured_extraction": False,
        "typical_page_count_low": 1,
        "typical_page_count_high": 50,
    },
]


def ensure_dim_filing_types(bucket: str) -> Dict:
    key = f"{S3_PREFIX}/dim_filing_types/part-0000.parquet"
    if _s3_key_exists(bucket, key):
        return {"created": False}
    df = pd.DataFrame(FILING_TYPES)
    tmp = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
    try:
        df.to_parquet(tmp.name, engine="pyarrow", compression="snappy", index=False)
        _s3.upload_file(tmp.name, bucket, key)
        return {"created": True}
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


def lambda_handler(event, context):
    if not S3_BUCKET:
        raise RuntimeError("S3_BUCKET_NAME env var is required")

    start_year = int(os.environ.get("SEED_START_YEAR", "2008"))
    end_year = int(os.environ.get("SEED_END_YEAR", "2030"))

    dim_date_result = ensure_dim_date(S3_BUCKET, start_year, end_year)
    filing_types_result = ensure_dim_filing_types(S3_BUCKET)

    resp = {
        "status": "ok",
        "bucket": S3_BUCKET,
        "dim_date": dim_date_result,
        "dim_filing_types": filing_types_result,
    }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(resp),
    }

