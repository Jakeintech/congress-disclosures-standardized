# Gold Layer Automation

This document describes the automated pipeline for keeping the gold layer and website up-to-date.

## Overview

The pipeline automatically:
1. Extracts data from PDFs (silver layer)
2. Transforms to gold layer analytics tables
3. Computes document quality metrics
4. Updates public website with latest data

## Automation Options

### Option 1: GitHub Actions (Recommended)

**Daily automated runs at 2 AM EST**

The pipeline runs automatically via GitHub Actions workflow (`.github/workflows/gold-layer-pipeline.yml`).

**Setup:**
1. Add AWS credentials to GitHub Secrets:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`

2. Enable the workflow in your repository

3. The workflow will:
   - Run daily at 2 AM EST
   - Run on code changes to pipeline scripts
   - Can be manually triggered via GitHub UI

**Manual trigger:**
```bash
# Via GitHub CLI
gh workflow run gold-layer-pipeline.yml

# Or via GitHub UI: Actions → Gold Layer Pipeline → Run workflow
```

### Option 2: Local Scheduled Runs (cron)

**Set up cron job for local/server execution**

Add to crontab (runs daily at 2 AM):
```bash
crontab -e

# Add this line:
0 2 * * * cd /path/to/congress-disclosures-standardized && ./scripts/run_full_pipeline.sh >> /var/log/gold-pipeline.log 2>&1
```

### Option 3: Manual Runs

**Run the full pipeline manually:**
```bash
cd /path/to/congress-disclosures-standardized
./scripts/run_full_pipeline.sh
```

**Run incremental rebuild (only updates what changed):**
```bash
python3 scripts/rebuild_gold_incremental.py
```

## Pipeline Components

### 1. Incremental Rebuild Script

`scripts/rebuild_gold_incremental.py` intelligently rebuilds only what needs updating:

- Checks S3 timestamps for silver → gold changes
- Rebuilds fact_filings if silver data updated
- Rebuilds aggregates if fact data updated
- Regenerates website manifest if aggregates updated
- Skips unnecessary work to save time/cost

**Usage:**
```bash
python3 scripts/rebuild_gold_incremental.py
```

**Logic:**
```
IF silver/filings OR silver/documents newer than gold/fact_filings:
  → Rebuild fact_filings

IF gold/fact_filings newer than gold/agg_document_quality:
  → Recompute agg_document_quality

IF gold/agg_document_quality newer than website/data/document_quality.json:
  → Regenerate website manifest
```

### 2. Full Pipeline Script

`scripts/run_full_pipeline.sh` runs the complete pipeline:

1. Queue pending extractions (optional)
2. Rebuild fact_filings
3. Recompute document quality aggregates
4. Regenerate website manifests
5. Upload website files to S3

**Usage:**
```bash
./scripts/run_full_pipeline.sh
```

### 3. Individual Scripts

Run specific pipeline steps manually:

```bash
# Rebuild fact table
python3 scripts/build_fact_filings.py

# Recompute document quality
python3 scripts/compute_agg_document_quality.py

# Regenerate website manifest
python3 scripts/generate_document_quality_manifest.py
```

## Monitoring

### Check Pipeline Status

**GitHub Actions:**
- View runs: https://github.com/YOUR_ORG/congress-disclosures-standardized/actions
- Email notifications on failure (configure in GitHub settings)

**Local cron:**
```bash
# View log
tail -f /var/log/gold-pipeline.log

# Check last run
cat /var/log/gold-pipeline.log | grep "Pipeline run complete"
```

### Verify Website Updates

After pipeline runs, check:
1. Website loads: http://congress-disclosures-standardized.s3-website-us-east-1.amazonaws.com/website/index.html
2. Document Quality tab shows recent data
3. Flagged members appear if any have >30% image PDFs

### Monitor S3 Data

```bash
# Check gold layer timestamps
aws s3 ls s3://congress-disclosures-standardized/gold/house/financial/facts/fact_filings/ --recursive | tail -1
aws s3 ls s3://congress-disclosures-standardized/gold/house/financial/aggregates/agg_document_quality/ --recursive | tail -1

