# STORY-056: Extraction Quality Dashboard

**Epic**: EPIC-001 | **Sprint**: Sprint 4 | **Points**: 3 | **Priority**: P1 | **Status**: To Do

## User Story
**As a** data quality engineer
**I want** CloudWatch dashboard tracking extraction quality metrics over time
**So that** I can monitor extraction improvements, detect regressions, and validate reprocessing efforts

## Acceptance Criteria
- **GIVEN** Extraction versioning deployed (STORY-054)
- **WHEN** CloudWatch dashboard is deployed
- **THEN** Dashboard displays extraction quality metrics by filing type and version
- **AND** Confidence scores tracked over time (trending chart)
- **AND** Field extraction success rates visualized (heatmap)
- **AND** Reprocessing progress monitored (% of data using latest version)
- **AND** Quality regressions trigger CloudWatch alarms
- **AND** Version adoption metrics displayed (version distribution)

## Problem Statement

**Without quality monitoring**:
- No visibility into whether new extractor versions actually improve quality
- Cannot detect quality regressions until they cause downstream issues
- No way to track reprocessing progress
- Unclear which filing types need extraction improvements

**With quality dashboard**:
- Real-time visibility into extraction quality trends
- Proactive detection of quality regressions
- Data-driven decisions on which extractors need improvement
- Clear before/after validation for reprocessing efforts

## Dashboard Design

### Widget 1: Extraction Confidence Scores (Time Series)
**Metric**: Average confidence score by filing type
**Visualization**: Line chart (7-day rolling average)
**Purpose**: Track overall extraction quality trends

```
Extraction Confidence Scores (7-Day Average)
┌─────────────────────────────────────────────────┐
│                                         ┌────── Type P (v1.1.0): 94%
│                                    ┌────┘
│                               ┌────┘
│   Type A: 89%  ───────────────┘
│
│   Type P (v1.0.0): 87% ────────┐
│                                 └────────────────
│
│   Type T: 72% ────────────────────────────────── (needs improvement!)
│
└─────────────────────────────────────────────────┘
    Dec 1          Dec 15          Jan 1          Jan 15
```

**CloudWatch Query**:
```sql
SELECT AVG(extraction_metadata.confidence_score) as avg_confidence
FROM "silver/objects/*/*/*.json"
WHERE filing_type = 'type_p'
GROUP BY filing_type, extractor_version
```

### Widget 2: Field Extraction Success Rates (Heatmap)
**Metric**: Field-level extraction rates by filing type
**Visualization**: Heatmap (green=good, yellow=ok, red=bad)
**Purpose**: Identify which fields need extraction improvements

```
Field Extraction Success Rates (Type P PTR)
┌──────────────────────────────────────────┐
│ Field                 │ v1.0.0 │ v1.1.0 │
├──────────────────────────────────────────┤
│ transaction_date      │  98%   │  98%   │ ████████████████████
│ asset_description     │  89%   │  91%   │ ████████████████▒▒▒▒
│ amount_low            │  87%   │  94%   │ ████████████████▒▒▒▒ ↑ +7%
│ amount_high           │  87%   │  94%   │ ████████████████▒▒▒▒ ↑ +7%
│ transaction_type      │  84%   │  85%   │ ███████████████▒▒▒▒▒
│ filer_name            │  99%   │  99%   │ ████████████████████
└──────────────────────────────────────────┘
```

**CloudWatch Metric Math**:
```python
# Custom metric published by extraction Lambdas
cloudwatch.put_metric_data(
    Namespace='CongressDisclosures/Extraction',
    MetricData=[
        {
            'MetricName': 'FieldExtractionRate',
            'Dimensions': [
                {'Name': 'FilingType', 'Value': 'type_p'},
                {'Name': 'Field', 'Value': 'amount_low'},
                {'Name': 'ExtractorVersion', 'Value': '1.1.0'}
            ],
            'Value': 0.94,  # 94% success rate
            'Unit': 'None'
        }
    ]
)
```

### Widget 3: Reprocessing Progress (Gauge)
**Metric**: Percentage of data using latest extractor version
**Visualization**: Gauge + progress bar
**Purpose**: Track migration to improved extractors

```
Version Adoption Rate (Type P)
┌─────────────────────────────────────┐
│                                     │
│   v1.1.0 Adoption: 24%              │
│   ████████░░░░░░░░░░░░░░░░░░░░░     │
│                                     │
│   12,450 filings using v1.1.0       │
│   39,870 filings still on v1.0.0    │
│                                     │
│   Target: 100% by Jan 31            │
└─────────────────────────────────────┘
```

