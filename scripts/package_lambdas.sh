#!/bin/bash
#
# Package Lambda functions with dependencies
#
# This script:
# 1. Installs Python dependencies into a package/ directory
# 2. Copies Lambda handler and lib/ code
# 3. Creates function.zip
# 4. Uploads to S3 for Terraform deployment
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAMBDAS_DIR="$PROJECT_ROOT/ingestion/lambdas"
LIB_DIR="$PROJECT_ROOT/ingestion/lib"
S3_BUCKET="${S3_BUCKET:-congress-disclosures-standardized}"
S3_PREFIX="lambda-deployments"

echo "================================"
echo "Lambda Packaging Script"
echo "================================"
echo "Project root: $PROJECT_ROOT"
echo "S3 Bucket: $S3_BUCKET"
echo ""

# Check prerequisites
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ python3 not found${NC}"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo -e "${RED}✗ aws CLI not found${NC}"
    exit 1
fi

# Function to package a single Lambda
package_lambda() {
    local lambda_name=$1
    local lambda_dir="$LAMBDAS_DIR/$lambda_name"

    echo -e "${YELLOW}[Packaging]${NC} $lambda_name"

    if [ ! -d "$lambda_dir" ]; then
        echo -e "${RED}✗ Lambda directory not found: $lambda_dir${NC}"
        return 1
    fi

    cd "$lambda_dir"

    # Clean previous build
    rm -rf package/ function.zip

    # Install dependencies if requirements.txt exists
    if [ -f "requirements.txt" ]; then
        echo "  Installing dependencies for Linux x86_64..."
        mkdir -p package

        # Install with platform targeting for Lambda (Linux x86_64, Python 3.11)
        pip3 install -r requirements.txt \
            -t package/ \
            --platform manylinux2014_x86_64 \
            --only-binary=:all: \
            --python-version 3.11 \
            --implementation cp \
            --quiet \
            --upgrade \
            2>&1 | grep -v "ERROR: pip's dependency resolver"

        # Clean up unnecessary files to reduce package size
        echo "  Cleaning up package..."
        find package/ -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
        find package/ -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
        find package/ -name "*.pyc" -delete
        find package/ -name "*.pyo" -delete
        find package/ -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

        cd package
    fi

    # Copy shared lib/ directory
    echo "  Copying shared lib..."
    mkdir -p lib
    cp -r "$LIB_DIR"/* lib/

    # Copy handler
    echo "  Copying handler..."
    cp "$lambda_dir/handler.py" .

    # Copy schemas if they exist
    if [ -d "$lambda_dir/schemas" ]; then
        echo "  Copying schemas..."
        cp -r "$lambda_dir/schemas" .
    fi

    # Create ZIP
    echo "  Creating function.zip..."
    zip -r -q ../function.zip .

    cd "$lambda_dir"

    # Get ZIP size
    local zip_size=$(du -h function.zip | cut -f1)
    echo -e "  ${GREEN}✓${NC} Package created: $zip_size"

    # Upload to S3
    echo "  Uploading to S3..."
    aws s3 cp function.zip "s3://$S3_BUCKET/$S3_PREFIX/$lambda_name/function.zip" --quiet
    echo -e "  ${GREEN}✓${NC} Uploaded to s3://$S3_BUCKET/$S3_PREFIX/$lambda_name/function.zip"

    # Clean up
    rm -rf package/

    echo ""
}

# Package all Lambda functions
echo "Packaging Lambda functions..."
echo ""

package_lambda "house_fd_ingest_zip"
package_lambda "house_fd_index_to_silver"
package_lambda "house_fd_extract_document"
package_lambda "house_fd_extract_structured"
package_lambda "gold_seed"
package_lambda "gold_seed_members"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}All Lambda functions packaged!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Next steps:"
echo "1. Update Lambda functions:"
echo "   cd infra/terraform && terraform apply -target=aws_lambda_function.ingest_zip -target=aws_lambda_function.index_to_silver -target=aws_lambda_function.extract_document"
echo "2. Or force redeploy:"
echo "   aws lambda update-function-code --function-name congress-disclosures-development-index-to-silver --s3-bucket $S3_BUCKET --s3-key $S3_PREFIX/house_fd_index_to_silver/function.zip"
