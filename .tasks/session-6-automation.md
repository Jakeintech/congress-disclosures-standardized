# Session 6: Full Pipeline Automation

**Duration**: Week 6 (7 days)
**Goal**: Implement daily incremental ingestion, Step Functions orchestration, Textract reprocessing, DLQ auto-retry, and complete Makefile for one-command deployment

---

## Prerequisites

- [x] Session 5 complete (API Gateway deployed)
- [ ] Gold layer stable and tested
- [ ] All extraction Lambdas functional
- [ ] Understanding of House.gov website structure for scraping

---

## Task Checklist

### 1. Daily Incremental Ingestion (Tasks 1-6)

- [ ] **Task 1.1**: Research House.gov incremental update mechanism
  - **Action**: Investigate how House posts new filings daily
  - **Discover**: RSS feed, daily index page, or API
  - **Document**: Update mechanism in `/docs/INCREMENTAL_INGESTION.md`
  - **Time**: 2 hours

- [ ] **Task 1.2**: Create web scraper for daily filings
  - **Action**: Write `/ingestion/lib/house_scraper.py`
  - **Functions**: `get_recent_filings()`, `get_filing_since_date()`
  - **Use**: BeautifulSoup or Selenium to scrape House.gov
  - **Deliverable**: Scraper library (250 lines)
  - **Time**: 4 hours

- [ ] **Task 1.3**: Create incremental ingest Lambda
  - **Action**: Write `/ingestion/lambdas/incremental_ingest/handler.py`
  - **Logic**: Get latest filing_date from Silver → scrape House.gov since that date → download new PDFs → upload to Bronze → queue for extraction
  - **Deliverable**: Lambda handler (300 lines)
  - **Time**: 5 hours

- [ ] **Task 1.4**: Add incremental ingest tests
  - **Action**: Create `/tests/unit/test_incremental_ingest.py`
  - **Tests**: Scraper logic, date filtering, deduplication
  - **Deliverable**: 10+ unit tests
  - **Time**: 2 hours

- [ ] **Task 1.5**: Configure incremental Lambda in Terraform
  - **Action**: Edit `/infra/terraform/lambda.tf`
  - **Add**: incremental-ingest Lambda with 15min timeout, EventBridge trigger
  - **Deliverable**: Terraform config
  - **Time**: 1 hour

- [ ] **Task 1.6**: Test incremental ingestion manually
  - **Action**: Invoke Lambda manually, verify new filings downloaded
  - **Deliverable**: Working incremental ingestion
  - **Time**: 1 hour

### 2. Step Functions Orchestration (Tasks 7-13)

- [ ] **Task 2.1**: Design Step Functions state machine
  - **Action**: Create state machine diagram
  - **Steps**:
    1. Trigger incremental ingestion
    2. Wait for Bronze uploads complete
    3. Check SQS queue depth (wait until empty)
    4. Trigger Gold layer rebuild (incremental)
    5. Update website manifests
    6. Send completion notification
  - **Deliverable**: State machine design diagram
  - **Time**: 2 hours

- [ ] **Task 2.2**: Create state machine JSON definition
  - **Action**: Write `/step_functions/pipeline_state_machine.json`
  - **States**: Task states for Lambda invocations, Wait states, Choice states for queue checking
  - **Error handling**: Retry logic, catch blocks, fallback states
  - **Deliverable**: State machine definition (400 lines)
  - **Time**: 5 hours

- [ ] **Task 2.3**: Create SQS queue depth checker Lambda
  - **Action**: Write `/ingestion/lambdas/check_queue_depth/handler.py`
  - **Logic**: Query SQS for ApproximateNumberOfMessages → return "EMPTY" or "PROCESSING"
  - **Deliverable**: Lambda handler (80 lines)
  - **Time**: 1 hour

- [ ] **Task 2.4**: Create incremental Gold rebuild trigger Lambda
  - **Action**: Write `/ingestion/lambdas/trigger_gold_rebuild/handler.py`
  - **Logic**: Invoke rebuild_gold_complete.py script with --mode incremental
  - **Use**: AWS Batch or long-running Lambda (15min timeout)
  - **Deliverable**: Lambda handler (120 lines)
  - **Time**: 2 hours

- [ ] **Task 2.5**: Create website manifest updater Lambda
  - **Action**: Write `/ingestion/lambdas/update_website_manifests/handler.py`
  - **Logic**: Generate manifest.json files for Bronze/Silver/Gold → upload to S3
  - **Deliverable**: Lambda handler (150 lines)
  - **Time**: 2 hours

