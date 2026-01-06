#!/bin/bash
# Build DuckDB Lambda Layer
# This creates a Lambda layer with DuckDB, PyArrow, and dependencies

set -e

LAYER_NAME="congress-duckdb"
PYTHON_VERSION="python3.11"

echo "Building DuckDB Lambda layer..."

# Clean previous builds
rm -rf python
rm -f ${LAYER_NAME}.zip

# Create python directory (Lambda layer structure)
mkdir -p python

# Install dependencies (use python3.11 -m pip to ensure correct version)
python3.11 -m pip install -r requirements.txt -t python/ --platform manylinux2014_x86_64 --python-version 3.11 --only-binary=:all:

# Remove unnecessary files to reduce size
echo "Cleaning up unnecessary files..."
find python -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find python -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find python -name "*.pyc" -delete
find python -name "*.pyo" -delete
find python -type f -name "*.so" -exec strip {} \; 2>/dev/null || true

# Create ZIP file
echo "Creating ZIP archive..."
zip -r ${LAYER_NAME}.zip python/ -q

# Get size
SIZE=$(du -h ${LAYER_NAME}.zip | cut -f1)
echo "Layer created: ${LAYER_NAME}.zip (${SIZE})"

# Publish to AWS Lambda (optional, requires AWS CLI)
if [ "$1" == "--publish" ]; then
    echo "Publishing layer to AWS Lambda..."
    aws lambda publish-layer-version \
        --layer-name ${LAYER_NAME} \
        --description "DuckDB 1.1.3 + PyArrow 18.1.0 for S3-native analytics (2025-12-25)" \
        --zip-file fileb://${LAYER_NAME}.zip \
        --compatible-runtimes python3.11 \
        --compatible-architectures x86_64 \
        --query 'LayerVersionArn' \
        --output text
    echo "Layer published successfully!"
else
    echo "Run with --publish flag to publish to AWS Lambda"
fi

echo "Done!"
