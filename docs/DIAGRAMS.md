# System Diagrams

Comprehensive visual documentation of the Congress Financial Disclosures pipeline architecture, data flow, and relationships.

---

## System Architecture Overview

```mermaid
graph TB
    subgraph "External"
        HC[House Clerk Website<br/>disclosures-clerk.house.gov]
    end

    subgraph "AWS Infrastructure"
        subgraph "Ingestion Layer"
            EB[EventBridge<br/>Cron Trigger]
            L1[Lambda: ingest_zip<br/>1024 MB, 5 min]
            L2[Lambda: index_to_silver<br/>512 MB, 2 min]
            L3[Lambda: extract_document<br/>2048 MB, 5 min]
            SQS[SQS Queue<br/>Extraction Jobs<br/>6 min visibility]
            DLQ[Dead Letter Queue<br/>After 3 retries]
        end

        subgraph "Storage: S3 Data Lake"
            direction TB
            Bronze[Bronze Layer<br/>Raw zip, XML, PDFs<br/>Versioned]
            Silver[Silver Layer<br/>Parquet tables<br/>Extracted text gzipped]
            Gold[Gold Layer<br/>Query-facing datasets<br/>Phase 2]
        end

        subgraph "Monitoring & Alerts"
            CW[CloudWatch<br/>Logs & Metrics<br/>30-day retention]
            SNS[SNS Topics<br/>Email Alerts]
            Dashboard[CloudWatch Dashboard<br/>Real-time metrics]
        end

        subgraph "External Services"
            TX[AWS Textract<br/>OCR Service<br/>DetectDocumentText]
        end
    end

    HC -->|HTTPS GET| L1
    EB -->|Cron: 0 2 * * *| L1
    L1 -->|Upload raw files| Bronze
    L1 -->|Synchronous invoke| L2
    L1 -->|Send batch of 10| SQS
    L2 -->|Read XML| Bronze
    L2 -->|Write Parquet| Silver
    SQS -->|Poll batch| L3
    L3 -->|Read PDF| Bronze
    L3 -->|OCR if image-based| TX
    TX -->|Return text| L3
    L3 -->|Write gzipped text| Silver
    L3 -->|Update metadata| Silver
    L3 -->|Max retries exceeded| DLQ
    L1 --> CW
    L2 --> CW
    L3 --> CW
    CW -->|Threshold breach| SNS
    SNS -->|Email| Dashboard
    Silver -->|Transform Phase 2| Gold

    style Bronze fill:#d4a373,color:#000
    style Silver fill:#c0c0c0,color:#000
    style Gold fill:#ffd700,color:#000
    style L1 fill:#4CAF50,color:#fff
    style L2 fill:#4CAF50,color:#fff
    style L3 fill:#4CAF50,color:#fff
    style SQS fill:#FF9900,color:#fff
    style TX fill:#FF9900,color:#fff
    style DLQ fill:#f44336,color:#fff
```

---

## Sequence Diagram: Complete Ingestion Flow

