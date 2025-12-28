# Frequently Asked Questions (FAQ)

Common questions and answers about the Congress Financial Disclosures project.

## Table of Contents
- [General Questions](#general-questions)
- [Getting Started](#getting-started)
- [Data Access](#data-access)
- [Development](#development)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Legal & Compliance](#legal--compliance)
- [Contributing](#contributing)

---

## General Questions

### What is this project?

This is an open-source data pipeline that ingests, processes, and standardizes U.S. House of Representatives financial disclosure reports. It transforms 15+ years of PDF filings into queryable structured data using AWS serverless infrastructure.

### Why does this exist?

Congressional financial disclosures are public records, but they're published as PDFs that are difficult to analyze at scale. This project makes the data accessible for:
- Investigative journalism
- Academic research
- Public transparency initiatives
- Data analysis and visualization

### Is this official data from Congress?

No, this is an independent project. The **source data** comes from the official House Clerk website (disclosures-clerk.house.gov), but this pipeline transforms and republishes it. Always verify critical information against official PDFs.

### How much does it cost to run?

The pipeline is optimized for AWS Free Tier:
- **Development/personal use**: $0-5/month (within free tier)
- **Processing 2025 data**: ~$0/month (using pypdf + Tesseract instead of Textract)
- **Production at scale**: $50-200/month depending on volume

See [[Cost-Management]] for details.

### What data is available?

Currently available:
- **House Financial Disclosures**: 2008-2025
- **Filing types**: Periodic Transaction Reports (PTRs), Annual Reports, Candidate Reports, Extensions
- **Extracted data**: Transactions, assets, income, liabilities

Planned:
- **Congress.gov data**: Bills, votes, committees
- **Lobbying disclosures**: Senate LDA database

### How current is the data?

- **Manual updates**: Run ingestion whenever you need latest data
- **Scheduled updates** (optional): Configure EventBridge for daily/weekly checks
- **Delay**: Data is available 30-45 days after House publishes (per statutory requirements)

---

## Getting Started

### What do I need to get started?

**Prerequisites**:
- AWS account (free tier eligible)
- Python 3.11+
- Terraform 1.5+
- Basic command line knowledge

See [[Quick-Start-Guide]] for step-by-step instructions.

### Can I use this without AWS?

The pipeline is designed for AWS, but you could adapt it to:
- **Google Cloud**: Replace Lambda with Cloud Functions, S3 with Cloud Storage
- **Azure**: Use Azure Functions and Blob Storage
- **Local**: Run scripts locally (slower, no serverless benefits)

However, AWS is recommended because the codebase is optimized for AWS services.

### Do I need to be a developer?

Basic technical skills help, but the project includes:
- Makefile commands for common tasks
- Detailed documentation
- Pre-configured Terraform

If you can run terminal commands and follow instructions, you can deploy it.

### What's the quickest way to see results?

```bash
# 1. Clone and setup
git clone https://github.com/Jakeintech/congress-disclosures-standardized.git
cd congress-disclosures-standardized
make setup

# 2. Deploy infrastructure
make init
make deploy

# 3. Ingest 2025 data
make ingest-current

# 4. Wait 5-10 minutes, then check results
aws s3 ls s3://your-bucket-name/silver/house/financial/filings/year=2025/
```

See [[Quick-Start-Guide]] for full details.

---

## Data Access

### How do I query the data?

Three options:

**1. Direct S3 Access** (Python):
```python
import pandas as pd
df = pd.read_parquet('s3://congress-disclosures-standardized/gold/house/financial/fact_transactions/year=2025/part-0000.parquet')
```

**2. Download Parquet files**:
```bash
aws s3 cp s3://congress-disclosures-standardized/gold/ . --recursive
```

**3. Public API** (planned):
```bash
curl https://api.congress-disclosures.org/v1/filings?year=2025
```

See [[API-Documentation]] and [[Query-Examples]].

### What format is the data in?

- **Storage format**: Apache Parquet (columnar, compressed)
- **Partitioning**: Hive-style by year (`year=2025`)
- **Compression**: Snappy
- **Access tools**: Python (pandas/PyArrow), R (arrow), DuckDB, Athena

### Can I download all the data at once?

Yes:
```bash
# Download entire Gold layer
aws s3 sync s3://your-bucket-name/gold/ ./local-data/

# Size: ~172 MB for 4 years of data (2022-2025)
```

### How do I get member names linked to bioguide IDs?

Use the `dim_members` dimension table:
```python
members = pd.read_parquet('s3://.../gold/house/financial/dimensions/dim_members/year=2025/part-0000.parquet')
```

This includes:
- First/last names
- Bioguide ID
- State/district
- Party affiliation (from Congress.gov API)

### What if I find errors in the data?

1. **Verify against original PDF**: Check the source PDF at disclosures-clerk.house.gov
2. **Report the issue**: Open a GitHub issue with doc_id and error details
3. **Check extraction metadata**: Look at `extraction_method` and `confidence_score` fields

Remember: This is automated extraction, not perfect. Always verify critical data.

---

## Development

### How do I run tests?

```bash
# Unit tests only
pytest tests/unit/

# Integration tests (requires AWS)
pytest tests/integration/

# With coverage
pytest --cov=ingestion tests/
```

See [[Running-Tests]] for details.

### How do I add a new filing type extractor?

1. Create extractor class in `ingestion/lib/extractors/type_X/`
2. Implement `extract_from_text()` method
3. Add tests
4. Register in extractor router

See [[Adding-Extractors]] for step-by-step guide.

### How do I test changes locally without deploying?

Use local development mode:
```bash
# Set local data directory
export LOCAL_DATA_DIR=/path/to/local/data

# Run extraction script
python scripts/local_extract_document.py --doc-id 10063228
```

See [[Local-Development-Mode]].

### Can I use Docker?

Not yet, but it's planned. Current deployment uses:
- Lambda (containerized automatically)
- Terraform for infrastructure
- Direct S3 storage

---

## Deployment

### How long does deployment take?

- **First deployment**: 5-10 minutes (Terraform provisions 25+ resources)
- **Lambda updates**: 30 seconds - 2 minutes
- **Terraform changes**: 1-5 minutes depending on scope

### What AWS regions are supported?

Tested in `us-east-1` (recommended). Should work in any region, but you'll need to:
- Update `AWS_REGION` in `.env`
- Ensure Congress.gov API is accessible
- Check Textract availability (if using it)

### Can I run multiple environments (dev/staging/prod)?

Yes, use Terraform workspaces:
```bash
terraform workspace new production
terraform workspace new staging
terraform workspace select production
terraform apply
```

See [[Self-Hosting-Guide#production-deployment]].

### How do I update Lambda code?

```bash
# Quick update (bypass Terraform)
make quick-deploy-extract

# Or full Terraform deployment
make package-all
make deploy
```

### What if Terraform state gets corrupted?

**Prevention**:
```bash
# Backup state before major changes
cd infra/terraform
terraform state pull > terraform.tfstate.backup
```

**Recovery**:
```bash
# Restore from backup
terraform state push terraform.tfstate.backup

# Or re-import resources
terraform import aws_s3_bucket.data_lake congress-disclosures-standardized
```

---

## Troubleshooting

### Lambda times out

**Solution 1**: Increase timeout
```hcl
# In terraform.tfvars
lambda_timeout_seconds = 600  # 10 minutes
```

**Solution 2**: Optimize code
- Process PDFs page-by-page
- Reduce PDF resolution for OCR
- Split large documents

See [[Troubleshooting#lambda-timeout]].

### SQS queue is stuck

**Check queue status**:
```bash
make check-extraction-queue
```

**Possible causes**:
- Lambda concurrency limit reached
- Lambda errors (check CloudWatch Logs)
- Visibility timeout too short

**Solution**:
```bash
# Check for Lambda errors
make logs-extract-recent

# Increase concurrency
# Edit terraform.tfvars: lambda_max_concurrent_executions = 10
make deploy
```

### Extraction quality is poor

**Check extraction metadata**:
```python
docs = pd.read_parquet('s3://.../silver/house/financial/documents/year=2025/')
low_quality = docs[docs['confidence_score'] < 0.7]
```

**Causes**:
- Image-based PDF (requires OCR)
- Corrupt PDF
- Unusual formatting

**Solution**:
- Enable OCR fallback
- Check original PDF manually
- Report extraction errors via GitHub issue

### S3 bucket policy errors

**Error**: `Access Denied` when accessing S3

**Solution**:
```bash
# Verify bucket policy
aws s3api get-bucket-policy --bucket your-bucket-name

# Re-apply Terraform
make deploy
```

### CloudWatch logs are missing

**Check log group exists**:
```bash
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/congress-disclosures
```

**Common cause**: Lambda hasn't been invoked yet
**Solution**: Trigger Lambda manually and check again

---

## Legal & Compliance

### Is this legal?

Yes. Financial disclosure reports are **public records** under the Ethics in Government Act. This project:
- Uses publicly available data
- Complies with 5 U.S.C. § 13107
- Is for transparency/research purposes

See [[Legal-and-Compliance]] for full details.

### Can I sell this data?

**No** (with exceptions):
- ❌ Commercial use is prohibited (except news/media)
- ❌ Cannot use for credit ratings
- ❌ Cannot use for fundraising/solicitation
- ✅ News organizations can use for reporting
- ✅ Academic research is permitted
- ✅ Public transparency projects are permitted

### What are the penalties for misuse?

Under 5 U.S.C. § 13107:
- **Federal criminal offense**
- Fine and/or imprisonment up to 1 year

### Do I need permission to use this data?

No permission needed for:
- Research
- Journalism
- Public transparency
- Educational use

**But you must**:
- Comply with statutory restrictions
- Cite the original source
- Not use for prohibited purposes

### Can I redistribute the data?

Yes, but:
- Must include attribution
- Must include legal disclaimer
- Recipients must also comply with 5 U.S.C. § 13107
- Consider MIT License terms

---

## Contributing

### How can I contribute?

Many ways:
- **Report bugs**: Open GitHub issues
- **Submit PRs**: Fix bugs, add features
- **Documentation**: Improve guides and examples
- **Test**: Run on your AWS account, report issues
- **Share**: Star the repo, tell others

See [[Contributing-Guide]] for details.

### What's the PR process?

1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes following coding standards
4. Add tests
5. Run `make check-contrib` (format, lint, test)
6. Submit PR with clear description

Maintainers review within 1-7 days.

### What should I work on?

Check GitHub issues labeled:
- `good-first-issue`: Beginner-friendly
- `help-wanted`: Community contributions needed
- `documentation`: Docs improvements

### Do you accept financial contributions?

Not currently. The project is designed to run on AWS Free Tier ($0/month), so funding isn't needed yet.

If you want to support: **Star the repo** and **share it** with others interested in government transparency.

---

## See Also

- [[Quick-Start-Guide]] - Get up and running in 15 minutes
- [[System-Architecture]] - How the pipeline works
- [[Troubleshooting]] - Common problems and solutions
- [[Contributing-Guide]] - How to contribute
- [[Legal-and-Compliance]] - Usage restrictions and compliance

---

**Still have questions?**

- Open a [GitHub Discussion](https://github.com/Jakeintech/congress-disclosures-standardized/discussions)
- Check the [GitHub Issues](https://github.com/Jakeintech/congress-disclosures-standardized/issues)
- Read the full documentation in the [docs/ directory](https://github.com/Jakeintech/congress-disclosures-standardized/tree/main/docs)
