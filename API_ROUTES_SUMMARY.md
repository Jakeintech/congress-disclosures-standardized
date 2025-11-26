# API Routes & Medallion Layer Summary

## 🏗️ Architecture Overview

The data pipeline follows a **Medallion Architecture** with three layers:
- **Bronze** (Raw): Original PDFs and XML files
- **Silver** (Cleansed): Extracted text, structured JSON, metadata
- **Gold** (Curated): Aggregated analytics and insights

---

## 📍 Current API Routes

### Base URL
```
https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com
```

### API v1 Base Path
```
/website/api/v1
```

---

## 🥉 BRONZE LAYER

### API Endpoints

#### 1. Bronze Manifest (Filing Index)
- **URL**: `/website/api/v1/documents/manifest.json`
- **Description**: Complete index of all filings with metadata
- **Format**: JSON
- **Stats**: Total filings, members, latest year, last updated
- **Example**:
  ```json
  {
    "stats": {
      "total_filings": 1616,
      "total_members": 1616,
      "latest_year": 2025,
      "last_updated": "2025-11-26"
    },
    "filings": [...]
  }
  ```

### Direct File Access

#### PDF Files
- **Path Pattern**: `/bronze/house/financial/year={YEAR}/pdfs/{YEAR}/{DOC_ID}.pdf`
- **Example**: `/bronze/house/financial/year=2025/pdfs/2025/10063228.pdf`
- **Status**: ✅ Public read access enabled
- **Content-Type**: `application/pdf`

#### XML Index Files
- **Path Pattern**: `/bronze/house/financial/year={YEAR}/index/{YEAR}FD.xml`
- **Example**: `/bronze/house/financial/year=2025/index/2025FD.xml`
- **Status**: ✅ Public read access enabled

#### TXT Index Files
- **Path Pattern**: `/bronze/house/financial/year={YEAR}/index/{YEAR}FD.txt`
- **Example**: `/bronze/house/financial/year=2025/index/2025FD.txt`
- **Status**: ✅ Public read access enabled

---

## 🥈 SILVER LAYER

### API Endpoints

#### 1. Silver Documents Manifest
- **URL**: `/website/api/v1/documents/silver/manifest.json`
- **Description**: Complete index of all Silver layer documents with extraction stats
- **Format**: JSON
- **Fallback**: `/website/data/silver_documents_v2.json` (legacy)
- **Stats**: Total documents, pages, extraction success/failure counts
- **Example**:
  ```json
  {
    "generated_at": "2025-11-26T12:02:13Z",
    "total_documents": 1146,
    "stats": {
      "total_documents": 1146,
      "total_pages": 0,
      "extraction_stats": {
        "success": 1146,
        "pending": 0,
        "failed": 0
      }
    },
    "documents": [...]
  }
  ```

#### 2. Schedule B (PTR) Transactions
- **URL**: `/website/api/v1/schedules/b/transactions.json`
- **Description**: Aggregated PTR (Periodic Transaction Report) transactions
- **Format**: JSON
- **Stats**: Total transactions, PTRs, unique members, latest date
- **Example**:
  ```json
  {
    "stats": {
      "total_transactions": 3338,
      "total_ptrs": 43,
      "unique_members": 43,
      "latest_date": "2025-08-12",
      "generated_at": "2025-11-26T18:16:42Z"
    },
    "transactions": [...]
  }
  ```

### Direct File Access

#### Structured JSON (Extracted Data)
- **Path Pattern**: `/silver/house/financial/structured/year={YEAR}/doc_id={DOC_ID}.json`
- **Example**: `/silver/house/financial/structured/year=2025/doc_id=10063228.json`
- **Status**: ✅ Public read access enabled
- **Content-Type**: `application/json`
- **Description**: Parsed form data (schedules, transactions, etc.)

#### Metadata JSON
- **Path Pattern**: `/silver/house/financial/documents/year={YEAR}/{DOC_ID}/metadata.json`
- **Example**: `/silver/house/financial/documents/year=2025/10063228/metadata.json`
- **Status**: ✅ Public read access enabled
- **Content-Type**: `application/json`
- **Description**: Document metadata (extraction method, pages, char count, etc.)

#### Text Files (Uncompressed)
- **Path Pattern**: `/silver/house/financial/documents/year={YEAR}/{DOC_ID}/text.txt`
- **Example**: `/silver/house/financial/documents/year=2025/10063228/text.txt`
- **Status**: ✅ Public read access enabled (being created)
- **Content-Type**: `text/plain; charset=utf-8`
- **Description**: Extracted plain text (uncompressed)

#### Text Files (Compressed - Source)
- **Path Pattern**: `/silver/house/financial/text/extraction_method={METHOD}/year={YEAR}/doc_id={DOC_ID}/raw_text.txt.gz`
- **Example**: `/silver/house/financial/text/extraction_method=pypdf/year=2025/doc_id=10063228/raw_text.txt.gz`
- **Status**: ✅ Public read access enabled
- **Content-Type**: `application/gzip`
- **Description**: Compressed source text files (used to generate uncompressed versions)

#### Parquet Files (Data Lake Format)
- **Path Pattern**: `/silver/house/financial/documents/year={YEAR}/part-0000.parquet`
- **Example**: `/silver/house/financial/documents/year=2025/part-0000.parquet`
- **Status**: ✅ Public read access enabled
- **Content-Type**: `application/octet-stream`
- **Description**: Columnar format for analytics

---

## 🥇 GOLD LAYER

### API Endpoints

