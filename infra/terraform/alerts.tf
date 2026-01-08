# ========================================
# Transaction Alerts Infrastructure
# ========================================
# SNS Topics, DynamoDB Tables, Lambda Functions, IAM Roles
# for real-time congressional transaction alerting

# SNS Topic for Transaction Alerts
resource "aws_sns_topic" "transaction_alerts" {
  name         = "${var.project_name}-transaction-alerts"
  display_name = "Congressional Transaction Alerts"

  tags = {
    Name        = "${var.project_name}-transaction-alerts"
    Environment = var.environment
    Purpose     = "Real-time alerts for high-value and correlated transactions"
  }
}

# DynamoDB Table: Alerts Storage
resource "aws_dynamodb_table" "alerts" {
  name         = "${var.project_name}-alerts"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "alert_id"

  attribute {
    name = "alert_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  attribute {
    name = "alert_type"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  global_secondary_index {
    name            = "alert-type-index"
    hash_key        = "alert_type"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  tags = {
    Name        = "${var.project_name}-alerts"
    Environment = var.environment
    Purpose     = "Alert storage with TTL (90 days)"
  }
}

# DynamoDB Table: Alert Subscriptions
resource "aws_dynamodb_table" "alert_subscriptions" {
  name         = "${var.project_name}-alert-subscriptions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "subscription_id"

  attribute {
    name = "subscription_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  global_secondary_index {
    name            = "user-subscriptions-index"
    hash_key        = "user_id"
    projection_type = "ALL"
  }

  tags = {
    Name        = "${var.project_name}-alert-subscriptions"
    Environment = var.environment
    Purpose     = "User subscription preferences for alerts"
  }
}

# IAM Role for Alert Lambda
resource "aws_iam_role" "transaction_alert_lambda_role" {
  name = "${var.project_name}-transaction-alert-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = {
    Name        = "${var.project_name}-transaction-alert-lambda-role"
    Environment = var.environment
  }
}

# Attach Basic Execution Role
resource "aws_iam_role_policy_attachment" "transaction_alert_lambda_basic" {
  role       = aws_iam_role.transaction_alert_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# IAM Policy for Alert Lambda
resource "aws_iam_role_policy" "transaction_alert_lambda_policy" {
  name = "${var.project_name}-transaction-alert-lambda-policy"
  role = aws_iam_role.transaction_alert_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.transaction_alerts.arn
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.alerts.arn,
          "${aws_dynamodb_table.alerts.arn}/index/*"
        ]
      }
    ]
  })
}

# Lambda Function: Transaction Alert
resource "aws_lambda_function" "transaction_alert" {
  filename         = "${path.module}/../../backend/functions/alerts/transaction_alert/function.zip"
  function_name    = "${var.project_name}-transaction-alert"
  role            = aws_iam_role.transaction_alert_lambda_role.arn
  handler         = "handler.lambda_handler"
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 256

  environment {
    variables = {
      ALERT_SNS_TOPIC_ARN = aws_sns_topic.transaction_alerts.arn
      ALERTS_TABLE_NAME   = aws_dynamodb_table.alerts.name
      LOG_LEVEL           = "INFO"
    }
  }

  tags = {
    Name        = "${var.project_name}-transaction-alert"
    Environment = var.environment
    Purpose     = "Generate and publish transaction alerts"
  }
}

# EventBridge Rule: Trigger on Gold Layer Updates
# Note: This is a placeholder. Actual trigger should be from Step Functions completion
resource "aws_cloudwatch_event_rule" "gold_transactions_updated" {
  name        = "${var.project_name}-gold-transactions-updated"
  description = "Trigger when new transactions added to Gold layer"

  # Placeholder pattern - replace with actual S3 event or Step Functions event
  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [var.s3_bucket_name]
      }
      object = {
        key = [{
          prefix = "data/gold/facts/fact_transactions/"
        }]
      }
    }
  })

  tags = {
    Name        = "${var.project_name}-gold-transactions-updated"
    Environment = var.environment
  }
}

# EventBridge Target: Invoke Alert Lambda
resource "aws_cloudwatch_event_target" "invoke_transaction_alert" {
  rule      = aws_cloudwatch_event_rule.gold_transactions_updated.name
  target_id = "TransactionAlertLambda"
  arn       = aws_lambda_function.transaction_alert.arn
}

# Lambda Permission: Allow EventBridge to Invoke
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.transaction_alert.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.gold_transactions_updated.arn
}

# ========================================
# Outputs
# ========================================

output "alert_sns_topic_arn" {
  value       = aws_sns_topic.transaction_alerts.arn
  description = "ARN of the transaction alerts SNS topic"
}

output "alerts_table_name" {
  value       = aws_dynamodb_table.alerts.name
  description = "Name of the alerts DynamoDB table"
}

output "transaction_alert_lambda_arn" {
  value       = aws_lambda_function.transaction_alert.arn
  description = "ARN of the transaction alert Lambda function"
}
