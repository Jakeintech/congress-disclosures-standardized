variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1" # Cheapest region for most services
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "development"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

variable "project_name" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "congress-disclosures"
}

variable "s3_bucket_name" {
  description = "Name for the S3 data lake bucket (must be globally unique)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]*[a-z0-9]$", var.s3_bucket_name))
    error_message = "S3 bucket name must be lowercase alphanumeric with hyphens."
  }
}

variable "enable_s3_versioning" {
  description = "Enable versioning on S3 bucket (recommended for bronze layer)"
  type        = bool
  default     = true
}

variable "s3_lifecycle_glacier_days" {
  description = "Days before transitioning silver data to Glacier (0 to disable)"
  type        = number
  default     = 365 # 1 year
}

variable "lambda_timeout_seconds" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 300 # 5 minutes

  validation {
    condition     = var.lambda_timeout_seconds >= 30 && var.lambda_timeout_seconds <= 900
    error_message = "Lambda timeout must be between 30 and 900 seconds."
  }
}

variable "lambda_ingest_memory_mb" {
  description = "Memory allocation for ingest Lambda in MB"
  type        = number
  default     = 1024 # Optimized for zip download/extraction

  validation {
    condition     = var.lambda_ingest_memory_mb >= 128 && var.lambda_ingest_memory_mb <= 10240
    error_message = "Lambda memory must be between 128 and 10240 MB."
  }
}

variable "lambda_extract_memory_mb" {
  description = "Memory allocation for extract Lambda in MB"
  type        = number
  default     = 2048 # Needs more memory for PDF/Textract processing

  validation {
    condition     = var.lambda_extract_memory_mb >= 128 && var.lambda_extract_memory_mb <= 10240
    error_message = "Lambda memory must be between 128 and 10240 MB."
  }
}

variable "lambda_index_memory_mb" {
  description = "Memory allocation for index Lambda in MB"
  type        = number
  default     = 512 # Lightweight XML/Parquet processing

  validation {
    condition     = var.lambda_index_memory_mb >= 128 && var.lambda_index_memory_mb <= 10240
    error_message = "Lambda memory must be between 128 and 10240 MB."
  }
}

variable "lambda_max_concurrent_executions" {
  description = "Maximum concurrent Lambda executions (controls costs)"
  type        = number
  default     = 10 # Reasonable limit for free tier

  validation {
    condition     = var.lambda_max_concurrent_executions >= 1 && var.lambda_max_concurrent_executions <= 1000
    error_message = "Concurrent executions must be between 1 and 1000."
  }
}

variable "sqs_visibility_timeout_seconds" {
  description = "SQS message visibility timeout (should be > Lambda timeout)"
  type        = number
  default     = 360 # 6 minutes (Lambda timeout + buffer)

  validation {
    condition     = var.sqs_visibility_timeout_seconds >= 30 && var.sqs_visibility_timeout_seconds <= 43200
    error_message = "SQS visibility timeout must be between 30 and 43200 seconds."
  }
}

variable "sqs_message_retention_days" {
  description = "Days to retain SQS messages"
  type        = number
  default     = 4

  validation {
    condition     = var.sqs_message_retention_days >= 1 && var.sqs_message_retention_days <= 14
    error_message = "SQS message retention must be between 1 and 14 days."
  }
}

variable "sqs_max_receive_count" {
  description = "Max receives before moving to DLQ"
  type        = number
  default     = 3

  validation {
    condition     = var.sqs_max_receive_count >= 1 && var.sqs_max_receive_count <= 1000
    error_message = "Max receive count must be between 1 and 1000."
  }
}

variable "cloudwatch_log_retention_days" {
  description = "CloudWatch Logs retention period in days"
  type        = number
  default     = 30 # Balance between auditability and cost

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.cloudwatch_log_retention_days)
    error_message = "Log retention must be a valid CloudWatch retention period."
  }
}

variable "enable_cost_alerts" {
  description = "Enable CloudWatch alarms for cost monitoring"
  type        = bool
  default     = true
}

variable "alert_email" {
  description = "Email address for CloudWatch alarms (optional)"
  type        = string
  default     = ""
}

variable "common_tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default = {
    Project    = "congress-disclosures-standardized"
    ManagedBy  = "terraform"
    Repository = "https://github.com/Jakeintech/congress-disclosures-standardized"
  }
}

variable "lambda_layer_arns" {
  description = "Optional Lambda Layer ARNs (e.g., for AWS SDK, pandas)"
  type        = list(string)
  default     = []
}

variable "enable_xray_tracing" {
  description = "Enable AWS X-Ray tracing for Lambdas (debugging)"
  type        = bool
  default     = false # Disabled by default to save costs
}

variable "textract_max_pages_sync" {
  description = "Max pages to process synchronously with Textract"
  type        = number
  default     = 10

  validation {
    condition     = var.textract_max_pages_sync >= 1 && var.textract_max_pages_sync <= 100
    error_message = "Textract sync max pages must be between 1 and 100."
  }
}

variable "textract_monthly_page_limit" {
  description = "Monthly page limit for Textract processing (AWS free tier: 1000 pages/month for 3 months)"
  type        = number
  default     = 1000

  validation {
    condition     = var.textract_monthly_page_limit >= 0 && var.textract_monthly_page_limit <= 100000
    error_message = "Textract monthly page limit must be between 0 and 100000."
  }
}

variable "extraction_version" {
  description = "Version string for extraction pipeline (for auditability)"
  type        = string
  default     = "1.0.0"
}

variable "seed_data_version" {
  description = "Version string for seed data run (bump to re-run bootstrap)"
  type        = string
  default     = "1"
}

variable "ssm_congress_api_key_param" {
  description = "SSM Parameter Store name for Congress.gov API key (leave blank to use default path per environment)"
  type        = string
  default     = ""
}

# Budget Configuration
variable "budget_alert_email" {
  description = "Email address for budget alerts (required for cost protection)"
  type        = string
}

variable "budget_monthly_limit" {
  description = "Monthly budget limit in USD"
  type        = string
  default     = "5.00"
}

variable "budget_daily_limit" {
  description = "Daily budget limit in USD (to catch runaway costs)"
  type        = string
  default     = "0.50"
}

variable "tesseract_layer_arn" {
  description = "ARN of Lambda Layer containing Tesseract binaries (e.g., Klayers)"
  type        = string
  default     = "arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p311-tesseract:1"
}
