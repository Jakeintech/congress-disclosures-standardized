"""Centralized S3 path registry for the politics data platform.

This module provides a single source of truth for all S3 paths across the data lake.
All paths use Hive-style partitioning (key=value) for compatibility with DuckDB,
Iceberg, and AWS Glue Data Catalog.

Architecture:
- Bronze: Immutable source data (raw PDFs, XML, JSON)
- Silver: Normalized Parquet tables (cleaned, deduplicated)
- Gold: Analytics-ready data (star schema with dimensions, facts, aggregates)

Bucket Structure:
    politics-data-platform/
    ├── data/
    │   ├── reference/           # Master data (members, assets, bills crosswalks)
    │   ├── bronze/              # Immutable source data
    │   ├── silver/              # Normalized Parquet
    │   └── gold/                # Analytics (star schema)
    ├── metadata/
    │   ├── iceberg/             # Iceberg metadata files
    │   ├── duckdb/              # DuckDB database files
    │   └── dbt/                 # DBT artifacts
    ├── api_cache/               # Pre-computed API responses
    └── public/
        └── website/             # Static website

"""

import os
from typing import Optional


class S3PathConfig:
    """Configuration for S3 bucket and path generation."""

    # Bucket name (override via environment variable)
    BUCKET = os.environ.get("S3_BUCKET_NAME", "politics-data-platform")

    # Top-level prefixes
    DATA_PREFIX = "data"
    METADATA_PREFIX = "metadata"
    API_CACHE_PREFIX = "api_cache"
    PUBLIC_PREFIX = "public"

    # Data layer prefixes
    REFERENCE_PREFIX = f"{DATA_PREFIX}/reference"
    BRONZE_PREFIX = f"{DATA_PREFIX}/bronze"
    SILVER_PREFIX = f"{DATA_PREFIX}/silver"
    GOLD_PREFIX = f"{DATA_PREFIX}/gold"

    # Data sources
    SOURCE_HOUSE_FD = "house_fd"
    SOURCE_CONGRESS_API = "congress_api"
    SOURCE_LOBBYING = "lobbying"

    # Gold layer sub-categories
    GOLD_DIMENSIONS = f"{GOLD_PREFIX}/dimensions"
    GOLD_FACTS = f"{GOLD_PREFIX}/facts"
    GOLD_AGGREGATES = f"{GOLD_PREFIX}/aggregates"


