# Session 3: All Filing Types Complete

**Duration**: Week 3 (5 days)
**Goal**: Implement extractors for Schedules F-I, Termination reports, Gift/Travel reports, Extensions, and deduplication logic to achieve 100% filing type coverage

---

## Prerequisites

- [x] Session 2 complete (Form A/B extractors working)
- [ ] Schedules F-I sample data identified (from Form A filings)
- [ ] Sample filings collected: Termination (T), Gift/Travel (G), Extension (X), Duplicate (D)
- [ ] Schedule schemas reviewed: F, G, H, I in `/ingestion/schemas/`

---

## Task Checklist

### 1. Schedule F - Agreements & Arrangements (Tasks 1-3)

- [ ] **Task 1.1**: Create Schedule F extractor
  - **Action**: Write `/ingestion/lib/extractors/schedules/schedule_f_extractor.py`
  - **Schema**: `/ingestion/schemas/schedule_f.json` (36 lines) - agreements, parties, status
  - **Extract**: Parties involved, date, terms/description, status (active/inactive)
  - **Deliverable**: ScheduleFExtractor class (120 lines)
  - **Time**: 2 hours

- [ ] **Task 1.2**: Implement Schedule F table parser
  - **Action**: Add `parse_table()` method
  - **Logic**: Textract TABLE blocks → handle multi-cell descriptions
  - **Special**: Date parsing (various formats), status detection
  - **Deliverable**: Table parser returning list of agreements
  - **Time**: 2 hours

- [ ] **Task 1.3**: Write Schedule F tests
  - **Action**: Create `/tests/unit/test_schedule_f_extractor.py`
  - **Tests**: Table parsing, date handling, status detection, multi-line text
  - **Deliverable**: 6+ unit tests
  - **Time**: 1 hour

### 2. Schedule G - Gifts (Tasks 4-6)

- [ ] **Task 2.1**: Create Schedule G extractor
  - **Action**: Write `/ingestion/lib/extractors/schedules/schedule_g_extractor.py`
  - **Schema**: `/ingestion/schemas/schedule_g.json` (40 lines) - source, description, value
  - **Extract**: Source name, description, date received, estimated value
  - **Deliverable**: ScheduleGExtractor class (130 lines)
  - **Time**: 2 hours

- [ ] **Task 2.2**: Implement Schedule G table parser
  - **Action**: Add `parse_table()` method
  - **Logic**: Textract TABLE blocks → handle gift descriptions (often long)
  - **Special**: Value parsing (may be text like "under $250"), date parsing
  - **Deliverable**: Table parser returning list of gifts
  - **Time**: 2 hours

- [ ] **Task 2.3**: Write Schedule G tests
  - **Action**: Create `/tests/unit/test_schedule_g_extractor.py`
  - **Tests**: Value parsing edge cases, description extraction, date handling
  - **Deliverable**: 6+ unit tests
  - **Time**: 1 hour

### 3. Schedule H - Travel Reimbursements (Tasks 7-9)

- [ ] **Task 3.1**: Create Schedule H extractor
  - **Action**: Write `/ingestion/lib/extractors/schedules/schedule_h_extractor.py`
  - **Schema**: `/ingestion/schemas/schedule_h.json` (37 lines) - sponsor, destination, dates, value
  - **Extract**: Sponsor name, destination, departure/return dates, reimbursement amount
  - **Deliverable**: ScheduleHExtractor class (140 lines)
  - **Time**: 2 hours

- [ ] **Task 3.2**: Implement Schedule H table parser
  - **Action**: Add `parse_table()` method
  - **Logic**: Textract TABLE blocks → handle date ranges, location parsing
  - **Special**: Parse departure/return dates (MM/DD/YYYY format), amount parsing
  - **Deliverable**: Table parser returning list of travel reimbursements
  - **Time**: 2 hours

- [ ] **Task 3.3**: Write Schedule H tests
  - **Action**: Create `/tests/unit/test_schedule_h_extractor.py`
  - **Tests**: Date range parsing, location extraction, amount parsing
  - **Deliverable**: 6+ unit tests
  - **Time**: 1 hour

### 4. Schedule I - Charitable Contributions (Tasks 10-12)

- [ ] **Task 4.1**: Create Schedule I extractor
  - **Action**: Write `/ingestion/lib/extractors/schedules/schedule_i_extractor.py`
  - **Schema**: `/ingestion/schemas/schedule_i.json` (30 lines) - organization, amount
  - **Extract**: Organization name, location, description, amount
  - **Deliverable**: ScheduleIExtractor class (110 lines)
  - **Time**: 2 hours