```mermaid
sequenceDiagram
    actor User
    participant EB as EventBridge
    participant L1 as Lambda:<br/>ingest_zip
    participant HC as House Clerk<br/>Website
    participant S3B as S3 Bronze
    participant L2 as Lambda:<br/>index_to_silver
    participant SQS as SQS Queue
    participant L3 as Lambda:<br/>extract_document
    participant TX as AWS Textract
    participant S3S as S3 Silver
    participant CW as CloudWatch

    Note over User,CW: Ingestion for year 2025

    User->>L1: Invoke lambda_handler({"year": 2025})
    activate L1
    L1->>CW: Log: Starting ingestion for year 2025

    L1->>HC: GET /2025FD.zip
    activate HC
    HC-->>L1: ZIP file (100-500 MB)
    deactivate HC

    L1->>S3B: PUT bronze/.../2025FD.zip
    L1->>S3B: PUT bronze/.../2025FD.xml
    L1->>S3B: PUT bronze/.../2025FD.txt

    loop For each PDF in ZIP (5k-15k files)
        L1->>S3B: PUT bronze/.../pdfs/2025/{DocID}.pdf
        L1->>SQS: SendMessage(doc_id, year, s3_key)
    end

    L1->>L2: Invoke (synchronous)
    activate L2
    L2->>S3B: GET bronze/.../2025FD.xml
    S3B-->>L2: XML content

    L2->>L2: Parse XML<br/>Extract all <Member> records

    L2->>S3S: PUT silver/.../filings/year=2025/part-0000.parquet
    L2->>S3S: PUT silver/.../documents/year=2025/part-0000.parquet
    L2->>CW: Log: Wrote N filings

    L2-->>L1: Success: {"filings_written": N}
    deactivate L2

    L1->>CW: Log: Ingestion complete
    L1-->>User: {"status": "success", "pdfs_queued": N}
    deactivate L1

    Note over SQS,L3: PDF Extraction (Parallel, max 10 concurrent)

    loop Until queue empty
        SQS->>L3: Poll messages (batch of 10)
        activate L3

        L3->>S3B: GET bronze/.../pdfs/2025/{DocID}.pdf
        S3B-->>L3: PDF bytes

        L3->>L3: Detect text layer<br/>using pypdf

        alt PDF has embedded text
            L3->>L3: Extract with pypdf<br/>(fast, free)
        else PDF is image-based
            L3->>TX: DetectDocumentText(PDF bytes)
            activate TX
            TX-->>L3: Extracted text blocks
            deactivate TX
        end

        L3->>S3S: PUT silver/.../text/year=2025/doc_id={DocID}/raw_text.txt.gz
        L3->>S3S: UPDATE silver/.../documents/.../part-0000.parquet
        L3->>SQS: DeleteMessage(receipt_handle)
        L3->>CW: Log: Extraction success
        deactivate L3
    end

    Note over DLQ: Failed messages after 3 retries<br/>go to Dead Letter Queue
```

---

## Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    BRONZE_ZIP ||--o{ BRONZE_PDF : contains
    BRONZE_ZIP ||--|| BRONZE_INDEX : contains
    BRONZE_INDEX ||--o{ SILVER_FILINGS : "parses to"
    BRONZE_PDF ||--|| SILVER_DOCUMENTS : "has metadata"
    BRONZE_PDF ||--|| SILVER_TEXT : "extracts to"
    SILVER_FILINGS ||--|| SILVER_DOCUMENTS : references
    SILVER_FILINGS }o--|| GOLD_FILINGS_FLAT : "denormalizes to (Phase 2)"
    SILVER_DOCUMENTS }o--|| GOLD_FILINGS_FLAT : "enriches (Phase 2)"
    SILVER_TEXT }o--|| GOLD_STRUCTURED : "parsed to (Phase 2)"

    BRONZE_ZIP {
        int year PK
        blob zip_content
        string source_url
        datetime download_timestamp
        string http_etag
        int size_bytes
    }

    BRONZE_INDEX {
        int year PK
        blob xml_content
        blob txt_content
        int record_count
    }

    BRONZE_PDF {
        string doc_id PK
        int year PK
        blob pdf_content
        string s3_key UK
        int file_size_bytes
    }

    SILVER_FILINGS {
        string doc_id PK
        int year PK
        date filing_date
        string filing_type
        string prefix
        string first_name
        string last_name
        string suffix
        string state_district
        string pdf_s3_key FK
        datetime silver_ingest_ts
    }

    SILVER_DOCUMENTS {
        string doc_id PK
        int year PK
        string pdf_sha256 UK
        int pdf_file_size_bytes
        int pages
        bool has_embedded_text
        string extraction_method
        string extraction_status
        string extraction_version
        datetime extraction_timestamp
        string text_s3_key FK
        int char_count
    }

    SILVER_TEXT {
        string doc_id PK
        int year PK
        blob text_gzipped
        int original_size_bytes
        int compressed_size_bytes
        float compression_ratio
    }

    GOLD_FILINGS_FLAT {
        string doc_id PK
        int year
        string member_display_name
        string state
        int district
        date filing_date
        string report_type_label
        int pages
        string extraction_method
        bool has_transactions
        bool has_assets
    }

    GOLD_STRUCTURED {
        string doc_id PK
        int year
        json assets
        json transactions
        json liabilities
        json positions
        string extraction_model
        float confidence_score
    }