class S3Paths:
    """S3 path generators for all data layers.

    All methods return paths WITHOUT the s3:// prefix and bucket name.
    Use build_s3_uri() to get full S3 URIs.

    Examples:
        >>> S3Paths.bronze_house_fd_raw_zip(2025)
        'data/bronze/house_fd/year=2025/raw_zip/2025FD.zip'

        >>> S3Paths.gold_dimension("dim_members")
        'data/gold/dimensions/dim_members/dim_members.parquet'

        >>> S3Paths.build_s3_uri(S3Paths.silver_house_fd_filings(2025))
        's3://politics-data-platform/data/silver/house_fd/filings/year=2025/'
    """

    # ============================================================================
    # REFERENCE DATA PATHS
    # ============================================================================

    @staticmethod
    def reference_members() -> str:
        """Master member registry (cross-source bioguide crosswalk)."""
        return f"{S3PathConfig.REFERENCE_PREFIX}/members/dim_members_master.parquet"

    @staticmethod
    def reference_bioguide_crosswalk() -> str:
        """Bioguide ID crosswalk (House ↔ Senate ↔ Congress.gov)."""
        return f"{S3PathConfig.REFERENCE_PREFIX}/bioguide_crosswalk/crosswalk.parquet"

    @staticmethod
    def reference_asset_crosswalk() -> str:
        """Asset/ticker crosswalk with sector classifications."""
        return f"{S3PathConfig.REFERENCE_PREFIX}/asset_crosswalk/assets.parquet"

    @staticmethod
    def reference_bill_crosswalk() -> str:
        """Bill ID crosswalk (normalize different bill ID formats)."""
        return f"{S3PathConfig.REFERENCE_PREFIX}/bill_crosswalk/bills.parquet"

    # ============================================================================
    # BRONZE LAYER - HOUSE FINANCIAL DISCLOSURES
    # ============================================================================

    @staticmethod
    def bronze_house_fd_base(year: int) -> str:
        """Base path for House FD data for a given year."""
        return f"{S3PathConfig.BRONZE_PREFIX}/{S3PathConfig.SOURCE_HOUSE_FD}/year={year}"

    @staticmethod
    def bronze_house_fd_raw_zip(year: int) -> str:
        """Raw ZIP file downloaded from House Clerk."""
        return f"{S3Paths.bronze_house_fd_base(year)}/raw_zip/{year}FD.zip"

    @staticmethod
    def bronze_house_fd_index_xml(year: int) -> str:
        """XML index file (metadata for all filings in year)."""
        return f"{S3Paths.bronze_house_fd_base(year)}/index/{year}FD.xml"

    @staticmethod
    def bronze_house_fd_index_txt(year: int) -> str:
        """Text index file (if available)."""
        return f"{S3Paths.bronze_house_fd_base(year)}/index/{year}FD.txt"

    @staticmethod
    def bronze_house_fd_pdfs(year: int, filing_type: str) -> str:
        """Directory containing PDFs for a specific filing type.

        Args:
            year: Year (e.g., 2025)
            filing_type: Filing type code (P, A, T, X, D, W)

        Returns:
            Path to PDFs directory
        """
        return f"{S3Paths.bronze_house_fd_base(year)}/filing_type={filing_type}/pdfs/"

    @staticmethod
    def bronze_house_fd_pdf(year: int, filing_type: str, doc_id: str) -> str:
        """Path to individual PDF file.

        Args:
            year: Year (e.g., 2025)
            filing_type: Filing type code (P, A, T, etc.)
            doc_id: Document ID (e.g., "10063228")
        """
        return f"{S3Paths.bronze_house_fd_pdfs(year, filing_type)}{doc_id}.pdf"

    # ============================================================================
    # BRONZE LAYER - CONGRESS.GOV API
    # ============================================================================

    @staticmethod
    def bronze_congress_bills(congress: int, bill_type: Optional[str] = None) -> str:
        """Congress.gov bills JSON files.

        Args:
            congress: Congress number (e.g., 118)
            bill_type: Optional bill type (hr, s, hjres, sjres, hconres, sconres, hres, sres)
        """
        base = f"{S3PathConfig.BRONZE_PREFIX}/{S3PathConfig.SOURCE_CONGRESS_API}/bills/congress={congress}"
        if bill_type:
            return f"{base}/bill_type={bill_type}/"
        return f"{base}/"

    @staticmethod
    def bronze_congress_bill(congress: int, bill_type: str, bill_number: int) -> str:
        """Individual bill JSON file."""
        return f"{S3Paths.bronze_congress_bills(congress, bill_type)}{bill_type}{bill_number}.json"

    @staticmethod
    def bronze_congress_members() -> str:
        """Congress.gov members JSON files."""
        return f"{S3PathConfig.BRONZE_PREFIX}/{S3PathConfig.SOURCE_CONGRESS_API}/members/"

    @staticmethod
    def bronze_congress_member(bioguide_id: str) -> str:
        """Individual member profile JSON."""
        return f"{S3Paths.bronze_congress_members()}{bioguide_id}.json"

    @staticmethod
    def bronze_congress_committees(chamber: Optional[str] = None) -> str:
        """Congress.gov committees JSON files.

        Args:
            chamber: Optional chamber filter (house, senate, joint)
        """
        base = f"{S3PathConfig.BRONZE_PREFIX}/{S3PathConfig.SOURCE_CONGRESS_API}/committees"
        if chamber:
            return f"{base}/chamber={chamber}/"
        return f"{base}/"

    # ============================================================================
    # BRONZE LAYER - LOBBYING DISCLOSURES
    # ============================================================================

    @staticmethod
    def bronze_lobbying_base(year: int, quarter: str) -> str:
        """Base path for lobbying data.

        Args:
            year: Year (e.g., 2024)
            quarter: Quarter (Q1, Q2, Q3, Q4)
        """
        return f"{S3PathConfig.BRONZE_PREFIX}/{S3PathConfig.SOURCE_LOBBYING}/year={year}/quarter={quarter}"

    @staticmethod
    def bronze_lobbying_xml(year: int, quarter: str, entity_type: str) -> str:
        """Lobbying XML files by entity type.

        Args:
            year: Year (e.g., 2024)
            quarter: Quarter (Q1, Q2, Q3, Q4)
            entity_type: Entity type (registrants, clients, issues, etc.)
        """
        return f"{S3Paths.bronze_lobbying_base(year, quarter)}/{entity_type}.xml"

    # ============================================================================
    # SILVER LAYER - HOUSE FINANCIAL DISCLOSURES
    # ============================================================================

    @staticmethod
    def silver_house_fd_base() -> str:
        """Base path for House FD silver layer."""
        return f"{S3PathConfig.SILVER_PREFIX}/{S3PathConfig.SOURCE_HOUSE_FD}"

    @staticmethod
    def silver_house_fd_filings(year: Optional[int] = None) -> str:
        """Silver filings table (Parquet)."""
        base = f"{S3Paths.silver_house_fd_base()}/filings"
        if year:
            return f"{base}/year={year}/"
        return f"{base}/"

    @staticmethod
    def silver_house_fd_documents(year: Optional[int] = None) -> str:
        """Silver documents table (PDF metadata + extraction status)."""
        base = f"{S3Paths.silver_house_fd_base()}/documents"
        if year:
            return f"{base}/year={year}/"
        return f"{base}/"

    @staticmethod
    def silver_house_fd_text(year: int, extraction_method: str, doc_id: str) -> str:
        """Extracted text (gzipped).

        Args:
            year: Year
            extraction_method: Method used (direct_text, ocr)
            doc_id: Document ID
        """
        return f"{S3Paths.silver_house_fd_base()}/text/extraction_method={extraction_method}/year={year}/{doc_id}.txt.gz"

    @staticmethod
    def silver_house_fd_objects(filing_type: str, year: Optional[int] = None) -> str:
        """Structured extraction JSON files.

        Args:
            filing_type: Filing type (type_p, type_a, type_t, etc.)
            year: Optional year partition
        """
        base = f"{S3Paths.silver_house_fd_base()}/objects/filing_type={filing_type}"
        if year:
            return f"{base}/year={year}/"
        return f"{base}/"

    @staticmethod
    def silver_house_fd_object(filing_type: str, year: int, doc_id: str) -> str:
        """Individual structured extraction JSON."""
        return f"{S3Paths.silver_house_fd_objects(filing_type, year)}{doc_id}.json"

    @staticmethod
    def silver_house_fd_objects_parquet(filing_type: str, year: Optional[int] = None) -> str:
        """Flattened Parquet view of objects (for faster querying).

        This is a denormalized/flattened version of the JSON objects for query performance.
        """
        base = f"{S3Paths.silver_house_fd_base()}/objects_parquet/filing_type={filing_type}"
        if year:
            return f"{base}/year={year}/"
        return f"{base}/"

    # ============================================================================
    # SILVER LAYER - CONGRESS.GOV
    # ============================================================================

    @staticmethod
    def silver_congress_bills(congress: Optional[int] = None) -> str:
        """Silver bills table (Parquet)."""
        base = f"{S3PathConfig.SILVER_PREFIX}/{S3PathConfig.SOURCE_CONGRESS_API}/bills"
        if congress:
            return f"{base}/congress={congress}/"
        return f"{base}/"

    @staticmethod
    def silver_congress_members() -> str:
        """Silver members table (Parquet)."""
        return f"{S3PathConfig.SILVER_PREFIX}/{S3PathConfig.SOURCE_CONGRESS_API}/members/"

    @staticmethod
    def silver_congress_committees(chamber: Optional[str] = None) -> str:
        """Silver committees table (Parquet)."""
        base = f"{S3PathConfig.SILVER_PREFIX}/{S3PathConfig.SOURCE_CONGRESS_API}/committees"
        if chamber:
            return f"{base}/chamber={chamber}/"
        return f"{base}/"

    # ============================================================================
    # SILVER LAYER - LOBBYING
    # ============================================================================

    @staticmethod
    def silver_lobbying_filings(year: Optional[int] = None, quarter: Optional[str] = None) -> str:
        """Silver lobbying filings table (Parquet)."""
        base = f"{S3PathConfig.SILVER_PREFIX}/{S3PathConfig.SOURCE_LOBBYING}/filings"
        if year:
            base = f"{base}/year={year}"
            if quarter:
                return f"{base}/quarter={quarter}/"
            return f"{base}/"
        return f"{base}/"

    # ============================================================================
    # GOLD LAYER - DIMENSIONS
    # ============================================================================

    @staticmethod
    def gold_dimension(table_name: str) -> str:
        """Gold dimension table.

        Args:
            table_name: Dimension table name (e.g., "dim_members", "dim_assets")
        """
        return f"{S3PathConfig.GOLD_DIMENSIONS}/{table_name}/{table_name}.parquet"

    @staticmethod
    def gold_dim_members() -> str:
        """Members dimension (SCD Type 2)."""
        return S3Paths.gold_dimension("dim_members")

    @staticmethod
    def gold_dim_assets() -> str:
        """Assets dimension (ticker, sector, industry)."""
        return S3Paths.gold_dimension("dim_assets")

    @staticmethod
    def gold_dim_bills() -> str:
        """Bills dimension."""
        return S3Paths.gold_dimension("dim_bills")

    @staticmethod
    def gold_dim_date() -> str:
        """Date dimension."""
        return S3Paths.gold_dimension("dim_date")

    # ============================================================================
    # GOLD LAYER - FACTS
    # ============================================================================

    @staticmethod
    def gold_fact(table_name: str, year: Optional[int] = None, month: Optional[int] = None) -> str:
        """Gold fact table with optional year/month partitioning.

        Args:
            table_name: Fact table name (e.g., "fact_ptr_transactions")
            year: Optional year partition
            month: Optional month partition (requires year)
        """
        base = f"{S3PathConfig.GOLD_FACTS}/{table_name}"
        if year:
            base = f"{base}/year={year}"
            if month:
                return f"{base}/month={month:02d}/"
            return f"{base}/"
        return f"{base}/"

    @staticmethod
    def gold_fact_ptr_transactions(year: Optional[int] = None, month: Optional[int] = None) -> str:
        """PTR transactions fact table."""
        return S3Paths.gold_fact("fact_ptr_transactions", year, month)

    @staticmethod
    def gold_fact_filings(year: Optional[int] = None) -> str:
        """All filings fact table."""
        return S3Paths.gold_fact("fact_filings", year)

    @staticmethod
    def gold_fact_lobbying(year: Optional[int] = None, quarter: Optional[str] = None) -> str:
        """Lobbying filings fact table.

        Note: Uses quarter partitioning instead of month.
        """
        base = f"{S3PathConfig.GOLD_FACTS}/fact_lobbying"
        if year:
            base = f"{base}/year={year}"
            if quarter:
                return f"{base}/quarter={quarter}/"
            return f"{base}/"
        return f"{base}/"

    # ============================================================================
    # GOLD LAYER - AGGREGATES
    # ============================================================================

    @staticmethod
    def gold_aggregate(metric_name: str, date: Optional[str] = None) -> str:
        """Gold aggregate table with optional date partitioning.

        Args:
            metric_name: Metric name (e.g., "trending_stocks")
            date: Optional date partition (YYYY-MM-DD format)
        """
        base = f"{S3PathConfig.GOLD_AGGREGATES}/{metric_name}"
        if date:
            return f"{base}/date={date}/"
        return f"{base}/"

    @staticmethod
    def gold_agg_trending_stocks() -> str:
        """Trending stocks aggregate (7/30/90-day rolling windows)."""
        return S3Paths.gold_aggregate("trending_stocks")

    @staticmethod
    def gold_agg_member_trading_stats() -> str:
        """Member-level trading statistics."""
        return S3Paths.gold_aggregate("member_trading_stats")

    @staticmethod
    def gold_agg_sector_activity() -> str:
        """Sector-level trading activity."""
        return S3Paths.gold_aggregate("sector_activity")

    @staticmethod
    def gold_agg_compliance_metrics() -> str:
        """Compliance metrics (late filings, violations)."""
        return S3Paths.gold_aggregate("compliance_metrics")

    @staticmethod
    def gold_agg_network_graph() -> str:
        """Member-asset-bill network graph (JSON)."""
        return f"{S3PathConfig.GOLD_AGGREGATES}/network_graph/network.json"

    @staticmethod
    def gold_agg_bill_trade_correlations() -> str:
        """Bill-trade correlations."""
        return S3Paths.gold_aggregate("bill_trade_correlations")

    # ============================================================================
    # METADATA PATHS
    # ============================================================================

    @staticmethod
    def metadata_iceberg(table_name: str) -> str:
        """Iceberg metadata directory for a table."""
        return f"{S3PathConfig.METADATA_PREFIX}/iceberg/{table_name}/metadata/"

    @staticmethod
    def metadata_duckdb(db_name: str = "prod") -> str:
        """DuckDB database file."""
        return f"{S3PathConfig.METADATA_PREFIX}/duckdb/{db_name}.duckdb"

    @staticmethod
    def metadata_dbt_artifacts() -> str:
        """DBT artifacts (manifest, catalog, run results)."""
        return f"{S3PathConfig.METADATA_PREFIX}/dbt/artifacts/"

    # ============================================================================
    # API CACHE PATHS
    # ============================================================================

    @staticmethod
    def api_cache_responses() -> str:
        """Pre-computed API responses (DynamoDB-backed)."""
        return f"{S3PathConfig.API_CACHE_PREFIX}/responses/"

    # ============================================================================
    # PUBLIC/WEBSITE PATHS
    # ============================================================================

    @staticmethod
    def public_website() -> str:
        """Static website files."""
        return f"{S3PathConfig.PUBLIC_PREFIX}/website/"

    @staticmethod
    def public_website_manifest() -> str:
        """Website manifest JSON."""
        return f"{S3Paths.public_website()}manifest.json"

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    @staticmethod
    def build_s3_uri(path: str, bucket: Optional[str] = None) -> str:
        """Build full S3 URI from path.

        Args:
            path: S3 key path (without bucket)
            bucket: Optional bucket name (defaults to S3PathConfig.BUCKET)

        Returns:
            Full S3 URI (s3://bucket/path)

        Examples:
            >>> S3Paths.build_s3_uri("data/bronze/house_fd/year=2025/")
            's3://politics-data-platform/data/bronze/house_fd/year=2025/'
        """
        bucket = bucket or S3PathConfig.BUCKET
        return f"s3://{bucket}/{path}"

    @staticmethod
    def parse_s3_uri(s3_uri: str) -> tuple[str, str]:
        """Parse S3 URI into bucket and key.

        Args:
            s3_uri: Full S3 URI (s3://bucket/key)

        Returns:
            Tuple of (bucket, key)

        Examples:
            >>> S3Paths.parse_s3_uri("s3://politics-data-platform/data/bronze/...")
            ('politics-data-platform', 'data/bronze/...')
        """
        if not s3_uri.startswith("s3://"):
            raise ValueError(f"Invalid S3 URI: {s3_uri}")

        parts = s3_uri[5:].split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""

        return bucket, key

    @staticmethod
    def get_bucket() -> str:
        """Get the configured S3 bucket name.

        Returns:
            Bucket name from environment or default
        """
        return S3PathConfig.BUCKET


# Convenience exports
BUCKET = S3PathConfig.BUCKET
build_s3_uri = S3Paths.build_s3_uri
parse_s3_uri = S3Paths.parse_s3_uri
