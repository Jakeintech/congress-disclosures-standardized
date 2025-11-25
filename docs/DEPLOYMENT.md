# Deployment Guide

Complete step-by-step guide for deploying the Congress Financial Disclosures pipeline to your own AWS account.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Terraform Deployment](#terraform-deployment)
- [First Ingestion Run](#first-ingestion-run)
- [Monitoring & Troubleshooting](#monitoring--troubleshooting)
- [Cost Management](#cost-management)
- [Updating the Pipeline](#updating-the-pipeline)
- [Backup & Disaster Recovery](#backup--disaster-recovery)

---

## Prerequisites

### Required Tools

1. **AWS CLI** (v2.0+)
   ```bash
   # Install on macOS
   brew install awscli

   # Install on Linux
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install

   # Verify installation
   aws --version
   ```

2. **Terraform** (1.5+)
   ```bash
   # Install on macOS
   brew tap hashicorp/tap
   brew install hashicorp/tap/terraform

   # Install on Linux
   wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
   unzip terraform_1.6.0_linux_amd64.zip
   sudo mv terraform /usr/local/bin/

   # Verify installation
   terraform --version
   ```

3. **Python** (3.11+)
   ```bash
   python3 --version
   ```

4. **Make** (optional but recommended)
   ```bash
   make --version
   ```

### AWS Account Setup

1. **Create AWS Account** (if you don't have one)
   - Visit https://aws.amazon.com/
   - Sign up for a free tier account
   - Verify email and add payment method

2. **Create IAM User for Deployment**
   ```bash
   # Using AWS Console:
   # 1. Go to IAM → Users → Create user
   # 2. Username: "terraform-deploy"
   # 3. Enable "Programmatic access"
   # 4. Attach policies:
   #    - AmazonS3FullAccess
   #    - AWSLambdaFullAccess
   #    - IAMFullAccess
   #    - AmazonSQSFullAccess
   #    - CloudWatchFullAccess
   #    - AmazonTextractFullAccess
   # 5. Save Access Key ID and Secret Access Key
   ```

3. **Configure AWS CLI**
   ```bash
   aws configure
   # AWS Access Key ID: <your-key>
   # AWS Secret Access Key: <your-secret>
   # Default region name: us-east-1
   # Default output format: json

   # Verify configuration
   aws sts get-caller-identity
   ```

---

## Initial Setup

### 1. Clone Repository

```bash
git clone https://github.com/Jakeintech/congress-disclosures-standardized.git
cd congress-disclosures-standardized
```

### 2. Create Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit with your values
nano .env  # or vim, code, etc.
```

**Important**: Set `S3_BUCKET_NAME` to a **globally unique** value:
```bash
S3_BUCKET_NAME=congress-disclosures-yourname-$(date +%s)
```

### 3. Configure Terraform Variables

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars

# Edit with your settings
nano terraform.tfvars
```

**Minimum required changes**:
```hcl
s3_bucket_name = "congress-disclosures-yourname-unique"  # MUST be globally unique
alert_email = "your-email@example.com"  # For CloudWatch alerts
```

**Recommended for free tier optimization**:
```hcl
lambda_max_concurrent_executions = 5  # Lower than default
cloudwatch_log_retention_days = 7     # Shorter retention
enable_cost_alerts = true
```

---

## Terraform Deployment

### Option A: Using Make (Recommended)

```bash
# From project root
make init      # Initialize Terraform
make plan      # Review changes
make deploy    # Apply infrastructure
```

### Option B: Manual Terraform Commands

```bash
cd infra/terraform

# Initialize
terraform init

# Review plan
terraform plan -out=tfplan

# Apply (type 'yes' when prompted)
terraform apply tfplan
```

### Deployment Time

First deployment takes **5-10 minutes**:
- S3 bucket creation: ~30 seconds
- IAM roles: ~1 minute
- Lambda functions: ~2 minutes each
- SQS queues: ~30 seconds
- CloudWatch resources: ~2 minutes

### Expected Output

```
Terraform will perform the following actions:
  + create 25+ resources

...

Apply complete! Resources: 25 added, 0 changed, 0 destroyed.

Outputs:

quick_reference = {
  "ingest_command" = "aws lambda invoke ..."
  "logs_extract" = "aws logs tail ..."
  ...
}

### Automatic Gold-Layer Seeding

On first apply, Terraform automatically invokes a bootstrap Lambda to seed gold-layer dimensions:

- `gold/house/financial/dimensions/dim_date/year=YYYY/part-0000.parquet`
- `gold/house/financial/dimensions/dim_filing_types/part-0000.parquet`

The seeding is idempotent and only writes missing partitions/files. To force a reseed (e.g., after logic changes), bump the Terraform variable `seed_data_version` in `terraform.tfvars`:

```hcl
seed_data_version = "2"
```

Then run `terraform apply` again. The seed Lambda will execute and update any missing outputs.

### Configure Congress.gov Key (for dim_members)

The `dim_members` seed Lambda reads your Congress.gov API key from AWS Systems Manager Parameter Store and seeds:

- `gold/house/financial/dimensions/dim_members/year=YYYY/part-0000.parquet`

1) Store your key (encrypted) in SSM. The default parameter name is based on environment:

```bash
aws ssm put-parameter \
  --name "/congress-disclosures/${ENVIRONMENT:-development}/congress-api-key" \
  --type "SecureString" \
  --value "<YOUR_CONGRESS_API_KEY>"
```

2) Optionally override the parameter name in `infra/terraform/terraform.tfvars`:

```hcl
ssm_congress_api_key_param = "/congress-disclosures/development/congress-api-key"
```

3) Apply Terraform. The members seed runs automatically (and is idempotent). If the parameter is missing, the seed step is skipped without failing the deployment. Bump `seed_data_version` to force reseed when needed.
```

### Verify Deployment

```bash
# Check S3 bucket exists
aws s3 ls | grep congress-disclosures

# Check Lambda functions
aws lambda list-functions | grep congress-disclosures

# Check SQS queues
aws sqs list-queues | grep congress-disclosures
```

---

## First Ingestion Run

### Trigger Ingestion for 2025

```bash
# Using AWS CLI
aws lambda invoke \
  --function-name congress-disclosures-development-ingest-zip \
  --payload '{"year": 2025}' \
  --cli-binary-format raw-in-base64-out \
  response.json

# Check response
cat response.json
```

**Expected response**:
```json
{
  "status": "success",
  "year": 2025,
  "pdfs_uploaded": 156,
  "sqs_messages_sent": 156,
  "timestamp": "2025-11-24T20:00:00Z"
}
```

### Monitor Progress

```bash
# Watch ingestion logs
aws logs tail /aws/lambda/congress-disclosures-development-ingest-zip --follow

# In another terminal, watch extraction logs
aws logs tail /aws/lambda/congress-disclosures-development-extract-document --follow

# Check SQS queue depth
aws sqs get-queue-attributes \
  --queue-url $(aws sqs get-queue-url --queue-name congress-disclosures-development-extract-queue --query 'QueueUrl' --output text) \
  --attribute-names ApproximateNumberOfMessages
```

### Verify Data in S3

```bash
# Check bronze layer
aws s3 ls s3://your-bucket-name/bronze/house/financial/year=2025/ --recursive | head -20

# Check silver layer (after extraction completes)
aws s3 ls s3://your-bucket-name/silver/house/financial/filings/year=2025/

# Download and inspect a Parquet file
aws s3 cp s3://your-bucket-name/silver/house/financial/filings/year=2025/part-0000.parquet .
python3 -c "import pandas as pd; df = pd.read_parquet('part-0000.parquet'); print(df.head())"
```

---

## Monitoring & Troubleshooting

### CloudWatch Dashboard

If you enabled `enable_cost_alerts = true`, view your dashboard:

```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=congress-disclosures-development-dashboard
```

### Common Issues

#### Issue: Lambda Timeout

**Symptom**: Extraction Lambda times out on large PDFs

**Solution**:
```hcl
# In terraform.tfvars
lambda_timeout_seconds = 600  # Increase to 10 minutes
lambda_extract_memory_mb = 3008  # Increase memory
```

Then re-deploy:
```bash
make deploy
```

#### Issue: Textract Throttling

**Symptom**: Logs show `ProvisionedThroughputExceededException`

**Solution**:
1. Reduce concurrent executions:
   ```hcl
   lambda_max_concurrent_executions = 3
   ```

2. Request Textract limit increase:
   - Go to AWS Service Quotas console
   - Search for "Textract"
   - Request increase for "Transactions per second"

#### Issue: SQS Messages in DLQ

**Symptom**: CloudWatch alarm for DLQ messages

**Solution**:
```bash
# Inspect DLQ messages
aws sqs receive-message \
  --queue-url $(aws sqs get-queue-url --queue-name congress-disclosures-development-extract-dlq --query 'QueueUrl' --output text) \
  --max-number-of-messages 10

# Re-process failed messages
# (TODO: Add reprocessing script in utils/)
```

#### Issue: Out of Disk Space

**Symptom**: Lambda logs show disk space errors

**Solution**:
```hcl
# In lambda.tf, increase ephemeral storage
ephemeral_storage {
  size = 2048  # 2 GB
}
```

### Debugging Lambda Functions

```bash
# Invoke with test event
aws lambda invoke \
  --function-name congress-disclosures-development-extract-document \
  --payload '{"Records": [{"body": "{\"doc_id\": \"8221216\", \"year\": 2025, \"s3_pdf_key\": \"bronze/house/financial/year=2025/pdfs/2025/8221216.pdf\"}"}]}' \
  --log-type Tail \
  response.json

# View logs
aws logs get-log-events \
  --log-group-name /aws/lambda/congress-disclosures-development-extract-document \
  --log-stream-name '$LATEST' \
  --limit 50
```

---

## Cost Management

### Estimated Monthly Costs

For processing 2025 data once:

| Service | Usage | Cost |
|---------|-------|------|
| S3 Storage (20 GB) | Standard | $0.46 |
| Lambda Compute | 5,000 GB-seconds | $0.08 |
| Lambda Requests | 10,000 invocations | $0.002 |
| Textract | 1,000 pages (free tier) | $0.00 |
| Textract | 9,000 additional pages | $13.50 |
| SQS | 10,000 messages | $0.00 |
| CloudWatch Logs | 1 GB | $0.50 |
| **Total** | | **~$14.56/month** |

**To minimize costs**:
- Process only needed years
- Use shorter log retention (7 days vs 30)
- Lower Lambda concurrency
- Disable X-Ray tracing
- Use Intelligent Tiering for S3

### Set Up Billing Alerts

```bash
# Create SNS topic for billing alerts
aws sns create-topic --name billing-alerts

# Subscribe your email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:billing-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com

# Create billing alarm (replace ACCOUNT_ID)
aws cloudwatch put-metric-alarm \
  --alarm-name monthly-bill-over-20-dollars \
  --alarm-description "Alert when monthly bill exceeds $20" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --evaluation-periods 1 \
  --threshold 20 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:billing-alerts
```

---

## Updating the Pipeline

### Update Lambda Code

```bash
# Make changes to Lambda handlers or libs
nano ingestion/lambdas/house_fd_ingest_zip/handler.py

# Package updated Lambda
make package-ingest

# Deploy updated function
cd ingestion/lambdas/house_fd_ingest_zip
aws lambda update-function-code \
  --function-name congress-disclosures-development-ingest-zip \
  --zip-file fileb://function.zip
```

### Update Terraform Infrastructure

```bash
# Make changes to Terraform files
nano infra/terraform/lambda.tf

# Plan and apply
cd infra/terraform
terraform plan
terraform apply
```

### Update Python Dependencies

```bash
# Update requirements.txt
nano ingestion/requirements.txt

# Re-package all Lambdas
make package-all

# Deploy (will update all Lambda functions)
make deploy
```

---

## Backup & Disaster Recovery

### Backup Strategy

**Bronze Layer** (immutable):
- S3 versioning is enabled
- Can restore any previous version
- Consider Cross-Region Replication for disaster recovery

**Silver Layer** (reproducible):
- Can be regenerated from bronze
- No additional backup needed

**Terraform State**:
```bash
# Backup state file
cd infra/terraform
terraform state pull > terraform.tfstate.backup

# Store securely (encrypted, version controlled separately)
```

### Disaster Recovery

**Scenario: Accidental deletion of S3 bucket**

```bash
# If versioning was enabled, restore from versions
aws s3api list-object-versions --bucket your-bucket-name

# If bucket was deleted entirely, re-run ingestion
aws lambda invoke --function-name congress-disclosures-development-ingest-zip \
  --payload '{"year": 2025}' response.json
```

**Scenario: Corrupted Parquet files**

```bash
# Delete corrupted files
aws s3 rm s3://your-bucket-name/silver/house/financial/filings/year=2025/ --recursive

# Re-trigger silver generation
aws lambda invoke --function-name congress-disclosures-development-index-to-silver \
  --payload '{"year": 2025}' response.json
```

---

## Production Deployment

For production deployments (not development/testing):

1. **Use Terraform Remote State**:
   ```hcl
   # In main.tf
   terraform {
     backend "s3" {
       bucket = "your-terraform-state-bucket"
       key    = "congress-disclosures/terraform.tfstate"
       region = "us-east-1"
       encrypt = true
       dynamodb_table = "terraform-locks"
     }
   }
   ```

2. **Enable Enhanced Monitoring**:
   ```hcl
   enable_xray_tracing = true
   cloudwatch_log_retention_days = 90
   ```

3. **Use Separate Environments**:
   ```bash
   # Create workspaces
   terraform workspace new production
   terraform workspace new staging

   # Deploy to production
   terraform workspace select production
   terraform apply
   ```

4. **Set Up Alerts**:
   - Configure `alert_email` in terraform.tfvars
   - Monitor CloudWatch alarms daily
   - Set up PagerDuty/OpsGenie integration

---

## Next Steps

After successful deployment:

1. **Process Historical Data**:
   ```bash
   for year in {2008..2025}; do
     aws lambda invoke \
       --function-name congress-disclosures-development-ingest-zip \
       --payload "{\"year\": $year}" \
       response_$year.json
     sleep 300  # Wait 5 minutes between years
   done
   ```

2. **Set Up Scheduled Ingestion**:
   - Add EventBridge cron rule to trigger nightly ingestion
   - See Phase 2 features for automation

3. **Build Gold Layer**:
   - Implement additional transformations
   - Create query-facing tables
   - Set up public API (see [docs/API_STRATEGY.md](API_STRATEGY.md))

4. **Contribute Improvements**:
   - Report issues on GitHub
   - Submit pull requests for enhancements
   - Share your use cases with the community

---

## Support & Resources

- **Documentation**: [docs/](.)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Legal Compliance**: [LEGAL_NOTES.md](LEGAL_NOTES.md)
- **Contributing**: [../CONTRIBUTING.md](../CONTRIBUTING.md)
- **GitHub Issues**: https://github.com/Jakeintech/congress-disclosures-standardized/issues

---

**Happy deploying! 🚀**

Remember: This is public data being made more accessible. Your deployment helps increase government transparency and accountability.
