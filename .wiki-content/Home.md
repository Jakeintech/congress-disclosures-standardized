# Congress Disclosures Standardized Wiki

**A comprehensive data pipeline for processing US Congressional financial disclosure reports**

[![GitHub Stars](https://img.shields.io/github/stars/Jakeintech/congress-disclosures-standardized)](https://github.com/Jakeintech/congress-disclosures-standardized)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![AWS](https://img.shields.io/badge/AWS-Lambda%20%7C%20S3%20%7C%20Step%20Functions-orange)](https://aws.amazon.com/)

---

## 🎯 What This Project Does

This project transforms **congressional financial disclosure PDFs** into **structured, queryable data** using a serverless AWS pipeline.

**Key Capabilities**:
- ✅ **15+ years of data** (2008-2025+)
- ✅ **All 12 filing types** (PTR, Annual, Termination, etc.)
- ✅ **3-layer medallion architecture** (Bronze → Silver → Gold)
- ✅ **Cost-optimized** ($15-50/month on AWS)
- ✅ **Free-tier friendly** with smart concurrency controls
- ✅ **Code-based extraction** (no expensive Textract)
- ✅ **Public API** for data access
- ✅ **Open source** (MIT License)

---

## 🚀 Quick Navigation

### I Want To...

**🏃 Get Started Fast**
- [Run locally in 15 minutes](Quick-Start-Guide)
- [Deploy to my AWS account](Self-Hosting-Guide)
- [Query the public API](API-Documentation)

**📚 Learn About The Project**
- [Understand the data](Data-Layers)
- [See the architecture](System-Architecture)
- [Review filing types](Filing-Types-Explained)

**💻 Develop & Contribute**
- [Set up development environment](Development-Setup)
- [Contribute code](Contributing-Guide)
- [AI Agent onboarding](AI-Agent-Onboarding)

**🛠️ Operate & Monitor**
- [Monitor the pipeline](Monitoring-Guide)
- [Troubleshoot issues](Troubleshooting)
- [Manage costs](Cost-Management)

**📖 Reference**
- [All commands](Command-Reference)
- [API endpoints](API-Endpoints-Reference)
- [Environment variables](Environment-Variables)

---

## 📊 Architecture At A Glance

```
House Clerk PDFs → Bronze (Raw) → Silver (Normalized) → Gold (Analytics)
                                                              ↓
                                                         Public API
                                                              ↓
                                                    Researchers, Journalists
```

**Technologies**: AWS Lambda | S3 | SQS | Step Functions | DynamoDB | Python 3.11 | Terraform

[Learn more about the architecture →](System-Architecture)

---

## 📁 Data Layers

### 🥉 Bronze Layer
**Purpose**: Byte-for-byte preservation of source data
- Original ZIP files from House Clerk
- XML metadata indexes
- Individual PDF files (15,000+ documents)

### 🥈 Silver Layer
**Purpose**: Cleaned, normalized, queryable data
- Parquet tables (filings, documents, text)
- Extracted text (gzipped)
- Structured JSON objects (by filing type)

### 🥇 Gold Layer
**Purpose**: Analytics-ready facts and dimensions
- Star schema (members, assets, dates)
- Fact tables (transactions, filings)
- Pre-computed aggregates (trending stocks, trading stats)

[Learn more about data layers →](Data-Layers)

---

## ⚖️ Legal & Compliance

This project complies with **5 U.S.C. § 13107** (Ethics in Government Act).

**✅ Permitted Uses**:
- Transparency & accountability
- Research & education
- News & journalism

**❌ Prohibited Uses**:
- Commercial products (except news/media)
- Credit rating determinations
- Political/charitable solicitation

[Read full legal notice →](Legal-and-Compliance)

---

## 🎓 For Different Audiences

### 📰 Researchers & Journalists
- Access structured trading data via [API](API-Documentation)
- Download Parquet files via [S3](Direct-S3-Access)
- Run [custom queries](Query-Examples)

### 💼 Self-Hosters
- Deploy to your AWS account: [Self-Hosting Guide](Self-Hosting-Guide)
- Customize extractors: [Adding Extractors](Adding-Extractors)
- Optimize costs: [Cost Management](Cost-Management)

### 👨‍💻 Developers
- Contribute improvements: [Contributing Guide](Contributing-Guide)
- Add new features: [Development Setup](Development-Setup)
- Write tests: [Testing Strategy](Testing-Strategy)

### 🤖 AI Agents
- Start here: [AI Agent Onboarding](AI-Agent-Onboarding)
- Follow workflow: [AI Agent Workflow](AI-Agent-Workflow)
- Claim tasks: [GitHub Projects Board](https://github.com/users/Jakeintech/projects/4)

### 🚨 Operations Teams
- Monitor pipelines: [Monitoring Guide](Monitoring-Guide)
- Respond to incidents: [Incident Response](Incident-Response)
- Manage queues: [Queue Management](Queue-Management)

---

## 📈 Project Status

| Component | Status | Details |
|-----------|--------|---------|
| **Bronze Ingestion** | ✅ Complete | House FD, Congress.gov, Lobbying |
| **Silver Transformation** | ✅ Complete | Parquet normalization, text extraction |
| **Gold Aggregation** | ✅ Complete | Facts, dimensions, pre-computed metrics |
| **Public API** | 🚧 Beta | Lambda endpoints deployed |
| **Website** | ✅ Live | congress-disclosures.org |
| **Documentation** | 📝 Ongoing | This wiki! |

[View roadmap →](https://github.com/Jakeintech/congress-disclosures-standardized/blob/main/docs/agile/ROADMAP.md)

---

## 💡 Key Features

### Step Functions Orchestration
- 4 state machines (House FD, Congress, Lobbying, Cross-dataset)
- Parallel processing with `MaxConcurrency: 10`
- Watermarking to prevent duplicate processing
- Quality gates with Soda checks

[Learn more →](State-Machines)

### Cost Optimization
- **Before**: $4,000/month (hourly triggers)
- **After**: $15-50/month (on-demand + optimizations)
- 95% cost reduction through smart scheduling

[Learn more →](Cost-Management)

### Intelligent Extraction
- **Direct text** (pypdf) → Free, fast, 95% accuracy
- **OCR fallback** (Tesseract) → Free, slower, 80-90% accuracy
- **Textract fallback** → Paid ($1.50/1000 pages), highest accuracy

[Learn more →](Extraction-Architecture)

---

## 🛠️ Technology Stack

**Infrastructure**: Terraform, AWS (Lambda, S3, SQS, Step Functions, DynamoDB, CloudWatch)
**Runtime**: Python 3.11
**Data Formats**: Parquet (Silver/Gold), JSON (Bronze), gzip (text)
**Extraction**: pypdf, Tesseract OCR, AWS Textract (fallback)
**Orchestration**: AWS Step Functions, EventBridge, SQS
**Testing**: pytest, moto (AWS mocking)
**CI/CD**: GitHub Actions
**Monitoring**: CloudWatch Logs, Alarms, X-Ray

---

## 🤝 Contributing

We welcome contributions! This project uses an **agile workflow** with GitHub Projects.

**How to contribute**:
1. Browse [open issues](https://github.com/Jakeintech/congress-disclosures-standardized/issues)
2. Read [Contributing Guide](Contributing-Guide)
3. Follow [commit conventions](Commit-Conventions)
4. Submit a [pull request](PR-Process)

**For AI agents**: See [AI Agent Onboarding](AI-Agent-Onboarding)

---

## ❓ FAQ

**Q: How much does it cost to run?**
A: $15-50/month on AWS free tier. [Details →](Cost-Management)

**Q: Is this legal to use?**
A: Yes, with restrictions (5 U.S.C. § 13107). [Details →](Legal-and-Compliance)

**Q: Can I run this locally?**
A: Yes! [Quick Start Guide →](Quick-Start-Guide)

[View all FAQs →](FAQ)

---

## 📚 Additional Resources

- **GitHub Repository**: [github.com/Jakeintech/congress-disclosures-standardized](https://github.com/Jakeintech/congress-disclosures-standardized)
- **Live Website**: congress-disclosures.org
- **GitHub Discussions**: [Ask questions](https://github.com/Jakeintech/congress-disclosures-standardized/discussions)
- **GitHub Issues**: [Report bugs](https://github.com/Jakeintech/congress-disclosures-standardized/issues)
- **API Documentation**: [API Endpoints →](API-Endpoints-Reference)

---

## 📞 Support

**Have questions?**
- Check the [FAQ](FAQ)
- Browse [Troubleshooting guide](Troubleshooting)
- Search this wiki (top right)
- Open a [GitHub Discussion](https://github.com/Jakeintech/congress-disclosures-standardized/discussions)
- File an [issue](https://github.com/Jakeintech/congress-disclosures-standardized/issues)

---

**Last Updated**: 2025-12-28
**License**: MIT
**Maintained by**: [Jakeintech](https://github.com/Jakeintech) and [contributors](https://github.com/Jakeintech/congress-disclosures-standardized/graphs/contributors)
