# Congress.gov API Configuration Variables

variable "congress_gov_api_key" {
  description = "API key for Congress.gov API (required for all API requests)"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.congress_gov_api_key) > 0
    error_message = "Congress.gov API key is required."
  }
}

variable "congress_api_base_url" {
  description = "Base URL for Congress.gov API"
  type        = string
  default     = "https://api.congress.gov/v3"

  validation {
    condition     = can(regex("^https://", var.congress_api_base_url))
    error_message = "API base URL must use HTTPS."
  }
}

variable "congress_api_rate_limit_per_hour" {
  description = "Maximum API requests per hour (Congress.gov limit: 5000/hour with API key)"
  type        = number
  default     = 5000 # Official Congress.gov API limit with key

  validation {
    condition     = var.congress_api_rate_limit_per_hour >= 1 && var.congress_api_rate_limit_per_hour <= 10000
    error_message = "API rate limit must be between 1 and 10000 requests per hour."
  }
}

variable "congress_api_key_ssm_path" {
  description = "SSM Parameter Store path for Congress.gov API key (overrides computed path)"
  type        = string
  default     = "" # Empty string means use computed path: /congress-disclosures/{environment}/congress-api-key

  validation {
    condition = var.congress_api_key_ssm_path == "" || can(regex("^/", var.congress_api_key_ssm_path))
    error_message = "SSM parameter path must start with / if provided."
  }
}

# Lambda Configuration for Congress Ingestion

variable "lambda_congress_fetch_memory_mb" {
  description = "Memory allocation for Congress API fetch Lambda in MB"
  type        = number
  default     = 512 # Lightweight API calls and JSON compression

  validation {
    condition     = var.lambda_congress_fetch_memory_mb >= 128 && var.lambda_congress_fetch_memory_mb <= 10240
    error_message = "Lambda memory must be between 128 and 10240 MB."
  }
}

variable "lambda_congress_orchestrator_memory_mb" {
  description = "Memory allocation for Congress API orchestrator Lambda in MB"
  type        = number
  default     = 1024 # Handles pagination and batch SQS operations

  validation {
    condition     = var.lambda_congress_orchestrator_memory_mb >= 128 && var.lambda_congress_orchestrator_memory_mb <= 10240
    error_message = "Lambda memory must be between 128 and 10240 MB."
  }
}

variable "lambda_congress_silver_memory_mb" {
  description = "Memory allocation for Congress Bronze-to-Silver Lambda in MB"
  type        = number
  default     = 1024 # Pandas DataFrame operations and Parquet writes

  validation {
    condition     = var.lambda_congress_silver_memory_mb >= 128 && var.lambda_congress_silver_memory_mb <= 10240
    error_message = "Lambda memory must be between 128 and 10240 MB."
  }
}

variable "lambda_congress_timeout_seconds" {
  description = "Lambda function timeout for Congress functions in seconds"
  type        = number
  default     = 300 # 5 minutes (sufficient for API calls with retries)

  validation {
    condition     = var.lambda_congress_timeout_seconds >= 30 && var.lambda_congress_timeout_seconds <= 900
    error_message = "Lambda timeout must be between 30 and 900 seconds."
  }
}

# SQS Configuration for Congress Pipeline

variable "sqs_congress_fetch_batch_size" {
  description = "Number of messages processed per Lambda invocation (Congress fetch queue)"
  type        = number
  default     = 10 # Balance between throughput and error handling

  validation {
    condition     = var.sqs_congress_fetch_batch_size >= 1 && var.sqs_congress_fetch_batch_size <= 10
    error_message = "SQS batch size must be between 1 and 10."
  }
}

variable "sqs_congress_silver_batch_size" {
  description = "Number of messages processed per Lambda invocation (Congress Bronze-to-Silver queue)"
  type        = number
  default     = 10

  validation {
    condition     = var.sqs_congress_silver_batch_size >= 1 && var.sqs_congress_silver_batch_size <= 10
    error_message = "SQS batch size must be between 1 and 10."
  }
}

variable "lambda_congress_fetch_max_concurrency" {
  description = "Maximum concurrent executions for Congress fetch Lambda (controls API rate limiting)"
  type        = number
  default     = 5 # Conservative to avoid hitting Congress.gov rate limits

  validation {
    condition     = var.lambda_congress_fetch_max_concurrency >= 1 && var.lambda_congress_fetch_max_concurrency <= 100
    error_message = "Max concurrency must be between 1 and 100."
  }
}

# Congress Data Configuration

variable "congress_number_default" {
  description = "Default Congress number for ingestion (118 = 2023-2025)"
  type        = number
  default     = 118

  validation {
    condition     = var.congress_number_default >= 93 && var.congress_number_default <= 200
    error_message = "Congress number must be between 93 (1973) and 200."
  }
}

variable "congress_ingest_entity_types" {
  description = "List of Congress entity types to ingest (for orchestrator)"
  type        = list(string)
  default     = ["member", "bill", "house_vote", "senate_vote", "committee"]

  validation {
    condition = alltrue([
      for entity in var.congress_ingest_entity_types :
      contains(["member", "bill", "amendment", "committee", "house_vote", "senate_vote"], entity)
    ])
    error_message = "Entity types must be valid Congress.gov entity types."
  }
}

variable "congress_ingest_bill_types" {
  description = "List of bill types to ingest (for bill orchestration)"
  type        = list(string)
  default     = ["hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"]

  validation {
    condition = alltrue([
      for bill_type in var.congress_ingest_bill_types :
      contains(["hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"], bill_type)
    ])
    error_message = "Bill types must be valid Congress.gov bill types."
  }
}

# Feature Flags

variable "enable_congress_pipeline" {
  description = "Enable Congress.gov pipeline infrastructure (Lambdas, SQS queues)"
  type        = bool
  default     = true
}

variable "enable_congress_incremental_sync" {
  description = "Enable daily incremental sync via EventBridge (cron)"
  type        = bool
  default     = false # Manual trigger only for now, enable after testing
}

# Tagging

variable "congress_common_tags" {
  description = "Common tags for Congress.gov pipeline resources"
  type        = map(string)
  default = {
    Component = "congress-ingestion"
    DataSource = "congress-api"
  }
}

# Computed Locals

locals {
  # Compute SSM parameter path for Congress API key
  congress_api_key_ssm_path = var.congress_api_key_ssm_path != "" ? var.congress_api_key_ssm_path : "/${var.project_name}-standardized/${var.environment}/congress-api-key"

  # Merge common tags with Congress-specific tags
  congress_tags = merge(var.common_tags, var.congress_common_tags)

  # Congress Lambda function names
  congress_fetch_lambda_name        = "${var.project_name}-${var.environment}-congress-fetch-entity"
  congress_orchestrator_lambda_name = "${var.project_name}-${var.environment}-congress-orchestrator"
  congress_silver_lambda_name       = "${var.project_name}-${var.environment}-congress-bronze-to-silver"

  # Congress SQS queue names
  congress_fetch_queue_name    = "${var.project_name}-${var.environment}-congress-fetch-queue"
  congress_fetch_dlq_name      = "${var.project_name}-${var.environment}-congress-fetch-dlq"
  congress_silver_queue_name   = "${var.project_name}-${var.environment}-congress-silver-queue"
  congress_silver_dlq_name     = "${var.project_name}-${var.environment}-congress-silver-dlq"
}