**CloudWatch Query**:
```sql
SELECT
    COUNT(*) FILTER (WHERE extractor_version = '1.1.0') * 100.0 / COUNT(*) as adoption_rate
FROM extraction_versions
WHERE filing_type = 'type_p'
```

### Widget 4: Quality Regressions (Alarm Status)
**Metric**: Fields with declining extraction rates
**Visualization**: Alarm widget (red if regression detected)
**Purpose**: Proactive detection of quality issues

```
Quality Regression Alarms
┌────────────────────────────────────────┐
│ ✅ Type P - No regressions             │
│ ✅ Type A - No regressions             │
│ ⚠️  Type T - Filer name field down 3%  │
│ ✅ Type X - No regressions             │
└────────────────────────────────────────┘
```

**CloudWatch Alarm**:
```python
cloudwatch.put_metric_alarm(
    AlarmName='TypeP-AmountLow-Regression',
    ComparisonOperator='LessThanThreshold',
    EvaluationPeriods=2,
    MetricName='FieldExtractionRate',
    Namespace='CongressDisclosures/Extraction',
    Period=86400,  # 1 day
    Statistic='Average',
    Threshold=0.90,  # Alert if drops below 90%
    ActionsEnabled=True,
    AlarmActions=[sns_topic_arn],
    Dimensions=[
        {'Name': 'FilingType', 'Value': 'type_p'},
        {'Name': 'Field', 'Value': 'amount_low'}
    ]
)
```

### Widget 5: Extraction Volume by Filing Type (Bar Chart)
**Metric**: Number of extractions by filing type and version
**Visualization**: Stacked bar chart
**Purpose**: Understand extraction workload distribution

```
Extractions by Filing Type (Last 30 Days)
┌─────────────────────────────────────────┐
│                                         │
│ Type P  ████████████████████ 25,430    │
│         ████ v1.0.0                     │
│         ████████████████ v1.1.0         │
│                                         │
│ Type A  ███████████ 12,890              │
│         ███████████ v1.0.0              │
│                                         │
│ Type T  ████ 4,230                      │
│         ████ v1.0.0                     │
└─────────────────────────────────────────┘
```

### Widget 6: Comparison Report Summary (Table)
**Metric**: Latest reprocessing comparison results
**Visualization**: Table widget
**Purpose**: Quick access to reprocessing validation data

```
Recent Reprocessing Comparisons
┌─────────────────────────────────────────────────────────────┐
│ Filing Type │ Date       │ Old→New Ver │ Improvement │ Status │
├─────────────────────────────────────────────────────────────┤
│ Type P      │ Jan 15     │ 1.0.0→1.1.0 │ +7.2%       │ ✅     │
│ Type A      │ Jan 12     │ 1.0.0→1.1.0 │ +4.1%       │ ✅     │
│ Type T      │ Jan 10     │ 1.0.0→1.0.1 │ -1.2%       │ ⚠️     │
│ Type P      │ Jan 5      │ 0.9.0→1.0.0 │ +12.5%      │ ✅     │
└─────────────────────────────────────────────────────────────┘
```

## Implementation

### 1. Custom CloudWatch Metrics

**Published by extraction Lambdas**:
```python
# ingestion/lambdas/house_fd_extract_structured_code/handler.py

def publish_extraction_metrics(extraction_result: Dict[str, Any]):
    """Publish extraction quality metrics to CloudWatch."""
    cloudwatch = boto3.client('cloudwatch')
    metadata = extraction_result['extraction_metadata']

    # Overall confidence score
    cloudwatch.put_metric_data(
        Namespace='CongressDisclosures/Extraction',
        MetricData=[
            {
                'MetricName': 'ConfidenceScore',
                'Dimensions': [
                    {'Name': 'FilingType', 'Value': metadata['filing_type']},
                    {'Name': 'ExtractorVersion', 'Value': metadata['extractor_version']}
                ],
                'Value': metadata['confidence_score'],
                'Unit': 'None',
                'Timestamp': datetime.utcnow()
            }
        ]
    )

    # Field-level extraction rates
    for field, confidence in metadata.get('field_confidence', {}).items():
        cloudwatch.put_metric_data(
            Namespace='CongressDisclosures/Extraction',
            MetricData=[
                {
                    'MetricName': 'FieldExtractionRate',
                    'Dimensions': [
                        {'Name': 'FilingType', 'Value': metadata['filing_type']},
                        {'Name': 'Field', 'Value': field},
                        {'Name': 'ExtractorVersion', 'Value': metadata['extractor_version']}
                    ],
                    'Value': confidence,
                    'Unit': 'None'
                }
            ]
        )

    # Data completeness
    cloudwatch.put_metric_data(
        Namespace='CongressDisclosures/Extraction',
        MetricData=[
            {
                'MetricName': 'DataCompleteness',
                'Dimensions': [
                    {'Name': 'FilingType', 'Value': metadata['filing_type']},
                    {'Name': 'ExtractorVersion', 'Value': metadata['extractor_version']}
                ],
                'Value': metadata.get('data_completeness', 0),
                'Unit': 'Percent'
            }
        ]
    )
```

