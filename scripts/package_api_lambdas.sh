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
python3 scripts/generate_version.py --output build/version.json --pretty || echo '{"version": "unknown"}' > build/version.json
echo "✓ Version generated"

echo "Finding API functions..."
if [ -n "$1" ]; then
    FUNCTIONS=("$1")
    echo "Using provided function: $1"
else
    FUNCTIONS=($(find "$API_LAMBDA_DIR" -maxdepth 2 -name "handler.py" -exec dirname {} \; | xargs -n 1 basename | sort))
    echo "Found ${#FUNCTIONS[@]} API functions to package."
fi

for func in "${FUNCTIONS[@]}"; do
    echo "Processing $func..."
    
    PKG_DIR="$BUILD_DIR/$func"
    rm -rf "$PKG_DIR"
    mkdir -p "$PKG_DIR"
    
    # Note: Dependencies like pydantic are now provided by Lambda Layer
    # Configure layer ARN via TF_VAR_pydantic_layer_arn environment variable
    
    # Copy handler
    cp "$API_LAMBDA_DIR/$func/handler.py" "$PKG_DIR/"
    
    # Copy shared library (api/lib)
    mkdir -p "$PKG_DIR/api"
    cp -r api/lib "$PKG_DIR/api/"
    touch "$PKG_DIR/api/__init__.py"

    # Include version.json
    cp build/version.json "$PKG_DIR/version.json"

    # Zip it up
    (cd "$PKG_DIR" && zip -r "../$func.zip" . > /dev/null)
    
    # Upload to S3
    aws s3 cp "$BUILD_DIR/$func.zip" "s3://$S3_BUCKET/$S3_PREFIX/$func.zip" --quiet
done

echo "Done! All ${#FUNCTIONS[@]} API Lambdas packaged and uploaded."
