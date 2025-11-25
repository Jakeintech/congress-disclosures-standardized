# API Key Setup Guide

This guide explains how to configure external API keys for the gold layer enrichment pipeline.

## Overview

The gold layer uses external APIs to enrich congressional financial disclosure data with additional context:

- **Congress.gov API**: Member bioguide IDs, party affiliation, committee assignments
- **Yahoo Finance**: Stock ticker validation, sector/industry classification, market cap
- **Coinbase API**: Cryptocurrency asset classification

## Quick Start

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Get your API keys** (see sections below)

3. **Edit `.env` and add your keys:**
   ```bash
   nano .env  # or use your preferred editor
   ```

4. **Verify configuration:**
   ```bash
   python3 scripts/verify_api_keys.py
   ```

## API Key Acquisition

### 1. Congress.gov API (Required)

The Congress.gov API provides authoritative data about members of Congress.

**Get Your Key:**
1. Visit: https://api.congress.gov/sign-up/
2. Fill out the form (requires email verification)
3. You'll receive your API key via email within minutes
4. Free tier: **5,000 requests per hour** (more than sufficient)

**Add to `.env`:**
```bash
CONGRESS_API_KEY=cCaINBJqvjZvUGVz6mY7Yk9MvS44nTRAOYHmdK0i
```

**Test it:**
```bash
curl "https://api.congress.gov/v3/member?api_key=YOUR_KEY&limit=1"
```

### 2. Yahoo Finance (Optional, No Key Needed)

We use the `yfinance` Python library, which doesn't require API keys.

**No setup required** - it works out of the box!

**What it provides:**
- Ticker symbol validation
- Company sector & industry (GICS classification)
- Market capitalization
- Current stock price

**Fallback:** If Yahoo Finance is down, we have regex patterns to extract tickers from asset names.

### 3. Coinbase API (Optional)

Only needed if you want to classify cryptocurrency assets (Bitcoin, Ethereum, etc.).

**Get Your Keys:**
1. Visit: https://portal.cdp.coinbase.com/access/api
2. Sign up/log in with your Coinbase account
3. Create an API key with "View" permissions
4. Copy both the API Key and API Secret

**Add to `.env`:**
```bash
COINBASE_API_KEY=organizations/xxx/apiKeys/xxx
COINBASE_API_SECRET=-----BEGIN EC PRIVATE KEY-----
MHcCAQEEI...
-----END EC PRIVATE KEY-----
```

**Enable crypto enrichment:**
```bash
ENABLE_CRYPTO_API_ENRICHMENT=true
```

## Alternative Stock APIs (Optional)

If you prefer not to use Yahoo Finance, you can use paid APIs with free tiers:

### IEX Cloud
- **Free tier:** 500,000 API calls per month
- **Sign up:** https://iexcloud.io/
- **Add to `.env`:**
  ```bash
  IEX_CLOUD_API_KEY=pk_xxx
  ```

### AlphaVantage
- **Free tier:** 500 API calls per day
- **Sign up:** https://www.alphavantage.co/
- **Add to `.env`:**
  ```bash
  ALPHA_VANTAGE_API_KEY=xxx
  ```

## Configuration Options

### Enable/Disable Enrichment Sources

Control which APIs are used:

```bash
# Congress.gov (highly recommended)
ENABLE_CONGRESS_API_ENRICHMENT=true

# Stock APIs (recommended for better asset classification)
ENABLE_STOCK_API_ENRICHMENT=true

# Crypto APIs (optional, only if you need crypto asset details)
ENABLE_CRYPTO_API_ENRICHMENT=false
```

### Caching Configuration

To avoid hitting rate limits and reduce API costs, we cache enrichment results:

```bash
# Cache TTL (time to live) in hours
ENRICHMENT_CACHE_TTL_HOURS=168  # 1 week default
```

**How it works:**
- First lookup: API call + cache write
- Subsequent lookups: Cache read (no API call)
- Cache expires after TTL
- Cache stored in `gold/cache/` S3 prefix

### Data Quality Thresholds

Configure thresholds for document quality tracking:

```bash
# Minimum confidence score for automated processing
MIN_CONFIDENCE_SCORE=0.85

# Flag members with >30% image-based PDFs
IMAGE_PDF_WARNING_THRESHOLD=0.30

# Document quality score weights (must sum to 1.0)
QUALITY_WEIGHT_CONFIDENCE=0.4     # 40% weight on extraction confidence
QUALITY_WEIGHT_FORMAT=0.3         # 30% weight on PDF format (text vs image)
QUALITY_WEIGHT_COMPLETENESS=0.3   # 30% weight on data completeness
```

