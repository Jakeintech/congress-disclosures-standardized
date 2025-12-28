"""
Pydantic response models for Congressional Trading API

Provides type-safe response models for Lambda handlers that enable:
- OpenAPI spec auto-generation
- Runtime validation (optional)
- TypeScript type generation
- Consistent response structure

Usage:
    from api.lib.response_models import APIResponse, PaginatedResponse, Member

    def lambda_handler(event, context):
        member_data = Member(
            bioguide_id="C001117",
            name="Crockett, Jasmine",
            party="D",
            state="TX",
            chamber="house"
        )
        response_data = APIResponse(
            success=True,
            data=member_data
        )
        return response_formatter.success_response(response_data.model_dump())
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from enum import Enum


# ============================================================================
# Base Models
# ============================================================================


class PaginationMetadata(BaseModel):
    """Pagination metadata for list responses"""

    total: int = Field(..., description="Total number of records available")
    count: int = Field(..., description="Number of records in current page")
    limit: int = Field(..., description="Maximum records per page")
    offset: int = Field(..., description="Offset from start (0-indexed)")
    has_next: bool = Field(..., description="Whether more pages exist")
    has_prev: bool = Field(..., description="Whether previous pages exist")
    next: Optional[str] = Field(None, description="URL for next page")
    prev: Optional[str] = Field(None, description="URL for previous page")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 541,
                "count": 20,
                "limit": 20,
                "offset": 0,
                "has_next": True,
                "has_prev": False,
                "next": "/v1/members?limit=20&offset=20",
                "prev": None,
            }
        }
    )


class ErrorDetail(BaseModel):
    """Error detail structure"""

    message: str = Field(..., description="Human-readable error message")
    code: Union[int, str] = Field(..., description="Error code (HTTP status or custom)")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error context"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Member not found",
                "code": 404,
                "details": {"bioguide_id": "C999999"},
            }
        }
    )


T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper"""

    success: bool = Field(..., description="Whether the request succeeded")
    data: T = Field(..., description="Response payload")
    version: Optional[str] = Field(
        None, description="API version (e.g., 'v20251220-33a4c83')"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional response metadata"
    )
    error: Optional[ErrorDetail] = Field(
        None, description="Error details (if success=False)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {"example": "data"},
                "version": "v20251220-33a4c83",
            }
        }
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response with metadata"""

    items: List[T] = Field(..., description="List of items in current page")
    pagination: PaginationMetadata = Field(..., description="Pagination metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [{"id": 1}, {"id": 2}],
                "pagination": {
                    "total": 100,
                    "count": 2,
                    "limit": 20,
                    "offset": 0,
                    "has_next": True,
                    "has_prev": False,
                },
            }
        }
    )


# ============================================================================
# Enums
# ============================================================================


class Chamber(str, Enum):
    """Congressional chamber"""

    HOUSE = "house"
    SENATE = "senate"


class Party(str, Enum):
    """Political party"""

    DEMOCRAT = "D"
    REPUBLICAN = "R"
    INDEPENDENT = "I"
    LIBERTARIAN = "L"


class TransactionType(str, Enum):
    """Financial transaction type"""

    PURCHASE = "purchase"
    SALE = "sale"
    EXCHANGE = "exchange"


class FilingType(str, Enum):
    """Filing disclosure type"""

    P = "P"  # Periodic Transaction Report (PTR)
    A = "A"  # Annual Report
    T = "T"  # Termination Report
    X = "X"  # Extension Request
    D = "D"  # Campaign Notice
    W = "W"  # Withdrawal Notice
    UNKNOWN = "unknown"


class BillType(str, Enum):
    """Congressional bill type"""

    HR = "hr"  # House Bill
    S = "s"  # Senate Bill
    HJRES = "hjres"  # House Joint Resolution
    SJRES = "sjres"  # Senate Joint Resolution
    HCONRES = "hconres"  # House Concurrent Resolution
    SCONRES = "sconres"  # Senate Concurrent Resolution
    HRES = "hres"  # House Resolution
    SRES = "sres"  # Senate Resolution


# ============================================================================
# Entity Models
# ============================================================================


class Member(BaseModel):
    """Congressional member"""

    bioguide_id: Optional[str] = Field(
        None, description="Unique bioguide ID (e.g., 'C001117')"
    )
    name: str = Field("Unknown", description="Full name (Last, First)")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    party: Optional[Party] = Field(None, description="Political party")
    state: Optional[str] = Field(None, description="Two-letter state code")
    chamber: Optional[Chamber] = Field(None, description="House or Senate")
    district: Optional[str] = Field(None, description="District number (House only)")
    in_office: Optional[bool] = Field(None, description="Currently in office")

    # Trading statistics (optional, included in some endpoints)
    total_trades: Optional[int] = Field(None, description="Total trades filed")
    total_value_low: Optional[int] = Field(None, description="Total value lower bound")
    total_value_high: Optional[int] = Field(None, description="Total value upper bound")
    trade_count_30d: Optional[int] = Field(None, description="Trades in last 30 days")
    trade_count_90d: Optional[int] = Field(None, description="Trades in last 90 days")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "bioguide_id": "C001117",
                "name": "Crockett, Jasmine",
                "party": "D",
                "state": "TX",
                "chamber": "house",
                "district": "30",
                "in_office": True,
                "total_trades": 42,
                "total_value_low": 150000,
                "total_value_high": 650000,
            }
        }
    )


class TradingStats(BaseModel):
    """Aggregated trading statistics for a member"""

    total_trades: int = Field(..., description="Total number of trades")
    unique_stocks: int = Field(..., description="Number of unique stock symbols traded")
    latest_trade_date: Optional[str] = Field(
        None, description="Date of most recent trade"
    )


class FilingBrief(BaseModel):
    """Brief summary of a filing"""

    doc_id: str = Field(..., description="Filing document ID")
    filing_type: str = Field(..., description="Type of filing (e.g., PTR, Annual)")
    filing_date: Any = Field(..., description="Date filing was submitted")


class NetWorth(BaseModel):
    """Estimated net worth information"""

    min: int = Field(..., description="Lower bound of estimated net worth")
    max: int = Field(..., description="Upper bound of estimated net worth")
    year: Optional[int] = Field(None, description="Year of disclosure")


class SectorAllocation(BaseModel):
    """Asset distribution by industry sector"""

    sector: str = Field(..., description="Industry sector name")
    value: float = Field(..., description="Total estimated value in this sector")
    percentage: float = Field(..., description="Percentage of total portfolio")


class MemberProfile(Member):
    """Full congressional member profile with analytics"""

    trading_stats: Optional[TradingStats] = None
    recent_filings: Optional[List[FilingBrief]] = None
    net_worth: Optional[NetWorth] = None
    sector_allocation: Optional[List[SectorAllocation]] = None


class Transaction(BaseModel):
    """Financial disclosure transaction"""

    transaction_id: Optional[str] = Field(None, description="Unique transaction ID")
    disclosure_date: Optional[date] = Field(
        None, description="Date transaction was disclosed"
    )
    transaction_date: Optional[date] = Field(
        None, description="Date transaction occurred"
    )
    ticker: Optional[str] = Field(None, description="Stock ticker symbol")
    asset_description: Optional[str] = Field(None, description="Full asset description")
    transaction_type: Optional[TransactionType] = Field(
        None, description="Purchase, sale, or exchange"
    )
    amount_low: Optional[int] = Field(None, description="Minimum transaction amount")
    amount_high: Optional[int] = Field(None, description="Maximum transaction amount")
    amount: Optional[str] = Field(
        None, description="Formatted transaction amount string"
    )

    # Member information
    bioguide_id: Optional[str] = Field(None, description="Bioguide ID of the filler")
    member_name: str = Field("Unknown", description="Display name of the member")
    filer_name: Optional[str] = Field(None, description="Alias for member_name")
    first_name: Optional[str] = Field(None, description="Member's first name")
    last_name: Optional[str] = Field(None, description="Member's last name")
    party: Optional[str] = Field(None, description="Party affiliation (D, R, I)")
    state: Optional[str] = Field(None, description="State abbreviation")
    chamber: str = Field("house", description="House or Senate")

    # Optional fields
    owner: Optional[str] = Field(
        None, description="Asset owner (self, spouse, dependent)"
    )
    cap_gains_over_200: Optional[bool] = Field(None, description="Capital gains > $200")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "disclosure_date": "2025-01-15",
                "transaction_date": "2025-01-10",
                "ticker": "NVDA",
                "asset_description": "NVIDIA Corporation",
                "transaction_type": "purchase",
                "amount_low": 1001,
                "amount_high": 15000,
                "bioguide_id": "C001117",
                "member_name": "Crockett, Jasmine",
                "party": "D",
                "state": "TX",
                "chamber": "house",
            }
        }
    )


class Stock(BaseModel):
    """Stock/asset information with trading activity"""

    ticker: str = Field(..., description="Stock ticker symbol")
    name: Optional[str] = Field(None, description="Company/asset name")

    # Trading activity
    trade_count: int = Field(..., description="Total trades of this stock")
    purchase_count: int = Field(0, description="Number of purchases")
    sale_count: int = Field(0, description="Number of sales")

    # Value aggregates
    total_value_low: Optional[int] = Field(None, description="Total value lower bound")
    total_value_high: Optional[int] = Field(None, description="Total value upper bound")

    # Legislative exposure (optional)
    bill_count: Optional[int] = Field(None, description="Related bills count")
    sector: Optional[str] = Field(None, description="Industry sector")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticker": "NVDA",
                "name": "NVIDIA Corporation",
                "trade_count": 87,
                "purchase_count": 52,
                "sale_count": 35,
                "total_value_low": 500000,
                "total_value_high": 2500000,
                "sector": "Technology",
            }
        }
    )


class StockStatistics(BaseModel):
    """Aggregated trading statistics for a specific stock"""

    total_trades: int = Field(..., description="Total trades by all members")
    unique_members: int = Field(
        ..., description="Number of unique members trading this stock"
    )
    purchase_count: int = Field(..., description="Number of purchase transactions")
    sale_count: int = Field(..., description="Number of sale transactions")
    latest_trade_date: Optional[str] = Field(
        None, description="Date of most recent trade"
    )


class StockDetail(BaseModel):
    """Detailed stock information with recent activity"""

    ticker: str = Field(..., description="Stock ticker symbol")
    name: Optional[str] = Field(None, description="Company/asset name")
    statistics: StockStatistics = Field(..., description="Aggregated trading stats")
    recent_trades: List[Transaction] = Field(
        ..., description="List of most recent trades"
    )


class Filing(BaseModel):
    """Financial disclosure filing"""

    doc_id: str = Field(..., description="Unique document ID")
    filing_type: Optional[FilingType] = Field(
        None, description="Filing type (P, A, T, etc.)"
    )
    filing_date: Optional[date] = Field(None, description="Date filed")
    filing_year: Optional[int] = Field(0, description="Year filed")

    # Member information
    bioguide_id: Optional[str] = Field(None, description="Member's bioguide ID")
    member_name: Optional[str] = Field(None, description="Member's full name")
    first_name: Optional[str] = Field(None, description="Member's first name")
    last_name: Optional[str] = Field(None, description="Member's last name")

    # Optional fields
    pdf_url: Optional[str] = Field(None, description="URL to PDF filing")
    has_structured_data: Optional[bool] = Field(
        None, description="Whether structured extraction succeeded"
    )
    transaction_count: Optional[int] = Field(
        None, description="Number of transactions in filing"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "doc_id": "10063228",
                "filing_type": "P",
                "filing_date": "2025-01-15",
                "filing_year": 2025,
                "bioguide_id": "C001117",
                "member_name": "Crockett, Jasmine",
                "has_structured_data": True,
                "transaction_count": 12,
            }
        }
    )


class Bill(BaseModel):
    """Congressional bill"""

    bill_id: str = Field(..., description="Unique bill ID (e.g., '119-hr-1234')")
    congress: int = Field(..., description="Congress number (e.g., 119)")
    bill_type: BillType = Field(..., description="Bill type (hr, s, etc.)")
    bill_number: int = Field(..., description="Bill number")

    title: str = Field(..., description="Bill title")
    introduced_date: Optional[date] = Field(None, description="Date introduced")

    # Sponsor information
    sponsor_bioguide_id: Optional[str] = Field(
        None, description="Sponsor's bioguide ID"
    )
    sponsor_name: Optional[str] = Field(None, description="Sponsor's name")
    sponsor_party: Optional[Party] = Field(None, description="Sponsor's party")
    sponsor_state: Optional[str] = Field(None, description="Sponsor's state")

    # Counts
    cosponsors_count: Optional[int] = Field(None, description="Number of cosponsors")
    actions_count: Optional[int] = Field(None, description="Number of actions")
    trade_correlations_count: Optional[int] = Field(
        0, description="Number of trade correlations"
    )

    # Enrichment
    top_industry_tags: Optional[List[str]] = Field(
        None, description="Top 2 industry tags"
    )
    latest_action_date: Optional[Any] = Field(None, description="Latest action date")
    latest_action_text: Optional[str] = Field(
        None, description="Latest action description"
    )
    days_since_action: Optional[int] = Field(
        None, description="Days since latest action"
    )

    # URLs
    congress_gov_url: Optional[str] = Field(None, description="Congress.gov URL")


class BillAction(BaseModel):
    """Congressional bill action"""

    action_date: str = Field(..., description="Date of action")
    action_text: str = Field(..., description="Full description of action")
    chamber: Optional[str] = Field(None, description="House or Senate")
    action_code: Optional[str] = Field(None, description="Congress action code")
    action_type: Optional[str] = Field(None, description="Type classification")


class BillIndustryTag(BaseModel):
    """Industry tagging for a bill"""

    industry: str = Field(..., description="Industry name")
    confidence: float = Field(..., description="Match confidence score (0-1)")
    tickers: List[str] = Field(
        default_factory=list, description="Related stock tickers"
    )
    keywords: List[str] = Field(
        default_factory=list, description="Matched keywords from bill text"
    )


class BillTradeCorrelation(BaseModel):
    """Correlation between a member's trade and a bill"""

    member: Member = Field(..., description="Member who traded")
    ticker: str = Field(..., description="Stock ticker")
    trade_date: str = Field(..., description="Date of trade")
    trade_type: str = Field(..., description="Purchase / Sale")
    amount_range: Optional[str] = Field(None, description="Trade value range")
    bill_action_date: str = Field(..., description="Related bill action date")
    days_offset: int = Field(..., description="Days between trade and action")
    correlation_score: int = Field(..., description="Strength of correlation (0-100)")
    role: Optional[str] = Field(
        None, description="Member's role (Sponsor/Cosponsor/Committee)"
    )
    committee_overlap: bool = Field(
        False, description="If member is on relevant committee"
    )
    match_type: Optional[str] = Field(
        None, description="Basis of match (direct/industry)"
    )