- [ ] **Task 2.6**: Configure Step Functions in Terraform
  - **Action**: Create `/infra/terraform/step_functions.tf`
  - **Resources**: State machine, IAM role, CloudWatch log group
  - **Deliverable**: Terraform config (200 lines)
  - **Time**: 3 hours

- [ ] **Task 2.7**: Test Step Functions state machine
  - **Action**: Deploy and execute state machine manually
  - **Verify**: All steps execute in order, waits for queue drain, Gold rebuild runs
  - **Deliverable**: Working state machine
  - **Time**: 2 hours

### 3. EventBridge Scheduling (Tasks 14-17)

- [ ] **Task 3.1**: Create EventBridge rule for daily pipeline
  - **Action**: Edit `/infra/terraform/eventbridge.tf`
  - **Schedule**: Daily at 2 AM EST (cron(0 7 * * ? *) UTC)
  - **Target**: Step Functions state machine
  - **Deliverable**: Terraform config
  - **Time**: 1 hour

- [ ] **Task 3.2**: Create EventBridge rule for monthly Textract reprocessing
  - **Action**: Add to eventbridge.tf
  - **Schedule**: 1st day of month at 3 AM EST (cron(0 8 1 * ? *) UTC)
  - **Target**: textract-reprocessing Lambda
  - **Deliverable**: Terraform config
  - **Time**: 30 min

- [ ] **Task 3.3**: Create EventBridge rule for weekly data quality checks
  - **Action**: Add to eventbridge.tf
  - **Schedule**: Every Sunday at 4 AM EST (cron(0 9 ? * SUN *) UTC)
  - **Target**: data-quality-validator Lambda (bulk mode)
  - **Deliverable**: Terraform config
  - **Time**: 30 min

- [ ] **Task 3.4**: Deploy EventBridge rules
  - **Action**: `terraform apply`
  - **Verify**: Rules created, targets configured
  - **Deliverable**: Automated scheduling
  - **Time**: 30 min

### 4. Textract Reprocessing Automation (Tasks 18-20)

- [ ] **Task 4.1**: Create Textract reprocessing Lambda
  - **Action**: Write `/ingestion/lambdas/textract_reprocessor/handler.py`
  - **Logic**: Query Silver for requires_textract_reprocessing=True → re-queue PDFs to extraction queue → update Silver status
  - **Deliverable**: Lambda handler (200 lines)
  - **Time**: 3 hours

- [ ] **Task 4.2**: Add budget check to reprocessing Lambda
  - **Action**: Enhance Lambda to check Textract monthly budget before queuing
  - **Logic**: Query Silver for textract_pages_used this month → if <limit, queue, else skip
  - **Deliverable**: Budget-aware reprocessing
  - **Time**: 1 hour

- [ ] **Task 4.3**: Test reprocessing Lambda
  - **Action**: Manually set requires_textract_reprocessing=True on test PDFs
  - **Trigger**: Lambda, verify PDFs re-queued and extracted
  - **Deliverable**: Working reprocessing
  - **Time**: 1.5 hours

### 5. DLQ Auto-Retry (Tasks 21-24)

- [ ] **Task 5.1**: Create DLQ error classifier
  - **Action**: Write `/ingestion/lib/error_classifier.py`
  - **Functions**: `classify_error()`, `is_retryable()`
  - **Categories**: Transient (throttling, timeout), Permanent (malformed PDF, missing file)
  - **Deliverable**: Error classifier library (150 lines)
  - **Time**: 2 hours

- [ ] **Task 5.2**: Create DLQ retry Lambda
  - **Action**: Write `/ingestion/lambdas/dlq_retry/handler.py`
  - **Logic**: Poll DLQ → classify errors → retry transient errors → alert on permanent errors
  - **Deliverable**: Lambda handler (250 lines)
  - **Time**: 4 hours

- [ ] **Task 5.3**: Add CloudWatch alarm for DLQ depth
  - **Action**: Edit `/infra/terraform/cloudwatch_alarms.tf`
  - **Alarm**: Trigger if DLQ has >10 messages
  - **Action**: Invoke dlq-retry Lambda
  - **Deliverable**: Terraform config
  - **Time**: 1 hour

- [ ] **Task 5.4**: Test DLQ retry flow
  - **Action**: Inject failing message into queue, verify DLQ capture, trigger retry Lambda
  - **Deliverable**: Working DLQ auto-retry
  - **Time**: 2 hours

