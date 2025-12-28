# Session 2: Form A/B Core Extraction

**Duration**: Week 2-3 (10 days)
**Goal**: Implement complete Form A/B (Annual & Candidate) extraction covering Schedules A-E with Textract-based parsing and confidence scoring

---

## Prerequisites

- [x] Session 1 complete (Bronze reorganized, validators ready)
- [ ] Sample Form A PDFs identified (10+ diverse samples)
- [ ] Textract budget allocated (500 pages minimum for testing)
- [ ] `/ingestion/schemas/house_fd_form_ab.json` reviewed (248 lines)
- [ ] `/ingestion/lib/extractors/ptr_extractor.py` reviewed (use as template)

---

## Task Checklist

### 1. Research & Planning (Tasks 1-5)

- [ ] **Task 1.1**: Collect representative Form A samples
  - **Action**: Query Bronze for 10 Form A PDFs: `aws s3 ls s3://.../filing_type=A/`
  - **Selection criteria**: Different years (2020-2025), different page counts (15-50), different members
  - **Deliverable**: List of 10 DocIDs in `/docs/form_a_samples.txt`
  - **Time**: 30 min

- [ ] **Task 1.2**: Manual analysis of Form A structure
  - **Action**: Download 3 samples, review PDF structure
  - **Document**: Header fields, Part I checkboxes, Schedule layouts, table structures
  - **Deliverable**: `/docs/FORM_A_ANALYSIS.md` with field mappings
  - **Time**: 2 hours

- [ ] **Task 1.3**: Map Textract blocks to Form A fields
  - **Action**: Run Textract on 1 sample, analyze JSON output
  - **Identify**: KEY_VALUE_PAIR patterns, TABLE structures, SELECTION_ELEMENT checkboxes
  - **Deliverable**: Textract block mapping document
  - **Time**: 2 hours

- [ ] **Task 1.4**: Design extractor architecture
  - **Action**: Plan class structure: `FormABExtractor` → `ScheduleAExtractor`, `ScheduleCExtractor`, etc.
  - **Deliverable**: UML class diagram in `/docs/form_ab_extractor_design.md`
  - **Time**: 1 hour

- [ ] **Task 1.5**: Review existing PTR extractor patterns
  - **Action**: Study `/ingestion/lib/extractors/ptr_extractor.py` lines 1-394
  - **Extract**: Reusable patterns for confidence scoring, checkbox detection, table parsing
  - **Deliverable**: Notes on reusable code
  - **Time**: 1 hour

### 2. Core Form A/B Extractor (Tasks 6-12)

- [ ] **Task 2.1**: Create base Form A/B extractor class
  - **Action**: Write `/ingestion/lib/extractors/form_ab_extractor.py`
  - **Inherit**: From `BaseExtractor` (if exists) or create standalone
  - **Methods**: `extract()`, `_parse_header()`, `_parse_part_i()`, `_route_to_schedules()`
  - **Deliverable**: Base class skeleton (100 lines)
  - **Time**: 2 hours

- [ ] **Task 2.2**: Implement header parser
  - **Action**: Add `_parse_header()` method
  - **Extract**: Filer name, title, state/district, reporting period (from/to dates), amendment indicator
  - **Logic**: Use Textract KEY_VALUE_PAIR blocks, regex for dates
  - **Deliverable**: Header parser with 8+ fields
  - **Time**: 2 hours

- [ ] **Task 2.3**: Implement Part I checkbox parser
  - **Action**: Add `_parse_part_i()` method
  - **Extract**: 10+ yes/no questions from Part I (status, qualified blind trust, etc.)
  - **Logic**: Use Textract SELECTION_ELEMENT blocks, match by question text
  - **Deliverable**: Part I parser returning dict of checkboxes
  - **Time**: 2 hours

- [ ] **Task 2.4**: Implement schedule router
  - **Action**: Add `_route_to_schedules()` method
  - **Logic**: Detect schedule headers in Textract blocks, route table data to appropriate schedule parser
  - **Deliverable**: Router that identifies Schedules A-I
  - **Time**: 2 hours

