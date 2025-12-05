"""Schema mappers for Congress.gov API JSON to Silver Parquet.

Transforms raw API responses from Bronze layer into normalized
Silver layer records.

Example:
    from ingestion.lib.congress_schema_mappers import map_member_to_silver

    bronze_json = {"member": {"bioguideId": "P000197", ...}}
    silver_record = map_member_to_silver(bronze_json)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def map_member_to_silver(bronze_json: Dict[str, Any]) -> Dict[str, Any]:
    """Map Congress.gov member API response to Silver schema.

    Args:
        bronze_json: Raw API response with 'member' key

    Returns:
        Flattened record matching dim_member Silver schema

    Example:
        >>> json_data = {"member": {"bioguideId": "P000197", "firstName": "Nancy", ...}}
        >>> record = map_member_to_silver(json_data)
        >>> record["bioguide_id"]
        'P000197'
    """
    member = bronze_json.get("member", {})

    if not member:
        logger.warning("Missing 'member' key in Bronze JSON")
        return {}

    # Extract base fields
    record = {
        "bioguide_id": member.get("bioguideId"),
        "first_name": member.get("firstName"),
        "last_name": member.get("lastName"),
        "party": _normalize_party(member.get("partyName") or member.get("party")),
        "state": member.get("state"),
        "district": _safe_int(member.get("district")),
    }

    # Extract chamber from current term
    terms = member.get("terms", {})
    if isinstance(terms, dict):
        terms = terms.get("item", [])
    if isinstance(terms, list) and terms:
        latest_term = terms[-1] if terms else {}
        chamber_raw = latest_term.get("chamber", "")
        record["chamber"] = _normalize_chamber(chamber_raw)
        # Get term years
        record["term_start_year"] = _safe_int(latest_term.get("startYear"))
        record["term_end_year"] = _safe_int(latest_term.get("endYear"))
    else:
        record["chamber"] = "unknown"
        record["term_start_year"] = None
        record["term_end_year"] = None

    # Extract portrait URL
    depiction = member.get("depiction", {})
    record["depiction_url"] = depiction.get("imageUrl") if depiction else None

    # Source timestamp
    update_date = member.get("updateDate")
    if update_date:
        record["source_last_modified"] = update_date
    else:
        record["source_last_modified"] = datetime.now(timezone.utc).isoformat()

    return record


def map_bill_to_silver(bronze_json: Dict[str, Any]) -> Dict[str, Any]:
    """Map Congress.gov bill API response to Silver schema.

    Args:
        bronze_json: Raw API response with 'bill' key

    Returns:
        Flattened record matching dim_bill Silver schema
    """
    bill = bronze_json.get("bill", {})

    if not bill:
        logger.warning("Missing 'bill' key in Bronze JSON")
        return {}

    congress = _safe_int(bill.get("congress"))
    bill_type = str(bill.get("type", "")).lower()
    bill_number = _safe_int(bill.get("number"))

    # Generate composite key
    bill_id = f"{congress}-{bill_type}-{bill_number}" if all([congress, bill_type, bill_number]) else None

    record = {
        "bill_id": bill_id,
        "congress": congress,
        "bill_type": bill_type,
        "bill_number": bill_number,
        "title": bill.get("title"),
        "title_short": bill.get("shortTitle"),
        "introduced_date": _parse_date(bill.get("introducedDate")),
        "origin_chamber": bill.get("originChamber"),
    }

    # Extract sponsor
    sponsors = bill.get("sponsors", [])
    if sponsors and isinstance(sponsors, list):
        primary = sponsors[0]
        record["sponsor_bioguide_id"] = primary.get("bioguideId")
        record["sponsor_name"] = primary.get("fullName")
    else:
        record["sponsor_bioguide_id"] = None
        record["sponsor_name"] = None

    # Policy area
    policy = bill.get("policyArea", {})
    record["policy_area"] = policy.get("name") if policy else None

    # Latest action
    latest = bill.get("latestAction", {})
    if latest:
        record["latest_action_date"] = _parse_date(latest.get("actionDate"))
        record["latest_action_text"] = latest.get("text")
    else:
        record["latest_action_date"] = None
        record["latest_action_text"] = None

    # Cosponsor count
    record["cosponsors_count"] = _safe_int(bill.get("cosponsors", {}).get("count"))

    # Source timestamp
    record["source_last_modified"] = bill.get("updateDate") or datetime.now(timezone.utc).isoformat()

    return record


def map_bill_actions_to_silver(bronze_json: Dict[str, Any], bill_id: str) -> List[Dict[str, Any]]:
    """Map bill actions API response to Silver schema.

    Args:
        bronze_json: Raw API response with 'actions' key
        bill_id: Parent bill composite key

    Returns:
        List of action records for bill_actions table
    """
    actions = bronze_json.get("actions", [])
    records = []

    for i, action in enumerate(actions):
        record = {
            "bill_id": bill_id,
            "action_date": _parse_date(action.get("actionDate")),
            "action_seq": i + 1,  # Sequence within day
            "action_text": action.get("text"),
            "action_type": action.get("type"),
            "action_code": action.get("actionCode"),
        }

        # Source system
        source = action.get("sourceSystem", {})
        record["source_system"] = source.get("name") if source else None

        record["silver_ingest_ts"] = datetime.now(timezone.utc).isoformat()
        records.append(record)

    return records


def map_bill_cosponsors_to_silver(bronze_json: Dict[str, Any], bill_id: str) -> List[Dict[str, Any]]:
    """Map bill cosponsors API response to Silver schema.

    Args:
        bronze_json: Raw API response with 'cosponsors' key
        bill_id: Parent bill composite key

    Returns:
        List of cosponsor records
    """
    cosponsors = bronze_json.get("cosponsors", [])
    records = []

    for cs in cosponsors:
        record = {
            "bill_id": bill_id,
            "cosponsor_bioguide_id": cs.get("bioguideId"),
            "cosponsor_name": cs.get("fullName"),
            "sponsorship_date": _parse_date(cs.get("sponsorshipDate")),
            "is_original_cosponsor": cs.get("isOriginalCosponsor", False),
            "party": _normalize_party(cs.get("party")),
            "state": cs.get("state"),
            "silver_ingest_ts": datetime.now(timezone.utc).isoformat(),
        }
        records.append(record)

    return records


def map_vote_to_silver(bronze_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Map House/Senate vote API response to Silver schema.

    Returns one record per member vote.

    Args:
        bronze_json: Raw API response with 'vote' key

    Returns:
        List of vote records for house_vote_members table
    """
    vote = bronze_json.get("vote", {})

    if not vote:
        logger.warning("Missing 'vote' key in Bronze JSON")
        return []

    congress = _safe_int(vote.get("congress"))
    session = _safe_int(vote.get("session"))
    roll_call = _safe_int(vote.get("rollCall"))
    chamber = _normalize_chamber(vote.get("chamber", ""))

    # Generate composite key
    vote_id = f"{congress}-{session}-{roll_call}"

    # Vote metadata
    vote_date = _parse_date(vote.get("date"))
    question = vote.get("question")
    result = vote.get("result")

    # Related bill (if any)
    related_bill = vote.get("bill", {})
    if related_bill:
        b_congress = related_bill.get("congress")
        b_type = str(related_bill.get("type", "")).lower()
        b_number = related_bill.get("number")
        bill_id = f"{b_congress}-{b_type}-{b_number}" if all([b_congress, b_type, b_number]) else None
    else:
        bill_id = None

    records = []
    members = vote.get("members", [])

    for m in members:
        record = {
            "vote_id": vote_id,
            "bioguide_id": m.get("bioguideId"),
            "member_name": m.get("name"),
            "party": _normalize_party(m.get("party")),
            "state": m.get("state"),
            "vote_cast": m.get("vote"),
            "vote_date": vote_date,
            "question": question,
            "result": result,
            "bill_id": bill_id,
            "chamber": chamber,
            "congress": congress,
            "session": session,
            "silver_ingest_ts": datetime.now(timezone.utc).isoformat(),
        }
        records.append(record)

    return records


