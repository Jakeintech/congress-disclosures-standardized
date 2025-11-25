# PDF Extraction Methods Comparison

## Overview

To ensure data quality and accuracy, we maintain **multiple extraction methods** and store their outputs separately for comparison. This allows us to:
1. Compare extraction accuracy between methods
2. Choose the best method for each PDF type
3. Continuously improve our extraction pipeline
4. Verify Textract accuracy justifies its cost

## Extraction Methods

### 1. **pypdf** (Code-Based, Free)
- **Type**: Text-based PDF extraction
- **Cost**: $0 (free Python library)
- **Speed**: Fast (~50-100ms per document)
- **Accuracy**: 95-99% for text-based PDFs
- **Limitations**: Cannot extract from image-based PDFs
- **Use Case**: Primary method for PDFs with embedded text

### 2. **Textract** (AWS Service, Paid)
- **Type**: OCR + text extraction with ML
- **Cost**: $1.50 per 1,000 pages (1,000 pages/month free for 3 months)
- **Speed**: Medium (~500-2000ms per document)
- **Accuracy**: 90-95% for image-based PDFs
- **Limitations**: Costs money, slower than pypdf
- **Use Case**: Image-based PDFs (scanned documents)

### 3. **Tesseract** (Open Source OCR, Free) - *Future*
- **Type**: Open source OCR
- **Cost**: $0 (free, open source)
- **Speed**: Slow (~2-5s per document)
- **Accuracy**: 75-85% for image-based PDFs
- **Limitations**: Lower accuracy than Textract
- **Use Case**: Fallback for image PDFs when Textract budget exhausted

### 4. **AI Structured Extraction** (Code-Based)
- **Type**: AI/LLM-based structured data extraction
- **Cost**: Depends on LLM used (Claude, GPT, etc.)
- **Input**: Text from any extraction method above
- **Output**: Structured JSON (transactions, assets, etc.)
- **Accuracy**: 85-95% depending on input text quality

## Data Storage Strategy

### Silver Layer Structure

```
silver/house/financial/
  text/                                    # Raw text extraction outputs
    extraction_method=pypdf/
      year=2025/
        doc_id=10072809/
          raw_text.txt.gz                  # pypdf extracted text
    extraction_method=textract/
      year=2025/
        doc_id=10072809/
          raw_text.txt.gz                  # Textract extracted text
          textract_response.json.gz        # Raw Textract JSON for comparison
    extraction_method=tesseract/           # Future
      year=2025/
        doc_id=10072809/
          ocr_text.txt.gz                  # Tesseract OCR text

  structured/                              # Structured extraction outputs
    extraction_method=ai-pypdf/
      year=2025/
        doc_id=10072809/
          structured.json                  # AI extraction from pypdf text
    extraction_method=ai-textract/
      year=2025/
        doc_id=10072809/
          structured.json                  # AI extraction from Textract text

  documents/                               # Metadata tracking
    year=2025/
      part-0000.parquet                    # Tracks which methods were used
```

## Metadata Tracking

The `house_fd_documents` table tracks which extraction method was used:

```python
{
  "doc_id": "10072809",
  "year": 2025,
  "extraction_method": "pypdf",              # Which method was used
  "textract_pages_used": 0,                  # Pages processed with Textract
  "requires_textract_reprocessing": false,   # Needs Textract for better accuracy?
  "extraction_month": "2025-11",             # When extraction happened
  "text_s3_key": "silver/.../raw_text.txt.gz"  # Path to extracted text
}
```

## Comparison Workflow

### 1. Compare Raw Extraction Quality

Query documents extracted with multiple methods:

```python
# Get documents with both pypdf and Textract extractions
docs_with_both = query_documents(
    extraction_methods=["pypdf", "textract"]
)

for doc in docs_with_both:
    pypdf_text = read_s3(f"silver/.../extraction_method=pypdf/.../raw_text.txt.gz")
    textract_text = read_s3(f"silver/.../extraction_method=textract/.../raw_text.txt.gz")
    textract_json = read_s3(f"silver/.../extraction_method=textract/.../textract_response.json.gz")

    # Compare lengths, character accuracy, etc.
    compare_extraction_quality(pypdf_text, textract_text, textract_json)
```

### 2. Compare Structured Extraction Accuracy

Query structured outputs from different extraction methods:

```python
# Get structured data from both pypdf and Textract sources
ai_pypdf_structured = read_s3(f"silver/.../extraction_method=ai-pypdf/.../structured.json")
ai_textract_structured = read_s3(f"silver/.../extraction_method=ai-textract/.../structured.json")

# Compare transaction counts, asset values, etc.
compare_structured_accuracy(ai_pypdf_structured, ai_textract_structured)
```

