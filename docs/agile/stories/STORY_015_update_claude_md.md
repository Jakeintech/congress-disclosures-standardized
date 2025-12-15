# STORY-015: Update CLAUDE.md with Step Functions Architecture

**Epic**: EPIC-001 | **Sprint**: Sprint 1 | **Points**: 5 | **Priority**: P1 | **Status**: To Do

## User Story
**As a** developer
**I want** CLAUDE.md updated with Step Functions documentation
**So that** I can deploy and operate the new architecture

## Acceptance Criteria
- **GIVEN** Updated CLAUDE.md file
- **WHEN** I read the documentation
- **THEN** Contains Step Functions architecture section
- **AND** Explains how to trigger state machine manually
- **AND** Documents EventBridge schedule
- **AND** Includes troubleshooting guide
- **AND** Updates all make commands

## Technical Tasks
- [ ] Add "Step Functions Architecture" section
- [ ] Document state machine design
- [ ] Add manual trigger commands
- [ ] Update "Pipeline Orchestration" section
- [ ] Remove outdated script-based references
- [ ] Add troubleshooting section
- [ ] Document monitoring approach
- [ ] Update make commands

## Implementation Outline
```markdown
## Step Functions Architecture

### Unified State Machine
The pipeline uses a single Step Functions state machine (`congress-data-platform`) that orchestrates:
- Bronze ingestion (parallel)
- Silver transformation (SQS-based)
- Gold aggregation (sequential)
- Quality validation
- API cache updates

### Manual Execution
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT:stateMachine:congress-data-platform \
  --input '{"execution_type":"manual","mode":"incremental"}'
```

### Monitoring
- View executions: AWS Console → Step Functions
- Check logs: CloudWatch Logs → /aws/states/congress-data-platform
- View traces: X-Ray → Service Map

### Troubleshooting
...
```

## Estimated Effort: 5 hours
**Target**: Dec 20, 2025
