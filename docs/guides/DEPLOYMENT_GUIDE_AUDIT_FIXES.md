# Complete Deployment Guide - API Audit Fixes

**Version**: 1.0.0
**Date**: December 20, 2025
**Status**: Ready for Production Deployment

---

## 📋 Quick Reference

This guide covers the complete deployment process for the API audit fixes, including all infrastructure changes, Lambda updates, and verification steps.

### What Changed

- ✅ **61 Lambda handlers** standardized to use `success_response()`
- ✅ **Version tracking** system implemented (/v1/version endpoint)
- ✅ **OpenAPI spec** updated with 6 new endpoints
- ✅ **Health checks** expanded from 12 to 30+ endpoints
- ✅ **Gold layer validation** script created
- ✅ **Makefile** updated with verification targets

---

## 🚀 Pre-Deployment Checklist

### 1. Local Verification

```bash
# Run handler audit (should show 100% Pattern A)
make audit-handlers

# Generate version file
python3 scripts/generate_version.py --pretty

# Verify no uncommitted changes (or commit first)
git status
```

**Expected Output**:
```
Pattern A (CORRECT): 61 handlers (100%)
Pattern B (DEPRECATED): 0 handlers
Pattern C (BROKEN): 0 handlers
```

### 2. Pre-Deployment Tests

```bash
# Run linting and type checks
make format-check
make lint

# Run unit tests
make test-unit

# Validate Gold layer (if deployed)
make verify-gold
```

---

## 📦 Deployment Process

### Step 1: Package API Lambdas

```bash
# This will:
# 1. Generate version.json with Git metadata
# 2. Package all 61 Lambda handlers
# 3. Include version.json in each package
# 4. Upload to S3

./scripts/package_api_lambdas.sh
```

**Expected Output**:
```
Generating version.json...
✓ Version generated: v20251220-33a4c83
Packaging API Lambdas...
Processing get_members...
...
All API Lambdas packaged and uploaded!
```

**Verification**:
```bash
# Check version.json was created
cat build/version.json | jq '.version'
# Should output something like: "v20251220-33a4c83"

# Verify S3 upload
aws s3 ls s3://congress-disclosures-standardized/lambda-deployments/api/ | head -5
```

### Step 2: Deploy Infrastructure

```bash
cd infra/terraform

# Review changes (should show new get_version Lambda + route)
terraform plan

# Apply changes
terraform apply
```

**Expected Terraform Changes**:
```
+ aws_lambda_function.api["get_version"]
+ aws_apigatewayv2_route.get_version
+ aws_apigatewayv2_integration.get_version
~ aws_lambda_function.api[...] (code changes for all handlers)
```

**Important**: Terraform will update all 61 Lambda functions with the new packaged code. This is expected and correct.

### Step 3: Wait for Deployment

```bash
# Wait 30-60 seconds for Lambda functions to update
sleep 60

# Verify Lambda functions are updated
aws lambda get-function --function-name congress-disclosures-api-get_version \
  --query 'Configuration.LastModified'
```

---

## ✅ Post-Deployment Verification

### Quick Verification (2-3 minutes)

```bash
# 1. Check version endpoint
make verify-api-version

# 2. Check critical endpoints
make verify-api-critical

# 3. Audit handlers (should still be 100% Pattern A)
make audit-handlers
```

**Expected Output**:
```
🔍 Checking API version...
Checking https://...execute-api.../v1/version...
PASS
--------------------

🔴 Checking critical endpoints...
✅ Passed: 4/4
```

### Comprehensive Verification (5-10 minutes)

```bash
# Run full verification suite
make verify-deployment
```

This runs:
1. **API health checks** (30+ endpoints)
2. **Gold layer validation** (data integrity)
3. **Handler audit** (response pattern compliance)

**Expected Output**:
```
🏥 Running API health checks...
============================================================
API Health Check - Testing 30 endpoints
Base URL: https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com
============================================================

Checking https://.../v1/version...
PASS
...

============================================================
SUMMARY
============================================================
✅ Passed: 30/30
❌ Failed: 0/30

✅ ALL HEALTH CHECKS PASSED

💎 Validating Gold layer...
✅ VALIDATION PASSED
Gold layer is healthy and ready for deployment

🔍 Auditing Lambda handlers...
✅ Pattern A (CORRECT): 61 handlers (100%)

✅ DEPLOYMENT VERIFICATION COMPLETE
   - API health checks passed
   - Gold layer validated
   - Handler audit passed
```

### Manual Spot Checks

```bash
# 1. Test version endpoint manually
curl https://YOUR_API_URL/v1/version | jq

# Expected response:
{
  "success": true,
  "data": {
    "version": "v20251220-33a4c83",
    "git": {
      "commit": "33a4c83d220eba54d3befffc007e4f9f904bd96b",
      "commit_short": "33a4c83",
      "branch": "main",
      "dirty": false
    },
    "build": {
      "timestamp": "2025-12-20T01:40:23.727620+00:00",
      "date": "20251220"
    },
    "api_version": "v1",
    "runtime": { ... },
    "status": "healthy"
  },
  "version": "v20251220-33a4c83"
}

# 2. Test a standard endpoint for version tag
curl https://YOUR_API_URL/v1/members?limit=1 | jq '.version'
# Should output: "v20251220-33a4c83"

# 3. Test for NaN values
curl https://YOUR_API_URL/v1/analytics/summary | grep -i "nan"
# Should return nothing (no matches)

# 4. Test error response format
curl https://YOUR_API_URL/v1/members/INVALID123 | jq
# Expected:
{
  "success": false,
  "error": {
    "message": "Member not found",
    "code": 404
  }
}
```

