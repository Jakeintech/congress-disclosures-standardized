# IAM role for Lambda functions
resource "aws_iam_role" "lambda_execution" {
  name = "${local.name_prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-lambda-role"
      Component = "iam"
    }
  )
}

# CloudWatch Logs policy (all Lambdas need this)
resource "aws_iam_role_policy" "lambda_logging" {
  name = "${local.name_prefix}-lambda-logging"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${local.region}:${local.account_id}:log-group:/aws/lambda/${local.name_prefix}-*:*"
      }
    ]
  })
}

# S3 policy for data lake access
resource "aws_iam_role_policy" "lambda_s3_access" {
  name = "${local.name_prefix}-lambda-s3"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:PutObjectAcl",
          "s3:DeleteObject" # Needed for cleanup/re-processing
        ]
        Resource = "${aws_s3_bucket.data_lake.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = aws_s3_bucket.data_lake.arn
      }
    ]
  })
}

# SQS policy for extraction queue
resource "aws_iam_role_policy" "lambda_sqs_access" {
  name = "${local.name_prefix}-lambda-sqs"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:SendMessage" # For ingestion Lambda to send messages
        ]
        Resource = [
          aws_sqs_queue.extraction_queue.arn,
          aws_sqs_queue.extraction_dlq.arn,
          aws_sqs_queue.structured_extraction_queue.arn, # For extract Lambda to queue structured extraction
          aws_sqs_queue.code_extraction_queue.arn,       # For code-based extraction
          aws_sqs_queue.code_extraction_dlq.arn          # Code extraction DLQ
        ]
      }
    ]
  })
}

# SSM Parameter Store access for Congress API key (used by dim_members seed)
resource "aws_iam_role_policy" "lambda_ssm_congress_api" {
  name = "${local.name_prefix}-lambda-ssm-congress-api"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "ssm:GetParameter"
        ],
        Resource = "arn:aws:ssm:${local.region}:${local.account_id}:parameter${local.ssm_congress_api_key_param}"
      }
    ]
  })
}

# Optional: X-Ray tracing policy (disabled by default for cost savings)
resource "aws_iam_role_policy" "lambda_xray_access" {
  count = var.enable_xray_tracing ? 1 : 0

  name = "${local.name_prefix}-lambda-xray"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords"
        ]
        Resource = "*"
      }
    ]
  })
}

# Cost Explorer access for cost visualization
resource "aws_iam_role_policy" "lambda_ce_access" {
  name = "${local.name_prefix}-lambda-ce"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ce:GetCostAndUsage"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_s3_list" {
  name = "${local.name_prefix}-lambda-s3-list"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.data_lake.arn
        Condition = {
          StringLike = {
            "s3:prefix" = [
              "bronze/*",
              "silver/*",
              "gold/*"
            ]
          }
        }
      }
    ]
  })
}

# VPC access policy (if Lambdas need VPC access in the future)
# Commented out by default as VPC access increases costs and cold start times
# resource "aws_iam_role_policy_attachment" "lambda_vpc_execution" {
#   role       = aws_iam_role.lambda_execution.name
#   policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
# }

# Output IAM role details
output "lambda_execution_role_arn" {
  description = "ARN of Lambda execution role"
  value       = aws_iam_role.lambda_execution.arn
}

output "lambda_execution_role_name" {
  description = "Name of Lambda execution role"
  value       = aws_iam_role.lambda_execution.name
}