### 3. Cost-Benefit Analysis

Track extraction costs and accuracy:

```sql
-- Total Textract costs this month
SELECT
    COUNT(*) as docs_processed,
    SUM(textract_pages_used) as total_pages,
    SUM(textract_pages_used) * 0.0015 as estimated_cost  -- $1.50 per 1,000 pages
FROM house_fd_documents
WHERE extraction_month = '2025-11'
  AND extraction_method LIKE 'textract%'
```

## Decision Tree

```
PDF Document
    │
    ├─ Has embedded text? (detect_has_text_layer)
    │   │
    │   ├─ YES → Use pypdf (fast, free, accurate)
    │   │         Store: silver/text/extraction_method=pypdf/
    │   │
    │   └─ NO → Image-based PDF
    │       │
    │       ├─ Textract budget available?
    │       │   │
    │       │   ├─ YES → Use Textract (paid, accurate)
    │       │   │         Store: silver/text/extraction_method=textract/
    │       │   │                (includes raw JSON for comparison)
    │       │   │
    │       │   └─ NO → Use pypdf + mark for reprocessing
    │       │             Store: silver/text/extraction_method=pypdf/
    │       │             Set: requires_textract_reprocessing=true
    │       │
    │       └─ (Future) Tesseract fallback
    │                   Store: silver/text/extraction_method=tesseract/
```

## Viewing & Comparing Extractions

### AWS Console

Navigate to S3 bucket: `congress-disclosures-standardized/silver/house/financial/text/`

View by extraction method:
- `extraction_method=pypdf/` - Free text extraction
- `extraction_method=textract/` - Paid OCR extraction (with raw JSON)

### Command Line

```bash
# List pypdf extractions
aws s3 ls s3://congress-disclosures-standardized/silver/house/financial/text/extraction_method=pypdf/year=2025/ --recursive

# List Textract extractions (includes raw JSON)
aws s3 ls s3://congress-disclosures-standardized/silver/house/financial/text/extraction_method=textract/year=2025/ --recursive

# Download and compare
aws s3 cp s3://.../extraction_method=pypdf/year=2025/doc_id=X/raw_text.txt.gz - | gunzip
aws s3 cp s3://.../extraction_method=textract/year=2025/doc_id=X/raw_text.txt.gz - | gunzip
aws s3 cp s3://.../extraction_method=textract/year=2025/doc_id=X/textract_response.json.gz - | gunzip | jq .
```

### Website/UI Comparison View

Future UI features:
- Side-by-side comparison of extraction methods
- Accuracy metrics dashboard
- Cost vs quality analysis
- Method recommendation system

## Quality Metrics

Track these metrics for each extraction method:

1. **Text Quality**
   - Character count
   - Word count
   - Special character handling
   - Line break preservation

2. **Structured Data Accuracy**
   - Transaction count matches
   - Asset value accuracy
   - Date parsing success rate
   - Checkbox/boolean detection

3. **Performance**
   - Extraction time (ms)
   - Cost per document
   - Success rate

4. **Coverage**
   - Percentage of documents processable
   - Failure rate by PDF type

## Budget Management

### Textract Free Tier Strategy

**Free Tier**: 1,000 pages/month for 3 months (new AWS customers)

**Budget Tracking**:
```python
# Check current month usage
monthly_usage = query_textract_pages_used(month="2025-11")
# Returns: 0/1,000 pages used

# Process newest documents first within budget
process_documents_with_textract(
    order_by="filing_date DESC",
    max_pages=1000 - monthly_usage
)
```

**After Free Tier**:
- Monthly processing limit: 1,000 pages (~$1.50/month)
- Prioritize newest/most important documents
- Use pypdf for text-based PDFs (still free)
- Mark image PDFs for next month's batch

## Continuous Improvement

### Monthly Review Process

1. **Accuracy Review**: Compare extraction methods for sample documents
2. **Cost Analysis**: Evaluate Textract ROI
3. **Method Selection**: Update decision tree based on findings
4. **Documentation**: Update this doc with learnings

### Feedback Loop

```python
# Flag documents for manual review
if confidence_score < 0.85:
    flag_for_manual_review(doc_id, extraction_method)

# Learn from manual corrections
manual_corrections = get_manual_corrections()
improve_extraction_pipeline(manual_corrections)
```

---

**Last Updated**: 2025-11-25
**Maintainer**: Data Engineering Team
