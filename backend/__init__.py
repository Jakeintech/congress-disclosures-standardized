"""
Politics Data Platform - Backend

Modern data lakehouse for congressional financial disclosures, 
legislative data, and lobbying activity.

Architecture:
- Bronze Layer: Raw, immutable source data
- Silver Layer: Normalized, queryable Parquet tables  
- Gold Layer: Analytics-ready star schema

Components:
- functions/: AWS Lambda function handlers
- lib/: Shared libraries and utilities
- scripts/: Data processing and aggregation scripts
- orchestration/: Step Functions state machine definitions
- layers/: Lambda layers (dependencies)
"""

__version__ = "2.0.0"
__author__ = "Jake (Jakeintech)"
__license__ = "MIT"
