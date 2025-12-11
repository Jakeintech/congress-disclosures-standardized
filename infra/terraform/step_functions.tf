# Step Functions State Machines for Data Pipeline Orchestration

# IAM Role for Step Functions
resource "aws_iam_role" "step_functions_role" {
  name = "${var.project_name}-step-functions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# IAM Policy for Step Functions
resource "aws_iam_role_policy" "step_functions_policy" {
  name = "${var.project_name}-step-functions-policy"
  role = aws_iam_role.step_functions_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${var.project_name}-*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.pipeline_alerts.arn
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = "arn:aws:states:${var.aws_region}:${data.aws_caller_identity.current.account_id}:stateMachine:${var.project_name}-*"
      },
      {
        Effect = "Allow"
        Action = [
          "events:PutTargets",
          "events:PutRule",
          "events:DescribeRule"
        ]
        Resource = "arn:aws:events:${var.aws_region}:${data.aws_caller_identity.current.account_id}:rule/*"
      }
    ]
  })
}

# Note: aws_caller_identity data source is defined in main.tf

# Template file for state machines (substitutes variables)
locals {
  state_machine_vars = {
    AWS_REGION     = var.aws_region
    AWS_ACCOUNT_ID = data.aws_caller_identity.current.account_id
    PROJECT_NAME   = var.project_name
  }
}

# House FD Pipeline State Machine
resource "aws_sfn_state_machine" "house_fd_pipeline" {
  name     = "${var.project_name}-house-fd-pipeline"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = templatefile("${path.module}/../../state_machines/house_fd_pipeline.json", local.state_machine_vars)

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions_logs.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-house-fd-pipeline"
    Project     = var.project_name
    Environment = var.environment
    Pipeline    = "house-fd"
  }
}

# Congress.gov Pipeline State Machine
resource "aws_sfn_state_machine" "congress_pipeline" {
  name     = "${var.project_name}-congress-pipeline"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = templatefile("${path.module}/../../state_machines/congress_pipeline.json", local.state_machine_vars)

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions_logs.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-congress-pipeline"
    Project     = var.project_name
    Environment = var.environment
    Pipeline    = "congress"
  }
}

# Lobbying Pipeline State Machine
resource "aws_sfn_state_machine" "lobbying_pipeline" {
  name     = "${var.project_name}-lobbying-pipeline"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = templatefile("${path.module}/../../state_machines/lobbying_pipeline.json", local.state_machine_vars)

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions_logs.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-lobbying-pipeline"
    Project     = var.project_name
    Environment = var.environment
    Pipeline    = "lobbying"
  }
}

# Cross-Dataset Correlation Pipeline State Machine
resource "aws_sfn_state_machine" "cross_dataset_correlation" {
  name     = "${var.project_name}-cross-dataset-correlation"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = templatefile("${path.module}/../../state_machines/cross_dataset_correlation.json", local.state_machine_vars)

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions_logs.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-cross-dataset-correlation"
    Project     = var.project_name
    Environment = var.environment
    Pipeline    = "correlation"
  }
}

# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions_logs" {
  name              = "/aws/vendedlogs/states/${var.project_name}-pipelines"
  retention_in_days = 30

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# Outputs
output "house_fd_pipeline_arn" {
  description = "ARN of House FD Pipeline state machine"
  value       = aws_sfn_state_machine.house_fd_pipeline.arn
}

output "congress_pipeline_arn" {
  description = "ARN of Congress.gov Pipeline state machine"
  value       = aws_sfn_state_machine.congress_pipeline.arn
}

output "lobbying_pipeline_arn" {
  description = "ARN of Lobbying Pipeline state machine"
  value       = aws_sfn_state_machine.lobbying_pipeline.arn
}

output "cross_dataset_correlation_arn" {
  description = "ARN of Cross-Dataset Correlation Pipeline state machine"
  value       = aws_sfn_state_machine.cross_dataset_correlation.arn
}

output "step_functions_role_arn" {
  description = "ARN of Step Functions execution role"
  value       = aws_iam_role.step_functions_role.arn
}
