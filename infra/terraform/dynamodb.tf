# DynamoDB Tables for Pipeline State Management

# Legacy table (keep for backward compatibility)
resource "aws_dynamodb_table" "house_fd_documents" {
  name           = "house_fd_documents"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "doc_id"
  range_key      = "year"

  attribute {
    name = "doc_id"
    type = "S"
  }

  attribute {
    name = "year"
    type = "N"
  }

  tags = {
    Name        = "house_fd_documents"
    Environment = var.environment
    Project     = "congress-disclosures"
  }
}

# Pipeline Watermarks Table (NEW - for incremental processing)
resource "aws_dynamodb_table" "pipeline_watermarks" {
  name         = "${var.project_name}-pipeline-watermarks"
  billing_mode = "PAY_PER_REQUEST"  # Free tier: 25GB storage, 25 WCU/RCU

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

# Legacy outputs
output "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.house_fd_documents.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table"
  value       = aws_dynamodb_table.house_fd_documents.arn
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