def map_committee_to_silver(bronze_json: Dict[str, Any]) -> Dict[str, Any]:
    """Map Congress.gov committee API response to Silver schema.

    Args:
        bronze_json: Raw API response with 'committee' key

    Returns:
        Flattened record matching dim_committee Silver schema
    """
    committee = bronze_json.get("committee", {})

    if not committee:
        logger.warning("Missing 'committee' key in Bronze JSON")
        return {}

    record = {
        "committee_code": committee.get("systemCode"),
        "name": committee.get("name"),
        "chamber": _normalize_chamber(committee.get("chamber", "")),
        "committee_type": committee.get("committeeTypeCode"),
        "parent_committee_code": committee.get("parent", {}).get("systemCode"),
        "url": committee.get("url"),
        "source_last_modified": committee.get("updateDate") or datetime.now(timezone.utc).isoformat(),
    }

    return record


# =============================================================================
# Helper Functions
# =============================================================================


def _normalize_party(party: Optional[str]) -> Optional[str]:
    """Normalize party name to code (D, R, I)."""
    if not party:
        return None

    party = str(party).strip().upper()

    if party in ("D", "DEMOCRATIC", "DEMOCRAT"):
        return "D"
    elif party in ("R", "REPUBLICAN"):
        return "R"
    elif party in ("I", "INDEPENDENT"):
        return "I"
    else:
        return party[0] if party else None


