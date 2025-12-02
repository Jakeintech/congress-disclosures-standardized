#!/bin/bash
# Update all API Lambda function codes

LAMBDAS=(
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
)

for lambda in "${LAMBDAS[@]}"; do
    echo "Updating $lambda..."
    aws lambda update-function-code \
        --function-name "congress-disclosures-development-api-$lambda" \
        --s3-bucket "congress-disclosures-standardized" \
        --s3-key "lambda-deployments/api/$lambda.zip" \
        --query 'LastUpdateStatus' \
        --output text
done

echo "✅ All Lambda functions updated"
