# State Machine Flow - Congress Disclosures Pipeline

## Overview
This document visualizes the Step Functions state machine orchestration for the House Financial Disclosures pipeline.

## House FD Pipeline State Machine

```mermaid
flowchart TD
    Start([Start Execution]) --> CheckUpdates[Check For New Filings<br/>Lambda: check_house_fd_updates]
    
    CheckUpdates --> IngestZip[Ingest ZIP File<br/>Lambda: ingest_zip<br/>Timeout: 600s]
    
    IngestZip --> IndexSilver[Index to Silver<br/>Lambda: index_to_silver<br/>Parse XML index]
    
    IndexSilver --> ExtractMap{Map State<br/>Extract Documents<br/>MaxConcurrency: 10}
    
    ExtractMap --> ExtractDoc[Extract Document<br/>Lambda: extract_document<br/>pypdf/OCR]
    
    ExtractDoc --> ExtractStructured[Extract Structured<br/>Lambda: extract_structured<br/>Code-based extraction]
    
    ExtractStructured --> WaitExtract[Wait 10s<br/>S3 consistency]
    
    WaitExtract --> ValidateSilver[Validate Silver Quality<br/>Lambda: run_soda_checks<br/>silver_transactions.yml]
    
    ValidateSilver -->|Pass| GoldParallel{Parallel State<br/>Build Gold Layer}
    ValidateSilver -->|Fail| NotifyQuality[Notify Quality Failure<br/>SNS Alert]
    
    GoldParallel --> DimMembers[Build dim_members<br/>SCD Type 2]
    GoldParallel --> DimAssets[Build dim_assets]
    GoldParallel --> FactTrans[Build fact_transactions]
    GoldParallel --> FactFilings[Build fact_filings]
    
    DimMembers --> ValidateGold[Validate Gold Quality<br/>Lambda: run_soda_checks<br/>gold_fact_transactions.yml]
    DimAssets --> ValidateGold
    FactTrans --> ValidateGold
    FactFilings --> ValidateGold
    
    ValidateGold -->|Pass| AggParallel{Parallel State<br/>Compute Aggregates}
    ValidateGold -->|Fail| NotifyQuality
    
    AggParallel --> TrendingStocks[Compute Trending Stocks<br/>7d, 30d, 90d windows]
    AggParallel --> MemberStats[Compute Member Stats]
    AggParallel --> DocQuality[Compute Document Quality]
    AggParallel --> NetworkGraph[Compute Network Graph]
    
    TrendingStocks --> UpdateCache[Update API Cache<br/>Pre-compute JSON responses]
    MemberStats --> UpdateCache
    DocQuality --> UpdateCache
    NetworkGraph --> UpdateCache
    
    UpdateCache --> TriggerCorrelation[Trigger Correlation Pipeline<br/>Sync execution]
    
    TriggerCorrelation --> PublishMetrics[Publish Metrics<br/>CloudWatch custom metrics]
    
    PublishMetrics --> Success([Pipeline Success])
    
    NotifyQuality --> QualityFail([Quality Check Failed])
    
    CheckUpdates -->|Error| NotifyFailure[Notify Pipeline Failure<br/>SNS Alert]
    IngestZip -->|Error| NotifyFailure
    IndexSilver -->|Error| NotifyFailure
    ExtractMap -->|Error| NotifyFailure
    GoldParallel -->|Error| NotifyFailure
    AggParallel -->|Error| NotifyFailure
    
    NotifyFailure --> PipelineFail([Pipeline Failed])
    
    style Success fill:#6bcf7f
    style QualityFail fill:#ffd93d
    style PipelineFail fill:#ff6b6b
    style ExtractMap fill:#a8dadc
    style GoldParallel fill:#a8dadc
    style AggParallel fill:#a8dadc
```

## Congress.gov Pipeline State Machine

