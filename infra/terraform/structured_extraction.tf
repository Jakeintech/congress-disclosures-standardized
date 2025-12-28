# Structured Extraction Terraform

resource "aws_sqs_queue" "structured_extraction_queue" {
  name                      = "congress-disclosures-development-structured-extraction-queue-v2"
  visibility_timeout_seconds = 5400
  message_retention_seconds  = 345600
}

resource "aws_lambda_function" "structured_extraction" {
  function_name = "congress-disclosures-development-structured-extraction"
  role          = aws_iam_role.structured_extraction_lambda_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 900
  memory_size   = 1024
  filename      = "${path.module}/../../ingestion/lambdas/house_fd_extract_structured/dist/package.zip"
  # Guard against missing local zip during plans that don't deploy this Lambda
  # This prevents plan/apply for unrelated targets (e.g., bucket policy) from failing.
  source_code_hash = try(filebase64sha256("${path.module}/../../ingestion/lambdas/house_fd_extract_structured/dist/package.zip"), null)

  environment {
    variables = {
      S3_BUCKET_NAME               = var.s3_bucket_name
      S3_BRONZE_PREFIX             = "bronze"
      S3_SILVER_PREFIX             = "silver"
      LOG_LEVEL                    = "INFO"
      STRUCTURED_EXTRACTION_QUEUE_URL = aws_sqs_queue.structured_extraction_queue.id
    }
  }
}

resource "aws_lambda_event_source_mapping" "sqs_to_lambda" {
  event_source_arn = aws_sqs_queue.structured_extraction_queue.arn
  function_name    = aws_lambda_function.structured_extraction.arn
  batch_size       = 10
  enabled          = true
}
