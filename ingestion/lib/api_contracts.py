"""
API Contracts for Congress Data Pipeline.

Defines typed schemas for API requests/responses and data validation
to prevent silent failures.
"""

from typing import Optional, Dict, Any, List, TypedDict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CongressMember(TypedDict, total=False):
    """Schema for a single member in the API response."""
    bioguideId: str
    name: str
    partyName: Optional[str]  # "Democratic", "Republican"
    state: Optional[str]
    district: Optional[int]
    terms: Optional[Dict[str, List[Dict[str, Any]]]]
    url: Optional[str]
    depiction: Optional[Dict[str, str]]


class MemberListResponse(TypedDict):
    """Schema for /member list endpoint response."""
    members: List[CongressMember]
    pagination: Optional[Dict[str, Any]]
    request: Optional[Dict[str, Any]]


class CongressMemberResponse(TypedDict):
    """Schema for /member/{bioguideId} details response."""
    member: CongressMember
    request: Optional[Dict[str, Any]]


class EnrichedMemberData(TypedDict, total=False):
    """Schema for enriched member data."""
    bioguide_id: Optional[str]
    party: Optional[str]
    chamber: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    is_current: bool
    enrichment_status: str


class DimMemberRecord(TypedDict):
    """Schema for dim_members table record."""
    member_key: int
    bioguide_id: Optional[str]
    first_name: str
    last_name: str
    full_name: str
    party: Optional[str]
    state: str
    district: Optional[int]
    state_district: str
    chamber: Optional[str]
    member_type: str
    start_date: Optional[str]
    end_date: Optional[str]
    is_current: bool
    effective_from: str
    effective_to: Optional[str]
    version: int


class NetworkGraphNode(TypedDict, total=False):
    """Schema for network graph node."""
    id: str
    group: str  # 'member' or 'asset'
    party: Optional[str]
    state: Optional[str]
    chamber: Optional[str]
    bioguide_id: Optional[str]
    value: float
    transaction_count: int
    degree: int
    radius: float


class NetworkGraphLink(TypedDict):
    """Schema for network graph link."""
    source: str
    target: str
    value: float
    count: int
    type: str


class NetworkGraphData(TypedDict):
    """Schema for complete network graph JSON."""
    metadata: Dict[str, Any]
    nodes: List[NetworkGraphNode]
    links: List[NetworkGraphLink]
    summary_stats: Optional[Dict[str, Any]]


def validate_enriched_member(data: Dict[str, Any]) -> EnrichedMemberData:
    """
    Validate enriched member data structure.
    
    Raises:
        ValueError: If required fields are missing or invalid
    """
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict, got {type(data)}")
    
    # Check enrichment status
    status = data.get('enrichment_status')
    if status not in ['success', 'not_found', 'error', 'fallback']:
        logger.warning(f"Invalid enrichment_status: {status}")
    
    # If enrichment succeeded, party should be present
    if status == 'success' and not data.get('party'):
        logger.warning("Enrichment marked as success but party is missing")
    
    return data  # type: ignore


def validate_member_list_response(data: Dict[str, Any]) -> MemberListResponse:
    """
    Validate /member list API response.
    
    Raises:
        ValueError: If response structure is invalid
    """
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict response, got {type(data)}")
        
    if 'members' not in data:
        # Some APIs return empty list or different structure on no results
        # But Congress API spec says 'members' array
        logger.warning("API response missing 'members' key")
        return {'members': [], 'pagination': {}, 'request': {}}  # type: ignore
        
    if not isinstance(data['members'], list):
        raise ValueError("'members' must be a list")
        
    return data  # type: ignore


def validate_dim_member_record(record: Dict[str, Any]) -> DimMemberRecord:
    """
    Validate dim_members record.
    
    Raises:
        ValueError: If required fields are missing
    """
    required_fields = ['first_name', 'last_name', 'full_name', 'state']
    
    for field in required_fields:
        if not record.get(field):
            raise ValueError(f"Required field '{field}' is missing or empty")
    
    # Warn if party is missing (not error, as fallback may not have it)
    if not record.get('party'):
        logger.warning(f"Member {record['full_name']} has no party affiliation")
    
    return record  # type: ignore


def validate_network_graph(data: Dict[str, Any]) -> NetworkGraphData:
    """
    Validate network graph data structure.
    
    Raises:
        ValueError: If structure is invalid
    """
    if 'nodes' not in data or 'links' not in data:
        raise ValueError("Network graph must have 'nodes' and 'links'")
    
    if not isinstance(data['nodes'], list) or not isinstance(data['links'], list):
        raise ValueError("'nodes' and 'links' must be lists")
    
    # Validate nodes
    member_nodes = [n for n in data['nodes'] if n.get('group') == 'member']
    members_with_party = [n for n in member_nodes if n.get('party')]
    
    if member_nodes and not members_with_party:
        raise ValueError("Network graph has member nodes but NONE have party data")
    
    party_coverage = len(members_with_party) / len(member_nodes) if member_nodes else 0
    
    if party_coverage < 0.5:
        logger.warning(f"Low party coverage in network graph: {party_coverage:.1%}")
    
    logger.info(f"Network graph validation: {len(data['nodes'])} nodes, "
                f"{len(data['links'])} links, {party_coverage:.1%} party coverage")
    
    return data  # type: ignore


def assert_data_quality(total: int, enriched: int, threshold: float = 0.8) -> None:
    """
    Assert that enrichment quality meets threshold.
    
    Args:
        total: Total number of records
        enriched: Number of successfully enriched records
        threshold: Minimum acceptable enrichment rate (default 0.8 = 80%)
    
    Raises:
        ValueError: If enrichment rate is below threshold
    """
    if total == 0:
        raise ValueError("No records to validate")
    
    rate = enriched / total
    
    if rate < threshold:
        raise ValueError(
            f"Enrichment rate {rate:.1%} is below threshold {threshold:.1%}. "
            f"Only {enriched}/{total} records were enriched successfully."
        )
    
    logger.info(f"✓ Data quality check passed: {rate:.1%} enrichment rate")