- [ ] **Task 4.2**: Implement Schedule I table parser
  - **Action**: Add `parse_table()` method
  - **Logic**: Textract TABLE blocks → standard table parsing
  - **Deliverable**: Table parser returning list of charitable contributions
  - **Time**: 1.5 hours

- [ ] **Task 4.3**: Write Schedule I tests
  - **Action**: Create `/tests/unit/test_schedule_i_extractor.py`
  - **Tests**: Organization name parsing, amount extraction
  - **Deliverable**: 6+ unit tests
  - **Time**: 1 hour

### 5. Termination Reports (Filing Type T) (Tasks 13-15)

- [ ] **Task 5.1**: Collect sample Termination reports
  - **Action**: Query Bronze for filing_type=T samples
  - **Selection**: 5 diverse samples from different years
  - **Deliverable**: List of 5 Termination DocIDs
  - **Time**: 30 min

- [ ] **Task 5.2**: Create Termination extractor
  - **Action**: Write `/ingestion/lib/extractors/termination_extractor.py`
  - **Inherit**: From FormABExtractor (similar structure)
  - **Extract**: Header, final reporting period, final financial positions
  - **Deliverable**: TerminationExtractor class (250 lines)
  - **Time**: 3 hours

- [ ] **Task 5.3**: Write Termination tests
  - **Action**: Create `/tests/unit/test_termination_extractor.py`
  - **Tests**: Header parsing, schedule extraction (Termination uses same schedules)
  - **Deliverable**: 8+ unit tests
  - **Time**: 1.5 hours

### 6. Gift/Travel Reports (Filing Type G) (Tasks 16-18)

- [ ] **Task 6.1**: Collect sample Gift/Travel reports
  - **Action**: Query Bronze for filing_type=G samples
  - **Selection**: 5 samples (some gift-only, some travel-only, some both)
  - **Deliverable**: List of 5 Gift/Travel DocIDs
  - **Time**: 30 min

- [ ] **Task 6.2**: Create Gift/Travel extractor
  - **Action**: Write `/ingestion/lib/extractors/gift_travel_extractor.py`
  - **Extract**: Filer info, gift table, travel table (reuse Schedule G/H parsers)
  - **Deliverable**: GiftTravelExtractor class (200 lines)
  - **Time**: 2 hours

- [ ] **Task 6.3**: Write Gift/Travel tests
  - **Action**: Create `/tests/unit/test_gift_travel_extractor.py`
  - **Tests**: Gift-only reports, travel-only reports, combined reports
  - **Deliverable**: 6+ unit tests
  - **Time**: 1 hour

### 7. Extension Requests (Filing Type X) (Tasks 19-20)

- [ ] **Task 7.1**: Create Extension extractor
  - **Action**: Write `/ingestion/lib/extractors/extension_extractor.py`
  - **Extract**: Filer name, original due date, extension request date, reason (text field)
  - **Note**: Simple extraction, mostly metadata
  - **Deliverable**: ExtensionExtractor class (80 lines)
  - **Time**: 1 hour

- [ ] **Task 7.2**: Write Extension tests
  - **Action**: Create `/tests/unit/test_extension_extractor.py`
  - **Tests**: Date parsing, reason text extraction
  - **Deliverable**: 4+ unit tests
  - **Time**: 30 min

### 8. Deduplication Logic (Tasks 21-24)

- [ ] **Task 8.1**: Design deduplication strategy
  - **Action**: Document in `/docs/DEDUPLICATION_STRATEGY.md`
  - **Logic**: Duplicate (type D) filings reference original DocID, amended filings (type F) supersede original
  - **Schema**: Add `is_superseded`, `superseded_by`, `supersedes` fields to Silver documents
  - **Deliverable**: Deduplication design doc
  - **Time**: 1 hour

- [ ] **Task 8.2**: Create deduplication library
  - **Action**: Write `/ingestion/lib/deduplicator.py`
  - **Functions**: `detect_duplicate()`, `link_amendment()`, `mark_superseded()`
  - **Logic**: Parse PDF text to find references to original filing, update DynamoDB/Parquet
  - **Deliverable**: Deduplication library (200 lines)
  - **Time**: 3 hours