### 2. Terraform Dashboard Definition

```hcl
# infra/terraform/cloudwatch_extraction_dashboard.tf (new file)

resource "aws_cloudwatch_dashboard" "extraction_quality" {
  dashboard_name = "${local.name_prefix}-extraction-quality"

  dashboard_body = jsonencode({
    widgets = [
      # Widget 1: Confidence Scores Time Series
      {
        type = "metric"
        properties = {
          title = "Extraction Confidence Scores (7-Day Average)"
          metrics = [
            ["CongressDisclosures/Extraction", "ConfidenceScore", {
              stat = "Average",
              period = 604800  # 7 days
            }]
          ]
          view = "timeSeries"
          region = var.aws_region
          yAxis = {
            left = {
              min = 0
              max = 1
            }
          }
        }
      },

      # Widget 2: Field Extraction Rates Heatmap
      {
        type = "metric"
        properties = {
          title = "Field Extraction Success Rates"
          metrics = [
            ["CongressDisclosures/Extraction", "FieldExtractionRate", {
              dimensions = {
                FilingType = "type_p"
              }
            }]
          ]
          view = "singleValue"
          region = var.aws_region
        }
      },

      # Widget 3: Reprocessing Progress Gauge
      {
        type = "metric"
        properties = {
          title = "Version Adoption Rate"
          metrics = [
            ["CongressDisclosures/Extraction", "VersionAdoptionRate", {
              stat = "Average",
              period = 86400
            }]
          ]
          view = "gauge"
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      },

      # Widget 4: Quality Regression Alarms
      {
        type = "alarm"
        properties = {
          title = "Quality Regression Alarms"
          alarms = [
            aws_cloudwatch_metric_alarm.field_extraction_regression["type_p_amount_low"].arn,
            aws_cloudwatch_metric_alarm.field_extraction_regression["type_a_asset_value"].arn,
            aws_cloudwatch_metric_alarm.confidence_score_regression.arn
          ]
        }
      },

      # Widget 5: Extraction Volume Bar Chart
      {
        type = "metric"
        properties = {
          title = "Extractions by Filing Type (Last 30 Days)"
          metrics = [
            ["CongressDisclosures/Extraction", "ExtractionCount", {
              stat = "Sum",
              period = 2592000  # 30 days
            }]
          ]
          view = "bar"
          stacked = true
        }
      },

      # Widget 6: Comparison Report Table
      {
        type = "log"
        properties = {
          title = "Recent Reprocessing Comparisons"
          query = <<-EOT
            SOURCE '/aws/lambda/reprocess-filings'
            | fields @timestamp, comparison.baseline_version, comparison.new_version, comparison.overall_improvement
            | sort @timestamp desc
            | limit 5
          EOT
          region = var.aws_region
        }
      }
    ]
  })
}
```

### 3. Quality Regression Alarms

