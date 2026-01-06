# DynamoDB Tables for Pipeline State Management



# Pipeline Watermarks Table (NEW - for incremental processing)
resource "aws_dynamodb_table" "pipeline_watermarks" {
  name         = "${var.project_name}-pipeline-watermarks"
  billing_mode = "PAY_PER_REQUEST" # Free tier: 25GB storage, 25 WCU/RCU

  hash_key  = "table_name"
  range_key = "watermark_type"

  attribute {
    name = "table_name"
    type = "S"
  }

  attribute {
    name = "watermark_type"
    type = "S"
  }

  attribute {
    name = "last_processed_timestamp"
    type = "S"
  }

  # GSI for querying by last update time
  global_secondary_index {
    name            = "TimestampIndex"
    hash_key        = "watermark_type"
    range_key       = "last_processed_timestamp"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-pipeline-watermarks"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "incremental-processing"
  }
}

# Pipeline Execution History Table (NEW - for monitoring)
resource "aws_dynamodb_table" "pipeline_execution_history" {
  name         = "${var.project_name}-pipeline-execution-history"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "pipeline_name"
  range_key = "execution_start_time"

  attribute {
    name = "pipeline_name"
    type = "S"
  }

  attribute {
    name = "execution_start_time"
    type = "S"
  }

  attribute {
    name = "execution_status"
    type = "S"
  }

  # GSI for querying by status
  global_secondary_index {
    name            = "StatusIndex"
    hash_key        = "execution_status"
    range_key       = "execution_start_time"
    projection_type = "ALL"
  }

  # TTL for automatic cleanup after 90 days
  ttl {
    enabled        = true
    attribute_name = "ttl_timestamp"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-pipeline-execution-history"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "pipeline-monitoring"
  }
}

# Extraction Versions Table (NEW - for tracking extractor quality metrics)
resource "aws_dynamodb_table" "extraction_versions" {
  name         = "${var.project_name}-extraction-versions"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "extractor_class"
  range_key = "extractor_version"

  attribute {
    name = "extractor_class"
    type = "S"
  }

  attribute {
    name = "extractor_version"
    type = "S"
  }

  attribute {
    name = "deployment_date"
    type = "S"
  }

  # GSI for querying by deployment date
  global_secondary_index {
    name            = "DeploymentDateIndex"
    hash_key        = "extractor_class"
    range_key       = "deployment_date"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-extraction-versions"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "extraction-quality-tracking"
    Sprint      = "sprint-2"
  }
}



# New outputs
output "watermarks_table_name" {
  description = "Name of DynamoDB watermarks table"
  value       = aws_dynamodb_table.pipeline_watermarks.name
}

output "watermarks_table_arn" {
  description = "ARN of DynamoDB watermarks table"
  value       = aws_dynamodb_table.pipeline_watermarks.arn
}

output "execution_history_table_name" {
  description = "Name of DynamoDB execution history table"
  value       = aws_dynamodb_table.pipeline_execution_history.name
}

output "execution_history_table_arn" {
  description = "ARN of DynamoDB execution history table"
  value       = aws_dynamodb_table.pipeline_execution_history.arn
}

output "extraction_versions_table_name" {
  description = "Name of DynamoDB extraction versions table"
  value       = aws_dynamodb_table.extraction_versions.name
}

output "extraction_versions_table_arn" {
  description = "ARN of DynamoDB extraction versions table"
  value       = aws_dynamodb_table.extraction_versions.arn
}