## AWS Deployment

### Local Development

For local testing, use your AWS CLI profile:

```bash
AWS_PROFILE=default
AWS_REGION=us-east-1
```

### Lambda Deployment

When deploying to Lambda, API keys are stored in **AWS Systems Manager Parameter Store** (not in environment variables):

```bash
# Store securely (encrypted)
aws ssm put-parameter \
  --name "/congress-disclosures/prod/congress-api-key" \
  --value "YOUR_KEY" \
  --type "SecureString" \
  --description "Congress.gov API key"

aws ssm put-parameter \
  --name "/congress-disclosures/prod/coinbase-api-key" \
  --value "YOUR_KEY" \
  --type "SecureString"

aws ssm put-parameter \
  --name "/congress-disclosures/prod/coinbase-api-secret" \
  --value "YOUR_SECRET" \
  --type "SecureString"
```

**Lambda functions automatically fetch from SSM** - no code changes needed!

## Security Best Practices

### DO:
- ✅ Use `.env` for local development
- ✅ Use AWS SSM Parameter Store for Lambda
- ✅ Use IAM roles with least privilege
- ✅ Rotate API keys periodically
- ✅ Monitor API usage in CloudWatch

### DON'T:
- ❌ Commit `.env` to git (already in `.gitignore`)
- ❌ Hardcode API keys in source code
- ❌ Share API keys in Slack/email
- ❌ Use production keys in development
- ❌ Grant excessive IAM permissions

## Troubleshooting

### "Congress API key invalid"

**Symptoms:** HTTP 403 errors from api.congress.gov

**Solutions:**
1. Verify your key is correct (copy-paste carefully)
2. Check if key is activated (check signup email)
3. Ensure you're not exceeding rate limit (5,000 req/hr)
4. Test key with curl:
   ```bash
   curl "https://api.congress.gov/v3/member?api_key=YOUR_KEY&limit=1"
   ```

### "Yahoo Finance not returning data"

**Symptoms:** Tickers not found, empty sector data

**Solutions:**
1. Check internet connectivity
2. Verify ticker symbol is correct (GOOGL not GOOGLE)
3. Try alternative stock API (IEX Cloud, AlphaVantage)
4. Check yfinance library version:
   ```bash
   pip show yfinance
   pip install --upgrade yfinance
   ```

### "Rate limit exceeded"

**Symptoms:** HTTP 429 errors

**Solutions:**
1. Increase cache TTL to reduce API calls
2. Use batch processing instead of real-time
3. Implement exponential backoff retry logic
4. Upgrade to paid API tier (if needed)

## Verification Script

Run this script to test all API connections:

```bash
python3 scripts/verify_api_keys.py
```

**Expected output:**
```
✅ Congress.gov API: OK (key valid, 4,998 requests remaining)
✅ Yahoo Finance: OK (no key required)
⚠️  Coinbase API: Disabled (ENABLE_CRYPTO_API_ENRICHMENT=false)
✅ Environment configuration: OK
✅ AWS SSM Parameter Store: OK (3 parameters found)

All systems operational!
```

## Cost Estimates

### Free Tier Usage (Expected)

| API | Monthly Calls | Free Limit | Cost |
|-----|--------------|------------|------|
| Congress.gov | ~500 | 5,000/hour | $0 |
| Yahoo Finance | ~2,000 | Unlimited | $0 |
| Coinbase | ~50 | N/A | $0 |
| **Total** | | | **$0** |

### If Exceeding Free Tier

- Congress.gov: No paid tier (you must stay within 5,000 req/hr)
- IEX Cloud: $9/month for 5M calls
- AlphaVantage: $50/month for 75,000 calls/day

**Our caching strategy keeps us well within free tiers!**

## Support

**API Issues:**
- Congress.gov: api@loc.gov
- IEX Cloud: support@iexcloud.io
- AlphaVantage: support@alphavantage.co

**Project Issues:**
- GitHub: https://github.com/anthropics/congress-disclosures-standardized/issues

## Related Documentation

- [Gold Layer Architecture](GOLD_LAYER.md)
- [Data Enrichment Pipeline](ENRICHMENT_PIPELINE.md)
- [Free Tier Optimization](FREE_TIER_OPTIMIZATION.md)
- [API Strategy](API_STRATEGY.md)