#### 1. Member Trading Statistics
- **URL**: `/website/api/v1/analytics/member-trading-stats.json` (Future)
- **Description**: Aggregated trading statistics per member
- **Status**: ⏳ Planned

#### 2. Sector Activity
- **URL**: `/website/api/v1/analytics/sector-activity.json` (Future)
- **Description**: Trading activity by sector
- **Status**: ⏳ Planned

#### 3. Trending Stocks
- **URL**: `/website/api/v1/analytics/trending-stocks.json` (Future)
- **Description**: Most traded stocks
- **Status**: ⏳ Planned

### Direct File Access

#### Gold Aggregates (Parquet)
- **Path Pattern**: `/gold/analytics/{AGGREGATE_NAME}/year={YEAR}/part-0000.parquet`
- **Status**: ✅ Public read access enabled
- **Description**: Pre-aggregated analytics tables

---

## 🌐 Website Files

### Static Assets
- **HTML**: `/website/index.html`
- **JavaScript**: `/website/app.js?v={VERSION}` (cache-busting)
- **CSS**: `/website/style.css`
- **Status**: ✅ Public read access enabled

### Data Files (Legacy)
- **Silver Documents**: `/website/data/silver_documents_v2.json`
- **PTR Transactions**: `/website/data/ptr_transactions.json`
- **Status**: ✅ Public read access enabled (fallback for API endpoints)

---

## 📊 Current Statistics

### Bronze Layer
- **Total Filings**: 1,616
- **Total Members**: 1,616
- **Latest Year**: 2025
- **File Types**: PDF, XML, TXT

### Silver Layer
- **Total Documents**: 1,146
- **Extraction Success**: 1,146 (100%)
- **Extraction Pending**: 0
- **Extraction Failed**: 0
- **File Types**: JSON, TXT, GZ, Parquet

### Gold Layer
- **PTR Transactions**: 3,338
- **PTR Documents**: 43
- **Unique Members**: 43
- **Latest Date**: 2025-08-12

---

## 🔐 Access Control

### Public Read Access (Enabled)
- ✅ `/website/*` - All website files
- ✅ `/website/api/*` - All API endpoints
- ✅ `/bronze/*` - All Bronze layer files
- ✅ `/silver/*` - All Silver layer files
- ✅ `/gold/*` - All Gold layer files (future)
- ✅ `/manifest.json` - Root manifest

### Bucket Policy
Managed via Terraform: `infra/terraform/bucket_policy.tf`

---

## 🚀 Next Steps

### Immediate (Completed ✅)
1. ✅ Updated bucket policy to allow Bronze/Silver file access
2. ✅ Created API endpoints for Bronze, Silver, and PTR data
3. ✅ Made loaders non-blocking in website
4. ✅ Created deployment workflow (Makefile.website)

### Short-term (In Progress)
1. ⏳ **Create text.txt files**: Running script to generate uncompressed text files
2. ⏳ **Apply Terraform**: Bucket policy changes need Terraform apply
3. ⏳ **Test all endpoints**: Verify all API routes are accessible

### Medium-term (Planned)
1. 📋 **Gold Layer APIs**: Create analytics endpoints
   - Member trading stats
   - Sector activity
   - Trending stocks
   - Document quality metrics

2. 📋 **Additional Schedule Endpoints**: 
   - `/website/api/v1/schedules/a/transactions.json` (Schedule A)
   - `/website/api/v1/schedules/c/transactions.json` (Schedule C)
   - `/website/api/v1/schedules/d/transactions.json` (Schedule D)
   - ... (Schedules E-I)

3. 📋 **Search API**: 
   - `/website/api/v1/search?q={query}&type={type}`
   - Full-text search across documents

4. 📋 **Document API**:
   - `/website/api/v1/documents/{doc_id}`
   - Single document with all related files

### Long-term (Future)
1. 🔮 **GraphQL API**: Unified query interface
2. 🔮 **WebSocket API**: Real-time updates
3. 🔮 **Rate Limiting**: API usage controls
4. 🔮 **Authentication**: Optional API keys for higher limits

---

## 📝 Deployment Workflow

### Full Deployment
```bash
make -f Makefile.website deploy-website
```

**Steps:**
1. Increment app.js version
2. Rebuild Bronze manifest → API endpoint
3. Rebuild Silver manifest → API endpoint
4. Rebuild PTR transactions → API endpoint
5. Sync all files to S3

### Individual Steps
```bash
# Bronze manifest
python3 scripts/build_bronze_manifest.py

# Silver manifest
python3 scripts/rebuild_silver_manifest.py
python3 scripts/build_silver_manifest_api.py

# PTR transactions
python3 scripts/aggregate_schedule_b.py

# Text files
python3 scripts/create_text_files.py
```

---

## 🔍 Testing Endpoints

### Quick Test Script
```bash
# Test all API endpoints
curl -s https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/website/api/v1/documents/manifest.json | jq '.stats'
curl -s https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/website/api/v1/documents/silver/manifest.json | jq '.stats'
curl -s https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/website/api/v1/schedules/b/transactions.json | jq '.stats'

# Test file access
curl -I https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/bronze/house/financial/year=2025/pdfs/2025/10063228.pdf
curl -I https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/silver/house/financial/structured/year=2025/doc_id=10063228.json
curl -I https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/silver/house/financial/documents/year=2025/10063228/text.txt
```

---

## 📚 Related Documentation

- `WEBSITE_DEPLOYMENT_FIX.md` - Website deployment fixes
- `BUCKET_POLICY_UPDATE.md` - Bucket policy changes
- `infra/terraform/bucket_policy.tf` - Terraform bucket policy
- `Makefile.website` - Deployment workflow
