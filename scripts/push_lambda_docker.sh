#!/bin/bash
# Build and push Lambda Docker image to ECR
# Usage: ./scripts/push_lambda_docker.sh <lambda_name> <ecr_repo_name>

set -e

LAMBDA_NAME=${1:-"house_fd_extract_structured_code"}
ECR_REPO_NAME=${2:-"congress-disclosures-extract-structured-code"}
AWS_REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAMBDA_DIR="$REPO_ROOT/ingestion/lambdas/${LAMBDA_NAME}"

echo "============================================"
echo "Building and Pushing Lambda Image"
echo "Lambda: $LAMBDA_NAME"
echo "ECR Repo: $ECR_REPO_NAME"
echo "ECR URI: $ECR_URI"
echo "============================================"

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Build Image
echo "Building Docker image..."
cd "$REPO_ROOT"
docker build -f "$LAMBDA_DIR/Dockerfile" -t "$ECR_REPO_NAME:latest" .

# Tag Image
echo "Tagging image..."
docker tag "$ECR_REPO_NAME:latest" "$ECR_URI:latest"

# Push Image
echo "Pushing image to ECR..."
docker push "$ECR_URI:latest"

echo "============================================"
echo "✅ Image pushed successfully!"
echo "Image URI: $ECR_URI:latest"
echo "============================================"
