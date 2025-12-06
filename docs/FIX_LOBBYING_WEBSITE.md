# Fix Lobbying Website

The lobbying explorer page is showing "Not Found" because the API routes aren't deployed and the data hasn't been processed through the Silver and Gold layers.

## Quick Fix (3 Steps)

### Step 1: Build Lobbying Data

Run all Silver and Gold layer scripts to process the Bronze lobbying data:

```bash
# Default year (2025)
make fix-lobbying

# Or specify a different year
make fix-lobbying YEAR=2024
```

This will:
- Process ~1500 Bronze lobbying filings
- Build Silver tables (filings, clients, registrants, lobbyists, activities)
- Build Gold dimensions and fact tables
- Take ~5-10 minutes

Expected output:
```
📊 SILVER LAYER (Normalized Tables)
================================================================================
🔧 Running: lobbying_build_silver_filings
✅ lobbying_build_silver_filings completed successfully (45.2s)
...
🏆 GOLD LAYER (Analytics & Dimensions)
================================================================================
🔧 Running: lobbying_build_dim_registrant
✅ lobbying_build_dim_registrant completed successfully (12.3s)
...
📊 EXECUTION SUMMARY
================================================================================
Silver Layer:
   ✅ Successful: 8/8
Gold Layer:
   ✅ Successful: 4/4
Total:
   ✅ 12/12 scripts completed successfully
```

### Step 2: Deploy API Gateway Routes

The lobbying API routes are defined in Terraform but not deployed:

```bash
cd infra/terraform
terraform plan  # Review changes
terraform apply  # Deploy
```

This will create the missing API routes:
- `GET /v1/lobbying/filings`
- `GET /v1/lobbying/clients/{client_id}`
- `GET /v1/lobbying/network`
- `GET /v1/congress/bills/{bill_id}/lobbying`
- `GET /v1/members/{bioguide_id}/lobbying`

### Step 3: Deploy Website

```bash
make deploy-website
```

This syncs the website files to S3 (the JS is already correct, it just needs the API to work).

## Verify It Works

### Test API Endpoint

```bash
curl 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com/v1/lobbying/filings?filing_year=2025&limit=10' | jq '.'
```

Expected response:
```json
{
  "filings": [
    {
      "filing_uuid": "abc-123",
      "client_name": "Example Corp",
      "registrant_name": "Lobbying Firm LLC",
      "income": 50000,
      "filing_year": 2025,
      "filing_period": "Q1"
    },
    ...
  ],
  "count": 10,
  "total": 1507
}
```

### Test Website

Open: https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/website/lobbying-explorer.html

You should see:
- ✅ Stats boxes with real numbers (Total Filings, Total Spend, etc.)
- ✅ Top 10 Clients chart with data
- ✅ Filings table populated with rows
- ✅ Filters and pagination working

## What Was Missing?

### 1. Silver Layer Data

The Bronze lobbying data existed but wasn't processed into Silver tables:

```bash
# Before
aws s3 ls s3://congress-disclosures-standardized/silver/lobbying/
# (empty or minimal)

# After
aws s3 ls s3://congress-disclosures-standardized/silver/lobbying/ --recursive
# Shows: filings/, clients/, registrants/, lobbyists/, activities/, etc.
```

### 2. Gold Layer Analytics

No aggregated data for API to serve:

```bash
# Before
aws s3 ls s3://congress-disclosures-standardized/gold/lobbying/
# (empty or minimal)

# After
aws s3 ls s3://congress-disclosures-standardized/gold/lobbying/ --recursive
# Shows: dim_client/, dim_registrant/, dim_lobbyist/, fact_activity/
```

### 3. API Gateway Routes

Routes defined in Terraform but not deployed:

```bash
# Before
aws apigatewayv2 get-routes --api-id yvpi88rhwl --query 'Items[?contains(RouteKey, `lobbying`)].RouteKey'
# (empty)

# After
aws apigatewayv2 get-routes --api-id yvpi88rhwl --query 'Items[?contains(RouteKey, `lobbying`)].RouteKey'
# Shows: GET /v1/lobbying/filings, etc.
```

## Understanding the Pipeline

### Data Flow

