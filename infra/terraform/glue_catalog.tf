# AWS Glue Data Catalog for Data Lake Metadata Management
#
# Glue Catalog provides:
# - Centralized metadata registry for all tables
# - Schema discovery and versioning
# - Integration with DuckDB, Athena, and future Iceberg tables
# - Free tier: 1M objects, $1/100K after

# Main data lake database
resource "aws_glue_catalog_database" "politics_data_platform" {
  name        = "politics_data_platform"
  description = "Congressional trading, legislative, and lobbying data"

  # Store database metadata in S3 for portability
  location_uri = "s3://${var.s3_bucket_name}/${var.glue_catalog_prefix}/databases/politics_data_platform/"

  # Iceberg support (for future Phase 2 migration)
  parameters = {
    "iceberg.enabled" = "true"
    "table_type"      = "ICEBERG"
  }
}

# Glue Crawler for automatic schema discovery
resource "aws_glue_crawler" "gold_layer_crawler" {
  name          = "${var.project_name}-gold-layer-crawler"
  role          = aws_iam_role.glue_crawler.arn
  database_name = aws_glue_catalog_database.politics_data_platform.name

  # Crawl schedule: Daily at 6 AM UTC (after nightly aggregations)
  schedule = var.glue_crawler_schedule

  # Catalog all Gold layer tables
  s3_target {
    path = "s3://${var.s3_bucket_name}/data/gold/dimensions/"
  }

  s3_target {
    path = "s3://${var.s3_bucket_name}/data/gold/facts/"
  }

  s3_target {
    path = "s3://${var.s3_bucket_name}/data/gold/aggregates/"
  }

  # Schema change handling
  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE" # Auto-update schemas
    delete_behavior = "LOG"                # Log deletions, don't remove from catalog
  }

  # Recrawl policy (only crawl new/changed files)
  recrawl_policy {
    recrawl_behavior = "CRAWL_NEW_FOLDERS_ONLY"
  }

  # Crawler configuration
  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Partitions = {
        AddOrUpdateBehavior = "InheritFromTable" # Use Hive partitioning
      }
    }
    Grouping = {
      TableGroupingPolicy = "CombineCompatibleSchemas" # Merge compatible partitions
    }
  })

  tags = {
    Name        = "${var.project_name}-gold-layer-crawler"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "schema-discovery"
  }
}

# Crawler for Silver layer (optional, less frequent)
resource "aws_glue_crawler" "silver_layer_crawler" {
  name          = "${var.project_name}-silver-layer-crawler"
  role          = aws_iam_role.glue_crawler.arn
  database_name = aws_glue_catalog_database.politics_data_platform.name

  # Run weekly (Silver schema changes less frequently)
  schedule = var.glue_silver_crawler_schedule

  # Silver layer targets
  s3_target {
    path = "s3://${var.s3_bucket_name}/data/silver/house_fd/"
  }

  s3_target {
    path = "s3://${var.s3_bucket_name}/data/silver/congress_api/"
  }

  s3_target {
    path = "s3://${var.s3_bucket_name}/data/silver/lobbying/"
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }

  recrawl_policy {
    recrawl_behavior = "CRAWL_NEW_FOLDERS_ONLY"
  }

  tags = {
    Name        = "${var.project_name}-silver-layer-crawler"
    Project     = var.project_name
    Environment = var.environment
    Purpose     = "schema-discovery"
  }
}

# IAM Role for Glue Crawler
resource "aws_iam_role" "glue_crawler" {
  name = "${var.project_name}-glue-crawler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-glue-crawler-role"
    Project     = var.project_name
    Environment = var.environment
  }
}

# Attach AWS managed Glue service policy
resource "aws_iam_role_policy_attachment" "glue_service_policy" {
  role       = aws_iam_role.glue_crawler.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Custom policy for S3 access
resource "aws_iam_role_policy" "glue_s3_access" {
  name = "${var.project_name}-glue-s3-access"
  role = aws_iam_role.glue_crawler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.data_lake.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.data_lake.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws-glue/*"
        ]
      }
    ]
  })
}

# CloudWatch Log Group for Crawler logs
resource "aws_cloudwatch_log_group" "glue_crawler" {
  name              = "/aws-glue/crawlers/${var.project_name}"
  retention_in_days = 7 # Keep logs for 7 days (cost optimization)

  tags = {
    Name        = "${var.project_name}-glue-crawler-logs"
    Project     = var.project_name
    Environment = var.environment
  }
}

# Data source for AWS account ID


# Outputs
output "glue_database_name" {
  description = "Name of Glue Catalog database"
  value       = aws_glue_catalog_database.politics_data_platform.name
}

output "glue_database_arn" {
  description = "ARN of Glue Catalog database"
  value       = aws_glue_catalog_database.politics_data_platform.arn
}

output "glue_crawler_name" {
  description = "Name of Glue Crawler for Gold layer"
  value       = aws_glue_crawler.gold_layer_crawler.name
}

output "glue_crawler_arn" {
  description = "ARN of Glue Crawler"
  value       = aws_glue_crawler.gold_layer_crawler.arn
}

output "glue_silver_crawler_name" {
  description = "Name of Glue Crawler for Silver layer"
  value       = aws_glue_crawler.silver_layer_crawler.name
}