- [ ] **Task 2.5**: Add confidence scoring framework
  - **Action**: Implement `_calculate_confidence()` method (reuse PTR logic)
  - **Metrics**: Textract confidence per field, expected vs extracted field count, data completeness
  - **Deliverable**: Confidence score (0.0-1.0) per extraction
  - **Time**: 1 hour

- [ ] **Task 2.6**: Add error handling and logging
  - **Action**: Wrap extraction in try/except, log extraction steps
  - **Handle**: Missing Textract blocks, malformed tables, unparseable dates
  - **Deliverable**: Robust error handling with CloudWatch logs
  - **Time**: 1 hour

- [ ] **Task 2.7**: Write unit tests for core extractor
  - **Action**: Create `/tests/unit/test_form_ab_extractor.py`
  - **Tests**: Header parsing, Part I checkboxes, schedule routing, confidence scoring
  - **Deliverable**: 10+ unit tests
  - **Time**: 2 hours

### 3. Schedule A - Assets & Unearned Income (Tasks 13-16)

- [ ] **Task 3.1**: Create Schedule A extractor
  - **Action**: Write `/ingestion/lib/extractors/schedules/schedule_a_extractor.py`
  - **Schema**: `/ingestion/schemas/schedule_a.json` (23 lines) - assets, income
  - **Deliverable**: ScheduleAExtractor class
  - **Time**: 30 min

- [ ] **Task 3.2**: Implement Schedule A table parser
  - **Action**: Add `parse_table()` method
  - **Extract**: Asset description, location (city/state), asset value code, income type, income amount code
  - **Logic**: Textract TABLE blocks → map columns by header text (fuzzy match)
  - **Deliverable**: Table parser returning list of assets
  - **Time**: 3 hours

- [ ] **Task 3.3**: Add asset categorization
  - **Action**: Implement `_categorize_asset()` helper
  - **Logic**: Keyword matching (stock, bond, real estate, mutual fund, etc.)
  - **Deliverable**: Asset category field populated
  - **Time**: 1 hour

- [ ] **Task 3.4**: Write Schedule A tests
  - **Action**: Create `/tests/unit/test_schedule_a_extractor.py`
  - **Tests**: Table parsing, asset categorization, value code mapping, edge cases
  - **Deliverable**: 8+ unit tests
  - **Time**: 1.5 hours

### 4. Schedule C - Earned Income (Tasks 17-19)

- [ ] **Task 4.1**: Create Schedule C extractor
  - **Action**: Write `/ingestion/lib/extractors/schedules/schedule_c_extractor.py`
  - **Schema**: `/ingestion/schemas/schedule_c.json` (30 lines) - source, type, amount
  - **Deliverable**: ScheduleCExtractor class
  - **Time**: 30 min

- [ ] **Task 4.2**: Implement Schedule C table parser
  - **Action**: Add `parse_table()` method
  - **Extract**: Source name, city/state, brief description, income amount
  - **Logic**: Textract TABLE blocks → handle multi-line descriptions
  - **Deliverable**: Table parser returning list of income sources
  - **Time**: 2 hours

- [ ] **Task 4.3**: Write Schedule C tests
  - **Action**: Create `/tests/unit/test_schedule_c_extractor.py`
  - **Tests**: Table parsing, description handling, amount extraction
  - **Deliverable**: 6+ unit tests
  - **Time**: 1 hour

### 5. Schedule D - Liabilities (Tasks 20-22)

- [ ] **Task 5.1**: Create Schedule D extractor
  - **Action**: Write `/ingestion/lib/extractors/schedules/schedule_d_extractor.py`
  - **Schema**: `/ingestion/schemas/schedule_d.json` (30 lines) - creditor, terms, amount
  - **Deliverable**: ScheduleDExtractor class
  - **Time**: 30 min

- [ ] **Task 5.2**: Implement Schedule D table parser
  - **Action**: Add `parse_table()` method
  - **Extract**: Creditor name, description/terms, month/year incurred, value code, interest rate
  - **Logic**: Textract TABLE blocks → handle date parsing (MM/YYYY)
  - **Deliverable**: Table parser returning list of liabilities
  - **Time**: 2 hours

- [ ] **Task 5.3**: Write Schedule D tests
  - **Action**: Create `/tests/unit/test_schedule_d_extractor.py`
  - **Tests**: Table parsing, date handling, rate parsing, value codes
  - **Deliverable**: 6+ unit tests
  - **Time**: 1 hour

