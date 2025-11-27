# Comprehensive PDF Extraction Pipeline Roadmap

**Status**: In Progress - Sprint 1
**Last Updated**: 2025-11-27
**Goal**: Free-tier-first extraction with human-in-loop Textract approval

---

## Executive Summary

This document outlines ALL remaining tasks to build a production-ready, agent-orchestrated PDF extraction pipeline. The architecture prioritizes **free extraction methods first** (text + OCR), then escalates to **human-approved Textract** only when necessary.

### Current State
- **Bronze Layer**: 2,761 PDFs ingested ✅
- **Text Extraction**: 1,560 PDFs extracted (in progress: 2,761 queued)
- **Structured Extraction**: 0 code-based, 1,135 Textract-based (legacy)
- **DLQ Issues**: Fixed (S3 path mismatch resolved)
- **Textract Auto-Call**: Disabled ✅

---

## Architecture: Agent-Friendly Extraction Pipeline

This pipeline is designed for **deterministic agent orchestration** with clear inputs, outputs, and conditions.

### Module Flow

```
PDF → [1] Classify → [2] Load Template → [3] Extract Regions →
[4] Normalize → [5] Pattern Match → [6] OCR Fallback →
[7] LLM Cleanup (Optional) → [8] Schema Validate → [9] Output JSON
```

### Module Specifications

#### Module 1: Document Classification
**Input**: `pdf_s3_key`
**Output**: `document_type` (PTR, Form_A, Form_B, Extension_Request, etc.)
**Method**: Existing text-based detection in `detect_filing_type(text)`
**Status**: ✅ Implemented (handler.py:125-168)

#### Module 2: Load Template Metadata
**Input**: `document_type`
**Output**: `template_regions.json`, `patterns.yaml`, `schema.json`
**Status**: ⚠️ Partial - schemas exist, need regions/patterns
**Location**:
- Schemas: `ingestion/schemas/house_fd_*.json`
- Regions: **TODO** - create `ingestion/templates/{type}/regions.json`
- Patterns: **TODO** - create `ingestion/templates/{type}/patterns.yaml`

#### Module 3: Extract Raw Text by Region
**Input**: `pdf_file`, `template_regions`
**Output**: `raw_extracts = {field_name: text_content}`
**Method Priority**:
1. Try pypdf text extraction (FREE, already working)
2. If empty/rasterized → OCR with Tesseract (FREE, not yet implemented)
3. Store extraction source: `text` or `ocr`

**Status**: ⚠️ Partial - pypdf works, Tesseract not integrated

#### Module 4: Normalize Extracted Text
**Input**: `raw_extracts`
**Output**: `normalized_extracts`
**Steps** (agent must apply in order):
1. Trim whitespace
2. Remove line-break artifacts (e.g., "Congr-\ness" → "Congress")
3. Fix broken hyphenations
4. Normalize numbers ("I20" → "120", "O" → "0")
5. Convert dates to canonical formats

**Status**: ⚠️ Partial - basic cleaning in PTRExtractor, needs standardization

#### Module 5: Pattern Application (Regex Parsing)
**Input**: `normalized_extracts`, `template_patterns`
**Output**: `structured_fields = {field_name: value or null}`
**Rules**:
- Apply each regex exactly once per field
- If multiple matches: pick first
- If no matches: set to null
- **Never hallucinate or guess**

**Status**: ✅ Implemented in PTRExtractor for PTR files
**TODO**: Implement for Form A/B, Extension, etc.

#### Module 6: OCR Fallback (For Scanned PDFs)
**Input**: `pdf_file`, `failed_regions` (where text extraction returned empty)
**Output**: `ocr_extracts`
**Method**:
- Convert PDF page to image (pdf2image)
- Preprocess: grayscale, denoise, deskew, enhance contrast
- Run Tesseract OCR (FREE)
- Merge with text extracts

**Status**: ❌ Not implemented
**Priority**: High (many PDFs are scanned/poor quality)