```mermaid
flowchart TD
    Start([Start Execution]) --> CheckCongress[Check Congress Updates<br/>Lambda: check_congress_updates<br/>DynamoDB watermarking]
    
    CheckCongress -->|New Data| FetchBills[Fetch Bills<br/>Congress.gov API<br/>fromDateTime parameter]
    CheckCongress -->|No New Data| End([No Action Needed])
    
    FetchBills --> FetchMembers[Fetch Members<br/>Congress.gov API]
    
    FetchMembers --> FetchDetails[Fetch Bill Details<br/>Parallel processing]
    
    FetchDetails --> WriteSilver[Write to Silver<br/>Parquet tables]
    
    WriteSilver --> ValidateQuality[Validate Silver Quality<br/>Soda checks]
    
    ValidateQuality -->|Pass| BuildGold[Build Gold Layer<br/>Dimensions + Facts]
    ValidateQuality -->|Fail| NotifyQuality[Quality Alert]
    
    BuildGold --> Success([Pipeline Success])
    NotifyQuality --> Fail([Quality Failed])
    
    style Success fill:#6bcf7f
    style Fail fill:#ff6b6b
```

## Lobbying Pipeline State Machine

```mermaid
flowchart TD
    Start([Start Execution]) --> CheckLobbying[Check Lobbying Updates<br/>Lambda: check_lobbying_updates<br/>S3 existence check]
    
    CheckLobbying -->|New Quarters| DownloadMap{Map State<br/>Download XML Files<br/>MaxConcurrency: 10}
    CheckLobbying -->|No New Data| End([No Action Needed])
    
    DownloadMap --> DownloadXML[Download XML<br/>Senate LDA database]
    
    DownloadXML --> ParseSilver[Parse XML to Silver<br/>Parquet tables]
    
    ParseSilver --> ValidateQuality[Validate Silver Quality<br/>Soda checks]
    
    ValidateQuality -->|Pass| BuildGold[Build Gold Layer<br/>fact_lobbying]
    ValidateQuality -->|Fail| NotifyQuality[Quality Alert]
    
    BuildGold --> ValidateGoldQuality[Validate Gold Quality]
    
    ValidateGoldQuality -->|Pass| ComputeAgg[Compute Lobbying Aggregates]
    ValidateGoldQuality -->|Fail| NotifyQuality
    
    ComputeAgg --> PublishMetrics[Publish Metrics]
    
    PublishMetrics --> Success([Pipeline Success])
    NotifyQuality --> Fail([Quality Failed])
    
    style Success fill:#6bcf7f
    style Fail fill:#ff6b6b
    style DownloadMap fill:#a8dadc
```

## Key Features

### Parallel Processing
- **Map States**: Process multiple documents/files concurrently
- **Parallel States**: Build multiple Gold tables simultaneously
- **MaxConcurrency**: 10 (prevents Lambda throttling)

### Error Handling
- **Retry Logic**: Exponential backoff on transient errors
- **Catch Blocks**: Graceful failure handling
- **SNS Alerts**: Immediate notification on failures

### Quality Gates
- **Silver Validation**: Schema, completeness, freshness checks
- **Gold Validation**: Referential integrity, business rules
- **Soda Integration**: YAML-defined quality checks

### Watermarking
- **House FD**: SHA256 hash comparison
- **Congress**: DynamoDB timestamp tracking
- **Lobbying**: S3 object existence checking

## Execution Patterns

### Scheduled Execution
```json
{
  "execution_type": "scheduled",
  "year": 2025
}
```

### Manual Execution
```json
{
  "execution_type": "manual",
  "year": 2024,
  "force_refresh": true
}
```

### Multi-Year Initial Load
```json
{
  "execution_type": "initial_load",
  "parameters": {
    "years": [2020, 2021, 2022, 2023, 2024, 2025]
  }
}
```

## Monitoring

- **CloudWatch Logs**: All Lambda executions logged
- **X-Ray Tracing**: Distributed tracing enabled
- **Step Functions Console**: Visual execution history
- **Custom Metrics**: Pipeline duration, success rate, data volume

## State Machine ARNs

- **House FD**: `arn:aws:states:us-east-1:ACCOUNT_ID:stateMachine:congress-disclosures-house-fd-pipeline`
- **Congress**: `arn:aws:states:us-east-1:ACCOUNT_ID:stateMachine:congress-disclosures-congress-pipeline`
- **Lobbying**: `arn:aws:states:us-east-1:ACCOUNT_ID:stateMachine:congress-disclosures-lobbying-pipeline`
- **Correlation**: `arn:aws:states:us-east-1:ACCOUNT_ID:stateMachine:congress-disclosures-cross-dataset-correlation`
