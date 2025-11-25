#!/bin/bash
set -e  # Exit on error

###############################################################################
# End-to-End Pipeline Orchestration
#
# This script runs the complete pipeline from extraction to website updates:
# 1. Queue pending PDFs for extraction
# 2. Wait for extractions to complete
# 3. Rebuild gold layer tables
# 4. Regenerate website manifests
# 5. Upload to S3
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "================================================================================"
echo "Congress Disclosures - Full Pipeline Run"
echo "================================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Queue pending extractions (optional - can be skipped if already running)
echo -e "${YELLOW}Step 1: Queue pending PDFs for extraction${NC}"
if command -v python3 &> /dev/null; then
    if [ -f "scripts/queue_pending_extractions.py" ]; then
        echo "  Queuing up to 100 pending documents..."
        python3 scripts/queue_pending_extractions.py --limit 100 || echo "  Note: queue_pending_extractions.py failed or no documents to queue"
    else
        echo "  Skipping: queue_pending_extractions.py not found"
    fi
else
    echo "  Skipping: python3 not found"
fi
echo ""

# Step 2: Wait for extractions (optional - for automated runs)
# Uncomment if you want to wait for extraction Lambda to finish
# echo -e "${YELLOW}Step 2: Waiting for extractions to complete${NC}"
# echo "  Sleeping 5 minutes to allow extraction Lambda to process..."
# sleep 300
# echo ""

# Step 3: Rebuild gold layer dimensions (if needed)
echo -e "${YELLOW}Step 3: Rebuild gold layer dimensions${NC}"
echo "  Note: Dimensions are typically static, skipping rebuild unless needed"
echo ""

# Step 4: Rebuild fact_filings with latest extraction data
echo -e "${YELLOW}Step 4: Rebuild fact_filings${NC}"
if python3 scripts/build_fact_filings.py; then
    echo -e "  ${GREEN}✅ fact_filings rebuilt${NC}"
else
    echo -e "  ${RED}❌ fact_filings rebuild failed${NC}"
    exit 1
fi
echo ""

# Step 5: Recompute document quality aggregates
echo -e "${YELLOW}Step 5: Recompute document quality aggregates${NC}"
if python3 scripts/compute_agg_document_quality.py; then
    echo -e "  ${GREEN}✅ agg_document_quality computed${NC}"
else
    echo -e "  ${RED}❌ agg_document_quality computation failed${NC}"
    exit 1
fi
echo ""

# Step 6: Regenerate website manifests
echo -e "${YELLOW}Step 6: Regenerate website manifests${NC}"
if python3 scripts/generate_document_quality_manifest.py; then
    echo -e "  ${GREEN}✅ document_quality.json manifest generated${NC}"
else
    echo -e "  ${RED}❌ Manifest generation failed${NC}"
    exit 1
fi
echo ""

# Step 7: Upload website files to S3
echo -e "${YELLOW}Step 7: Upload website files to S3${NC}"
if aws s3 cp website/index.html s3://congress-disclosures-standardized/website/index.html --content-type text/html && \
   aws s3 cp website/app.js s3://congress-disclosures-standardized/website/app.js --content-type application/javascript && \
   aws s3 cp website/document_quality.js s3://congress-disclosures-standardized/website/document_quality.js --content-type application/javascript && \
   aws s3 cp website/style.css s3://congress-disclosures-standardized/website/style.css --content-type text/css; then
    echo -e "  ${GREEN}✅ Website files uploaded${NC}"
else
    echo -e "  ${RED}❌ Website upload failed${NC}"
    exit 1
fi
echo ""

# Summary
echo "================================================================================"
echo -e "${GREEN}✅ Pipeline run complete!${NC}"
echo "================================================================================"
echo ""
echo "Website: http://congress-disclosures-standardized.s3-website-us-east-1.amazonaws.com/website/index.html"
echo ""
echo "Next steps:"
echo "  - View Document Quality tab to see flagged members"
echo "  - Check gold layer tables in S3 for analytics data"
echo "  - Run this script regularly to keep data fresh"
echo ""