# Check website data
aws s3 ls s3://congress-disclosures-standardized/website/data/ --recursive
```

## Troubleshooting

### Pipeline fails with "No data found"

**Cause:** Silver layer not populated yet

**Fix:**
1. Run extraction pipeline first to populate silver layer
2. Queue extractions: `python3 scripts/queue_pending_extractions.py --limit 100`
3. Wait for extraction Lambda to process
4. Re-run gold pipeline

### Website shows stale data

**Cause:** Manifest not regenerated or not uploaded

**Fix:**
```bash
python3 scripts/generate_document_quality_manifest.py
aws s3 cp website/data/document_quality.json s3://congress-disclosures-standardized/website/data/document_quality.json --content-type application/json
```

### GitHub Actions fails with AWS credentials error

**Cause:** AWS secrets not configured

**Fix:**
1. Go to repo Settings → Secrets and variables → Actions
2. Add `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
3. Ensure IAM user has S3 read/write permissions

### Incremental rebuild doesn't detect changes

**Cause:** Clock skew or S3 timestamp issues

**Fix:** Force full rebuild:
```bash
./scripts/run_full_pipeline.sh
```

## Cost Optimization

The incremental rebuild script minimizes costs by:
- **Skipping unchanged data** - Only rebuilds what changed
- **Efficient S3 queries** - Uses list operations, not downloads
- **Parallel processing** - Multiple scripts can run concurrently

**Estimated costs (daily runs):**
- S3 requests: ~$0.001/day
- Data transfer: ~$0.01/day
- GitHub Actions: Free (2,000 minutes/month)
- **Total: ~$0.30/month**

## Advanced Configuration

### Environment Variables

Set in `.env` or GitHub Secrets:

```bash
# S3 Configuration
S3_BUCKET_NAME=congress-disclosures-standardized

# Quality thresholds
MIN_CONFIDENCE_SCORE=0.85              # Minimum extraction confidence
IMAGE_PDF_WARNING_THRESHOLD=0.30       # Flag if >30% image PDFs

# Quality score weights (must sum to 1.0)
QUALITY_WEIGHT_CONFIDENCE=0.4          # 40% weight on extraction confidence
QUALITY_WEIGHT_FORMAT=0.3              # 30% weight on PDF format (text vs image)
QUALITY_WEIGHT_COMPLETENESS=0.3        # 30% weight on data completeness
```

### Customizing Schedule

**GitHub Actions:**
Edit `.github/workflows/gold-layer-pipeline.yml`:
```yaml
on:
  schedule:
    - cron: '0 7 * * *'  # Daily at 2 AM EST
    # Change to:
    - cron: '0 */6 * * *'  # Every 6 hours
```

**Cron:**
```bash
# Every 6 hours
0 */6 * * * cd /path/to/repo && ./scripts/run_full_pipeline.sh

# Twice daily (2 AM and 2 PM)
0 2,14 * * * cd /path/to/repo && ./scripts/run_full_pipeline.sh
```

## Future Enhancements

Planned automation improvements:

1. **Lambda-based triggers** - Rebuild gold layer automatically when silver layer updates (S3 event triggers)
2. **SNS notifications** - Alert on pipeline failures or when new flagged members detected
3. **CloudWatch dashboards** - Monitor pipeline health and data freshness
4. **Incremental PTR processing** - Only process new PTRs, not full rebuilds
5. **Multi-year partitioning** - Optimize queries by year

## Summary

The gold layer pipeline is now **fully automated**:

✅ **GitHub Actions** runs daily at 2 AM EST
✅ **Incremental rebuilds** only update changed data
✅ **Website auto-updates** with latest analytics
✅ **Cost-optimized** - skips unnecessary work
✅ **Monitoring** via GitHub Actions UI and S3 timestamps

**Next steps:**
1. Configure AWS credentials in GitHub Secrets
2. Enable GitHub Actions workflow
3. Monitor first automated run
4. Verify website updates correctly

For questions or issues, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or open a GitHub issue.