### 6. Schedule E - Positions (Tasks 23-25)

- [ ] **Task 6.1**: Create Schedule E extractor
  - **Action**: Write `/ingestion/lib/extractors/schedules/schedule_e_extractor.py`
  - **Schema**: `/ingestion/schemas/schedule_e.json` (42 lines) - organization, position
  - **Deliverable**: ScheduleEExtractor class
  - **Time**: 30 min

- [ ] **Task 6.2**: Implement Schedule E table parser
  - **Action**: Add `parse_table()` method
  - **Extract**: Organization name, city/state, position, date appointed
  - **Logic**: Textract TABLE blocks → handle multi-line organization names
  - **Deliverable**: Table parser returning list of positions
  - **Time**: 2 hours

- [ ] **Task 6.3**: Write Schedule E tests
  - **Action**: Create `/tests/unit/test_schedule_e_extractor.py`
  - **Tests**: Table parsing, organization name handling, date parsing
  - **Deliverable**: 6+ unit tests
  - **Time**: 1 hour

### 7. Integration & Pipeline Update (Tasks 26-31)

- [ ] **Task 7.1**: Update structured extraction Lambda
  - **Action**: Edit `/ingestion/lambdas/house_fd_extract_structured/handler.py`
  - **Add**: Import FormABExtractor, route filing_type='A' or 'C' to FormABExtractor
  - **Deliverable**: Lambda routes Form A/B filings correctly
  - **Time**: 1 hour

- [ ] **Task 7.2**: Update Lambda to save schedule data
  - **Action**: Modify handler to save individual schedule JSON files
  - **Path**: `silver/structured/year={YEAR}/doc_id={DOC_ID}/schedule_a.json`, `schedule_c.json`, etc.
  - **Deliverable**: Schedule data persisted separately
  - **Time**: 1 hour

- [ ] **Task 7.3**: Add Form A/B validation
  - **Action**: Update data quality Lambda to validate Form A/B schemas
  - **Use**: SchemaValidator from Session 1, validate against `/ingestion/schemas/house_fd_form_ab.json`
  - **Deliverable**: Form A/B extractions validated
  - **Time**: 1 hour

- [ ] **Task 7.4**: Create integration test suite
  - **Action**: Write `/tests/integration/test_form_ab_e2e.py`
  - **Test**: End-to-end extraction on 3 sample Form A PDFs
  - **Verify**: Header, Part I, Schedules A/C/D/E all extracted, validation passes
  - **Deliverable**: E2E test with assertions
  - **Time**: 2 hours

- [ ] **Task 7.5**: Test on 10 sample Form A filings
  - **Action**: Run extraction Lambda on 10 sample DocIDs
  - **Verify**: Structured JSON created, all schedules present, confidence >0.7
  - **Deliverable**: 10 successful extractions
  - **Time**: 2 hours

- [ ] **Task 7.6**: Analyze extraction failures and iterate
  - **Action**: Review failed extractions, identify patterns (missing headers, malformed tables)
  - **Fix**: Update extractors to handle edge cases
  - **Deliverable**: Improved extractor code
  - **Time**: 2 hours

### 8. Documentation & Deployment (Tasks 32-35)

- [ ] **Task 8.1**: Document Form A/B extractor usage
  - **Action**: Write `/docs/FORM_AB_EXTRACTOR.md`
  - **Include**: Field mappings, schedule structure, confidence scoring, examples
  - **Deliverable**: Complete extractor documentation
  - **Time**: 2 hours

- [ ] **Task 8.2**: Update schema documentation
  - **Action**: Document each schedule schema with field descriptions
  - **Add**: Examples for Schedule A, C, D, E in `/docs/SCHEMA_EXAMPLES.md`
  - **Deliverable**: Schema documentation
  - **Time**: 1 hour

- [ ] **Task 8.3**: Package and deploy Lambdas
  - **Action**: `make package-all && make deploy-lambdas`
  - **Verify**: house-fd-extract-structured updated with Form A/B logic
  - **Deliverable**: Deployed Lambda
  - **Time**: 30 min

