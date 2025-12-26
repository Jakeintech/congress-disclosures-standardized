# STORY-030: Implement Silver Transformation Phase

**Epic**: EPIC-001 | **Sprint**: Sprint 3 | **Points**: 5 | **Priority**: P0 | **Status**: To Do

## User Story
**As a** data engineer
**I want** Silver transformation with SQS queue polling
**So that** extraction completes before Gold processing

## Acceptance Criteria
- **GIVEN** Silver phase in state machine
- **WHEN** Execution reaches Silver
- **THEN** Queues extraction messages to SQS
- **AND** Polls queue until empty (not fixed 10s wait)
- **AND** Proceeds to Gold only when queue depth = 0

## Technical Tasks
- [ ] Add IndexToSilver Task state
- [ ] Add ExtractDocumentsMap with MaxConcurrency=10
- [ ] Add WaitForQueueEmpty loop
- [ ] Add CheckQueueStatus Choice state
- [ ] Configure SQS queue URL
- [ ] Test queue polling logic

## Implementation
```json
"WaitForExtractionComplete": {
  "Type": "Task",
  "Resource": "arn:aws:states:::sqs:getQueueAttributes",
  "Parameters": {
    "QueueUrl": "${SQS_QUEUE_URL}",
    "AttributeNames": ["ApproximateNumberOfMessages"]
  },
  "Next": "CheckQueueEmpty"
},
"CheckQueueEmpty": {
  "Type": "Choice",
  "Choices": [{
    "Variable": "$.Attributes.ApproximateNumberOfMessages",
    "NumericEquals": 0,
    "Next": "GoldDimensions"
  }],
  "Default": "WaitThenCheckAgain"
}
```

## Estimated Effort: 5 hours
**Target**: Dec 31, 2025
