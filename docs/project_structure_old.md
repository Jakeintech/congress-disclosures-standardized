# Politics Data Platform - Project Structure

**Last Updated**: 2025-01-06
**Version**: 2.0.0 (Reorganized frontend/backend separation)

## Overview

This project follows a clean separation between frontend and backend code, with clear boundaries and dependencies.

```
congress-disclosures-standardized/
├── frontend/                     # Frontend application
├── backend/                      # Backend services & data processing
├── infra/                        # Infrastructure as Code (Terraform)
├── docs/                         # Documentation
├── tests/                        # Test suites
├── data/                         # Local data (gitignored)
└── [config files]                # Root configuration
```

---

## Directory Structure

### `/frontend/` - Frontend Application

**Technology**: Next.js 15, React 19, TypeScript, TailwindCSS

```
frontend/
└── website/
    ├── src/
    │   ├── app/                  # Next.js App Router pages
    │   │   ├── page.tsx          # Dashboard (/)
    │   │   ├── members/          # Members listing & detail
    │   │   ├── bills/            # Bills search & detail
    │   │   ├── transactions/     # Transaction filtering
    │   │   ├── lobbying-network/ # D3.js network visualization
    │   │   └── influence-tracker/# Analytics dashboard
    │   ├── components/           # React components
    │   │   ├── ui/               # shadcn/ui components
    │   │   ├── charts/           # Recharts visualizations
    │   │   ├── ErrorBoundary.tsx # Error handling
    │   │   └── [domain components]
    │   ├── lib/                  # Utilities
    │   │   ├── api.ts            # API client
    │   │   ├── cache.ts          # Client-side caching
    │   │   └── utils.ts          # Helpers
    │   └── types/                # TypeScript definitions
    │       ├── api.ts            # API response types
    │       └── [domain types]
    ├── public/                   # Static assets
    ├── e2e/                      # Playwright tests
    ├── docs/                     # Frontend docs
    ├── next.config.js            # Next.js configuration
    ├── tailwind.config.ts        # TailwindCSS config
    └── package.json              # NPM dependencies
```

**Key Features**:
- Server-side rendering (SSR) for SEO
- Static site generation for performance
- Error boundaries on all pages
- Integration tests for API endpoints
- Vercel deployment configuration

**Build & Deploy**:
```bash
cd frontend/website
npm install
npm run build      # Static export to out/
npm test           # Integration tests
vercel --prod      # Deploy to Vercel
```

---

### `/backend/` - Backend Services

**Technology**: Python 3.11, AWS Lambda, Step Functions, DuckDB, DBT

```
backend/
├── functions/                   # AWS Lambda functions
│   ├── ingestion/               # Bronze layer (data ingestion)
│   │   ├── house_fd_ingest_zip/
│   │   ├── house_fd_extract_document/
│   │   ├── house_fd_index_to_silver/
│   │   ├── congress_api_ingest/
│   │   └── [other ingestion lambdas]
│   └── api/                     # API endpoints (Gold layer queries)
│       ├── get_members/
│       ├── get_trades/
│       ├── get_trending_stocks/
│       └── [60+ API handlers]
│
├── lib/                         # Shared libraries
│   ├── ingestion/               # Ingestion utilities
│   │   ├── s3_utils.py          # S3 operations
│   │   ├── s3_path_registry.py  # Centralized path management
│   │   ├── parquet_writer.py    # Parquet upsert operations
│   │   ├── extraction/          # PDF extraction framework
│   │   ├── extractors/          # Filing-type extractors
│   │   ├── enrichment.py        # Data enrichment
│   │   └── [other utils]
│   ├── api/                     # API utilities
│   │   ├── api_cache.py         # DynamoDB caching (NEW)
│   │   ├── rate_limiter.py      # Rate limiting (NEW)
│   │   └── [other API utils]
│   └── schemas/                 # Pydantic schemas
│
├── scripts/                     # Data processing scripts
│   ├── build_reference_members.py
│   ├── build_dim_members_simple.py
│   ├── build_fact_ptr_transactions.py
│   ├── compute_agg_trending_stocks.py
│   ├── run_smart_pipeline.py
│   └── [180+ scripts]
│
├── orchestration/               # Step Functions state machines
│   ├── house_fd_pipeline.json
│   ├── congress_pipeline.json
│   ├── lobbying_pipeline.json
│   └── cross_dataset_correlation.json
│
├── layers/                      # Lambda layers
│   ├── duckdb/                  # DuckDB layer
│   ├── soda_core/               # Data quality checks
│   └── [other layers]
│
└── lambda_layers/               # Layer build configs
```