- [ ] **Task 8.4**: Run production extraction on all Form A filings
  - **Action**: Trigger extraction for all `filing_type=A` and `filing_type=C` in Bronze
  - **Monitor**: CloudWatch logs for errors
  - **Deliverable**: All Form A/B filings extracted
  - **Time**: 3 hours (depending on count)

---

## Files Created/Modified

### Created (12 files)
- `/ingestion/lib/extractors/form_ab_extractor.py` - Core Form A/B extractor (400+ lines)
- `/ingestion/lib/extractors/schedules/schedule_a_extractor.py` - Schedule A (150 lines)
- `/ingestion/lib/extractors/schedules/schedule_c_extractor.py` - Schedule C (100 lines)
- `/ingestion/lib/extractors/schedules/schedule_d_extractor.py` - Schedule D (120 lines)
- `/ingestion/lib/extractors/schedules/schedule_e_extractor.py` - Schedule E (130 lines)
- `/tests/unit/test_form_ab_extractor.py` - Core tests (200 lines)
- `/tests/unit/test_schedule_a_extractor.py` - Schedule A tests (150 lines)
- `/tests/unit/test_schedule_c_extractor.py` - Schedule C tests (100 lines)
- `/tests/unit/test_schedule_d_extractor.py` - Schedule D tests (100 lines)
- `/tests/unit/test_schedule_e_extractor.py` - Schedule E tests (100 lines)
- `/tests/integration/test_form_ab_e2e.py` - E2E tests (200 lines)
- `/docs/FORM_AB_EXTRACTOR.md` - Documentation

### Modified (5 files)
- `/ingestion/lambdas/house_fd_extract_structured/handler.py` - Form A/B routing
- `/ingestion/lambdas/data_quality_validator/handler.py` - Form A/B validation
- `/docs/form_a_samples.txt` - Sample DocIDs
- `/docs/FORM_A_ANALYSIS.md` - Structure analysis
- `/docs/SCHEMA_EXAMPLES.md` - Schema examples

---

## Acceptance Criteria

✅ **Extractors Implemented**
- FormABExtractor with header, Part I, schedule routing
- Schedule A, C, D, E extractors functional
- Confidence scoring implemented

✅ **Data Extraction**
- 10 sample Form A PDFs extracted successfully
- All schedules (A, C, D, E) parsed
- Structured JSON saved to Silver layer
- Average confidence score >0.75

✅ **Validation**
- Schema validation passes for all extractions
- Data quality reports generated
- No critical anomalies detected

✅ **Testing**
- 40+ unit tests passing
- 3+ integration tests passing
- E2E test on real Form A filings

✅ **Documentation**
- Form A/B extractor documented
- Schema examples provided
- Field mappings documented

---

## Testing Checklist

### Unit Tests
- [ ] Header parsing: 5+ tests
- [ ] Part I checkboxes: 3+ tests
- [ ] Schedule A: 8+ tests (table parsing, categorization)
- [ ] Schedule C: 6+ tests (income parsing)
- [ ] Schedule D: 6+ tests (liability parsing, dates)
- [ ] Schedule E: 6+ tests (position parsing)
- [ ] Confidence scoring: 4+ tests
- [ ] Run: `pytest tests/unit/test_*extractor.py -v`

### Integration Tests
- [ ] End-to-end extraction on 3 Form A samples
- [ ] Verify all schedules extracted
- [ ] Verify JSON structure matches schema
- [ ] Run: `pytest tests/integration/test_form_ab_e2e.py -v`

### Manual Tests
- [ ] Extract 10 sample Form A filings via Lambda
- [ ] Inspect structured JSON for completeness
- [ ] Review confidence scores (target >0.75)
- [ ] Check data quality reports for issues

---

## Deployment Steps

1. **Local Development & Testing**
   ```bash
   pytest tests/unit/test_form_ab_extractor.py -v
   pytest tests/unit/test_schedule_*_extractor.py -v
   pytest tests/integration/test_form_ab_e2e.py -v
   ```

2. **Package Lambdas**
   ```bash
   make package-all
   ```

3. **Deploy to AWS**
   ```bash
   make deploy-lambdas
   ```

4. **Trigger Sample Extractions**
   ```bash
   aws lambda invoke \
     --function-name house-fd-extract-structured \
     --payload '{"doc_id":"10000123","year":2024,"filing_type":"A"}' \
     response.json
   ```