- [ ] **Task 8.3**: Create deduplication Lambda
  - **Action**: Write `/ingestion/lambdas/deduplication_processor/handler.py`
  - **Trigger**: SQS queue (fired after extraction complete)
  - **Logic**: Check if filing_type in [D, F] → run deduplicator → update Silver metadata
  - **Deliverable**: Deduplication Lambda
  - **Time**: 2 hours

- [ ] **Task 8.4**: Update Silver schema with dedup fields
  - **Action**: Edit `/ingestion/schemas/house_fd_documents.json`
  - **Add**: `is_superseded` (bool), `superseded_by` (doc_id), `supersedes` (doc_id), `is_duplicate` (bool), `original_filing` (doc_id)
  - **Deliverable**: Updated schema
  - **Time**: 30 min

### 9. Integration & Routing (Tasks 25-28)

- [ ] **Task 9.1**: Update extraction Lambda routing
  - **Action**: Edit `/ingestion/lambdas/house_fd_extract_structured/handler.py`
  - **Add**: Route filing_type T → TerminationExtractor, G → GiftTravelExtractor, X → ExtensionExtractor
  - **Deliverable**: Complete filing type routing
  - **Time**: 1 hour

- [ ] **Task 9.2**: Update FormABExtractor with Schedules F-I
  - **Action**: Edit `/ingestion/lib/extractors/form_ab_extractor.py`
  - **Import**: Schedule F, G, H, I extractors
  - **Add**: Route schedules in `_route_to_schedules()` method
  - **Deliverable**: Form A/B now extracts all 9 schedules
  - **Time**: 1 hour

- [ ] **Task 9.3**: Test full filing type coverage
  - **Action**: Create `/tests/integration/test_all_filing_types.py`
  - **Test**: Extract 1 sample of each filing type (P, A, C, T, G, X)
  - **Verify**: All extractions successful, structured JSON created
  - **Deliverable**: E2E test covering all types
  - **Time**: 2 hours

- [ ] **Task 9.4**: Deploy and test deduplication
  - **Action**: Package deduplication Lambda, deploy
  - **Test**: Manually mark a filing as duplicate, verify deduplicator links it correctly
  - **Deliverable**: Working deduplication Lambda
  - **Time**: 1.5 hours

---

## Files Created/Modified

### Created (13 files)
- `/ingestion/lib/extractors/schedules/schedule_f_extractor.py` - Schedule F (120 lines)
- `/ingestion/lib/extractors/schedules/schedule_g_extractor.py` - Schedule G (130 lines)
- `/ingestion/lib/extractors/schedules/schedule_h_extractor.py` - Schedule H (140 lines)
- `/ingestion/lib/extractors/schedules/schedule_i_extractor.py` - Schedule I (110 lines)
- `/ingestion/lib/extractors/termination_extractor.py` - Termination reports (250 lines)
- `/ingestion/lib/extractors/gift_travel_extractor.py` - Gift/Travel reports (200 lines)
- `/ingestion/lib/extractors/extension_extractor.py` - Extensions (80 lines)
- `/ingestion/lib/deduplicator.py` - Deduplication logic (200 lines)
- `/ingestion/lambdas/deduplication_processor/handler.py` - Dedup Lambda (150 lines)
- `/tests/unit/test_schedule_f_extractor.py` - Schedule F tests (100 lines)
- `/tests/unit/test_schedule_g_extractor.py` - Schedule G tests (100 lines)
- `/tests/unit/test_schedule_h_extractor.py` - Schedule H tests (100 lines)
- `/tests/unit/test_schedule_i_extractor.py` - Schedule I tests (100 lines)
- `/tests/unit/test_termination_extractor.py` - Termination tests (150 lines)
- `/tests/unit/test_gift_travel_extractor.py` - Gift/Travel tests (120 lines)
- `/tests/unit/test_extension_extractor.py` - Extension tests (80 lines)
- `/tests/integration/test_all_filing_types.py` - Full coverage test (200 lines)
- `/docs/DEDUPLICATION_STRATEGY.md` - Dedup design doc

### Modified (3 files)
- `/ingestion/lib/extractors/form_ab_extractor.py` - Add Schedules F-I routing
- `/ingestion/lambdas/house_fd_extract_structured/handler.py` - Add T/G/X routing
- `/ingestion/schemas/house_fd_documents.json` - Add deduplication fields

---

## Acceptance Criteria

