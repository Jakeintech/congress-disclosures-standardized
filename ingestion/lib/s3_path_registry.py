from datetime import datetime
from typing import Optional, Union

class S3Paths:
    """
    Centralized registry for all S3 paths in the Politics Data Platform.
    
    Structure:
    - data/reference/: Master reference data
    - data/bronze/: Raw immutable source data
    - data/silver/: Normalized Parquet (Hive partitioned)
    - data/gold/: Analytics (Star schema)
    - metadata/: System metadata (Iceberg, DuckDB, DBT)
    """
    
    BUCKET = "politics-data-platform"  # Default bucket, can be overridden env var if needed
    
    # =========================================================================
    # REFERENCE DATA
    # =========================================================================
    
    @staticmethod
    def reference_members_master() -> str:
        """Master member registry (cross-source)."""
        return "data/reference/members/dim_members_master.parquet"
        
    @staticmethod
    def reference_asset_crosswalk() -> str:
        """Asset/ticker crosswalk with sector classifications."""
        return "data/reference/asset_crosswalk/assets.parquet"
        
    @staticmethod
    def reference_bill_crosswalk() -> str:
        """Bill ID normalization crosswalk."""
        return "data/reference/bill_crosswalk/bills.parquet"
        
    # =========================================================================
    # BRONZE LAYER (Raw Data)
    # =========================================================================
    
    @staticmethod
    def bronze_house_fd_pdf(year: int, filing_type: str, doc_id: str) -> str:
        """Raw House FD PDF path."""
        return f"data/bronze/house_fd/year={year}/filing_type={filing_type}/pdfs/{doc_id}.pdf"
        
    @staticmethod
    def bronze_house_fd_prefix(year: int) -> str:
        """Prefix for House FD raw data for a year."""
        return f"data/bronze/house_fd/year={year}/"

    @staticmethod
    def bronze_congress_bill_json(congress: int, bill_type: str, bill_number: str) -> str:
        """Raw Congress.gov Bill JSON."""
        return f"data/bronze/congress_api/entity=bills/congress={congress}/type={bill_type}/number={bill_number}/bill.json"
        
    @staticmethod
    def bronze_lobbying_filing_xml(year: int, quarter: str, filing_uuid: str) -> str:
        """Raw Lobbying Disclosure XML."""
        return f"data/bronze/lobbying/year={year}/quarter={quarter}/{filing_uuid}.xml"
        
    # =========================================================================
    # SILVER LAYER (Normalized Parquet/JSON - Hive Partitioned)
    # =========================================================================
    
    @staticmethod
    def silver_house_fd_objects(year: int, doc_id: str) -> str:
        """Extracted objects (JSON) from House FD."""
        return f"data/silver/house_fd/objects/year={year}/{doc_id}.json"
        
    @staticmethod
    def silver_congress_bills_parquet(congress: int) -> str:
        """Normalized Congress bills (Parquet)."""
        return f"data/silver/congress_api/bills/congress={congress}/bills.parquet"
        
    # =========================================================================
    # GOLD LAYER (Analytics - Star Schema)
    # =========================================================================
    
    @staticmethod
    def gold_dim_members() -> str:
        """Gold dimension: Members."""
        return "data/gold/dimensions/dim_members/"
        
    @staticmethod
    def gold_fact_transactions(year: int = None) -> str:
        """Gold fact: Transactions."""
        if year:
            return f"data/gold/facts/fact_transactions/year={year}/"
        return "data/gold/facts/fact_transactions/"