**Key Components**:

#### 1. Lambda Functions (`functions/`)
- **Ingestion**: Download, extract, normalize raw data
- **API**: Query endpoints serving Gold layer data
- All functions follow consistent structure:
  - `handler.py` - Lambda entry point
  - `requirements.txt` - Dependencies
  - `README.md` - Function documentation

#### 2. Shared Libraries (`lib/`)
- **S3 Operations**: Centralized S3 path management, upload/download
- **Extraction Framework**: Multi-strategy PDF text extraction
- **Data Quality**: Parquet writers, manifest generators
- **API Utilities**: Caching, rate limiting, authentication

#### 3. Scripts (`scripts/`)
- **Reference Data**: Build member, asset, bill crosswalks
- **Gold Layer**: Build dimensions, facts, aggregates
- **Orchestration**: Pipeline runners, validators
- **Migration**: ~30K lines being ported to DBT

#### 4. Orchestration (`orchestration/`)
- Step Functions definitions for multi-step pipelines
- Watermarking, parallel processing, error handling
- Event-driven architecture foundations

**Development**:
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/unit
pytest tests/integration

# Package Lambda
cd functions/ingestion/house_fd_ingest_zip
zip -r function.zip .

# Deploy (via Terraform)
cd ../../../infra/terraform
terraform apply -target=aws_lambda_function.house_fd_ingest_zip
```

---

### `/infra/` - Infrastructure as Code

**Technology**: Terraform, AWS

```
infra/
└── terraform/
    ├── main.tf                  # Provider configuration
    ├── variables.tf             # Input variables
    ├── outputs.tf               # Terraform outputs
    │
    ├── s3.tf                    # Data lake bucket
    ├── dynamodb.tf              # Pipeline state tables
    ├── dynamodb_api.tf          # API layer tables (NEW)
    ├── glue_catalog.tf          # AWS Glue Data Catalog (NEW)
    │
    ├── lambda.tf                # Core Lambda functions
    ├── lambda_congress.tf       # Congress.gov lambdas
    ├── lambda_lobbying.tf       # Lobbying lambdas
    ├── api_lambdas.tf           # API endpoint lambdas
    │
    ├── api_gateway.tf           # HTTP API configuration
    ├── step_functions.tf        # State machines
    ├── eventbridge.tf           # Scheduled rules
    │
    ├── sqs.tf                   # SQS queues
    ├── sns.tf                   # SNS topics (alerts)
    ├── cloudwatch.tf            # Logs & monitoring
    │
    ├── iam.tf                   # IAM roles & policies
    ├── github_oidc.tf           # GitHub Actions OIDC
    ├── budgets.tf               # AWS Budget alerts
    └── [other tf files]
```

**Key Resources**:
- **S3 Bucket**: `congress-disclosures-standardized` (soon: `politics-data-platform`)
- **DynamoDB Tables**: 7 tables (pipeline state, API layer)
- **Lambda Functions**: 80+ functions
- **Step Functions**: 4 state machines
- **API Gateway**: HTTP API with 60+ routes

**Deploy**:
```bash
cd infra/terraform

# Initialize
terraform init

# Plan changes
terraform plan -out=tfplan

# Apply
terraform apply tfplan

# View outputs
terraform output
```

---

### `/docs/` - Documentation

```
docs/
├── ARCHITECTURE.md              # System architecture
├── DEPLOYMENT.md                # Deployment guide
├── EXTRACTION_ARCHITECTURE.md   # PDF extraction details
├── API_STRATEGY.md              # API design
├── API_ENDPOINTS.md             # API reference
├── LEGAL_NOTES.md               # Compliance (5 U.S.C. § 13107)
│
├── TERRAFORM_AUDIT.md           # Infrastructure audit
├── TERRAFORM_MODERNIZATION.md   # Modernization roadmap
│
├── agile/                       # Agile artifacts
│   ├── DEFINITION_OF_DONE.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── [sprint docs]
│
└── examples/                    # Code examples
```

---

### `/tests/` - Test Suites

```
tests/
├── unit/                        # Unit tests
│   ├── test_s3_paths.py
│   ├── test_extractors.py
│   └── [other unit tests]
│
├── integration/                 # Integration tests
│   ├── test_house_fd_pipeline.py
│   ├── test_api_endpoints.py
│   └── [other integration tests]
│
├── api/                         # API contract tests
│   └── test_api_schemas.py
│
└── fixtures/                    # Test data
    ├── sample_pdfs/
    ├── sample_json/
    └── mock_responses/