```

---

## State Machine: PDF Extraction Process

```mermaid
stateDiagram-v2
    [*] --> Queued: SQS message sent
    Queued --> Downloaded: Lambda polls
    Downloaded --> InspectPDF: Read file
    InspectPDF --> HasText: Check text layer
    InspectPDF --> IsImage: No text layer

    HasText --> ExtractPyPDF: pypdf extraction
    ExtractPyPDF --> ValidateText: Check char count
    ValidateText --> UploadText: >100 chars
    ValidateText --> IsImage: <100 chars (fallback)

    IsImage --> EstimatePages: Check file size
    EstimatePages --> TextractSync: ≤10 pages
    EstimatePages --> TextractAsync: >10 pages

    TextractSync --> ParseResponse: API call
    TextractAsync --> PollJob: Start job
    PollJob --> PollJob: Wait 5s (retry)
    PollJob --> ParseResponse: Job complete
    PollJob --> Failed: Timeout (5 min)

    ParseResponse --> UploadText: Success
    ParseResponse --> Failed: Parse error

    UploadText --> CompressText: gzip
    CompressText --> S3Upload: Upload to silver
    S3Upload --> UpdateMetadata: Update Parquet
    UpdateMetadata --> DeleteMessage: Remove from SQS
    DeleteMessage --> Complete: Success

    Failed --> RetryCheck: Check attempt count
    RetryCheck --> Queued: <3 attempts
    RetryCheck --> DLQ: ≥3 attempts
    DLQ --> [*]
    Complete --> [*]

    note right of HasText
        Decision Point:
        - Text-based: pypdf (free, fast)
        - Image-based: Textract ($0.0015/page)
    end note

    note right of TextractSync
        Textract limits:
        - Sync: ≤10 pages, <5 MB
        - Async: Any size, S3 required
    end note

    note right of UpdateMetadata
        Records updated:
        - extraction_status
        - extraction_method
        - text_s3_key
        - char_count
        - duration_seconds
    end note
```

---

## Data Lineage Flowchart

```mermaid
flowchart LR
    subgraph Sources
        HC[House Clerk Website<br/>disclosures-clerk.house.gov]
    end

    subgraph Bronze[Bronze Layer - Raw Data]
        BZ[2025FD.zip]
        BX[2025FD.xml]
        BP[8221216.pdf]
    end

    subgraph Silver[Silver Layer - Normalized]
        SF[house_fd_filings<br/>Parquet]
        SD[house_fd_documents<br/>Parquet]
        ST[raw_text.txt.gz]
    end

    subgraph Gold[Gold Layer - Query-Facing]
        GF[filings_flat<br/>Parquet]
        GA[assets<br/>Parquet]
        GT[transactions<br/>Parquet]
    end

    subgraph Consumers
        API[REST API]
        WEB[Web Dashboard]
        RES[Researchers]
    end

    HC -->|Download| BZ
    BZ -->|Extract| BX
    BZ -->|Extract| BP

    BX -->|Parse XML| SF
    BP -->|Extract Text| ST
    BP -->|Get Metadata| SD

    SF --> GF
    SD --> GF
    ST --> GA
    ST --> GT

    GF --> API
    GF --> WEB
    GA --> API
    GT --> API
    GF --> RES
    GA --> RES
    GT --> RES

    style HC fill:#3498db,color:#fff
    style BZ fill:#d4a373,color:#000
    style BX fill:#d4a373,color:#000
    style BP fill:#d4a373,color:#000
    style SF fill:#c0c0c0,color:#000
    style SD fill:#c0c0c0,color:#000
    style ST fill:#c0c0c0,color:#000
    style GF fill:#ffd700,color:#000
    style GA fill:#ffd700,color:#000
    style GT fill:#ffd700,color:#000