class BillCommittee(BaseModel):
    """Committee or subcommittee associated with a bill"""

    system_code: str = Field(..., description="Committee system code")
    name: str = Field(..., description="Full committee name")
    chamber: str = Field(..., description="House or Senate")
    activity: List[str] = Field(
        default_factory=list, description="Type of activity (referral, markup, etc.)"
    )


class RelatedBill(BaseModel):
    """Bill related to another bill"""

    related_bill_id: str = Field(..., description="Related bill's unique ID")
    title: str = Field(..., description="Related bill's title")
    type: str = Field(..., description="Type of relationship")
    identified_by: Optional[str] = Field(None, description="Who identified the link")


class BillTitle(BaseModel):
    """Official or short title for a bill"""

    title: str = Field(..., description="Title text")
    type: str = Field(..., description="Title type (Short, Official, etc.)")
    chamber: Optional[str] = Field(None, description="Associated chamber")


class BillDetail(BaseModel):
    """Full detail response for a congressional bill"""

    bill: Bill = Field(..., description="Base bill metadata")
    sponsor: Optional[Member] = Field(None, description="Primary sponsor")
    cosponsors: List[Member] = Field(
        default_factory=list, description="List of cosponsors"
    )
    cosponsors_count: int = Field(0, description="Total number of cosponsors")
    actions_recent: List[BillAction] = Field(
        default_factory=list, description="Recent actions timeline"
    )
    actions_count_total: int = Field(0, description="Total number of actions")
    industry_tags: List[BillIndustryTag] = Field(
        default_factory=list, description="Industry focus tags"
    )
    trade_correlations: List[BillTradeCorrelation] = Field(
        default_factory=list, description="Recent trade activity"
    )
    trade_correlations_count: int = Field(0, description="Number of related trades")
    committees: List[BillCommittee] = Field(
        default_factory=list, description="Assigned committees"
    )
    related_bills: List[RelatedBill] = Field(
        default_factory=list, description="Related legislation"
    )
    titles: List[BillTitle] = Field(
        default_factory=list, description="All known titles"
    )
    congress_gov_url: Optional[str] = Field(
        None, description="Official Congress.gov URL"
    )