```

**Run Tests**:
```bash
# Unit tests only
pytest tests/unit -v

# Integration tests (requires AWS credentials)
pytest tests/integration -v

# All tests with coverage
pytest tests/ --cov=backend --cov-report=html
```

---

### `/data/` - Local Data (Gitignored)

```
data/
├── bronze/                      # Raw downloads (for local testing)
├── silver/                      # Processed data
├── gold/                        # Analytics-ready
└── test_samples/                # Small test datasets
```

**Note**: This directory is gitignored. Production data lives in S3.

---

## Root Files

### Configuration Files

```
.
├── .env                         # Environment variables (gitignored)
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
├── .github/                     # GitHub Actions workflows
├── .python-version              # pyenv Python version
├── requirements.txt             # Python dependencies
├── package.json                 # Root npm scripts (if any)
├── Makefile                     # Common commands
└── README.md                    # Project overview
```

### Documentation Files (Root)

```
├── MASTER_EXECUTION_PLAN.md     # 16-week modernization roadmap
├── AGENT_GUIDE.md               # Agent-friendly automation
├── PROJECT_STRUCTURE.md         # This file
├── CONTRIBUTING.md              # Contribution guidelines
├── LICENSE                      # MIT License
└── CHANGELOG.md                 # Version history
```

---

## Import Paths & References

### Python Imports (Backend)

**OLD** (pre-reorganization):
```python
from ingestion.lib.s3_utils import upload_file_to_s3
from api.lib.duckdb_client import DuckDBClient
```

**NEW** (post-reorganization):
```python
from backend.lib.ingestion.s3_utils import upload_file_to_s3
from backend.lib.api.duckdb_client import DuckDBClient
```

### Terraform References

**OLD**:
```hcl
filename = "${path.module}/../../ingestion/lambdas/house_fd_ingest_zip/function.zip"
```

**NEW**:
```hcl
filename = "${path.module}/../../backend/functions/ingestion/house_fd_ingest_zip/function.zip"
```

### Git Paths

When referencing files in documentation:
- Frontend: `frontend/website/src/app/page.tsx`
- Backend Lambda: `backend/functions/ingestion/house_fd_ingest_zip/handler.py`
- Shared lib: `backend/lib/ingestion/s3_path_registry.py`
- Infrastructure: `infra/terraform/s3.tf`

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js)                      │
│  frontend/website/src/app/                                  │
│  - Dashboard, Members, Bills, Transactions, Analytics       │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/HTTPS
                       ▼
┌─────────────────────────────────────────────────────────────┐
│               API GATEWAY (AWS HTTP API)                    │
│  Routes → backend/functions/api/*                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│            BACKEND API LAMBDAS (Python 3.11)                │
│  backend/functions/api/                                     │
│  - get_members, get_trades, get_trending_stocks             │
│  Uses: backend/lib/api/ (caching, rate limiting)            │
└──────────────────────┬──────────────────────────────────────┘
                       │ DuckDB queries
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  GOLD LAYER (S3 Parquet)                    │
│  s3://politics-data-platform/data/gold/                     │
│  - dimensions/ (members, assets, bills)                     │
│  - facts/ (transactions, filings)                           │
│  - aggregates/ (trending_stocks, member_stats)              │
└──────────────────────┬──────────────────────────────────────┘
                       │ Built by
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              SILVER LAYER (S3 Parquet + JSON)               │
│  s3://politics-data-platform/data/silver/                   │
│  - Normalized tables (filings, documents)                   │
│  - Structured extractions (objects/)                        │
└──────────────────────┬──────────────────────────────────────┘
                       │ Extracted from
                       ▼
┌─────────────────────────────────────────────────────────────┐
│            BRONZE LAYER (S3 Raw Files)                      │
│  s3://politics-data-platform/data/bronze/                   │
│  - PDFs (house_fd/)                                         │
│  - JSON (congress_api/)                                     │
│  - XML (lobbying/)                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │ Ingested by
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         INGESTION LAMBDAS (Step Functions)                  │
│  backend/functions/ingestion/                               │
│  - house_fd_ingest_zip                                      │
│  - house_fd_extract_document                                │
│  - congress_api_ingest                                      │
│  Uses: backend/lib/ingestion/ (extraction, s3_utils)        │
└──────────────────────┬──────────────────────────────────────┘
                       │ Downloads from
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  EXTERNAL DATA SOURCES                      │
│  - House Clerk (disclosures-clerk.house.gov)                │
│  - Congress.gov API (api.congress.gov)                      │
│  - Senate LDA (soprweb.senate.gov)                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Frontend
- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript 5
- **UI**: React 19, TailwindCSS, shadcn/ui
- **Charts**: Recharts, D3.js
- **Testing**: Playwright (E2E), Jest (unit)
- **Hosting**: Vercel

### Backend
- **Language**: Python 3.11
- **Compute**: AWS Lambda (serverless)
- **Orchestration**: AWS Step Functions
- **Queue**: AWS SQS, EventBridge
- **Database**: DynamoDB (metadata), S3 (data lake)
- **Catalog**: AWS Glue Data Catalog
- **Query Engine**: DuckDB (embedded)
- **Transformation**: DBT Core (in progress)

### Infrastructure
- **IaC**: Terraform
- **Cloud**: AWS (US East 1)
- **CI/CD**: GitHub Actions
- **Monitoring**: CloudWatch, X-Ray
- **Alerting**: SNS, AWS Budgets

### Data Formats
- **Bronze**: PDF, XML, JSON (raw)
- **Silver**: Parquet (compressed, Hive-partitioned)
- **Gold**: Parquet (star schema, Iceberg-ready)

---

## Development Workflow

### Frontend Development
```bash
cd frontend/website
npm install
npm run dev          # http://localhost:3000
npm test             # Run tests
npm run build        # Production build
```

### Backend Development
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run local tests
pytest tests/unit

# Package Lambda
cd functions/ingestion/house_fd_ingest_zip
zip -r function.zip handler.py

# Deploy via Terraform
cd ../../../infra/terraform
terraform apply -target=aws_lambda_function.house_fd_ingest_zip
```

