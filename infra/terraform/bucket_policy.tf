resource "aws_s3_bucket_policy" "public_read_access" {
  bucket = aws_s3_bucket.data_lake.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource = [
          "${aws_s3_bucket.data_lake.arn}/website/*",
          "${aws_s3_bucket.data_lake.arn}/website/api/*",
          "${aws_s3_bucket.data_lake.arn}/docs/*",
          "${aws_s3_bucket.data_lake.arn}/favicon.ico",
          "${aws_s3_bucket.data_lake.arn}/robots.txt",
          "${aws_s3_bucket.data_lake.arn}/manifest.json",
          "${aws_s3_bucket.data_lake.arn}/bronze/*",
          "${aws_s3_bucket.data_lake.arn}/silver/*"
        ]
      },
      {
        Sid       = "PublicListSpecificPrefixes"
        Effect    = "Allow"
        Principal = "*"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.data_lake.arn
        Condition = {
          StringLike = {
            "s3:prefix" = [
              "website/*",
              "website/api/*",
              "docs/*",
              "favicon.ico",
              "robots.txt",
              "manifest.json",
              "bronze/*",
              "silver/*"
            ]
          }
        }
      }
    ]
  })
}