def _normalize_chamber(chamber: str) -> str:
    """Normalize chamber name to lowercase."""
    if not chamber:
        return "unknown"

    chamber = str(chamber).strip().lower()

    if "house" in chamber:
        return "house"
    elif "senate" in chamber:
        return "senate"
    elif "joint" in chamber:
        return "joint"
    else:
        return chamber


def _safe_int(value: Any) -> Optional[int]:
    """Safely convert value to int."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_date(date_str: Optional[str]) -> Optional[str]:
    """Parse date string to YYYY-MM-DD format."""
    if not date_str:
        return None

    # Already in correct format
    if len(date_str) == 10 and date_str[4] == "-":
        return date_str

    # Try parsing various formats
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%SZ"]:
        try:
            dt = datetime.strptime(date_str[:19], fmt.replace("Z", ""))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return date_str[:10] if len(date_str) >= 10 else date_str


# =============================================================================
# Entity Routing
# =============================================================================

def get_schema_mapper(entity_type: str):
    """Get schema mapper function for entity type.

    Args:
        entity_type: Entity type (member, bill, committee, house_vote, senate_vote)

    Returns:
        Mapper function

    Raises:
        ValueError: If entity type not supported
    """
    mappers = {
        "member": map_member_to_silver,
        "bill": map_bill_to_silver,
        "committee": map_committee_to_silver,
    }

    if entity_type not in mappers:
        raise ValueError(f"Unsupported entity type: {entity_type}")

    return mappers[entity_type]


def get_silver_table_path(entity_type: str, **partition_values) -> str:
    """Get Silver S3 path for entity type.

    Args:
        entity_type: Entity type
        **partition_values: Partition key values (chamber, congress, etc.)

    Returns:
        S3 key pattern for Silver table
    """
    base = f"silver/congress"

    if entity_type == "member":
        chamber = partition_values.get("chamber", "unknown")
        is_current = partition_values.get("is_current", "true")
        return f"{base}/dim_member/chamber={chamber}/is_current={is_current}/part-0000.parquet"

    elif entity_type == "bill":
        congress = partition_values.get("congress", 0)
        bill_type = partition_values.get("bill_type", "unknown")
        return f"{base}/dim_bill/congress={congress}/bill_type={bill_type}/part-0000.parquet"

    elif entity_type == "committee":
        chamber = partition_values.get("chamber", "unknown")
        return f"{base}/dim_committee/chamber={chamber}/part-0000.parquet"

    elif entity_type in ("house_vote", "senate_vote"):
        congress = partition_values.get("congress", 0)
        session = partition_values.get("session", 1)
        return f"{base}/house_vote_members/congress={congress}/session={session}/part-0000.parquet"

    else:
        return f"{base}/{entity_type}/part-0000.parquet"
