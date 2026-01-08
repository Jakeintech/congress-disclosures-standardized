#!/bin/bash
#
# Test the full Congressional disclosures pipeline
#
# This script tests all Lambda functions in sequence:
# 1. Ingest ZIP (uploads 2025FD files to bronze)
# 2. Index to Silver (parses XML index)
# 3. Extract Document (extracts PDF content)
#

set -e  # Exit on error

# Configuration
YEAR=2025
S3_BUCKET="congress-disclosures-standardized"
LAMBDA_PREFIX="congress-disclosures-development"
DOWNLOADS_DIR="/Users/jake/Downloads/2025FD"

echo "================================"
echo "Congressional Disclosures Pipeline Test"
echo "Year: $YEAR"
echo "Bucket: $S3_BUCKET"
echo "================================"
echo ""

# Step 1: Upload 2025FD files to bronze layer (manual upload, not via Lambda)
echo "[1/4] Uploading 2025FD files to S3..."
aws s3 cp "$DOWNLOADS_DIR/2025FD.xml" "s3://$S3_BUCKET/bronze/house/financial/year=$YEAR/index/$YEAR"FD.xml
aws s3 cp "$DOWNLOADS_DIR/2025FD.txt" "s3://$S3_BUCKET/bronze/house/financial/year=$YEAR/index/$YEAR"FD.txt
echo "✓ Files uploaded to bronze layer"
echo ""

# Step 2: Invoke index-to-silver Lambda
echo "[2/4] Invoking index-to-silver Lambda..."
RESPONSE=$(aws lambda invoke \
  --function-name "${LAMBDA_PREFIX}-index-to-silver" \
  --payload '{"year": 2025}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/index-to-silver-response.json 2>&1)

if [ $? -eq 0 ]; then
  echo "✓ index-to-silver completed"
  cat /tmp/index-to-silver-response.json | python3 -m json.tool
  echo ""
else
  echo "✗ index-to-silver failed"
  echo "$RESPONSE"
  exit 1
fi

# Step 3: Check silver layer output
echo "[3/4] Checking silver layer Parquet files..."
aws s3 ls "s3://$S3_BUCKET/silver/house/financial/filings/year=$YEAR/" --recursive --human-readable
aws s3 ls "s3://$S3_BUCKET/silver/house/financial/documents/year=$YEAR/" --recursive --human-readable
echo ""

# Step 4: Test manifest generation (if available)
echo "[4/4] Checking for manifest.json..."
if aws s3 ls "s3://$S3_BUCKET/manifest.json" >/dev/null 2>&1; then
  echo "✓ manifest.json exists"
  aws s3 cp "s3://$S3_BUCKET/manifest.json" /tmp/manifest.json
  echo "Manifest stats:"
  cat /tmp/manifest.json | python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Total filings: {data['stats']['total_filings']}\"); print(f\"Latest year: {data['stats']['latest_year']}\"); print(f\"Last updated: {data['stats']['last_updated']}\")"
else
  echo "⚠ manifest.json not found (will be generated after adding manifest generator)"
fi
echo ""

echo "================================"
echo "Pipeline test complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Add manifest generation to Lambda"
echo "2. Deploy website to S3"
echo "3. Add cost protection"
