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

## 🤝 Contributing

1.  Run checks before committing:
    ```bash
    make check-contrib
    ```