5. **Monitor Execution**
   ```bash
   make logs-extract
   aws s3 ls s3://congress-disclosures-standardized/silver/structured/year=2024/doc_id=10000123/
   ```

6. **Bulk Extraction** (if confident)
   ```bash
   python scripts/trigger_form_a_extractions.py --year 2024
   ```

---

## Rollback Plan

If Form A/B extraction fails:

1. **Lambda Rollback**: Redeploy previous version
   ```bash
   git checkout HEAD~1 ingestion/lambdas/house_fd_extract_structured/
   make deploy-lambdas
   ```

2. **Data Cleanup**: Remove partial extractions
   ```bash
   aws s3 rm s3://congress-disclosures-standardized/silver/structured/year=2024/ \
     --recursive --exclude "*" --include "*doc_id=*filing_type=A*"
   ```

3. **Revert Routing**: Disable Form A/B routing in Lambda (add early return)

---

## Next Session Handoff

**Prerequisites for Session 3 (All Filing Types)**:
- ✅ Form A/B extraction working (Schedules A-E)
- ✅ Extractor pattern established (reusable for other filing types)
- ✅ Schedule-specific parsers created
- ✅ Validation framework tested on Form A/B

**Data Needed**:
- Sample PDFs for Schedules F, G, H, I (from Form A filings)
- Sample Termination reports (filing_type=T)
- Sample Gift/Travel reports (filing_type=G)

**Code Dependencies**:
- FormABExtractor as base for Termination extractor
- Schedule parsers (A-E) as templates for F-I

---

## Session 2 Success Metrics

- **Extractors**: 5 classes (1 core + 4 schedules)
- **Test coverage**: 40+ tests, 100% passing
- **Sample extraction success rate**: >80% (8/10 samples)
- **Average confidence score**: >0.75
- **Code volume**: ~1,500 lines (extractors + tests)
- **Documentation**: 2 docs updated
- **Time**: Completed in 10 days (Week 2-3)

**Status**: ⏸️ NOT STARTED | 🔄 IN PROGRESS | ✅ COMPLETE

---

## Session 2 Actual Completion Notes

**Date**: 2025-11-26
**Status**: ✅ **PHASE 1 COMPLETE** (70%) - ⏸️ **NEEDS ENHANCEMENT SESSION**

### What Was Delivered

**✅ COMPLETE:**
1. FormABExtractor base class (515 lines) with header, Part I, table routing
2. Schedule A, C, D, E extractors (570 lines total)
3. Lambda routing updated and deployed
4. Comprehensive analysis document with ALL data points identified
5. Visual inspection of 4 real Form A filings completed

**⚠️ NEEDS ENHANCEMENT:**
Through detailed visual analysis, we identified **10 critical missing data points**:
- Asset type codes [XX]
- DESCRIPTION fields
- LOCATION fields
- Stock tickers (ABBV)
- Account grouping notations
- Multiple income types (comma-separated)
- Exclusions section
- Certification section
- Exact amounts in Schedule C
- "None disclosed" distinction

**See `/docs/FORM_A_COMPLETE_ANALYSIS.md` for complete field inventory.**

### Files Delivered
- `form_ab_extractor.py` (515 lines)
- `schedule_a_extractor.py` (207 lines)
- `schedule_c_extractor.py` (119 lines)
- `schedule_d_extractor.py` (168 lines)
- `schedule_e_extractor.py` (77 lines)
- `FORM_A_COMPLETE_ANALYSIS.md` (280+ lines) - **Critical documentation**
- `SESSION_2_COMPLETION_SUMMARY.md` - Detailed summary

### Next Session Required

**Session 2.5: Form A/B Enhancement** (estimated 4-5 hours)
1. Update Schedule A with regex patterns for codes/tickers/descriptions
2. Add Exclusions and Certification extraction
3. Handle "None disclosed" properly
4. Test on 10+ samples
5. Achieve 95% field capture rate

**Recommendation**: Complete Session 2.5 before proceeding to Session 3 to ensure high-quality data extraction.

**Current Extraction Quality**: 70% complete (basic fields working, critical enhancements documented and ready to implement)

**Status**: ⏸️ PAUSED - Enhancement session needed
