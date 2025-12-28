# Congress Disclosures Standardized

A robust, serverless data pipeline for ingesting, extracting, and analyzing US Congress financial disclosures.

## 🚀 Getting Started

### Prerequisites
- **Python 3.11+**
- **Terraform**
- **AWS CLI** (configured with credentials)
- **Make**

### Quick Start (Fresh Install)

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/Jakeintech/congress-disclosures-standardized.git
    cd congress-disclosures-standardized
    ```

2.  **Setup Environment**:
    ```bash
    make setup
    # Edit .env with your specific configuration if needed
    ```

3.  **Deploy Infrastructure**:
    ```bash
    make init
    make deploy
    ```

4.  **Run Pipeline (Ingest & Process)**:
    ```bash
    make run-pipeline
    ```

5.  **View Website**:
    ```bash
    make deploy-website
    # URL will be printed in the output
    ```

## 📊 Project Management

We use an agile workflow managed through GitHub.

- **Agile Board**: [Congress Disclosures Agile Board](https://github.com/users/Jakeintech/projects)
- **Current Sprint**: [Sprint 3: Integration](docs/agile/sprints/SPRINT_3_PLAN.md)
- **Roadmap**: [Visual Roadmap](docs/agile/ROADMAP.md)
- **Issues & Backlog**: [GitHub Issues](https://github.com/Jakeintech/congress-disclosures-standardized/issues)

## 🤖 AI Agent Quick Start

If you are an AI agent onboarding to this project:

1.  **Onboarding**: See [.github/AGENT_ONBOARDING.md](.github/AGENT_ONBOARDING.md)
2.  **Workflow**: Follow the [.github/AI_AGENT_WORKFLOW.md](.github/AI_AGENT_WORKFLOW.md)
3.  **Task Template**: Use [.github/AI_AGENT_TASK_TEMPLATE.md](.github/AI_AGENT_TASK_TEMPLATE.md)
4.  **Reference**: Check the [.github/QUICK_REFERENCE.md](.github/QUICK_REFERENCE.md)

## 🛠️ Pipeline Operations

The pipeline is orchestrated by `scripts/run_smart_pipeline.py` and supports several modes:

*   **Full Reset**: `make reset-and-run-all`
    *   Deploys Infra -> Wipes Data -> Ingests -> Extracts -> Aggregates -> Deploys Website.
    *   *Use with caution!*

*   **Daily Update**:
    *   Run automatically via GitHub Actions (`daily_incremental.yml`).
    *   Manually: `python3 scripts/run_smart_pipeline.py --mode incremental`

*   **Reprocess Existing Data**:
    *   `python3 scripts/run_smart_pipeline.py --mode reprocess`

## 🏗️ Architecture

*   **Bronze Layer**: Raw Zips and PDFs from House Clerk.
*   **Silver Layer**: Extracted text and structured JSON (Parquet).
*   **Gold Layer**: Aggregated facts, stats, and network graphs (Parquet/JSON).
*   **Orchestration**: Python script + AWS Lambda + SQS (Sequential execution).

### Data Medallion ERD

```mermaid
erDiagram
    %% ═══════════════════════════════════════════════════════════════
    %% BRONZE LAYER - Raw/Immutable Data
    %% ═══════════════════════════════════════════════════════════════
    
    BRONZE_RAW_ZIP {
        string s3_key PK "bronze/.../raw_zip/YYYYFD.zip"
        string year
        string sha256
        timestamp download_ts
    }
    
    BRONZE_INDEX_XML {
        string s3_key PK "bronze/.../index/YYYYFD.xml"
        string year
        int filing_count
    }
    
    BRONZE_PDF {
        string doc_id PK
        string s3_key "bronze/.../pdfs/{doc_id}.pdf"
        string year
        string filing_type "P,A,T,X,D,W..."
        string member_name
        string state_district
        float quality_score
        string extraction_method
        boolean extraction_processed
    }
    
    BRONZE_CONGRESS_MEMBER {
        string bioguide_id PK
        string chamber "house|senate"
        date ingest_date
        string s3_key "bronze/congress/member/..."
    }
    
    BRONZE_CONGRESS_BILL {
        string bill_id PK "{congress}-{type}-{number}"
        int congress
        string bill_type "hr,s,hjres..."
        date ingest_date
    }
    
    BRONZE_CONGRESS_VOTE {
        string vote_id PK "{congress}-{session}-{roll}"
        int congress
        int session
        date ingest_date
    }

    %% ═══════════════════════════════════════════════════════════════
    %% SILVER LAYER - Normalized/Queryable
    %% ═══════════════════════════════════════════════════════════════
    
    SILVER_FILINGS {
        string doc_id PK
        int year
        date filing_date
        string filing_type
        string first_name
        string last_name
        string state_district
        string pdf_s3_key FK
        timestamp silver_ingest_ts
    }
    
    SILVER_DOCUMENTS {
        string doc_id PK
        int year
        string pdf_sha256
        bigint pdf_file_size
        int pages
        boolean has_embedded_text
        string extraction_method "pypdf|ocr|textract"
        string extraction_status "pending|success|failed"
        string text_s3_key
    }
    
    SILVER_TEXT {
        string doc_id PK
        int year
        string extraction_method "direct_text|ocr"
        string text_s3_key "silver/.../text/*.txt.gz"
    }
    
    SILVER_OBJECTS_PTR {
        string doc_id PK
        int year
        json transactions "Schedule B transactions"
        float confidence_score
        float completeness_pct
    }
    
    SILVER_OBJECTS_ANNUAL {
        string doc_id PK
        int year
        json assets "Schedule A"
        json income "Schedule B"
        json liabilities "Schedule C"
    }
    
    SILVER_DIM_MEMBER {
        string member_sk PK "UUID surrogate"
        string bioguide_id NK
        string first_name
        string last_name
        string party "R|D|I"
        string state
        int district
        string chamber
        date effective_date
        date end_date
        boolean is_current
    }
    
    SILVER_DIM_BILL {
        string bill_id PK "{congress}-{type}-{number}"
        int congress
        string bill_type
        string title
        date introduced_date
        string sponsor_bioguide_id FK
        string policy_area
    }
    
    SILVER_BILL_COSPONSORS {
        string bill_id PK,FK
        string cosponsor_bioguide_id PK,FK
        date sponsorship_date
        boolean is_original_cosponsor
    }
    
    SILVER_VOTE_MEMBERS {
        string vote_id PK,FK
        string bioguide_id PK,FK
        string vote_cast "Yea|Nay|Present|Not Voting"
        date vote_date
    }

    %% ═══════════════════════════════════════════════════════════════
    %% GOLD LAYER - Analytics/Query-Facing
    %% ═══════════════════════════════════════════════════════════════
    
    GOLD_DIM_MEMBERS {
        int member_key PK "Surrogate"
        string bioguide_id NK
        string full_name
        string party
        string state_district
        string chamber
        boolean is_current
        date effective_from
        date effective_to
        int version "SCD Type 2"
    }
    
    GOLD_DIM_ASSETS {
        int asset_key PK
        string asset_name
        string ticker_symbol
        string asset_type "Stock|Bond|Crypto|Fund"
        string sector
        string industry
        boolean is_publicly_traded
        int occurrence_count
    }
    
    GOLD_DIM_FILING_TYPES {
        int filing_type_key PK
        string filing_type_code "P|A|T|X|D|W"
        string filing_type_name
        boolean is_transaction_report
    }
    
    GOLD_DIM_DATE {
        int date_key PK "YYYYMMDD"
        date full_date
        int year
        int quarter
        int month
        int congressional_session
    }
    
    GOLD_FACT_PTR_TRANSACTIONS {
        bigint transaction_key PK
        int member_key FK
        int asset_key FK
        int filing_type_key FK
        int transaction_date_key FK
        string doc_id
        string transaction_type "Purchase|Sale|Exchange"
        bigint amount_low
        bigint amount_high
        int days_to_filing
        boolean is_late_filing
        float extraction_confidence
    }
    
    GOLD_FACT_FILINGS {
        bigint filing_key PK
        int member_key FK
        int filing_type_key FK
        int filing_date_key FK
        string doc_id
        int transaction_count
        int asset_count
        boolean is_timely_filed
        float overall_confidence
    }
    
    GOLD_AGG_MEMBER_STATS {
        int member_key FK
        date period_start
        int total_transactions
        int unique_assets_traded
        float avg_days_to_filing
        int late_filing_count
        float concentration_score
    }
    
    GOLD_AGG_TRENDING_STOCKS {
        int date_key FK
        int asset_key FK
        int transactions_last_7d
        int unique_members_last_7d
        float buy_sell_ratio
        boolean is_trending_buy
    }
    
    GOLD_AGG_DOCUMENT_QUALITY {
        int member_key FK
        date period_start
        int total_filings
        float image_pdf_pct
        float avg_confidence_score
        float quality_score
        string quality_category "Excellent|Good|Fair|Poor"
    }
    
    GOLD_AGG_NETWORK_GRAPH {
        int member_key FK
        int asset_key FK
        int transaction_count
        bigint total_volume_low
        date last_transaction
    }

    %% ═══════════════════════════════════════════════════════════════
    %% RELATIONSHIPS
    %% ═══════════════════════════════════════════════════════════════
    
    %% Bronze to Silver
    BRONZE_RAW_ZIP ||--o{ BRONZE_INDEX_XML : "extracts"
    BRONZE_INDEX_XML ||--o{ BRONZE_PDF : "lists"
    BRONZE_PDF ||--|| SILVER_FILINGS : "normalizes"
    BRONZE_PDF ||--|| SILVER_DOCUMENTS : "metadata"
    SILVER_DOCUMENTS ||--|| SILVER_TEXT : "extracts"
    SILVER_TEXT ||--o| SILVER_OBJECTS_PTR : "structures"
    SILVER_TEXT ||--o| SILVER_OBJECTS_ANNUAL : "structures"
    
    %% Bronze Congress to Silver
    BRONZE_CONGRESS_MEMBER ||--|| SILVER_DIM_MEMBER : "normalizes"
    BRONZE_CONGRESS_BILL ||--|| SILVER_DIM_BILL : "normalizes"
    BRONZE_CONGRESS_BILL ||--o{ SILVER_BILL_COSPONSORS : "has"
    BRONZE_CONGRESS_VOTE ||--o{ SILVER_VOTE_MEMBERS : "records"
    SILVER_DIM_MEMBER ||--o{ SILVER_BILL_COSPONSORS : "cosponsors"
    SILVER_DIM_MEMBER ||--o{ SILVER_VOTE_MEMBERS : "votes"
    
    %% Silver to Gold Dimensions
    SILVER_FILINGS ||--|| GOLD_DIM_MEMBERS : "enriches"
    SILVER_DIM_MEMBER ||--|| GOLD_DIM_MEMBERS : "merges"
    SILVER_OBJECTS_PTR ||--o{ GOLD_DIM_ASSETS : "creates"
    
    %% Gold Fact Tables
    GOLD_DIM_MEMBERS ||--o{ GOLD_FACT_PTR_TRANSACTIONS : "trades"
    GOLD_DIM_ASSETS ||--o{ GOLD_FACT_PTR_TRANSACTIONS : "traded"
    GOLD_DIM_FILING_TYPES ||--o{ GOLD_FACT_PTR_TRANSACTIONS : "classifies"
    GOLD_DIM_DATE ||--o{ GOLD_FACT_PTR_TRANSACTIONS : "when"
    
    GOLD_DIM_MEMBERS ||--o{ GOLD_FACT_FILINGS : "files"
    GOLD_DIM_FILING_TYPES ||--o{ GOLD_FACT_FILINGS : "type"
    GOLD_DIM_DATE ||--o{ GOLD_FACT_FILINGS : "filed_on"
    
    %% Gold Aggregates
    GOLD_FACT_PTR_TRANSACTIONS ||--o{ GOLD_AGG_MEMBER_STATS : "aggregates"
    GOLD_FACT_PTR_TRANSACTIONS ||--o{ GOLD_AGG_TRENDING_STOCKS : "aggregates"
    GOLD_FACT_FILINGS ||--o{ GOLD_AGG_DOCUMENT_QUALITY : "aggregates"
    GOLD_FACT_PTR_TRANSACTIONS ||--o{ GOLD_AGG_NETWORK_GRAPH : "builds"
```

### Data Flow

```
House Clerk ZIP → Bronze PDFs → Silver Text → Silver Structured → Gold Facts/Aggregates
Congress.gov API → Bronze JSON → Silver Dims → Gold Member Enrichment
```

## 🤝 Contributing

We welcome contributions! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on branch naming, commit messages, and our AI agent workflow.

1.  Run checks before committing:
    ```bash
    make check-contrib
    ```
