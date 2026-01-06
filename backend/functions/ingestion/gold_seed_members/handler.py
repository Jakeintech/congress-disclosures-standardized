"""
Lambda to seed dim_members dimension using Congress.gov API (via SSM-stored key).

Writes Parquet to:
  gold/house/financial/dimensions/dim_members/year=YYYY/part-0000.parquet

Idempotent: if the Parquet file for the target year exists, it skips writing.
"""

import hashlib
import json
import os
import tempfile
from datetime import datetime
from typing import Dict, List, Optional

import boto3
import pandas as pd
import requests


S3_BUCKET = os.environ.get("S3_BUCKET_NAME") or os.environ.get("BUCKET")
S3_PREFIX = "gold/house/financial/dimensions"
SSM_PARAM = os.environ.get("SSM_CONGRESS_API_KEY_PARAM", "/congress-disclosures/development/congress-api-key")
TARGET_YEAR = int(os.environ.get("DIM_MEMBERS_TARGET_YEAR", str(datetime.utcnow().year)))

s3 = boto3.client("s3")
ssm = boto3.client("ssm")


def _s3_key_exists(bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False


def _get_api_key() -> str:
    resp = ssm.get_parameter(Name=SSM_PARAM, WithDecryption=True)
    return resp["Parameter"]["Value"]


def _surrogate_from_bioguide(bioguide_id: Optional[str]) -> int:
    if not bioguide_id:
        return 0
    h = hashlib.sha1(bioguide_id.encode("utf-8")).digest()
    return int.from_bytes(h[:4], "big")


def _fetch_all_members(api_key: str) -> List[Dict]:
    base = "https://api.congress.gov/v3/member"
    params = {"api_key": api_key, "format": "json", "limit": 250, "offset": 0}
    members: List[Dict] = []

    while True:
        r = requests.get(base, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        batch = data.get("members") or data.get("member") or []
        # Normalize list
        if isinstance(batch, dict):
            batch = batch.get("item", [])
        members.extend(batch)

        # Pagination handling
        meta = data.get("pagination") or data.get("page") or {}
        total = meta.get("count") or meta.get("total")
        limit = meta.get("limit") or params["limit"]
        offset = meta.get("offset") or params.get("offset", 0)

        if total is None:
            # Fallback: stop when returned less than limit
            if len(batch) < params["limit"]:
                break
            params["offset"] = params.get("offset", 0) + params["limit"]
            continue

        next_offset = offset + limit
        if next_offset >= total:
            break
        params["offset"] = next_offset

    return members


def _extract_latest_term(terms_obj: Dict) -> Dict:
    items = []
    if not terms_obj:
        return {}
    if isinstance(terms_obj, dict):
        items = terms_obj.get("item") or []
    elif isinstance(terms_obj, list):
        items = terms_obj
    if not items:
        return {}
    # Terms may not be sorted. Sort by endYear if present; else startYear
    def keyfn(t: Dict):
        ey = t.get("endYear") or t.get("startYear") or 0
        try:
            return int(ey)
        except Exception:
            return 0

    items_sorted = sorted(items, key=keyfn)
    return items_sorted[-1]


def build_dim_members_df(members_raw: List[Dict]) -> pd.DataFrame:
    rows: List[Dict] = []
    for m in members_raw:
        # API fields are inconsistent; use .get defensively
        bioguide = m.get("bioguideId") or m.get("bioguideID") or m.get("bioguide")
        name = (m.get("name") or "").strip()

        # Parse name - API returns "Last, First" format
        first_name = None
        last_name = None
        if name and "," in name:
            parts = name.split(",", 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip() if len(parts) > 1 else None
        else:
            # Fallback for names without comma
            first_name = m.get("firstName", "").strip() or None
            last_name = m.get("lastName", "").strip() or None
            if not first_name and not last_name and name:
                # Last fallback - use full name as last name
                last_name = name

        full_name = name or (first_name + (" " if last_name else "") + last_name).strip() if (first_name or last_name) else None
        # Convert party name to code
        party_name = m.get("partyName") or m.get("party")
        party = None
        if party_name:
            if party_name.lower().startswith("democrat"):
                party = "D"
            elif party_name.lower().startswith("republican"):
                party = "R"
            elif party_name.lower().startswith("independent"):
                party = "I"
            else:
                party = party_name[:1].upper()  # Use first letter as fallback

        # State - convert from full name to abbreviation
        state_full = m.get("state")
        state = state_full  # Will standardize later if needed
        district = None
        try:
            district_raw = m.get("district")
            if district_raw is not None and str(district_raw).isdigit():
                district = int(district_raw)
        except Exception:
            district = None
        chamber = m.get("chamber") or m.get("currentRole", {}).get("chamber")
        member_type = m.get("memberType") or "Member"
        terms = m.get("terms") or {}
        latest = _extract_latest_term(terms)
        party_latest = latest.get("party") or party
        start_year = latest.get("startYear")
        end_year = latest.get("endYear")

        def _to_date(y: Optional[str]) -> Optional[str]:
            if not y:
                return None
            try:
                return f"{int(y)}-01-03"
            except Exception:
                return None

        start_date = _to_date(start_year)
        end_date = _to_date(end_year)
        is_current = end_year is None

        # State district - store with abbreviated code (e.g., NJ11)
        state_district = None
        if state and district is not None:
            # State mapping - full name to abbreviation
            STATE_ABBR = {
                "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
                "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
                "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
                "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
                "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
                "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
                "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
                "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
                "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
                "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
                "District of Columbia": "DC", "Puerto Rico": "PR", "Guam": "GU", "Virgin Islands": "VI",
                "American Samoa": "AS", "Northern Mariana Islands": "MP"
            }
            state_abbr = STATE_ABBR.get(state, state if len(state) == 2 else state[:2].upper())
            state = state_abbr
            state_district = f"{state_abbr}{str(district).zfill(2)}"

        # Effective from: choose start_year of latest term; fallback to current year
        effective_from_year = None
        try:
            effective_from_year = int(start_year) if start_year else TARGET_YEAR
        except Exception:
            effective_from_year = TARGET_YEAR

        row = {
            "member_key": _surrogate_from_bioguide(bioguide),
            "bioguide_id": bioguide,
            "first_name": first_name or None,
            "last_name": last_name or None,
            "full_name": full_name or None,
            "party": party_latest or party,
            "state": state,
            "district": district,
            "state_district": state_district,
            "chamber": chamber,
            "member_type": member_type,
            "start_date": start_date,
            "end_date": end_date,
            "is_current": bool(is_current),
            "effective_from": f"{effective_from_year}-01-03",
            "effective_to": None if is_current else end_date,
            "version": 1,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        rows.append(row)

    return pd.DataFrame(rows)


def ensure_dim_members(bucket: str, target_year: int) -> Dict:
    s3_key = f"{S3_PREFIX}/dim_members/year={target_year}/part-0000.parquet"
    if _s3_key_exists(bucket, s3_key):
        return {"created": False, "s3_key": s3_key}

    api_key = _get_api_key()
    members_raw = _fetch_all_members(api_key)
    df = build_dim_members_df(members_raw)

    tmp = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
    try:
        df.to_parquet(tmp.name, engine="pyarrow", compression="snappy", index=False)
        s3.upload_file(tmp.name, bucket, s3_key)
        return {"created": True, "count": len(df), "s3_key": s3_key}
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


def lambda_handler(event, context):
    if not S3_BUCKET:
        return {"statusCode": 500, "body": json.dumps({"error": "S3_BUCKET_NAME required"})}

    try:
        result = ensure_dim_members(S3_BUCKET, TARGET_YEAR)
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"status": "ok", "result": result}),
        }
    except Exception as e:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"status": "error", "message": str(e)}),
        }

