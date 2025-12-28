# SNS Topics for Pipeline Alerts and Notifications

# Pipeline Alerts Topic
resource "aws_sns_topic" "pipeline_alerts" {
  name = "${var.project_name}-pipeline-alerts"

  tags = {
    Name        = "${var.project_name}-pipeline-alerts"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "pipeline-monitoring"
  }
}

# Email subscription for pipeline alerts (optional, controlled by variable)
resource "aws_sns_topic_subscription" "pipeline_alerts_email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.pipeline_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Optional: SMS subscription for critical alerts
resource "aws_sns_topic_subscription" "pipeline_alerts_sms" {
  count     = var.alert_phone_number != "" ? 1 : 0
  topic_arn = aws_sns_topic.pipeline_alerts.arn
  protocol  = "sms"
  endpoint  = var.alert_phone_number
}

# Optional: Lambda subscription for custom alert handling
# resource "aws_sns_topic_subscription" "pipeline_alerts_lambda" {
#   count     = var.enable_custom_alert_handler ? 1 : 0
#   topic_arn = aws_sns_topic.pipeline_alerts.arn
#   protocol  = "lambda"
#   endpoint  = aws_lambda_function.custom_alert_handler[0].arn
# }

# Data Quality Alerts Topic (separate from general pipeline alerts)
resource "aws_sns_topic" "data_quality_alerts" {
  name = "${var.project_name}-data-quality-alerts"

  tags = {
    Name        = "${var.project_name}-data-quality-alerts"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "data-quality-monitoring"
  }
}

# Email subscription for data quality alerts
resource "aws_sns_topic_subscription" "data_quality_alerts_email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.data_quality_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Outputs
output "pipeline_alerts_topic_arn" {
  description = "ARN of SNS topic for pipeline alerts"
  value       = aws_sns_topic.pipeline_alerts.arn
}

output "data_quality_alerts_topic_arn" {
  description = "ARN of SNS topic for data quality alerts"
  value       = aws_sns_topic.data_quality_alerts.arn
}
