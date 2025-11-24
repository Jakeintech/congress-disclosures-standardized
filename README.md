# Congress Financial Disclosures - Standardized Data Pipeline

A transparent, open-source pipeline for converting U.S. House of Representatives financial disclosure reports into structured, queryable data.

## Overview

This project downloads official House financial disclosure PDFs from [disclosures-clerk.house.gov](https://disclosures-clerk.house.gov/FinancialDisclosure), extracts their contents, and stores them in a **medallion architecture data lake** (bronze/silver/gold) on AWS S3.

### Key Features

- **Transparent & reproducible**: Every transformation is auditable with full provenance tracking
- **Legally compliant**: Built for transparency/research/news use per 5 U.S.C. § 13107
- **AWS-native**: Uses Lambda, S3, SQS, and Textract for scalable, cost-effective processing
- **Open source**: MIT licensed, infrastructure-as-code with Terraform

### Current Status: Phase 1 (Bronze + Silver)

**Implemented:**
- Bronze layer: Raw ingestion of zip files, XML/TXT indexes, and PDFs
- Silver layer: Normalized Parquet tables (`house_fd_filings`, `house_fd_documents`, `house_fd_text`)
- PDF text extraction: pypdf for text-based PDFs, AWS Textract for image-based PDFs

**Planned (Phase 2):**
- Gold layer: Cleaned, denormalized query-facing tables
- Structured extraction: Parsing assets, transactions, liabilities into JSON schema
- Member ID crosswalk: Mapping to Congress.gov bioguide IDs
- Public API: Query interface for researchers and journalists

## Architecture

### Data Lake Structure

```
s3://congress-disclosures/
  bronze/house/financial/
    year=2025/
      raw_zip/2025FD.zip
      index/2025FD.xml, 2025FD.txt
      pdfs/2025/{DocID}.pdf

  silver/house/financial/
    filings/year=2025/*.parquet        # Normalized filing metadata
    documents/year=2025/*.parquet      # PDF extraction status
    text/year=2025/doc_id={DocID}/...  # Extracted text

  gold/house/financial/                # (Phase 2)
    filings_flat/*.parquet
    holdings/*.parquet
    transactions/*.parquet
```

### Processing Flow

```
1. house_fd_ingest_zip Lambda
   └─> Downloads YEARFD.zip from House website
   └─> Uploads to S3 bronze layer
   └─> Sends PDF extraction jobs to SQS

2. house_fd_index_to_silver Lambda
   └─> Parses XML index into Parquet table

3. house_fd_extract_document Lambda (triggered by SQS)
   └─> Downloads PDF from S3
   └─> Extracts text (pypdf or Textract)
   └─> Uploads to silver layer
```

## Quick Start

### Prerequisites

- AWS account with credentials configured
- Terraform 1.5+
- Python 3.11+
- Make (optional, for convenience commands)

### Deployment

1. **Clone and navigate to repo**:
   ```bash
   git clone https://github.com/Jakeintech/congress-disclosures-standardized.git
   cd congress-disclosures-standardized
   ```

2. **Configure Terraform variables**:
   ```bash
   cd infra/terraform
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your AWS region, bucket name, etc.
   ```

3. **Deploy infrastructure**:
   ```bash
   make init    # Initialize Terraform
   make plan    # Review changes
   make deploy  # Apply infrastructure
   ```

4. **Trigger ingestion for a year**:
   ```bash
   aws lambda invoke \
     --function-name house-fd-ingest-zip \
     --payload '{"year": 2025}' \
     response.json
   ```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed deployment instructions.

## Legal & Compliance

This project is designed for **transparency, research, and news purposes** in accordance with the Ethics in Government Act.

**Prohibited uses** (per 5 U.S.C. § 13107):
- Commercial purposes (except news/media disseminating to public)
- Determining or establishing credit ratings
- Soliciting money (political, charitable, or otherwise)

See [docs/LEGAL_NOTES.md](docs/LEGAL_NOTES.md) for full legal context.

## Project Structure

```
/
├── infra/terraform/        # Infrastructure-as-code
├── ingestion/
│   ├── lambdas/           # Lambda function handlers
│   ├── lib/               # Shared Python libraries
│   └── schemas/           # JSON schemas for validation
├── tests/                 # Unit and integration tests
├── docs/                  # Documentation
└── .github/workflows/     # CI/CD pipelines
```

## Data Sources

- **House Financial Disclosures**: https://disclosures-clerk.house.gov/FinancialDisclosure
- **Yearly zip pattern**: `https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{YEAR}FD.zip`
- **PDF pattern**: `https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{YEAR}/{DocID}.pdf`

## Contributing

Contributions welcome! Please read our contribution guidelines and code of conduct before submitting PRs.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Disclaimer

This dataset is derived from official public financial disclosure reports made available by the U.S. House of Representatives. The original reports are available at [disclosures-clerk.house.gov](https://disclosures-clerk.house.gov/FinancialDisclosure).

Data has been transformed and extracted by automated processes and **may contain errors**. This project is for transparency & research purposes only and is not affiliated with Congress or any government entity.

## Contact & Support

- **Issues**: [GitHub Issues](https://github.com/Jakeintech/congress-disclosures-standardized/issues)
- **Documentation**: [docs/](docs/)
- **Architecture details**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