### 6. Complete Makefile (Tasks 25-29)

- [ ] **Task 6.1**: Create make deploy-all target
  - **Action**: Edit `/Makefile`
  - **Steps**:
    1. `make deploy-infra` (Terraform apply)
    2. `make package-all` (package all Lambdas)
    3. `make deploy-lambdas` (upload Lambda ZIPs)
    4. `make seed-data` (run gold-seed Lambdas)
    5. `make trigger-initial-pipeline` (kick off first run)
  - **Deliverable**: One-command full deployment
  - **Time**: 2 hours

- [ ] **Task 6.2**: Create make run-pipeline target
  - **Action**: Add to Makefile
  - **Command**: Trigger Step Functions state machine execution
  - **Use**: AWS CLI to start execution
  - **Deliverable**: One-command pipeline run
  - **Time**: 30 min

- [ ] **Task 6.3**: Create make tail-pipeline target
  - **Action**: Add to Makefile
  - **Command**: Follow Step Functions execution + Lambda logs in real-time
  - **Use**: AWS CLI describe-execution + CloudWatch tail
  - **Deliverable**: Real-time pipeline monitoring
  - **Time**: 1 hour

- [ ] **Task 6.4**: Create make check-status target
  - **Action**: Add to Makefile
  - **Command**: Display pipeline status, extraction progress, Gold layer stats
  - **Output**: Table showing Bronze/Silver/Gold counts, queue depth, latest run status
  - **Deliverable**: Status dashboard in terminal
  - **Time**: 1.5 hours

- [ ] **Task 6.5**: Document all Makefile targets
  - **Action**: Add help target to Makefile
  - **Command**: `make help` displays all targets with descriptions
  - **Deliverable**: Self-documenting Makefile
  - **Time**: 1 hour

### 7. End-to-End Testing (Tasks 30-33)

- [ ] **Task 7.1**: Test full deployment from scratch
  - **Action**: Deploy to fresh AWS account using `make deploy-all`
  - **Verify**: All infrastructure created, Lambdas deployed, initial data seeded
  - **Deliverable**: Successful fresh deployment
  - **Time**: 3 hours

- [ ] **Task 7.2**: Test daily incremental pipeline
  - **Action**: Trigger Step Functions manually with `make run-pipeline`
  - **Verify**: Incremental ingestion runs, new filings extracted, Gold updated
  - **Deliverable**: Working daily pipeline
  - **Time**: 2 hours

- [ ] **Task 7.3**: Test Textract reprocessing
  - **Action**: Wait for monthly trigger or invoke manually
  - **Verify**: PDFs with requires_textract_reprocessing=True are re-extracted
  - **Deliverable**: Working monthly reprocessing
  - **Time**: 1.5 hours

- [ ] **Task 7.4**: Test DLQ auto-retry
  - **Action**: Inject error into extraction, verify DLQ capture and retry
  - **Deliverable**: Working DLQ auto-retry
  - **Time**: 1 hour

---

## Files Created/Modified

### Created (17 files)
- `/ingestion/lib/house_scraper.py` - Web scraper (250 lines)
- `/ingestion/lambdas/incremental_ingest/handler.py` - Incremental ingestion (300 lines)
- `/ingestion/lambdas/check_queue_depth/handler.py` - Queue checker (80 lines)
- `/ingestion/lambdas/trigger_gold_rebuild/handler.py` - Gold trigger (120 lines)
- `/ingestion/lambdas/update_website_manifests/handler.py` - Manifest updater (150 lines)
- `/ingestion/lambdas/textract_reprocessor/handler.py` - Textract reprocessing (200 lines)
- `/ingestion/lib/error_classifier.py` - Error classifier (150 lines)
- `/ingestion/lambdas/dlq_retry/handler.py` - DLQ retry (250 lines)
- `/step_functions/pipeline_state_machine.json` - State machine def (400 lines)
- `/infra/terraform/step_functions.tf` - Step Functions config (200 lines)
- `/infra/terraform/eventbridge.tf` - EventBridge rules (150 lines)
- `/infra/terraform/cloudwatch_alarms.tf` - CloudWatch alarms (100 lines)
- `/tests/unit/test_incremental_ingest.py` - Tests (200 lines)
- `/docs/INCREMENTAL_INGESTION.md` - Documentation

### Modified (2 files)
- `/Makefile` - Complete automation targets
- `/infra/terraform/lambda.tf` - New Lambda configurations

---

## Acceptance Criteria