# ============================================================================
# Committee Models
# ============================================================================


class Subcommittee(BaseModel):
    """Congressional subcommittee"""

    systemCode: str = Field(..., description="Unique subcommittee system code")
    name: str = Field(..., description="Full subcommittee name")
    type: Optional[str] = Field(None, description="Subcommittee type")
    url: Optional[str] = Field(None, description="Congress.gov URL")
    updateDate: Optional[str] = Field(None, description="Last update date")


class Committee(BaseModel):
    """Congressional committee"""

    systemCode: str = Field(
        ..., description="Unique committee system code (e.g., 'HSAP00')"
    )
    name: str = Field(..., description="Full committee name")
    chamber: str = Field(..., description="House, Senate, or Joint")
    type: str = Field(..., description="Committee type (standing, select, etc.)")
    subcommitteeCount: int = Field(0, description="Number of subcommittees")
    subcommittees: List[Subcommittee] = Field(
        default_factory=list, description="List of subcommittees"
    )
    url: Optional[str] = Field(None, description="Congress.gov URL")
    updateDate: Optional[str] = Field(None, description="Last update date")


class CommitteeDetail(Committee):
    """Detailed committee information with members and bills"""

    members: List[Member] = Field(default_factory=list, description="Committee members")
    bills: List[Bill] = Field(
        default_factory=list, description="Bills referred to committee"
    )
    reports: List[str] = Field(default_factory=list, description="Committee reports")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "bill_id": "119-hr-1234",
                "congress": 119,
                "bill_type": "hr",
                "bill_number": 1234,
                "title": "American Innovation Act of 2025",
                "introduced_date": "2025-01-10",
                "sponsor_bioguide_id": "C001117",
                "sponsor_name": "Crockett, Jasmine",
                "sponsor_party": "D",
                "sponsor_state": "TX",
                "cosponsors_count": 42,
            }
        }
    )