```

---

## Cost Optimization Decision Tree

```mermaid
graph TD
    Start[PDF Document] --> CheckText{Has<br/>Text Layer?}

    CheckText -->|Yes| UsePyPDF[Use pypdf<br/>Cost: $0<br/>Speed: 0.5-2s]
    CheckText -->|No| CheckSize{Estimate<br/>Page Count}

    UsePyPDF --> Success[Extract Complete]

    CheckSize -->|≤10 pages| UseTextractSync[Textract Sync<br/>Cost: $0.015<br/>Speed: 5-10s]
    CheckSize -->|>10 pages| CheckVolume{Monthly<br/>Volume?}

    UseTextractSync --> Success

    CheckVolume -->|Low<br/><1000 pages| UseTextractAsync[Textract Async<br/>Cost: $0.015/page<br/>Speed: 30-60s]
    CheckVolume -->|High<br/>>1000 pages| ConsiderTesseract{Budget<br/>Constraint?}

    UseTextractAsync --> Success

    ConsiderTesseract -->|Yes| UseTesseract[Tesseract OCR<br/>Cost: $0<br/>Speed: 10-30s<br/>Accuracy: Lower]
    ConsiderTesseract -->|No| UseTextractAsync

    UseTesseract --> Success

    Success --> Store[Store in<br/>Silver Layer<br/>gzip compressed]

    style UsePyPDF fill:#4CAF50,color:#fff
    style UseTextractSync fill:#FFC107,color:#000
    style UseTextractAsync fill:#FF9800,color:#fff
    style UseTesseract fill:#9E9E9E,color:#fff
    style Success fill:#2196F3,color:#fff
```

---

## Deployment Architecture

```mermaid
C4Context
    title System Context Diagram for Congress Disclosures Pipeline

    Person(user, "User", "Researcher, journalist, or developer")
    Person(admin, "Administrator", "Manages infrastructure")

    System(pipeline, "Congress Disclosures Pipeline", "Ingests and processes House financial disclosures")

    System_Ext(house, "House Clerk Website", "Source of financial disclosure data")
    System_Ext(textract, "AWS Textract", "OCR service for image-based PDFs")

    Rel(user, pipeline, "Queries data via", "S3/API")
    Rel(admin, pipeline, "Deploys and monitors", "Terraform/AWS Console")
    Rel(pipeline, house, "Downloads disclosures from", "HTTPS")
    Rel(pipeline, textract, "OCR requests", "AWS SDK")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

---

## Monitoring & Alerting Flow

```mermaid
graph TB
    subgraph Lambdas
        L1[ingest_zip]
        L2[index_to_silver]
        L3[extract_document]
    end

    subgraph Metrics
        M1[Invocations]
        M2[Errors]
        M3[Duration]
        M4[Throttles]
        M5[Concurrent Executions]
    end

    subgraph Alarms
        A1[Error Rate > 5%]
        A2[Duration > 2 min avg]
        A3[Throttles > 5/min]
        A4[DLQ Messages > 0]
    end

    subgraph Actions
        SNS[SNS Topic]
        Email[Email Alert]
        Dashboard[CloudWatch Dashboard]
    end

    L1 --> M1
    L1 --> M2
    L1 --> M3
    L2 --> M1
    L2 --> M2
    L2 --> M3
    L3 --> M1
    L3 --> M2
    L3 --> M3
    L3 --> M4
    L3 --> M5

    M2 --> A1
    M3 --> A2
    M4 --> A3
    DLQ[SQS DLQ] --> A4

    A1 --> SNS
    A2 --> SNS
    A3 --> SNS
    A4 --> SNS

    SNS --> Email
    M1 --> Dashboard
    M2 --> Dashboard
    M3 --> Dashboard
    M4 --> Dashboard

    style A1 fill:#f44336,color:#fff
    style A2 fill:#ff9800,color:#fff
    style A3 fill:#ff9800,color:#fff
    style A4 fill:#f44336,color:#fff
```

---

For more details on each component, see:
- [ARCHITECTURE.md](ARCHITECTURE.md): Detailed technical architecture
- [DEPLOYMENT.md](DEPLOYMENT.md): Step-by-step deployment guide
- [API_STRATEGY.md](API_STRATEGY.md): Public API design and rate limiting
