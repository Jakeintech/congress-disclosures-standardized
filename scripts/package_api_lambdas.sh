#!/bin/bash
set -e

# Directory setup
API_LAMBDA_DIR="api/lambdas"
BUILD_DIR="build/api"
S3_BUCKET="congress-disclosures-standardized"
S3_PREFIX="lambda-deployments/api"

# Ensure build directory exists
mkdir -p "$BUILD_DIR"

# Generate version.json with build metadata
echo "Generating version.json..."
python3 scripts/generate_version.py --output build/version.json --pretty
echo "✓ Version generated: $(cat build/version.json | grep '\"version\"' | cut -d':' -f2 | tr -d ' ",')"

# List of API functions (matching api_lambdas.tf)
FUNCTIONS=(
    "get_members"
    "get_member"
    "get_member_trades"
    "get_member_portfolio"
    "get_trades"
    "get_stock"
    "get_stock_activity"
    "get_stocks"
    "get_top_traders"
    "get_trending_stocks"
    "get_sector_activity"
    "get_compliance"
    "get_trading_timeline"
    "get_summary"
    "search"
    "get_filings"
    "get_filing"
    "get_aws_costs"
    "list_s3_objects"
)

echo "Packaging API Lambdas..."

for func in "${FUNCTIONS[@]}"; do
    echo "Processing $func..."
    
    # Create temporary package directory
    PKG_DIR="$BUILD_DIR/$func"
    rm -rf "$PKG_DIR"
    mkdir -p "$PKG_DIR"
    
    # Copy handler
    if [ -f "$API_LAMBDA_DIR/$func/handler.py" ]; then
        cp "$API_LAMBDA_DIR/$func/handler.py" "$PKG_DIR/"
    else
        echo "Warning: Handler not found for $func"
        continue
    fi
    
    # Copy shared library (api/lib)
    # The Lambda expects 'from api.lib import ...' so we need to put 'lib' inside an 'api' folder
    mkdir -p "$PKG_DIR/api"
    cp -r api/lib "$PKG_DIR/api/"
    # Create __init__.py if missing to make it a package
    touch "$PKG_DIR/api/__init__.py"

    # Include version.json in package root (for version tracking)
    cp build/version.json "$PKG_DIR/version.json"

    # Zip it up
    cd "$PKG_DIR"
    zip -r "../$func.zip" . > /dev/null
    cd - > /dev/null
    
    # Upload to S3
    echo "Uploading $func.zip to s3://$S3_BUCKET/$S3_PREFIX/$func.zip"
    aws s3 cp "$BUILD_DIR/$func.zip" "s3://$S3_BUCKET/$S3_PREFIX/$func.zip"
done

echo "All API Lambdas packaged and uploaded!"