### Full Stack Development
```bash
# Terminal 1: Frontend
cd frontend/website && npm run dev

# Terminal 2: Mock API (if needed)
cd backend && python -m http.server 8000

# Terminal 3: Watch tests
pytest tests/ --watch
```

---

## Migration Notes

This structure was reorganized on **2025-01-06** to separate frontend and backend concerns.

**What Changed**:
- `website/` → `frontend/website/`
- `ingestion/` → `backend/` (with reorganization)
- `api/` → `backend/` (with reorganization)
- `scripts/` → `backend/scripts/`
- `layers/` → `backend/layers/`
- `state_machines/` → `backend/orchestration/`

**What Stayed**:
- `infra/terraform/` - Infrastructure as Code (root level)
- `docs/` - Documentation (root level)
- `tests/` - Test suites (root level)
- `.github/` - GitHub workflows (root level)

**Import Path Changes**:
- `from ingestion.lib` → `from backend.lib.ingestion`
- `from api.lib` → `from backend.lib.api`

**Terraform Path Changes**:
- `ingestion/lambdas/` → `backend/functions/ingestion/`
- `api/lambdas/` → `backend/functions/api/`

All changes were automated via scripts with validation.

---

## Contributing

See `CONTRIBUTING.md` for detailed contribution guidelines.

**Quick Start**:
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes in appropriate directory (frontend/ or backend/)
4. Run tests (`pytest` for backend, `npm test` for frontend)
5. Commit with conventional commits (`feat:`, `fix:`, `docs:`)
6. Push and create Pull Request

---

## License

MIT License - See `LICENSE` file

---

## Contact

**Project Owner**: Jake (GitHub: @Jakeintech)
**Repository**: https://github.com/Jakeintech/congress-disclosures-standardized

**Questions or Issues**: Open a GitHub issue
