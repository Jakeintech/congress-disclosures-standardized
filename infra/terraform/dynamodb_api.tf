# DynamoDB Tables for API Layer (Authentication, Caching, Usage Tracking)

# API Response Cache (TTL-based automatic expiration)
resource "aws_dynamodb_table" "api_cache" {
  name         = "${var.project_name}-api-cache"
  billing_mode = "PAY_PER_REQUEST" # Free tier: 25 WCU/RCU, pay only for usage

  hash_key = "cache_key"

  attribute {
    name = "cache_key"
    type = "S"
  }

  # TTL for automatic cache expiration
  ttl {
    enabled        = true
    attribute_name = "expires_at"
  }

  # Enable point-in-time recovery for production safety
  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-api-cache"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "api-response-caching"
    Layer       = "api"
  }
}

# API Keys Table (for authentication and tier management)
resource "aws_dynamodb_table" "api_keys" {
  name         = "${var.project_name}-api-keys"
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "api_key_hash"

  attribute {
    name = "api_key_hash"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  # GSI for querying by user_id (e.g., get all keys for a user)
  global_secondary_index {
    name            = "UserIdIndex"
    hash_key        = "user_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  # TTL for key expiration (e.g., trial keys expire after 30 days)
  ttl {
    enabled        = true
    attribute_name = "expires_at"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-api-keys"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "api-authentication"
    Layer       = "api"
  }
}

# API Usage Tracking (for billing and rate limiting)
resource "aws_dynamodb_table" "api_usage" {
  name         = "${var.project_name}-api-usage"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "user_id"
  range_key = "timestamp"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "hour_key"
    type = "S"
  }

  # GSI for hourly aggregation (for rate limiting)
  global_secondary_index {
    name            = "HourlyUsageIndex"
    hash_key        = "user_id"
    range_key       = "hour_key"
    projection_type = "ALL"
  }

  # TTL for automatic cleanup after 90 days (compliance + cost optimization)
  ttl {
    enabled        = true
    attribute_name = "ttl"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-api-usage"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "usage-metering"
    Layer       = "api"
  }
}

# API Usage Aggregates (daily/monthly rollups for billing)
resource "aws_dynamodb_table" "api_usage_aggregates" {
  name         = "${var.project_name}-api-usage-aggregates"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "user_id"
  range_key = "date"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "date"
    type = "S" # Format: YYYY-MM-DD
  }

  attribute {
    name = "month"
    type = "S" # Format: YYYY-MM
  }

  # GSI for monthly billing queries
  global_secondary_index {
    name            = "MonthlyBillingIndex"
    hash_key        = "user_id"
    range_key       = "month"
    projection_type = "ALL"
  }

  # TTL for cleanup after 2 years (legal retention)
  ttl {
    enabled        = true
    attribute_name = "ttl"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-api-usage-aggregates"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "billing-aggregation"
    Layer       = "api"
  }
}

# Outputs
output "api_cache_table_name" {
  description = "Name of API cache DynamoDB table"
  value       = aws_dynamodb_table.api_cache.name
}

output "api_cache_table_arn" {
  description = "ARN of API cache DynamoDB table"
  value       = aws_dynamodb_table.api_cache.arn
}

output "api_keys_table_name" {
  description = "Name of API keys DynamoDB table"
  value       = aws_dynamodb_table.api_keys.name
}

output "api_keys_table_arn" {
  description = "ARN of API keys DynamoDB table"
  value       = aws_dynamodb_table.api_keys.arn
}

output "api_usage_table_name" {
  description = "Name of API usage tracking DynamoDB table"
  value       = aws_dynamodb_table.api_usage.name
}

output "api_usage_table_arn" {
  description = "ARN of API usage tracking DynamoDB table"
  value       = aws_dynamodb_table.api_usage.arn
}

output "api_usage_aggregates_table_name" {
  description = "Name of API usage aggregates DynamoDB table"
  value       = aws_dynamodb_table.api_usage_aggregates.name
}

output "api_usage_aggregates_table_arn" {
  description = "ARN of API usage aggregates DynamoDB table"
  value       = aws_dynamodb_table.api_usage_aggregates.arn
}