# ============================================================================
# Analytics Models
# ============================================================================


class TrendingStock(BaseModel):
    """Trending stock with recent activity"""

    ticker: str
    name: Optional[str] = None
    trade_count_7d: int = Field(..., description="Trades in last 7 days")
    trade_count_30d: int = Field(..., description="Trades in last 30 days")
    purchase_count: int = 0
    sale_count: int = 0
    net_sentiment: Optional[str] = Field(
        None, description="bullish, bearish, or neutral"
    )
    unique_members: Optional[int] = Field(None, description="Unique members trading")


class TopTrader(BaseModel):
    """Top trading member"""

    bioguide_id: str
    name: str
    party: Party
    state: str
    chamber: Chamber
    total_trades: int
    total_value_low: int
    total_value_high: int
    recent_trades_30d: int


class DashboardSummary(BaseModel):
    """Dashboard summary statistics"""

    total_members: int
    total_trades: int
    total_filings: int
    total_bills: int
    avg_trades_per_member: float
    last_updated: datetime


class ComplianceMetric(BaseModel):
    """Compliance metrics for a member"""

    bioguide_id: str
    member_name: str
    total_filings: int
    on_time_filings: int
    late_filings: int
    compliance_rate: float = Field(..., ge=0.0, le=1.0)
    avg_days_late: Optional[float] = None


