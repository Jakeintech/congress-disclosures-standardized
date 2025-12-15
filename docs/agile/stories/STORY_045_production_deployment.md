# STORY-045: Production Deployment & Validation

**Epic**: EPIC-001 | **Sprint**: Sprint 4 | **Points**: 3 | **Priority**: P0 | **Status**: To Do

## User Story
**As a** platform operator
**I want** successful production deployment
**So that** system is live and operational

## Acceptance Criteria
- **GIVEN** All code merged to main
- **WHEN** I deploy to production
- **THEN** All infrastructure deploys successfully
- **AND** First pipeline execution completes
- **AND** API returns fresh data
- **AND** Website displays updated metrics
- **AND** No critical bugs in first 24 hours

## Technical Tasks
- [ ] Pre-deployment checklist review
- [ ] Run `terraform plan` in production
- [ ] Deploy Terraform to production
- [ ] Enable EventBridge daily trigger
- [ ] Run first production pipeline execution
- [ ] Verify Bronze data
- [ ] Verify Silver data
- [ ] Verify Gold data
- [ ] Verify API responses
- [ ] Verify website displays data
- [ ] Monitor for 24 hours
- [ ] Post-deployment review

## Pre-Deployment Checklist
- [ ] All tests passing
- [ ] Code review approved
- [ ] Documentation complete
- [ ] Terraform plan reviewed
- [ ] Rollback plan ready
- [ ] Stakeholders notified

## Deployment Commands
```bash
# 1. Verify tests
pytest tests/ -v

# 2. Deploy infrastructure
cd infra/terraform
terraform plan
terraform apply

# 3. Verify deployment
aws stepfunctions list-state-machines
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `congress-disclosures`)].FunctionName'

# 4. Trigger first execution
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:... \
  --input '{"execution_type":"manual","mode":"full_refresh"}'

# 5. Monitor
watch -n 10 'aws stepfunctions describe-execution --execution-arn <ARN>'
```

## Validation Steps
- [ ] State machine executed successfully
- [ ] Bronze: 5,000+ PDFs in S3
- [ ] Silver: Parquet tables created
- [ ] Gold: Fact tables created
- [ ] API: GET /members returns 200
- [ ] Website: Dashboard loads
- [ ] Cost: First day < $5

## Success Criteria
- [ ] Pipeline success rate: 100% (first run)
- [ ] Execution time: < 2 hours
- [ ] Data quality: All Soda checks passing
- [ ] API latency: < 5 seconds (p99)
- [ ] Cost: Within $20/month projection

## Post-Deployment (24 Hours)
- [ ] No critical bugs
- [ ] Pipeline runs successfully (scheduled)
- [ ] Monitoring dashboards functional
- [ ] Alerts working (test alert sent)
- [ ] Team trained on operations

## Epic Completion Sign-Off
- [ ] Engineering: Deployment successful
- [ ] QA: All tests passing
- [ ] Product: Acceptance criteria met
- [ ] Stakeholders: Business value delivered

**🎉 EPIC-001 COMPLETE! 🎉**

## Estimated Effort: 3 hours (deployment + monitoring)
**Target**: Jan 10, 2026

## Epic Launch Date: January 11, 2026