✅ **Daily Incremental Ingestion**
- Scraper detects new filings from House.gov
- New PDFs downloaded and uploaded to Bronze
- Extraction queue populated automatically

✅ **Step Functions Orchestration**
- State machine orchestrates full pipeline
- Waits for queue drain before Gold rebuild
- Handles errors gracefully

✅ **Automated Scheduling**
- Daily pipeline runs at 2 AM EST
- Monthly Textract reprocessing on 1st
- Weekly data quality checks on Sunday

✅ **Textract Reprocessing**
- Budget-limited PDFs reprocessed monthly
- Budget check prevents overspend
- Silver status updated after reprocessing

✅ **DLQ Auto-Retry**
- Transient errors automatically retried
- Permanent errors flagged for manual review
- CloudWatch alarms trigger retry

✅ **One-Command Deployment**
- `make deploy-all` deploys entire stack
- `make run-pipeline` triggers daily run
- `make tail-pipeline` monitors execution

✅ **Testing**
- Fresh deployment successful
- Daily pipeline tested end-to-end
- All automation tested

---

## Testing Checklist

### Unit Tests
- [ ] Incremental ingestion scraper: 10+ tests
- [ ] Error classifier: 6+ tests
- [ ] Run: `pytest tests/unit/test_incremental_ingest.py -v`

### Integration Tests
- [ ] Full deployment from scratch
- [ ] Daily pipeline end-to-end
- [ ] Textract reprocessing flow
- [ ] DLQ retry flow
- [ ] Step Functions execution
- [ ] EventBridge triggers

### Manual Tests
- [ ] `make deploy-all` on fresh AWS account
- [ ] `make run-pipeline` triggers state machine
- [ ] `make tail-pipeline` shows real-time logs
- [ ] `make check-status` displays accurate stats
- [ ] Verify EventBridge rules trigger on schedule

---

## Deployment Steps

1. **Deploy Infrastructure**
   ```bash
   cd infra/terraform
   terraform plan -out=automation.tfplan
   terraform apply automation.tfplan
   ```

2. **Package All Lambdas**
   ```bash
   make package-all
   ```

3. **Deploy Complete Stack**
   ```bash
   make deploy-all
   ```

4. **Verify Deployment**
   ```bash
   make check-status
   ```

5. **Test Daily Pipeline**
   ```bash
   make run-pipeline
   make tail-pipeline
   ```

6. **Verify EventBridge Schedules**
   ```bash
   aws events list-rules --name-prefix congress-disclosures
   ```

7. **Monitor First Automated Run**
   - Wait for 2 AM EST next day
   - Check CloudWatch logs for Step Functions execution
   - Verify new filings ingested

---

## Rollback Plan

If automation fails:

1. **Disable EventBridge Rules**
   ```bash
   aws events disable-rule --name congress-disclosures-daily-pipeline
   ```

2. **Revert to Manual Triggers**
   - Use existing manual Lambda invocations
   - Manual Gold rebuilds with scripts

3. **Terraform Rollback**
   ```bash
   terraform destroy -target=aws_sfn_state_machine.pipeline
   terraform destroy -target=aws_cloudwatch_event_rule.daily_pipeline
   ```

4. **Keep Core Infrastructure**
   - Bronze/Silver/Gold layers unaffected
   - API Gateway continues serving data

---

## Next Session Handoff

**Prerequisites for Session 7 (Monitoring & Docs)**:
- ✅ Full automation deployed and tested
- ✅ Daily pipeline running automatically
- ✅ One-command deployment working
- ✅ All Lambdas functional

**What's Automated**:
- Daily incremental ingestion (2 AM EST)
- Gold layer rebuilds (after ingestion)
- Textract reprocessing (monthly)
- DLQ auto-retry (on alarm)
- Data quality checks (weekly)

**Manual Tasks Remaining**:
- Initial deployment (`make deploy-all`)
- Monitoring and troubleshooting
- Documentation updates

---

## Session 6 Success Metrics

- **Lambdas**: 6 new automation Lambdas
- **Step Functions**: 1 state machine (6 steps)
- **EventBridge**: 3 scheduled rules
- **Makefile**: 10+ new targets
- **Automation**: 100% - no manual steps for daily operations
- **Code volume**: ~2,500 lines (Lambdas + state machine + Makefile)
- **Time**: Completed in 7 days (Week 6)

**Status**: ⏸️ NOT STARTED | 🔄 IN PROGRESS | ✅ COMPLETE