class NetworkNode(BaseModel):
    """Node in network graph"""

    id: str
    label: str
    type: str = Field(..., description="member, stock, bill, or lobbyist")
    group: Optional[str] = None


class NetworkLink(BaseModel):
    """Link in network graph"""

    source: str
    target: str
    value: float = Field(..., description="Link weight/strength")
    type: str = Field(..., description="trades, sponsors, lobbies, etc.")


class NetworkGraphData(BaseModel):
    """Network graph structure"""

    nodes: List[NetworkNode]
    links: List[NetworkLink]
    aggregates: Optional[Dict[str, Any]] = None


# ============================================================================
# System/Utility Models
# ============================================================================


class GitInfo(BaseModel):
    """Git commit information"""

    commit: str = Field(..., description="Full git commit hash")
    commit_short: str = Field(..., description="Short git commit hash (7 chars)")
    branch: str = Field(..., description="Git branch name")
    dirty: bool = Field(
        False, description="Whether working tree had uncommitted changes"
    )


class BuildInfo(BaseModel):
    """Build information"""

    timestamp: str = Field(..., description="Build timestamp (ISO 8601)")
    date: str = Field(..., description="Build date (YYYY-MM-DD)")


class RuntimeInfo(BaseModel):
    """Lambda runtime information"""

    function_name: str = Field(..., description="Lambda function name")
    function_version: str = Field(..., description="Lambda function version")
    aws_request_id: Optional[str] = Field(None, description="AWS request ID")
    memory_limit_mb: Optional[int] = Field(None, description="Memory limit in MB")