✅ **Schedules F-I Implemented**
- Schedule F, G, H, I extractors functional
- All 9 schedules now extracted from Form A/B
- Integrated into FormABExtractor

✅ **All Filing Types Covered**
- Termination (T) extractor working
- Gift/Travel (G) extractor working
- Extension (X) extractor working
- 100% filing type coverage (P, A, C, T, X, D, E, N, B, F, G, U)

✅ **Deduplication Implemented**
- Duplicate filings linked to originals
- Amended filings marked as superseding
- Silver schema includes dedup fields

✅ **Testing**
- 40+ new unit tests passing
- Integration test covers all filing types
- Deduplication tested on sample data

✅ **Production Ready**
- All extractors deployed
- Routing logic complete
- Lambda handles all filing types

---

## Testing Checklist

### Unit Tests
- [ ] Schedule F: 6+ tests
- [ ] Schedule G: 6+ tests
- [ ] Schedule H: 6+ tests
- [ ] Schedule I: 6+ tests
- [ ] Termination: 8+ tests
- [ ] Gift/Travel: 6+ tests
- [ ] Extension: 4+ tests
- [ ] Deduplication: 6+ tests
- [ ] Run: `pytest tests/unit/ -v`

### Integration Tests
- [ ] Extract 1 sample of each filing type (P, A, C, T, G, X)
- [ ] Verify all schedules extracted from Form A
- [ ] Test deduplication on duplicate/amended filings
- [ ] Run: `pytest tests/integration/test_all_filing_types.py -v`

### Manual Tests
- [ ] Trigger extraction for each filing type via Lambda
- [ ] Inspect structured JSON for completeness
- [ ] Verify deduplication links correct filings

---

## Deployment Steps

1. **Local Testing**
   ```bash
   pytest tests/unit/test_schedule_*.py -v
   pytest tests/unit/test_termination_extractor.py -v
   pytest tests/unit/test_gift_travel_extractor.py -v
   pytest tests/integration/test_all_filing_types.py -v
   ```

2. **Package Lambdas**
   ```bash
   make package-all
   ```

3. **Deploy**
   ```bash
   make deploy-lambdas
   terraform apply  # For deduplication queue/Lambda
   ```

4. **Test Each Filing Type**
   ```bash
   # Test Termination
   aws lambda invoke --function-name house-fd-extract-structured \
     --payload '{"doc_id":"T_SAMPLE_ID","year":2024,"filing_type":"T"}' response.json

   # Test Gift/Travel
   aws lambda invoke --function-name house-fd-extract-structured \
     --payload '{"doc_id":"G_SAMPLE_ID","year":2024,"filing_type":"G"}' response.json
   ```

5. **Verify Deduplication**
   ```bash
   # Check Silver for dedup fields
   aws s3 cp s3://congress-disclosures-standardized/silver/house/financial/documents/year=2024/ . --recursive
   python -c "import pandas as pd; df = pd.read_parquet('part-0000.parquet'); print(df[['doc_id', 'is_superseded', 'superseded_by']])"
   ```

---

## Rollback Plan

If extraction or deduplication fails:

1. **Extractor Rollback**: Revert to Session 2 extractors
2. **Lambda Rollback**: Redeploy previous version
3. **Schema Rollback**: Remove dedup fields from Silver schema (non-breaking change)
4. **Queue Cleanup**: Purge deduplication queue if needed

---

## Next Session Handoff

**Prerequisites for Session 4 (Gold Layer)**:
- ✅ All filing types extractable (P, A, C, T, G, X, etc.)
- ✅ All 9 schedules extracted from Form A/B
- ✅ Deduplication logic working
- ✅ Structured JSON for all filing types in Silver

**Data Needed**:
- Complete Silver layer with all filing types extracted
- Deduplication metadata (superseded flags)
- Sample data for testing Gold aggregations

**Code Dependencies**:
- Silver tables fully populated
- Extractors stable and tested

---

## Session 3 Success Metrics

- **Extractors**: 7 new classes (4 schedules + 3 filing types + dedup)
- **Test coverage**: 40+ tests, 100% passing
- **Filing type coverage**: 100% (12 types)
- **Schedule coverage**: 100% (A-I, all 9 schedules)
- **Code volume**: ~1,700 lines (extractors + dedup + tests)
- **Time**: Completed in 5 days (Week 3)

**Status**: ⏸️ NOT STARTED | 🔄 IN PROGRESS | ✅ COMPLETE
