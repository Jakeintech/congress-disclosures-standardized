# Data Pipeline Architecture & Flow

## Overview
This document describes the exact pipeline flow from Bronze (PDF ingestion) to Gold (API endpoints), including the schedule extraction logic.

## Architecture Diagram

```mermaid
graph TB
    subgraph Bronze["🥉 Bronze Layer (Raw Data)"]
        PDF[PDFs in S3<br/>bronze/house/financial/year=YYYY/pdfs/]
    end

    subgraph Silver["🥈 Silver Layer (Extracted Data)"]
        TEXT[Text Extraction<br/>silver/.../text/<br/>(Raw Text + Metadata)]
        STRUCT[Structured Extraction<br/>silver/.../structured/<br/>(Full JSON with Schedules A-I)]
    end

    subgraph Gold["🥇 Gold Layer (Aggregated API)"]
        API_B[Schedule B: Transactions<br/>api/v1/schedules/b/transactions.json]
        API_MANIFEST[Document Manifest<br/>api/v1/documents/manifest.json]
    end

    subgraph UI["🌐 UI Layer"]
        WEB[Static Website<br/>Fetches from /api/v1/]
    end

    PDF -->|S3 Event| TEXTRACT_LAMBDA[Textract Lambda]
    TEXTRACT_LAMBDA --> TEXT
    
    TEXT -->|SQS Trigger| STRUCT_LAMBDA[Structured Extraction Lambda]
    STRUCT_LAMBDA --> STRUCT
    
    STRUCT -->|Scheduled/Event| GOLD_LAMBDA[Gold Aggregation Scripts]
    
    GOLD_LAMBDA --> API_B
    GOLD_LAMBDA --> API_MANIFEST
    
    API_B --> WEB
    API_MANIFEST --> WEB
```

## Detailed Data Flow

### 1. Ingestion (Bronze)
- **Source**: House Clerk website
- **Storage**: S3 `bronze/house/financial/year={YYYY}/pdfs/{doc_id}.pdf`
- **Trigger**: S3 Event Notification -> `extract_document` Lambda

### 2. Text Extraction (Silver - Text)
- **Lambda**: `house_fd_extract_document`
- **Process**:
  - Checks for embedded text (pypdf)
  - If image-only, uses AWS Textract (Sync/Async)
- **Output**: 
  - `silver/house/financial/text/.../raw_text.txt.gz`
  - `silver/house/financial/documents/.../metadata.json`

### 3. Structured Extraction (Silver - Structured)
- **Lambda**: `house_fd_extract_structured`
- **Trigger**: SQS `structured-extraction-queue-v2`
- **Process**:
  - Uses AWS Textract `StartDocumentAnalysis` (Tables + Forms)
  - Parses blocks into Schedules A-I
- **Output**: `silver/house/financial/structured/year={YYYY}/doc_id={doc_id}.json`
- **Schema**:
  ```json
  {
    "doc_id": "1234567",
    "year": 2025,
    "schedules": {
      "A": { "type": "Assets", "tables": [...] },
      "B": { "type": "Transactions", "tables": [...] },
      ...
      "I": { "type": "Charity", "tables": [...] }
    }
  }
  ```

### 4. Aggregation (Gold)
- **Scripts**: `aggregate_schedule_b.py`, `rebuild_silver_manifest.py`
- **Process**:
  - Scans DynamoDB / Silver Structured JSONs
  - Flattens hierarchical data into queryable arrays
  - Enriches with member metadata (Name, District, etc.)
- **Output**: Static JSON API endpoints
  - `/api/v1/schedules/b/transactions.json`
  - `/api/v1/documents/manifest.json`

## Schedule Mapping

| Schedule | Description | Extraction Status |
|----------|-------------|-------------------|
| **A** | Assets & Unearned Income | ✅ Supported |
| **B** | Transactions (PTR) | ✅ Supported |
| **C** | Earned Income | ✅ Supported |
| **D** | Liabilities | ✅ Supported |
| **E** | Positions | ✅ Supported |
| **F** | Agreements | ✅ Supported |
| **G** | Gifts | ✅ Supported |
| **H** | Travel Payments | ✅ Supported |
| **I** | Charity Contributions | ✅ Supported |

## API Endpoints

Base URL: `https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/website/api/v1/`

- **Transactions**: `/schedules/b/transactions.json`
- **Manifest**: `/documents/manifest.json`