```hcl
# Create alarms for each critical field
resource "aws_cloudwatch_metric_alarm" "field_extraction_regression" {
  for_each = toset([
    "type_p_amount_low",
    "type_p_amount_high",
    "type_a_asset_value",
    "type_t_filer_name"
  ])

  alarm_name          = "${local.name_prefix}-extraction-regression-${each.key}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "FieldExtractionRate"
  namespace           = "CongressDisclosures/Extraction"
  period              = 86400  # 1 day
  statistic           = "Average"
  threshold           = 0.85  # Alert if extraction rate drops below 85%
  alarm_description   = "Extraction quality regression detected for ${each.key}"
  actions_enabled     = true
  alarm_actions       = [aws_sns_topic.pipeline_alerts.arn]

  dimensions = {
    FilingType = split("_", each.key)[0]
    Field      = join("_", slice(split("_", each.key), 1, length(split("_", each.key))))
  }

  tags = local.standard_tags
}

# Overall confidence score alarm
resource "aws_cloudwatch_metric_alarm" "confidence_score_regression" {
  alarm_name          = "${local.name_prefix}-confidence-score-regression"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  metric_name         = "ConfidenceScore"
  namespace           = "CongressDisclosures/Extraction"
  period              = 86400
  statistic           = "Average"
  threshold           = 0.80  # Alert if overall confidence drops below 80%
  alarm_description   = "Overall extraction confidence has dropped significantly"
  actions_enabled     = true
  alarm_actions       = [aws_sns_topic.pipeline_alerts.arn]

  tags = local.standard_tags
}
```

## Benefits

1. **Proactive Quality Monitoring**: Detect quality regressions before they cause downstream issues
2. **Data-Driven Improvements**: Identify which filing types/fields need extraction work
3. **Reprocessing Validation**: Verify that new extractors actually improve quality
4. **Version Migration Tracking**: Monitor progress of migrating to improved extractors
5. **Historical Trending**: Track extraction quality improvements over months/years
6. **Operational Visibility**: One dashboard for all extraction quality concerns

## Testing Strategy

### Manual Testing (1 hour)
1. Deploy dashboard to dev environment
2. Trigger extractions with various confidence scores
3. Verify metrics appear in dashboard within 5 minutes
4. Test regression alarm by publishing low confidence metrics
5. Verify SNS notification sent

### Integration Test (1 test)
```python
# tests/integration/test_extraction_dashboard.py

def test_extraction_metrics_published_to_cloudwatch():
    """Test that extraction Lambdas publish metrics to CloudWatch."""
    # Extract a PDF
    lambda_client.invoke(
        FunctionName='house-fd-extract-structured-code',
        Payload=json.dumps({'doc_id': '20063228', 'filing_type': 'type_p'})
    )

    # Wait for metrics to propagate
    time.sleep(60)

    # Query CloudWatch for metrics
    cloudwatch = boto3.client('cloudwatch')
    response = cloudwatch.get_metric_statistics(
        Namespace='CongressDisclosures/Extraction',
        MetricName='ConfidenceScore',
        Dimensions=[
            {'Name': 'FilingType', 'Value': 'type_p'}
        ],
        StartTime=datetime.utcnow() - timedelta(minutes=5),
        EndTime=datetime.utcnow(),
        Period=300,
        Statistics=['Average']
    )

    assert len(response['Datapoints']) > 0
    assert 0 <= response['Datapoints'][0]['Average'] <= 1
```

## Estimated Effort: 3 hours
- 1 hour: Custom CloudWatch metrics in extraction Lambdas
- 1 hour: Terraform dashboard + alarm definitions
- 1 hour: Testing and validation

## Dependencies
- **Requires STORY-054**: Extraction versioning (provides version metrics)
- **Enhanced by STORY-055**: Reprocessing (provides comparison report data)
- **Complements STORY-038**: Pipeline dashboard (separate concern)

## AI Development Notes
**Baseline**: CloudWatch dashboard best practices + custom metrics
**Pattern**: Namespace-based metrics + dimensional filtering
**Files to Create**:
- infra/terraform/cloudwatch_extraction_dashboard.tf (new, ~300 lines)
- tests/integration/test_extraction_dashboard.py (new, 1 test)

**Files to Modify**:
- ingestion/lambdas/house_fd_extract_structured_code/handler.py:120-180 (add publish_extraction_metrics)
- ingestion/lib/extractors/base_extractor.py:95-110 (add metric publishing to create_extraction_metadata)

**Token Budget**: 2,000 tokens (dashboard JSON + metrics + alarm)

**Acceptance Criteria Verification**:
1. ✅ Dashboard displays confidence scores over time
2. ✅ Field-level extraction rates visualized
3. ✅ Reprocessing progress tracked
4. ✅ Quality regressions trigger alarms
5. ✅ Version adoption metrics displayed

**Target**: Sprint 4, Day 1 (January 6, 2026)

---

**NOTE**: This dashboard provides critical visibility into extraction quality, enabling data-driven decisions on which extractors to improve and validation of reprocessing efforts.