---

## 🔍 Troubleshooting

### Issue: Version endpoint returns 404

**Cause**: Terraform didn't create the route or Lambda

**Solution**:
```bash
cd infra/terraform
terraform refresh
terraform apply

# Verify Lambda exists
aws lambda get-function --function-name congress-disclosures-api-get_version

# Verify route exists
aws apigatewayv2 get-routes --api-id YOUR_API_ID | grep "/v1/version"
```

### Issue: Endpoints return old version or no version

**Cause**: Lambdas weren't updated with new packages

**Solution**:
```bash
# Re-package and re-deploy
./scripts/package_api_lambdas.sh
cd infra/terraform && terraform apply

# Force Lambda update
aws lambda update-function-code \
  --function-name congress-disclosures-api-get_members \
  --s3-bucket congress-disclosures-standardized \
  --s3-key lambda-deployments/api/get_members.zip
```

### Issue: Some endpoints still return literal "NaN"

**Cause**: Handler not using `success_response()` or has local `clean_nan()`

**Solution**:
```bash
# Identify problematic handlers
make audit-handlers

# If any Pattern B/C found, fix and re-deploy:
# 1. Edit handler to use success_response()
# 2. Re-package: ./scripts/package_api_lambdas.sh
# 3. Re-deploy: cd infra/terraform && terraform apply
```

### Issue: Health checks fail for some endpoints

**Cause**: Data may not exist yet, or endpoint has bugs

**Solution**:
```bash
# Test specific endpoint
make verify-api --endpoint /v1/FAILING_ENDPOINT

# Check Lambda logs
aws logs tail /aws/lambda/congress-disclosures-api-FUNCTION_NAME --follow

# If critical endpoint, investigate immediately
# If non-critical, note for investigation
```

---

## 📊 Monitoring Post-Deployment

### CloudWatch Metrics to Watch

1. **Lambda Errors** (first 24 hours)
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Errors \
     --dimensions Name=FunctionName,Value=congress-disclosures-api-get_version \
     --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Sum
   ```

2. **API Gateway 4xx/5xx Errors**
   - Monitor for spikes in error rates
   - Should remain < 1% of total requests

3. **Lambda Duration**
   - Check for performance regressions
   - Version endpoint should be < 100ms
   - Other endpoints should be < 1000ms

### Automated Monitoring

```bash
# Set up cron job for periodic health checks (optional)
crontab -e

# Add:
0 * * * * cd /path/to/repo && make verify-api-critical >> /var/log/api-health.log 2>&1
```

---

## 🎯 Success Criteria

Deployment is successful if ALL of the following are true:

- ✅ `make verify-deployment` passes without errors
- ✅ `/v1/version` endpoint returns correct Git hash
- ✅ All critical endpoints return 200 status
- ✅ No literal "NaN" strings found in any response
- ✅ Error responses use standardized format
- ✅ `make audit-handlers` shows 100% Pattern A compliance
- ✅ CloudWatch shows no Lambda errors (first 1 hour)

---

## 🔄 Rollback Procedure

If deployment fails verification:

### Option 1: Quick Rollback (Terraform)

```bash
cd infra/terraform

# Rollback to previous state
terraform apply -refresh-only
terraform plan -destroy -target=aws_lambda_function.api["get_version"]
# Review, then destroy only new resources

# Redeploy old code
git checkout HEAD~1 infra/terraform/
terraform apply
```

### Option 2: Full Rollback (Git)

```bash
# Revert to previous commit
git revert HEAD
git push

# Redeploy
./scripts/package_api_lambdas.sh
cd infra/terraform && terraform apply
```

### Option 3: Manual Lambda Update

```bash
# Upload old code for specific Lambda
aws lambda update-function-code \
  --function-name congress-disclosures-api-FUNCTION \
  --s3-bucket YOUR_BUCKET \
  --s3-key lambda-deployments/OLD_CODE.zip
```

---

## 📚 Additional Resources

- **API Audit Summary**: `docs/API_AUDIT_FIXES_SUMMARY.md`
- **OpenAPI Specification**: `docs/openapi.yaml`
- **Architecture Docs**: `docs/ARCHITECTURE.md`
- **Handler Patterns**: See audit summary for Pattern A/B/C explanations

---

## 📞 Support

If issues persist after following this guide:

1. Check CloudWatch Logs for specific errors
2. Run `make audit-handlers` to verify code patterns
3. Review `docs/API_AUDIT_FIXES_SUMMARY.md` for implementation details
4. Create GitHub issue with:
   - Output of `make verify-deployment`
   - CloudWatch logs (if applicable)
   - Steps to reproduce

---

## ✅ Final Checklist

Before marking deployment complete:

- [ ] All 61 Lambda functions updated
- [ ] `/v1/version` endpoint accessible
- [ ] `make verify-deployment` passes
- [ ] No CloudWatch errors in first hour
- [ ] OpenAPI spec validated
- [ ] Documentation updated
- [ ] Team notified of deployment
- [ ] Monitoring dashboards checked

---

**Deployment Status**: 🟢 READY FOR PRODUCTION

Last Updated: December 20, 2025
