# Workflow Execution Flow

This document visualizes the execution flow of the daily_incremental.yml workflow.

## Daily Scheduled Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions Workflow                       │
│                   (daily_incremental.yml)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Cron: 0 6 * * * (6:00 AM UTC)
                              ▼
                    ┌──────────────────┐
                    │  Checkout Code   │
                    └──────────────────┘
                              │
                              ▼
                 ┌─────────────────────────┐
                 │  Configure AWS Creds    │
                 │  (OIDC Role Assume)     │
                 └─────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │  Trigger Step Function       │
                │  aws stepfunctions           │
                │    start-execution           │
                │                              │
                │  Input:                      │
                │  {                           │
                │    execution_type: scheduled │
                │    year: <current year>      │
                │    mode: incremental         │
                │  }                           │
                └──────────────────────────────┘
                              │
                              │ Returns Execution ARN
                              ▼
                  ┌────────────────────┐
                  │  Wait Loop (30s)   │
                  │  Max: 2 hours      │
                  └────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │  Poll Status      │
                    │  describe-exec    │
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐          ┌─────────┐          ┌──────────┐
   │SUCCEEDED│          │ FAILED  │          │ RUNNING  │
   └─────────┘          └─────────┘          └──────────┘
        │                     │                     │
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐          ┌─────────┐          ┌──────────┐
   │Print out│          │Print err│          │Sleep 30s │
   │Exit 0   │          │Exit 1   │          │Continue  │
   └─────────┘          └─────────┘          └──────────┘
                                                    │
                                                    │
                                                    └────┐
                                                         │
                                                    ┌────▼──────┐
                                                    │ Timeout?  │
                                                    │ >2 hours  │
                                                    └────┬──────┘
                                                         │
                                                    ┌────▼────┐
                                                    │ Exit 1  │
                                                    └─────────┘
```

## Manual Trigger Flow (workflow_dispatch)

```
┌─────────────────────────────────────────────────────────────┐
│              User Triggers via GitHub UI                    │
│                                                              │
│  Inputs:                                                    │
│    - year: 2024 (optional)                                  │
│    - mode: full_refresh (optional)                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Same flow as   │
                  │  scheduled run  │
                  │                 │
                  │  But with user- │
                  │  specified year │
                  │  and mode       │
                  └─────────────────┘
```

## Step Functions State Machine Execution

```
┌──────────────────────────────────────────────────────────────┐
│          AWS Step Functions State Machine                    │
│        (house-fd-pipeline or congress-pipeline)              │
└──────────────────────────────────────────────────────────────┘
                           │
                           │ Receives input from GitHub Actions
                           ▼
              ┌───────────────────────────┐
              │  CheckExecutionType       │
              │  (initial_load vs manual) │
              └───────────────────────────┘
                           │
                           ▼
              ┌───────────────────────────┐
              │  CheckForNewFilings       │
              │  (Lambda)                 │
              └───────────────────────────┘
                           │
                           ▼
              ┌───────────────────────────┐
              │  IngestZip                │
              │  (Lambda)                 │
              └───────────────────────────┘
                           │
                           ▼
              ┌───────────────────────────┐
              │  IndexToSilver            │
              │  (Lambda)                 │
              └───────────────────────────┘
                           │
                           ▼
              ┌───────────────────────────┐
              │  ExtractDocumentsMap      │
              │  (Distributed Map)        │
              └───────────────────────────┘
                           │
                           ▼
              ┌───────────────────────────┐
              │  ValidateSilverQuality    │
              │  (Soda Checks)            │
              └───────────────────────────┘
                           │
                           ▼
              ┌───────────────────────────┐
              │  TransformToGoldParallel  │
              │  (Multiple branches)      │
              └───────────────────────────┘
                           │
                           ▼
              ┌───────────────────────────┐
              │  ComputeAggregates        │
              │  (Parallel)               │
              └───────────────────────────┘
                           │
                           ▼
              ┌───────────────────────────┐
              │  PublishMetrics           │
              │  (CloudWatch)             │
              └───────────────────────────┘
                           │
                           ▼
                    ┌──────────┐
                    │ SUCCESS  │
                    └──────────┘
```

## Error Handling Flow

```
                    ┌──────────────────┐
                    │  Step Fails      │
                    └──────────────────┘
                            │
                    ┌───────┴────────┐
                    │                │
                    ▼                ▼
            ┌───────────┐    ┌──────────────┐
            │  Retry?   │    │  No Retry    │
            │  (3x)     │    │  Config      │
            └───────────┘    └──────────────┘
                    │                │
                    │                │
                    └────────┬───────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Catch Block    │
                    │  (if defined)   │
                    └─────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    ▼                 ▼
         ┌──────────────────┐  ┌──────────────┐
         │ NotifyFailure    │  │ Continue     │
         │ (SNS)            │  │ (mark failed)│
         └──────────────────┘  └──────────────┘
                    │
                    ▼
              ┌──────────┐
              │  FAILED  │
              └──────────┘
                    │
                    │ GitHub Actions detects
                    ▼
         ┌──────────────────────┐
         │  Workflow Exit 1     │
         │  (failure status)    │
         └──────────────────────┘
```

## Key Differences from Old Approach

### Before (Python Script)
```
GitHub Actions
      │
      ▼
  Setup Python
      │
      ▼
Install Dependencies
      │
      ▼
Run run_smart_pipeline.py
      │
      ├─ Invoke Lambda
      ├─ Wait for queue
      ├─ Run aggregations
      └─ Exit
```

### After (Step Functions)
```
GitHub Actions
      │
      ▼
  AWS CLI
      │
      ▼
Start Step Functions
      │
      ▼
Poll for completion
      │
      ├─ SUCCEEDED → Exit 0
      ├─ FAILED → Exit 1
      └─ TIMEOUT → Exit 1
```

## Benefits

1. **Separation of Concerns**: GitHub Actions only responsible for triggering
2. **Better Monitoring**: Step Functions provides visual execution flow
3. **Error Recovery**: Automatic retries and error handling in state machine
4. **Scalability**: Step Functions can coordinate long-running workflows
5. **Cost Efficiency**: No need to run GitHub Actions runner while waiting

## Monitoring Points

1. **GitHub Actions Logs**: Trigger and wait loop output
2. **Step Functions Console**: Visual execution graph and state transitions
3. **CloudWatch Logs**: Detailed Lambda and state machine logs
4. **CloudWatch Metrics**: Pipeline success/failure metrics
5. **SNS Alerts**: Failure notifications (if configured)
