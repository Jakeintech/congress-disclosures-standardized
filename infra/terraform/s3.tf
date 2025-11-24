# Main data lake bucket
resource "aws_s3_bucket" "data_lake" {
  bucket = var.s3_bucket_name

  tags = merge(
    local.standard_tags,
    {
      Name      = var.s3_bucket_name
      Component = "storage"
      Purpose   = "data-lake"
    }
  )
}

# Block all public access (security best practice)
resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning for bronze layer (immutable archive)
resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  versioning_configuration {
    status = var.enable_s3_versioning ? "Enabled" : "Disabled"
  }
}

# Server-side encryption (free, always enabled)
resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256" # SSE-S3 is free
    }
    bucket_key_enabled = true # Reduces KMS costs if using KMS later
  }
}

# Lifecycle policy for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  # Bronze layer: Keep in Standard, enable versioning
  rule {
    id     = "bronze-layer-versioning"
    status = "Enabled"

    filter {
      prefix = "bronze/"
    }

    noncurrent_version_expiration {
      noncurrent_days = 90 # Delete old versions after 90 days
    }
  }

  # Silver layer: Transition to Glacier after 1 year (optional)
  dynamic "rule" {
    for_each = var.s3_lifecycle_glacier_days > 0 ? [1] : []

    content {
      id     = "silver-layer-glacier"
      status = "Enabled"

      filter {
        prefix = "silver/"
      }

      transition {
        days          = var.s3_lifecycle_glacier_days
        storage_class = "GLACIER"
      }
    }
  }

  # Abort incomplete multipart uploads after 7 days (saves costs)
  rule {
    id     = "abort-incomplete-multipart"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  # Delete temporary files after 1 day
  rule {
    id     = "cleanup-temp-files"
    status = "Enabled"

    filter {
      prefix = "tmp/"
    }

    expiration {
      days = 1
    }
  }
}

# CORS configuration (if needed for future web UI)
resource "aws_s3_bucket_cors_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"] # Restrict this in production
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# Intelligent-Tiering for gold layer (future optimization)
resource "aws_s3_bucket_intelligent_tiering_configuration" "gold_layer" {
  bucket = aws_s3_bucket.data_lake.id
  name   = "gold-layer-optimization"

  status = "Enabled"

  filter {
    prefix = "gold/"
  }

  tiering {
    access_tier = "ARCHIVE_ACCESS"
    days        = 90
  }

  tiering {
    access_tier = "DEEP_ARCHIVE_ACCESS"
    days        = 180
  }
}

# Bucket notification for future event-driven processing
resource "aws_s3_bucket_notification" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  # Placeholder for future Lambda triggers
  # lambda_function {
  #   lambda_function_arn = aws_lambda_function.index_to_silver.arn
  #   events              = ["s3:ObjectCreated:*"]
  #   filter_prefix       = "bronze/house/financial/"
  #   filter_suffix       = ".xml"
  # }
}

# Output bucket details
output "s3_bucket_id" {
  description = "S3 data lake bucket name"
  value       = aws_s3_bucket.data_lake.id
}

output "s3_bucket_arn" {
  description = "S3 data lake bucket ARN"
  value       = aws_s3_bucket.data_lake.arn
}

output "s3_bucket_domain_name" {
  description = "S3 bucket domain name"
  value       = aws_s3_bucket.data_lake.bucket_domain_name
}
