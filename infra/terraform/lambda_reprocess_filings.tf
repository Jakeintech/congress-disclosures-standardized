# Lambda function: reprocess_filings
# STORY-055: Selective Reprocessing Lambda

resource "aws_lambda_function" "reprocess_filings" {
  function_name = "${local.name_prefix}-reprocess-filings"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"

  # Deploy from S3 (packages >50 MB must use S3)
  s3_bucket = aws_s3_bucket.data_lake.id
  s3_key    = "lambda-deployments/reprocess_filings/function.zip"

  timeout     = 900  # 15 minutes for batch processing
  memory_size = 2048 # 2 GB for processing multiple PDFs

  environment {
    variables = {
      S3_BUCKET_NAME          = aws_s3_bucket.data_lake.id
      DYNAMODB_VERSIONS_TABLE = aws_dynamodb_table.extraction_versions.name
      SNS_ALERTS_ARN          = aws_sns_topic.pipeline_alerts.arn
      LOG_LEVEL               = "INFO"
      PYTHONUNBUFFERED        = "1"
      TZ                      = "UTC"
    }
  }

  # Enable X-Ray tracing
  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-reprocess-filings"
      Component = "lambda"
      Purpose   = "selective-reprocessing"
      Story     = "STORY-055"
    }
  )

  lifecycle {
    ignore_changes = [
      source_code_hash,
      filename
    ]
  }

  depends_on = [
    aws_cloudwatch_log_group.reprocess_filings,
    aws_iam_role_policy.lambda_logging
  ]
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "reprocess_filings" {
  name              = "/aws/lambda/${local.name_prefix}-reprocess-filings"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = merge(
    local.standard_tags,
    {
      Name  = "${local.name_prefix}-reprocess-filings-logs"
      Story = "STORY-055"
    }
  )
}

# IAM Policy for Bronze/Silver/Reports S3 access
resource "aws_iam_role_policy" "reprocess_filings_s3" {
  name = "${local.name_prefix}-reprocess-filings-s3"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${aws_s3_bucket.data_lake.arn}/bronze/*",
          "${aws_s3_bucket.data_lake.arn}/silver/*",
          "${aws_s3_bucket.data_lake.arn}/reports/*",
          aws_s3_bucket.data_lake.arn
        ]
      }
    ]
  })
}

# IAM Policy for DynamoDB extraction_versions table
resource "aws_iam_role_policy" "reprocess_filings_dynamodb" {
  name = "${local.name_prefix}-reprocess-filings-dynamodb"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.extraction_versions.arn,
          "${aws_dynamodb_table.extraction_versions.arn}/index/*"
        ]
      }
    ]
  })
}

# IAM Policy for SNS notifications
resource "aws_iam_role_policy" "reprocess_filings_sns" {
  name = "${local.name_prefix}-reprocess-filings-sns"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.pipeline_alerts.arn
      }
    ]
  })
}

# Output
output "reprocess_filings_function_name" {
  description = "Name of reprocess_filings Lambda function"
  value       = aws_lambda_function.reprocess_filings.function_name
}

output "reprocess_filings_function_arn" {
  description = "ARN of reprocess_filings Lambda function"
  value       = aws_lambda_function.reprocess_filings.arn
}
