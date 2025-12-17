# Congress.gov Pipeline Lambda Functions

# =============================================================================
# Lambda Function: congress_api_fetch_entity
# =============================================================================

resource "aws_lambda_function" "congress_fetch_entity" {
  count = var.enable_congress_pipeline ? 1 : 0

  function_name = local.congress_fetch_lambda_name
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"

  # Deploy from S3 (packages >50 MB must use S3)
  s3_bucket        = aws_s3_bucket.data_lake.id
  s3_key           = "lambda-deployments/congress_api_fetch_entity/function.zip"
  source_code_hash = fileexists("${path.module}/../../ingestion/lambdas/congress_api_fetch_entity/function.zip") ? filebase64sha256("${path.module}/../../ingestion/lambdas/congress_api_fetch_entity/function.zip") : null

  timeout     = var.lambda_congress_timeout_seconds
  memory_size = var.lambda_congress_fetch_memory_mb

  # Environment variables
  environment {
    variables = {
      S3_BUCKET_NAME             = aws_s3_bucket.data_lake.id
      CONGRESS_API_KEY           = "" # Placeholder - will be overridden by SSM parameter at runtime
      CONGRESS_API_KEY_SSM_PATH  = local.congress_api_key_ssm_path
      CONGRESS_API_BASE_URL      = var.congress_api_base_url
      EXTRACTION_VERSION         = var.extraction_version
      LOG_LEVEL                  = "INFO"
      PYTHONUNBUFFERED           = "1"
      TZ                         = "UTC"
      CONGRESS_SILVER_QUEUE_URL  = var.enable_congress_pipeline ? aws_sqs_queue.congress_silver_queue[0].url : ""
      CONGRESS_FETCH_QUEUE_URL   = var.enable_congress_pipeline ? aws_sqs_queue.congress_fetch_queue[0].url : ""
    }
  }

  # Reserved concurrent executions disabled to avoid account limits
  # Rate limiting handled by SQS scaling_config instead
  # reserved_concurrent_executions = var.lambda_congress_fetch_max_concurrency

  # Enable X-Ray tracing (optional)
  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }


  tags = merge(
    local.congress_tags,
    {
      Name      = local.congress_fetch_lambda_name
      Component = "lambda"
      Purpose   = "congress-api-fetch"
    }
  )

  # Ignore changes to source code hash (managed by CI/CD)
  lifecycle {
    ignore_changes = [
      source_code_hash,
      filename,
      environment[0].variables["CONGRESS_API_KEY"] # Will be populated by SSM at runtime
    ]
  }

  # Depends on log group and IAM policies
  depends_on = [
    aws_cloudwatch_log_group.congress_fetch_lambda[0],
    aws_iam_role_policy.lambda_logging,
    aws_iam_role_policy.lambda_s3_access,
    aws_iam_role_policy.lambda_sqs_access,
    aws_iam_role_policy.lambda_ssm_congress_api
  ]
}

