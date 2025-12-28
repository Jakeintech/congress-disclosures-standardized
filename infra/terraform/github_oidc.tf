resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com",
  ]

  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1", # GitHub's OIDC thumbprint
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd"  # Backup thumbprint
  ]
}

resource "aws_iam_role" "github_actions" {
  name = "${local.name_prefix}-github-actions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Condition = {
          StringLike = {
            "token.actions.githubusercontent.com:sub" : "repo:Jakeintech/congress-disclosures-standardized:*"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "github_actions_policy" {
  name = "${local.name_prefix}-github-actions-policy"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          aws_s3_bucket.data_lake.arn,
          "${aws_s3_bucket.data_lake.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "arn:aws:lambda:${local.region}:${local.account_id}:function:${local.name_prefix}-*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:GetQueueUrl",
          "sqs:GetQueueAttributes",
          "sqs:PurgeQueue"
        ]
        Resource = "arn:aws:sqs:${local.region}:${local.account_id}:${local.name_prefix}-*"
      }
    ]
  })
}

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
  description = "ARN of the IAM role for GitHub Actions"
}
