# Data Layers

Detailed documentation of Bronze, Silver, and Gold data layers in the medallion architecture.

## Overview

The pipeline uses a **medallion architecture** with three progressive layers of data refinement:

1. **Bronze**: Raw, immutable source data
2. **Silver**: Cleaned, normalized, queryable data
3. **Gold**: Aggregated, business-ready data

## Bronze Layer

**Purpose**: Byte-for-byte preservation of source data

**Location**: `s3://congress-disclosures-standardized/bronze/house/financial/`

**Structure**:
```
bronze/house/financial/
└── year=2025/
    ├── raw_zip/
    │   └── 2025FD.zip
    ├── index/
    │   ├── 2025FD.xml
    │   └── 2025FD.txt
    └── pdfs/
        └── 2025/
            ├── 8221216.pdf
            ├── 8221217.pdf
            └── ...
```

**Metadata Tracking**:
- `source_url`: Download source
- `download_timestamp`: Ingestion time
- `http_etag`, `http_last_modified`: Caching info
- `ingest_version`: Pipeline version
- `extraction-processed`: Processing state flag

**Retention**: Permanent (immutable archive)

## Silver Layer

**Purpose**: Cleaned, typed, analytics-ready data

**Location**: `s3://congress-disclosures-standardized/silver/house/financial/`

**Structure**:
```
silver/house/financial/
├── filings/
│   └── year=2025/
│       └── part-0000.parquet
├── documents/
│   └── year=2025/
│       └── part-0000.parquet
├── text/
│   └── extraction_method=direct_text/
│       └── year=2025/
│           └── doc_id=8221216/
│               └── raw_text.txt.gz
└── objects/
    └── filing_type=type_p/
        └── year=2025/
            └── doc_id=20033421.json
```

**Tables**:
- `filings/`: Filing metadata from XML
- `documents/`: PDF metadata + extraction status
- `text/`: Extracted text (gzipped)
- `objects/`: Structured JSON by filing type

**Format**: Parquet (Snappy compression) + gzipped text

**Partitioning**: By year

## Gold Layer

**Purpose**: Query-optimized, aggregated data for end users

**Location**: `s3://congress-disclosures-standardized/gold/house/financial/`

**Structure**:
```
gold/house/financial/
├── dimensions/
│   ├── dim_members/
│   ├── dim_assets/
│   ├── dim_date/
│   └── dim_filing_types/
├── facts/
│   ├── fact_ptr_transactions/
│   └── fact_filings/
└── aggregates/
    ├── agg_trending_stocks/
    ├── agg_member_trading_stats/
    ├── agg_document_quality/
    └── agg_network_graph/
```

**Dimensions** (SCD Type 2):
- `dim_members`: Member info, bioguide IDs
- `dim_assets`: Asset names, tickers
- `dim_date`: Date dimension
- `dim_filing_types`: Filing type reference

**Facts** (Star Schema):
- `fact_ptr_transactions`: All PTR transactions
- `fact_filings`: All filing metadata

**Aggregates** (Pre-computed):
- `agg_trending_stocks`: 7d, 30d, 90d windows
- `agg_member_trading_stats`: Trading metrics
- `agg_document_quality`: PDF quality scores
- `agg_network_graph`: Member-asset networks

## Data Flow Between Layers

```
Bronze → Silver → Gold

Raw     Normalized    Aggregated
PDFs    Parquet       Star Schema
```

**Bronze → Silver**:
- Extract text from PDFs
- Parse XML index
- Validate schema
- Write Parquet

**Silver → Gold**:
- Build dimensions (SCD Type 2)
- Build facts (star schema)
- Compute aggregates
- Validate referential integrity

## See Also

- [[Medallion-Architecture]] - Architecture overview
- [[Data-Schemas]] - Detailed schemas
- [[System-Architecture]] - Technical architecture