#### Module 7: LLM Cleanup (Optional, Low Priority)
**Input**: `structured_fields`, `output_schema`
**Output**: `llm_corrected_fields`
**Trigger Conditions**:
- Field is null after all extraction attempts
- Field fails schema validation
- Field contains detectable formatting errors

**Method**: Small local LLM (e.g., Llama 3.2 1B) with constrained prompt
**Status**: ❌ Not planned for initial release
**Priority**: Low (can add in future sprint)

#### Module 8: Schema Validation
**Input**: `structured_fields`, `output_schema`
**Output**: `validated_json` or validation errors
**Method**: Python `jsonschema` library
**Rules**:
1. If valid → proceed to finalize
2. If invalid → log errors, set confidence = 0
3. If LLM cleanup enabled → retry once
4. If still invalid → queue for human review

**Status**: ⚠️ Partial - schemas exist, validation not enforced

#### Module 9: Finalize & Output
**Input**: `document_type`, `validated_json`, `extraction_metadata`
**Output**:
```json
{
  "doc_id": "20026548",
  "year": 2025,
  "filing_type": "PTR",
  "extraction_metadata": {
    "method": "code_based",
    "extraction_sources": ["text", "ocr"],
    "confidence_score": 0.85,
    "textract_recommended": false,
    "missing_fields": ["spouse_dependent_transactions"],
    "extraction_timestamp": "2025-11-27T19:00:00Z"
  },
  "fields": { ...validated_json... }
}
```

**Status**: ✅ Implemented in house_fd_extract_structured_code

---

## Sprint Breakdown

### **SPRINT 1: Code-Based PTR Extraction** (Current)

**Goal**: Extract 1,500+ PTR files using existing PTRExtractor (FREE)

#### Tasks

- [x] 1.1: Create house_fd_extract_structured_code Lambda handler (DONE)
- [ ] 1.2: Create requirements.txt for new Lambda
- [ ] 1.3: Update scripts/package_lambdas.sh to include new Lambda
- [ ] 1.4: Package Lambda with extractors library
- [ ] 1.5: Create Terraform config for structured_code Lambda
- [ ] 1.6: Create SQS queue: code_extraction_queue
- [ ] 1.7: Wire extract_document → code_extraction_queue (after text extraction)
- [ ] 1.8: Deploy Lambda and queue to AWS
- [ ] 1.9: Test with 10 PTR samples (verify field capture)
- [ ] 1.10: Monitor extraction: confidence scores, missing fields
- [ ] 1.11: Update pipeline_status.json to track code-based extractions

**Deliverables**:
- Deployed Lambda: `congress-disclosures-development-extract-structured-code`
- SQS Queue: `congress-disclosures-development-code-extraction-queue`
- S3 Output: `silver/house/financial/structured_code/year=2025/filing_type=PTR/`
- Test Results: Field capture rates for 10 PTR samples

**Estimated Time**: 2-3 hours

---

### **SPRINT 2: Template-Based Form A/B Extraction**

**Goal**: Extract Form A/B using text + patterns (60-80% field capture), NO Textract

#### Tasks

##### 2.1: Template Creation
- [ ] 2.1.1: Analyze 20 Form A samples to identify text patterns
- [ ] 2.1.2: Create `ingestion/templates/form_a/regions.json` (bounding boxes for key sections)
- [ ] 2.1.3: Create `ingestion/templates/form_a/patterns.yaml` (regex patterns per field)
- [ ] 2.1.4: Create `ingestion/templates/form_b/regions.json`
- [ ] 2.1.5: Create `ingestion/templates/form_b/patterns.yaml`

##### 2.2: FormABTextExtractor Implementation
- [ ] 2.2.1: Create `ingestion/lib/extractors/form_ab_text_extractor.py`
- [ ] 2.2.2: Implement header parsing (name, office, state, filing_date)
- [ ] 2.2.3: Implement checkbox detection (YES/NO fields via text proximity)
- [ ] 2.2.4: Implement table detection (whitespace/alignment-based)
- [ ] 2.2.5: Implement Schedule routing (A-I detection)
- [ ] 2.2.6: Add confidence scoring (% of expected fields found)
- [ ] 2.2.7: Add gap tracking (list missing fields per schedule)

