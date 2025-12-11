#!/bin/bash
# Week 2 Deployment Script - DuckDB Gold Transformations
# Run this from the project root directory

set -e  # Exit on error

echo "========================================="
echo "Week 2 Deployment: DuckDB Gold Layer"
echo "========================================="
echo ""

# Check we're in the right directory
if [ ! -f "Makefile" ]; then
    echo "❌ Error: Must run from project root directory"
    exit 1
fi

echo "✓ Running from project root"
echo ""

# Step 1: Build DuckDB Lambda Layer
echo "Step 1/4: Building DuckDB Lambda layer..."
echo "-------------------------------------------"
cd layers/duckdb
if [ ! -f "build.sh" ]; then
    echo "❌ Error: build.sh not found"
    exit 1
fi

chmod +x build.sh
./build.sh

if [ ! -f "congress-duckdb.zip" ]; then
    echo "❌ Error: Layer build failed"
    exit 1
fi

echo "✓ DuckDB layer built successfully"
echo "  Size: $(du -h congress-duckdb.zip | cut -f1)"
cd ../..
echo ""

# Step 2: Package Gold Transformation Lambda Functions
echo "Step 2/4: Packaging Gold transformation functions..."
echo "-------------------------------------------"
mkdir -p build
cd api/lambdas/gold_transformations

if [ ! -f "build_fact_transactions_duckdb.py" ]; then
    echo "❌ Error: Gold transformation scripts not found"
    exit 1
fi

zip -r ../../../build/gold_transformations.zip *.py > /dev/null 2>&1

cd ../../..
if [ ! -f "build/gold_transformations.zip" ]; then
    echo "❌ Error: Packaging failed"
    exit 1
fi

echo "✓ Lambda functions packaged successfully"
echo "  Size: $(du -h build/gold_transformations.zip | cut -f1)"
echo ""

# Step 3: Terraform Validate
echo "Step 3/4: Validating Terraform configuration..."
echo "-------------------------------------------"
cd infra/terraform
terraform validate

if [ $? -ne 0 ]; then
    echo "❌ Error: Terraform validation failed"
    exit 1
fi

echo "✓ Terraform configuration valid"
echo ""

# Step 4: Terraform Plan
echo "Step 4/4: Showing Terraform plan..."
echo "-------------------------------------------"
terraform plan \
    -target=aws_dynamodb_table.pipeline_watermarks \
    -target=aws_dynamodb_table.pipeline_execution_history \
    -target=aws_sns_topic.pipeline_alerts \
    -target=aws_sns_topic.data_quality_alerts \
    -target=aws_lambda_layer_version.duckdb \
    -target=aws_lambda_function.build_fact_transactions_duckdb \
    -target=aws_lambda_function.build_dim_members_duckdb \
    -target=aws_lambda_function.compute_trending_stocks_duckdb \
    -out=week2.tfplan

if [ $? -ne 0 ]; then
    echo "❌ Error: Terraform plan failed"
    exit 1
fi

echo ""
echo "========================================="
echo "✓ Pre-deployment checks complete!"
echo "========================================="
echo ""
echo "Review the plan above. To deploy, run:"
echo "  cd infra/terraform"
echo "  terraform apply week2.tfplan"
echo ""
echo "Or to deploy immediately:"
echo "  cd infra/terraform && terraform apply week2.tfplan"
echo ""
echo "After deployment, test with:"
echo "  make -f Makefile.week2 invoke-build-fact-transactions"
echo ""