class VersionData(BaseModel):
    """API version information"""

    version: str = Field(..., description="Version string (e.g., 'v20251220-33a4c83')")
    git: GitInfo = Field(..., description="Git commit information")
    build: BuildInfo = Field(..., description="Build timestamp information")
    api_version: str = Field("v1", description="API version")
    runtime: RuntimeInfo = Field(..., description="Lambda runtime information")
    status: str = Field("healthy", description="API health status")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "version": "v20251220-33a4c83",
                "git": {
                    "commit": "33a4c83f1e2a3b4c5d6e7f8g9h0i1j2k3l4m5n6",
                    "commit_short": "33a4c83",
                    "branch": "main",
                    "dirty": False,
                },
                "build": {"timestamp": "2025-12-20T10:30:00Z", "date": "2025-12-20"},
                "api_version": "v1",
                "runtime": {
                    "function_name": "get_version",
                    "function_version": "$LATEST",
                    "aws_request_id": "abc-123-def-456",
                    "memory_limit_mb": 512,
                },
                "status": "healthy",
            }
        }
    )


# ============================================================================
# Explicit Response Classes for OpenAPI
# ============================================================================


# Simple responses (non-paginated)
class MemberResponse(APIResponse[Member]):
    pass


class MemberProfileResponse(APIResponse[MemberProfile]):
    pass


class MembersListResponse(APIResponse[List[Member]]):
    pass


class StockResponse(APIResponse[StockDetail]):
    pass


class TransactionResponse(APIResponse[Transaction]):
    pass


class FilingResponse(APIResponse[Filing]):
    pass


class BillResponse(APIResponse[BillDetail]):
    pass


class CommitteeResponse(APIResponse[CommitteeDetail]):
    pass


class CommitteesPaginatedResponse(APIResponse[PaginatedResponse[Committee]]):
    pass


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


# Paginated responses
class MembersPaginatedResponse(APIResponse[PaginatedResponse[Member]]):
    pass


class StocksPaginatedResponse(APIResponse[PaginatedResponse[Stock]]):
    pass


class TransactionsPaginatedResponse(APIResponse[PaginatedResponse[Transaction]]):
    pass


class FilingsPaginatedResponse(APIResponse[PaginatedResponse[Filing]]):
    pass


class BillsPaginatedResponse(APIResponse[PaginatedResponse[Bill]]):
    pass


# Analytics responses
class DashboardResponse(APIResponse[DashboardSummary]):
    pass


class TrendingStocksResponse(APIResponse[List[TrendingStock]]):
    pass


class TopTradersResponse(APIResponse[List[TopTrader]]):
    pass


class NetworkGraphResponse(APIResponse[NetworkGraphData]):
    pass


class ComplianceResponse(APIResponse[List[ComplianceMetric]]):
    pass


# System/utility responses
class VersionResponse(APIResponse[VersionData]):
    pass