# Lambda event source mapping for Congress fetch queue
resource "aws_lambda_event_source_mapping" "congress_fetch_queue" {
  count = var.enable_congress_pipeline ? 1 : 0

  event_source_arn = aws_sqs_queue.congress_fetch_queue[0].arn
  function_name    = aws_lambda_function.congress_fetch_entity[0].arn

  # Batch processing configuration
  batch_size                         = var.sqs_congress_fetch_batch_size
  maximum_batching_window_in_seconds = 5 # Wait up to 5 seconds to collect batch

  # Error handling
  function_response_types = ["ReportBatchItemFailures"] # Partial batch failures

  # Scaling configuration
  scaling_config {
    maximum_concurrency = var.lambda_congress_fetch_max_concurrency
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "congress_fetch_lambda_arn" {
  description = "ARN of Congress fetch Lambda function"
  value       = var.enable_congress_pipeline ? aws_lambda_function.congress_fetch_entity[0].arn : ""
}

output "congress_fetch_lambda_name" {
  description = "Name of Congress fetch Lambda function"
  value       = var.enable_congress_pipeline ? aws_lambda_function.congress_fetch_entity[0].function_name : ""
}

output "congress_fetch_lambda_invoke_arn" {
  description = "Invoke ARN of Congress fetch Lambda function"
  value       = var.enable_congress_pipeline ? aws_lambda_function.congress_fetch_entity[0].invoke_arn : ""
}

# =============================================================================
# Lambda Function: congress_api_ingest_orchestrator
# =============================================================================

resource "aws_lambda_function" "congress_orchestrator" {
  count = var.enable_congress_pipeline ? 1 : 0

  function_name = local.congress_orchestrator_lambda_name
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"

  # Deploy from S3
  s3_bucket        = aws_s3_bucket.data_lake.id
  s3_key           = "lambda-deployments/congress_api_ingest_orchestrator/function.zip"
  source_code_hash = fileexists("${path.module}/../../ingestion/lambdas/congress_api_ingest_orchestrator/function.zip") ? filebase64sha256("${path.module}/../../ingestion/lambdas/congress_api_ingest_orchestrator/function.zip") : null

  timeout     = 900 # 15 minutes max (for paginating through all bills)
  memory_size = var.lambda_congress_orchestrator_memory_mb

  # Environment variables
  environment {
    variables = {
      S3_BUCKET_NAME              = aws_s3_bucket.data_lake.id
      CONGRESS_API_KEY_SSM_PATH   = local.congress_api_key_ssm_path
      CONGRESS_API_BASE_URL       = var.congress_api_base_url
      CONGRESS_FETCH_QUEUE_URL    = var.enable_congress_pipeline ? aws_sqs_queue.congress_fetch_queue[0].url : ""
      LOG_LEVEL                   = "INFO"
      PYTHONUNBUFFERED            = "1"
      TZ                          = "UTC"
    }
  }

  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }


  tags = merge(
    local.congress_tags,
    {
      Name      = local.congress_orchestrator_lambda_name
      Component = "lambda"
      Purpose   = "congress-orchestrator"
    }
  )

  lifecycle {
    ignore_changes = [
      source_code_hash,
      filename
    ]
  }

  depends_on = [
    aws_cloudwatch_log_group.congress_orchestrator_lambda[0],
    aws_iam_role_policy.lambda_logging,
    aws_iam_role_policy.lambda_s3_access,
    aws_iam_role_policy.lambda_sqs_access,
    aws_iam_role_policy.lambda_ssm_congress_api
  ]
}

# CloudWatch Log Group for Orchestrator defined in cloudwatch_congress.tf

output "congress_orchestrator_lambda_arn" {
  description = "ARN of Congress orchestrator Lambda function"
  value       = var.enable_congress_pipeline ? aws_lambda_function.congress_orchestrator[0].arn : ""
}

output "congress_orchestrator_lambda_name" {
  description = "Name of Congress orchestrator Lambda function"
  value       = var.enable_congress_pipeline ? aws_lambda_function.congress_orchestrator[0].function_name : ""
}

# =============================================================================
# Lambda Function: congress_bronze_to_silver
# =============================================================================

# Custom Layer for Pandas/PyArrow (Linux binaries)
resource "aws_lambda_layer_version" "congress_pandas_layer" {
  layer_name          = "congress-pandas-pyarrow-layer"
  s3_bucket           = aws_s3_bucket.data_lake.id
  s3_key              = "lambda-deployments/layers/pandas_pyarrow/layer.zip"
  compatible_runtimes = ["python3.11"]
  description         = "Custom layer with pandas 2.1.4, pyarrow 14.0.2, numpy 1.26.4 (stripped)"
}

resource "aws_lambda_function" "congress_bronze_to_silver" {
  count = var.enable_congress_pipeline ? 1 : 0

  function_name = local.congress_silver_lambda_name
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"

  # Deploy from S3
  s3_bucket        = aws_s3_bucket.data_lake.id
  s3_key           = "lambda-deployments/congress_bronze_to_silver/function.zip"
  source_code_hash = fileexists("${path.module}/../../ingestion/lambdas/congress_bronze_to_silver/function.zip") ? filebase64sha256("${path.module}/../../ingestion/lambdas/congress_bronze_to_silver/function.zip") : null

  timeout     = var.lambda_congress_timeout_seconds
  memory_size = var.lambda_congress_silver_memory_mb

  # Use custom layer
  layers = [
    aws_lambda_layer_version.congress_pandas_layer.arn
  ]

  # Environment variables
  environment {
    variables = {
      S3_BUCKET_NAME   = aws_s3_bucket.data_lake.id
      LOG_LEVEL        = "INFO"
      PYTHONUNBUFFERED = "1"
      TZ               = "UTC"
      HOME             = "/tmp"
    }
  }

  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }


  tags = merge(
    local.congress_tags,
    {
      Name      = local.congress_silver_lambda_name
      Component = "lambda"
      Purpose   = "congress-bronze-to-silver"
    }
  )

  lifecycle {
    ignore_changes = [
      source_code_hash,
      filename
    ]
  }

  depends_on = [
    aws_cloudwatch_log_group.congress_silver_lambda[0],
    aws_iam_role_policy.lambda_logging,
    aws_iam_role_policy.lambda_s3_access,
    aws_iam_role_policy.lambda_sqs_access
  ]
}

# CloudWatch Log Group for Silver Lambda defined in cloudwatch_congress.tf

# Lambda event source mapping for Congress Silver queue

resource "aws_lambda_event_source_mapping" "congress_silver_queue" {
  count = var.enable_congress_pipeline ? 1 : 0

  event_source_arn = aws_sqs_queue.congress_silver_queue[0].arn
  function_name    = aws_lambda_function.congress_bronze_to_silver[0].arn

  batch_size                         = var.sqs_congress_silver_batch_size
  maximum_batching_window_in_seconds = 5

  function_response_types = ["ReportBatchItemFailures"]

  scaling_config {
    maximum_concurrency = var.lambda_congress_fetch_max_concurrency
  }

  depends_on = [
    aws_lambda_function.congress_bronze_to_silver[0]
  ]
}

output "congress_silver_lambda_arn" {
  description = "ARN of Congress Bronze-to-Silver Lambda function"
  value       = var.enable_congress_pipeline ? aws_lambda_function.congress_bronze_to_silver[0].arn : ""
}

output "congress_silver_lambda_name" {
  description = "Name of Congress Bronze-to-Silver Lambda function"
  value       = var.enable_congress_pipeline ? aws_lambda_function.congress_bronze_to_silver[0].function_name : ""
}