##### 2.3: Integration
- [ ] 2.3.1: Update house_fd_extract_structured_code to route Form A/B to new extractor
- [ ] 2.3.2: Test with 20 Form A samples
- [ ] 2.3.3: Test with 10 Form B samples
- [ ] 2.3.4: Document field capture rates per schedule

**Deliverables**:
- Template files for Form A/B
- FormABTextExtractor class
- Test results showing 60-80% field capture
- Gap analysis showing which fields need Textract

**Estimated Time**: 6-8 hours

---

### **SPRINT 3: OCR Fallback for Scanned PDFs**

**Goal**: Handle scanned/poor-quality PDFs using Tesseract OCR (FREE)

#### Tasks

##### 3.1: OCR Infrastructure
- [ ] 3.1.1: Add Tesseract to Lambda layer (or use Lambda container image)
- [ ] 3.1.2: Add pdf2image, Pillow to requirements
- [ ] 3.1.3: Create `ingestion/lib/ocr_processor.py`

##### 3.2: Image Preprocessing Pipeline
- [ ] 3.2.1: Implement PDF page → image conversion
- [ ] 3.2.2: Implement grayscale conversion
- [ ] 3.2.3: Implement denoising (cv2.fastNlMeansDenoising)
- [ ] 3.2.4: Implement deskewing (detect angle, rotate)
- [ ] 3.2.5: Implement contrast enhancement (CLAHE)
- [ ] 3.2.6: Implement binarization (Otsu's method)

##### 3.3: OCR Extraction
- [ ] 3.3.1: Implement region-based OCR (extract specific bounding boxes)
- [ ] 3.3.2: Implement OCR confidence scoring (Tesseract provides this)
- [ ] 3.3.3: Add OCR result caching (avoid re-OCR on retry)
- [ ] 3.3.4: Integrate OCR fallback into Module 3 (text extraction)

##### 3.4: Quality Detection
- [ ] 3.4.1: Detect scanned PDFs (no embedded text)
- [ ] 3.4.2: Detect poor-quality scans (low confidence OCR)
- [ ] 3.4.3: Flag for human review if OCR confidence < 0.6

##### 3.5: Testing
- [ ] 3.5.1: Test with 10 scanned PTR samples
- [ ] 3.5.2: Test with 10 scanned Form A samples
- [ ] 3.5.3: Compare OCR vs text extraction quality

**Deliverables**:
- OCR Lambda layer (or container image)
- OCR preprocessing pipeline
- OCR-extracted structured data
- Quality comparison report

**Estimated Time**: 8-10 hours

---

### **SPRINT 4: Admin UI - Extraction Review & Textract Approval**

**Goal**: Human-in-loop workflow for gap analysis and Textract approval

#### Tasks

##### 4.1: Backend API
- [ ] 4.1.1: Create API endpoint: `GET /api/extractions/stats` (overall stats)
- [ ] 4.1.2: Create API endpoint: `GET /api/extractions/pending` (low-confidence docs)
- [ ] 4.1.3: Create API endpoint: `GET /api/extractions/{doc_id}` (detail view)
- [ ] 4.1.4: Create API endpoint: `POST /api/extractions/{doc_id}/approve-textract`
- [ ] 4.1.5: Create API endpoint: `POST /api/extractions/batch-approve` (pattern-based)

##### 4.2: Admin UI Pages
- [ ] 4.2.1: Create `website/admin/extraction_review.html`
- [ ] 4.2.2: Build extraction stats dashboard (by filing type)
- [ ] 4.2.3: Build pending review table (sortable, filterable)
- [ ] 4.2.4: Build detail modal:
  - Left: PDF viewer with highlighting
  - Right: Extracted JSON with missing fields highlighted in red
  - Bottom: Approve/Reject buttons
- [ ] 4.2.5: Build pattern analysis view:
  - "80% of Form A missing Schedule G" → Batch approve Textract for Schedule G
- [ ] 4.2.6: Build Textract budget tracker (pages used/remaining)

##### 4.3: Textract Approval Queue
- [ ] 4.3.1: Create SQS queue: `textract_approval_queue`
- [ ] 4.3.2: Update house_fd_extract_structured_code to queue low-confidence docs
- [ ] 4.3.3: Create Lambda: `house_fd_textract_approved` (processes approved docs)
- [ ] 4.3.4: Implement manual trigger workflow (only on human approval)

##### 4.4: Data Visibility (User's Primary Request)
- [ ] 4.4.1: Create UI table views for each filing type:
  - PTR: All transactions table (sortable, filterable)
  - Form A: All assets table with schedules
  - Form B: Similar to Form A
- [ ] 4.4.2: Show existing 1,135 Textract-extracted JSONs
- [ ] 4.4.3: Show new code-extracted JSONs
- [ ] 4.4.4: Add filtering: by year, by filing type, by member
- [ ] 4.4.5: Add export: CSV/JSON download per filing type

**Deliverables**:
- Extraction review admin UI
- Textract approval workflow
- Data transparency tables
- Budget tracking dashboard

**Estimated Time**: 10-12 hours

---

### **SPRINT 5: Debugging & Monitoring Tools**

**Goal**: Operational excellence - debug, monitor, and optimize pipeline

#### Tasks

##### 5.1: Debug Pipeline Command
- [ ] 5.1.1: Create `scripts/debug_pipeline.py`
- [ ] 5.1.2: Implement end-to-end tracing:
  ```bash
  make debug-pipeline doc_id=20026548
  ```
  **Output**:
  - Bronze PDF status (exists? size? metadata?)
  - Extraction queue message (sent? received? failed?)
  - Lambda logs (house_fd_extract_document)
  - Text extraction output (S3 path, size, snippet)
  - Code extraction queue message
  - Lambda logs (house_fd_extract_structured_code)
  - Structured JSON output (S3 path, confidence, missing fields)
  - DLQ status (in DLQ? error message?)
- [ ] 5.1.3: Add visual pipeline diagram with status indicators
- [ ] 5.1.4: Add retry commands at each stage

##### 5.2: Enhanced Queue Management
- [ ] 5.2.1: Create failure classification queues:
  - `extraction_dlq_duplicate_id`
  - `extraction_dlq_poor_quality`
  - `extraction_dlq_corrupted_pdf`
  - `extraction_dlq_unknown_type`
- [ ] 5.2.2: Update Lambda error handling to route to specific DLQs
- [ ] 5.2.3: Create `make classify-dlq-failures` command
- [ ] 5.2.4: Create retry workflows per failure type

##### 5.3: Monitoring Dashboard
- [ ] 5.3.1: Create real-time pipeline metrics:
  - PDFs processed/hour
  - Text extraction success rate
  - Code extraction confidence distribution
  - Textract budget burn rate
  - DLQ failure breakdown
- [ ] 5.3.2: Add CloudWatch alarms:
  - DLQ depth > 100
  - Textract budget > 80% used
  - Extraction success rate < 90%
- [ ] 5.3.3: Create daily digest email (summary of pipeline health)

##### 5.4: Data Quality Validation
- [ ] 5.4.1: Wire data_quality_validator Lambda (already created, not integrated)
- [ ] 5.4.2: Implement validation rules:
  - Required fields present
  - Date formats valid
  - Amounts are numeric
  - Filing type matches expected schema
- [ ] 5.4.3: Generate data quality reports (S3 output)
- [ ] 5.4.4: Add quality score to pipeline_status.json

**Deliverables**:
- Debug pipeline command
- Classified DLQs
- Monitoring dashboard
- Data quality validation

**Estimated Time**: 8-10 hours

---

### **SPRINT 6: Template Expansion (Remaining Filing Types)**

**Goal**: Support all filing types (Extension, Termination, Campaign, etc.)

#### Tasks

##### 6.1: Extension Request (Type X)
- [ ] 6.1.1: Analyze samples (already done in TYPE_X_EXTENSION_COMPLETE_ANALYSIS.md)
- [ ] 6.1.2: Create template (regions.json, patterns.yaml)
- [ ] 6.1.3: Implement ExtensionTextExtractor (already exists at ingestion/lib/extractors/extension_extractor.py - needs integration)
- [ ] 6.1.4: Test with 10 samples

##### 6.2: Termination Report (Type T)
- [ ] 6.2.1: Analyze samples
- [ ] 6.2.2: Create template
- [ ] 6.2.3: Implement TerminationTextExtractor (already exists at ingestion/lib/extractors/termination_extractor.py - needs integration)
- [ ] 6.2.4: Test with 5 samples

##### 6.3: Campaign Notice (Type D)
- [ ] 6.3.1: Analyze samples (TYPE_D_CAMPAIGN_NOTICE_ANALYSIS.md exists)
- [ ] 6.3.2: Create template
- [ ] 6.3.3: Implement CampaignNoticeExtractor
- [ ] 6.3.4: Test with 5 samples

##### 6.4: Other Types (W, N, F, G, U, etc.)
- [ ] 6.4.1: Inventory all filing types from Bronze layer
- [ ] 6.4.2: Analyze samples for each type
- [ ] 6.4.3: Create templates
- [ ] 6.4.4: Implement extractors or use generic fallback

**Deliverables**:
- Templates for all filing types
- Extractors for all filing types
- Test coverage: 5-10 samples per type

**Estimated Time**: 12-15 hours (varies by type count)

---

## Integration Checklist

### Infrastructure
- [ ] All Lambda functions deployed
- [ ] All SQS queues created
- [ ] All event source mappings configured
- [ ] CloudWatch log groups created
- [ ] IAM permissions verified
- [ ] S3 bucket structure correct

### Data Flow
- [ ] Bronze → Text extraction working
- [ ] Text → Code extraction working
- [ ] Code extraction → Structured JSON output
- [ ] Low-confidence → Textract approval queue
- [ ] Human approval → Textract processing
- [ ] Textract → Final structured JSON
- [ ] Failed messages → Appropriate DLQ

### Validation
- [ ] All schemas enforced via jsonschema
- [ ] Data quality validator running
- [ ] Duplicate detection working
- [ ] File type detection accurate

### Monitoring
- [ ] Pipeline metrics tracked
- [ ] CloudWatch alarms configured
- [ ] Debug command operational
- [ ] Make commands documented

### UI
- [ ] Admin extraction review page
- [ ] Data tables for each filing type
- [ ] PDF viewer working
- [ ] Filtering/sorting/export working
- [ ] Textract budget tracker visible

---

## Make Command Reference

### Deployment
```bash
make deploy                    # Deploy all infrastructure
make package-extract          # Package extraction Lambda
make package-structured-code  # Package structured extraction Lambda
make upload-lambdas           # Upload all Lambda packages to S3
```

### Pipeline Operations
```bash
make run-silver-pipeline      # Queue all Bronze PDFs for extraction
make check-extraction-queue   # Check queue depth
make check-dlq                # Check DLQ depth
make purge-queues             # Clear all queues (careful!)
make redrive-dlq              # Move DLQ messages back to main queue
```

### Debugging
```bash
make debug-pipeline doc_id=XXXXX  # End-to-end trace for one document
make classify-dlq-failures        # Analyze DLQ failure patterns
make logs-extract                 # Tail extraction Lambda logs
make logs-structured              # Tail structured extraction Lambda logs
```

### Testing
```bash
make test-extractions             # Run extraction tests
make validate-schemas             # Validate all JSON schemas
make test-filing-type type=PTR    # Test specific filing type extraction
```

### Monitoring
```bash
make update-pipeline-status       # Update pipeline_status.json
make upload-pipeline-status       # Upload to S3 for UI
make data-quality-report          # Generate quality report
```

---

## Template File Structure

Each filing type will have a template directory:

```
ingestion/templates/
├── ptr/
│   ├── regions.json       # Bounding boxes for text extraction
│   ├── patterns.yaml      # Regex patterns for field extraction
│   └── schema.json        # JSON schema for validation (symlink to ingestion/schemas/)
├── form_a/
│   ├── regions.json
│   ├── patterns.yaml
│   └── schema.json
├── form_b/
│   ├── regions.json
│   ├── patterns.yaml
│   └── schema.json
└── extension_request/
    ├── regions.json
    ├── patterns.yaml
    └── schema.json
```

### regions.json Example (PTR)
```json
{
  "filer_name": {
    "page": 1,
    "bbox": [50, 100, 500, 150],
    "extraction_method": "text"
  },
  "filing_date": {
    "page": 1,
    "bbox": [50, 160, 300, 190],
    "extraction_method": "text"
  },
  "transactions_table": {
    "page": "1-N",
    "bbox": [50, 300, 750, 1000],
    "extraction_method": "table",
    "fallback": "ocr"
  }
}
```

### patterns.yaml Example (PTR)
```yaml
filer_name:
  pattern: "Name:?\\s*([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)+)"
  required: true

filing_date:
  pattern: "Filing Date:?\\s*(\\d{1,2}/\\d{1,2}/\\d{4})"
  required: true
  format: "date"

filing_status:
  pattern: "Status:?\\s*(Member|Candidate|Terminated Member)"
  required: true
  enum: ["Member", "Candidate", "Terminated Member"]

transaction_date:
  pattern: "(\\d{2}/\\d{2}/\\d{4})"
  required: true
  format: "date"
  context: "transactions_table"

asset_name:
  pattern: "(?:Asset|Description):?\\s*([A-Za-z0-9\\s,.-]+?)(?:Ticker|Owner|Type|$)"
  required: true
  context: "transactions_table"
```

---

## Success Metrics

### Sprint 1 (PTR Extraction)
- ✅ 1,500+ PTRs extracted
- ✅ 80%+ average confidence score
- ✅ <10% missing filer_name/filing_date
- ✅ Textract usage: 0 pages

### Sprint 2 (Form A/B Text Extraction)
- ✅ 60-80% field capture for Form A/B headers
- ✅ 50-70% field capture for Schedules A-I (varies by schedule)
- ✅ Gap analysis identifies which schedules need Textract
- ✅ Textract usage: 0 pages

### Sprint 3 (OCR Fallback)
- ✅ Scanned PDFs detected and processed
- ✅ OCR confidence scores tracked
- ✅ Text + OCR combined field capture > text alone
- ✅ Textract usage: 0 pages

### Sprint 4 (Admin UI)
- ✅ All extracted data visible in UI
- ✅ Users can review extraction gaps
- ✅ Users can approve Textract for specific docs/patterns
- ✅ Textract budget tracker shows usage
- ✅ Textract usage: <200 pages/month (human-approved only)

### Overall Pipeline
- ✅ 95%+ PDFs successfully extracted (text or text+OCR)
- ✅ <5% requiring Textract
- ✅ <2% in DLQ (permanent failures)
- ✅ Data quality score: 85%+ average
- ✅ Budget: <$20/month (mostly Lambda, minimal Textract)

---

## Priority Order

**Week 1**: Sprint 1 (PTR extraction) - IN PROGRESS
**Week 2**: Sprint 2 (Form A/B text extraction)
**Week 3**: Sprint 3 (OCR fallback) + Sprint 4 (Admin UI)
**Week 4**: Sprint 5 (Debugging tools) + Sprint 6 (Remaining types)

---

## Open Questions

1. **LLM Integration**: Should we add local LLM cleanup layer? (Low priority)
2. **Async Textract**: Do we need async Textract for large docs? (Already implemented in existing handler)
3. **Versioning**: Should we version extraction methods? (e.g., v1 = text, v2 = text+OCR, v3 = Textract)
4. **Audit Trail**: Should we track who approved Textract for each doc?
5. **Reprocessing**: How to handle schema changes? (Reprocess all docs or just new ones?)

---

**End of Document**
