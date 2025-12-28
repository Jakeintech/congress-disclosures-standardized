# Quick Start Guide

Get the Congress Disclosures pipeline running on your local machine in **15 minutes** or deploy to AWS in **30 minutes**.

---

## Prerequisites

Before starting, ensure you have:

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Make** - Pre-installed on macOS/Linux, [Windows guide](https://gnuwin32.sourceforge.net/packages/make.htm)
- **Git** - [Download](https://git-scm.com/)
- **AWS CLI** (for AWS deployment) - [Installation guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **Terraform** (for AWS deployment) - [Download](https://www.terraform.io/downloads)

---

## Option 1: Run Locally (15 Minutes)

Perfect for testing, development, or analyzing a small dataset without AWS costs.

### Step 1: Clone the Repository

```bash
git clone https://github.com/Jakeintech/congress-disclosures-standardized.git
cd congress-disclosures-standardized
```

### Step 2: Setup Environment

```bash
make setup
```

This command:
- Creates Python virtual environment
- Installs all dependencies
- Generates `.env` file from template
- Verifies your setup

### Step 3: Run Pipeline Locally

```bash
make local-run
```

This will:
- Download sample PDFs
- Extract text and structured data
- Generate local Parquet files in `local_data/`
- Skip AWS services entirely

### Step 4: View Results

```bash
# Browse the data structure
ls -R local_data/

# Start local HTTP server to explore data
make local-serve
# Opens at http://localhost:8000
```

### What You'll See

```
local_data/
├── bronze/
│   └── house/financial/year=2025/pdfs/
├── silver/
│   ├── filings/
│   ├── documents/
│   └── text/
└── gold/
    ├── facts/
    └── dimensions/
```

### Next Steps

- [Understanding the Data](Data-Layers) - Learn about Bronze/Silver/Gold
- [Query Examples](Query-Examples) - Run SQL queries on Parquet files
- [Deploy to AWS](Self-Hosting-Guide) - Scale up to full dataset

---

## Option 2: Deploy to AWS (30 Minutes)

Deploy the full serverless pipeline to process 15+ years of disclosure data.

### Step 1: AWS Prerequisites

1. **AWS Account** - [Create one](https://aws.amazon.com/free/) if needed
2. **Configure AWS CLI**:
   ```bash
   aws configure
   # Enter: Access Key, Secret Key, Region (us-east-1), Format (json)
   ```
3. **Verify credentials**:
   ```bash
   make verify-aws
   ```

### Step 2: Clone & Setup

```bash
git clone https://github.com/Jakeintech/congress-disclosures-standardized.git
cd congress-disclosures-standardized
make setup
```

### Step 3: Configure Environment

Edit `.env` file:

```bash
# Required settings
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012  # Your AWS account ID
S3_BUCKET_NAME=congress-disclosures-YOUR-UNIQUE-NAME
PROJECT_NAME=congress-disclosures
ENVIRONMENT=production

# Optional (use defaults or customize)
LOG_LEVEL=INFO
```

### Step 4: Deploy Infrastructure

```bash
# Initialize Terraform
make init

# Preview changes
make plan

# Deploy (interactive confirmation)
make deploy
```

This creates:
- S3 bucket for data storage
- Lambda functions for processing
- SQS queues for job management
- Step Functions for orchestration
- IAM roles and policies
- CloudWatch alarms

**Expected time**: 5-10 minutes

### Step 5: Run First Ingestion

```bash
# Ingest current year (recommended for first run)
make ingest-current

# Monitor progress
make check-extraction-queue
make logs-extract
```

**Expected time**:
- Ingestion: 5-10 minutes
- Extraction: 30-60 minutes (depending on concurrency)

### Step 6: Generate Gold Layer

```bash
make aggregate-data
```

This creates analytics-ready tables for querying.

### Step 7: Deploy Website (Optional)

```bash
make deploy-website
```

Access your data through a web interface.

---

## Verification Steps

### Check Pipeline Status

```bash
# View Terraform outputs
make output

# Check queue status
make check-extraction-queue

# View recent logs
make logs-extract-recent
```

### Expected Outputs

After successful deployment:

```
Outputs:

api_gateway_url = "https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod"
lambda_extract_function_name = "congress-disclosures-extract-document"
lambda_ingest_function_name = "congress-disclosures-ingest-zip"
s3_bucket_name = "congress-disclosures-standardized"
sqs_extraction_queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/extraction-queue"
```

### Test Data Access

```bash
# Query S3 directly
aws s3 ls s3://YOUR-BUCKET-NAME/bronze/house/financial/

# Check Silver layer
aws s3 ls s3://YOUR-BUCKET-NAME/silver/filings/
```

---

## Common First-Time Issues

### Issue: `make` command not found

**Solution**:
```bash
# macOS
xcode-select --install

# Linux (Ubuntu/Debian)
sudo apt-get install build-essential

# Windows
# Install via Chocolatey: choco install make
# Or use WSL2
```

### Issue: AWS credentials error

**Solution**:
```bash
# Reconfigure AWS CLI
aws configure

# Or export temporary credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

### Issue: Terraform state conflicts

**Solution**:
```bash
# If you've run terraform before
rm -rf .terraform terraform.tfstate*
make init
```

### Issue: S3 bucket name already exists

**Solution**: S3 bucket names must be globally unique. Edit `.env`:
```bash
S3_BUCKET_NAME=congress-disclosures-YOUR-COMPANY-prod
```

Then re-run:
```bash
make deploy
```

---

## Cost Estimates

### Local Mode
- **Cost**: $0 (no AWS charges)
- **Limitations**: Small dataset, no automation

### AWS Deployment (Free Tier)
- **S3 Storage**: $0 (first 5GB free)
- **Lambda**: $0 (first 1M requests free)
- **Data Transfer**: ~$5-10/month
- **Total**: **$15-50/month** for full dataset

[Learn more about cost optimization →](Cost-Management)

---

## Next Steps

### For Users
- [Understand the data layers](Data-Layers)
- [Learn about filing types](Filing-Types-Explained)
- [Query examples](Query-Examples)

### For Developers
- [Development setup guide](Development-Setup)
- [System architecture overview](System-Architecture)
- [Contributing guide](Contributing-Guide)

### For Operators
- [Monitoring guide](Monitoring-Guide)
- [Running pipelines](Running-Pipelines)
- [Troubleshooting](Troubleshooting)

---

## Getting Help

**Stuck? Have questions?**

1. Check the [FAQ](FAQ)
2. Search [Troubleshooting guide](Troubleshooting)
3. Search this wiki (top right)
4. Open a [GitHub Discussion](https://github.com/Jakeintech/congress-disclosures-standardized/discussions)
5. File an [issue](https://github.com/Jakeintech/congress-disclosures-standardized/issues)

---

**See also**:
- [Self-Hosting Guide](Self-Hosting-Guide) - Detailed deployment guide
- [Local Development Mode](Local-Development-Mode) - Advanced local development
- [Command Reference](Command-Reference) - All available make commands
