# AWS Budgets for Cost Protection
# Monitors spending and sends alerts to prevent exceeding free tier

# SNS Topic for Budget Alerts
resource "aws_sns_topic" "budget_alerts" {
  name         = "${local.name_prefix}-budget-alerts"
  display_name = "Congress Disclosures Budget Alerts"

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-budget-alerts"
      Component = "monitoring"
      Purpose   = "cost-protection"
    }
  )
}

# SNS Topic Subscription (Email)
resource "aws_sns_topic_subscription" "budget_email" {
  topic_arn = aws_sns_topic.budget_alerts.arn
  protocol  = "email"
  endpoint  = var.budget_alert_email
}

# Monthly Budget - Free Tier Limit
resource "aws_budgets_budget" "monthly_free_tier" {
  name         = "${local.name_prefix}-monthly-free-tier"
  budget_type  = "COST"
  limit_amount = var.budget_monthly_limit
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name = "LinkedAccount"
    values = [
      data.aws_caller_identity.current.account_id
    ]
  }

  # Alert at 80% of budget
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [aws_sns_topic.budget_alerts.arn]
  }

  # Alert at 100% of budget
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [aws_sns_topic.budget_alerts.arn]
  }

  # Forecasted alert at 100%
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type            = "PERCENTAGE"
    notification_type         = "FORECASTED"
    subscriber_sns_topic_arns = [aws_sns_topic.budget_alerts.arn]
  }

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-monthly-budget"
      Component = "monitoring"
    }
  )
}

# Daily Budget - Catch runaway costs early
resource "aws_budgets_budget" "daily_limit" {
  name         = "${local.name_prefix}-daily-limit"
  budget_type  = "COST"
  limit_amount = var.budget_daily_limit
  limit_unit   = "USD"
  time_unit    = "DAILY"

  cost_filter {
    name = "LinkedAccount"
    values = [
      data.aws_caller_identity.current.account_id
    ]
  }

  # Alert at 100% of daily budget
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [aws_sns_topic.budget_alerts.arn]
  }

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-daily-budget"
      Component = "monitoring"
    }
  )
}

# Service-specific budgets for high-risk services
resource "aws_budgets_budget" "lambda_budget" {
  name         = "${local.name_prefix}-lambda-budget"
  budget_type  = "COST"
  limit_amount = "5.00"  # Lambda costs should be near zero in free tier
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name = "Service"
    values = [
      "AWS Lambda"
    ]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [aws_sns_topic.budget_alerts.arn]
  }

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-lambda-budget"
      Component = "monitoring"
      Service   = "lambda"
    }
  )
}

resource "aws_budgets_budget" "s3_budget" {
  name         = "${local.name_prefix}-s3-budget"
  budget_type  = "COST"
  limit_amount = "2.00"  # S3 should be mostly free tier
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name = "Service"
    values = [
      "Amazon Simple Storage Service"
    ]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [aws_sns_topic.budget_alerts.arn]
  }

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-s3-budget"
      Component = "monitoring"
      Service   = "s3"
    }
  )
}

# CloudWatch Alarm for Cost Anomaly Detection
resource "aws_cloudwatch_metric_alarm" "estimated_charges" {
  alarm_name          = "${local.name_prefix}-estimated-charges-alarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "21600"  # 6 hours
  statistic           = "Maximum"
  threshold           = var.budget_monthly_limit
  alarm_description   = "Alert when estimated charges exceed monthly budget"
  alarm_actions       = [aws_sns_topic.budget_alerts.arn]

  dimensions = {
    Currency = "USD"
  }

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-billing-alarm"
      Component = "monitoring"
    }
  )
}

# Lambda for Emergency Shutdown (Optional)
resource "aws_lambda_function" "emergency_shutdown" {
  function_name = "${local.name_prefix}-emergency-shutdown"
  role          = aws_iam_role.shutdown_lambda.arn
  handler       = "shutdown.lambda_handler"
  runtime       = "python3.11"
  timeout       = 60
  memory_size   = 128

  filename         = "${path.module}/lambda_packages/emergency_shutdown.zip"
  source_code_hash = fileexists("${path.module}/lambda_packages/emergency_shutdown.zip") ? filebase64sha256("${path.module}/lambda_packages/emergency_shutdown.zip") : null

  environment {
    variables = {
      ENVIRONMENT           = var.environment
      PROJECT_NAME          = var.project_name
      LAMBDA_FUNCTION_ARNS  = jsonencode([
        aws_lambda_function.ingest_zip.arn,
        aws_lambda_function.index_to_silver.arn,
        aws_lambda_function.extract_document.arn,
      ])
      SNS_TOPIC_ARN = aws_sns_topic.budget_alerts.arn
    }
  }

  tags = merge(
    local.standard_tags,
    {
      Name      = "${local.name_prefix}-emergency-shutdown"
      Component = "lambda"
      Purpose   = "cost-protection"
    }
  )
}

# IAM Role for Shutdown Lambda
resource "aws_iam_role" "shutdown_lambda" {
  name = "${local.name_prefix}-shutdown-lambda-role"

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
      Name      = "${local.name_prefix}-shutdown-lambda-role"
      Component = "iam"
    }
  )
}

# IAM Policy for Shutdown Lambda
resource "aws_iam_role_policy" "shutdown_lambda_policy" {
  name = "${local.name_prefix}-shutdown-lambda-policy"
  role = aws_iam_role.shutdown_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:UpdateFunctionConfiguration",
          "lambda:GetFunction",
          "lambda:ListFunctions"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.budget_alerts.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# SNS Topic Subscription for Emergency Shutdown Lambda
resource "aws_sns_topic_subscription" "shutdown_lambda" {
  topic_arn = aws_sns_topic.budget_alerts.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.emergency_shutdown.arn
}

# Lambda Permission for SNS
resource "aws_lambda_permission" "allow_sns" {
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.emergency_shutdown.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.budget_alerts.arn
}