```
Bronze (Raw JSON from LDA API)
  ↓
  lobbying_build_silver_* scripts
  ↓
Silver (Parquet tables)
  ├─ filings/
  ├─ clients/
  ├─ registrants/
  ├─ lobbyists/
  ├─ activities/
  ├─ activity_bills/
  ├─ government_entities/
  └─ contributions/
  ↓
  lobbying_build_dim_* and lobbying_build_fact_* scripts
  ↓
Gold (Dimensions & Facts)
  ├─ dim_client/
  ├─ dim_registrant/
  ├─ dim_lobbyist/
  └─ fact_activity/
  ↓
  API Lambda reads from Gold layer
  ↓
  Website fetches from API
```

### Scripts Run by `make fix-lobbying`

**Silver Layer (8 scripts):**
1. `lobbying_build_silver_filings.py` - Main filing metadata
2. `lobbying_build_silver_registrants.py` - Lobbying firms
3. `lobbying_build_silver_clients.py` - Organizations being represented
4. `lobbying_build_silver_lobbyists.py` - Individual lobbyists
5. `lobbying_build_silver_activities.py` - Lobbying activities
6. `lobbying_build_silver_activity_bills.py` - Bill references (NLP extracted)
7. `lobbying_build_silver_government_entities.py` - Gov agencies contacted
8. `lobbying_build_silver_contributions.py` - Political contributions

**Gold Layer (4 scripts):**
1. `lobbying_build_dim_registrant.py` - Registrant dimension (SCD Type 2)
2. `lobbying_build_dim_client.py` - Client dimension
3. `lobbying_build_dim_lobbyist.py` - Lobbyist dimension
4. `lobbying_build_fact_activity.py` - Activity fact table

## Troubleshooting

### "No Bronze lobbying data found"

Run lobbying ingestion first:

```bash
python3 scripts/trigger_lda_ingestion.py --year 2025 --type all
```

### "Script failed"

Check which script failed and run it individually:

```bash
python3 scripts/lobbying_build_silver_filings.py
```

Check CloudWatch logs:

```bash
# If it's a Lambda issue
make logs-lda-ingest

# Check S3 for data
aws s3 ls s3://congress-disclosures-standardized/bronze/lobbying/ --recursive | head -20
```

### API Still Returns "Not Found"

1. Verify routes are deployed:
```bash
aws apigatewayv2 get-routes --api-id yvpi88rhwl --query 'Items[?contains(RouteKey, `lobbying`)].RouteKey' --output table
```

2. Check Lambda exists:
```bash
aws lambda get-function --function-name congress-disclosures-development-api-get_lobbying_filings
```

3. Test Lambda directly:
```bash
aws lambda invoke --function-name congress-disclosures-development-api-get_lobbying_filings \
  --payload '{"queryStringParameters": {"filing_year": "2025", "limit": "10"}}' \
  response.json && cat response.json | jq '.'
```

### Website Shows "Loading" Forever

1. Check browser console (F12) for errors
2. Verify API endpoint in `website/js/lobbying-explorer.js` matches your API Gateway URL
3. Check CORS is configured properly in API Gateway

## Manual Alternative

If `make fix-lobbying` fails, run scripts individually:

```bash
# Silver
python3 scripts/lobbying_build_silver_filings.py
python3 scripts/lobbying_build_silver_registrants.py
python3 scripts/lobbying_build_silver_clients.py
python3 scripts/lobbying_build_silver_lobbyists.py
python3 scripts/lobbying_build_silver_activities.py
python3 scripts/lobbying_build_silver_activity_bills.py
python3 scripts/lobbying_build_silver_government_entities.py
python3 scripts/lobbying_build_silver_contributions.py

# Gold
python3 scripts/lobbying_build_dim_registrant.py
python3 scripts/lobbying_build_dim_client.py
python3 scripts/lobbying_build_dim_lobbyist.py
python3 scripts/lobbying_build_fact_activity.py
```

## Future Prevention

Add lobbying scripts to `run_smart_pipeline.py` so they run automatically with incremental updates.

The pipeline already includes them (lines 405-421 in `scripts/run_smart_pipeline.py`), so running:

```bash
python3 scripts/run_smart_pipeline.py --mode aggregate
```

Will process lobbying data going forward.

## Summary

**Root cause:** Lobbying data existed in Bronze but wasn't processed through Silver/Gold layers, and API routes weren't deployed.

**Solution:**
1. `make fix-lobbying` - Process data
2. `terraform apply` - Deploy API routes
3. `make deploy-website` - Deploy website

**Time:** ~10-15 minutes total

**Result:** Fully functional lobbying explorer with real data! 💰
