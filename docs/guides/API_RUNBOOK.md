# API Production Runbook

## Quick Reference

### Health Checks
```bash
# Check API health
python scripts/test_api_production.py

# Run contract tests
pytest tests/test_api_contracts.py -v

# Check specific endpoint
curl https://your-api-url.execute-api.us-east-1.amazonaws.com/v1/version
```

### Deployment
```bash
# Package and deploy
make package-api
cd infra/terraform && terraform apply

# Deploy specific function
aws lambda update-function-code \
  --function-name congress-disclosures-development-api-get_trades \
  --zip-file fileb://api/lambdas/get_trades/get_trades.zip
```

### Monitoring
```bash
# View Lambda logs
aws logs tail /aws/lambda/congress-disclosures-development-api-get_trades --follow

# Check error rates
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=congress-disclosures-development-api-get_trades \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

## Troubleshooting

### Issue: Endpoint returns 500 error
1. Check CloudWatch logs: `aws logs tail /aws/lambda/[function-name] --follow`
2. Look for Python exceptions or DuckDB errors
3. Verify S3 data exists: `aws s3 ls s3://congress-disclosures-standardized/gold/`
4. Test locally: `python scripts/test_lambda_locally.py --handler [handler-name]`

### Issue: Timeout errors
1. Check function timeout setting (should be 30s for API, 900s for processing)
2. Review query complexity in CloudWatch Insights
3. Consider adding pagination or caching

### Issue: DuckDB errors
1. **union_by_name error**: Check DuckDB version matches local
2. **Type mismatch**: Verify CAST operations in SQL
3. **S3 access**: Confirm Lambda has S3 read permissions

## Rollback Procedures

### Rolling back a bad deployment
```bash
# 1. Get previous version
aws lambda get-function --function-name [name] --query 'Configuration.Version'

# 2. Update alias to previous version
aws lambda update-alias \
  --function-name [name] \
  --name production \
  --function-version [previous-version]

# 3. Or redeploy from git
git checkout [previous-commit]
make package-api
terraform apply -target=aws_lambda_function.api
```

## Performance Benchmarks

### Expected Response Times
- `/v1/version`: < 100ms
- `/v1/trades` (10 records): < 2s
- `/v1/analytics/summary`: < 5s
- Congress API proxies: < 3s (depends on Congress.gov)

### Alarm Thresholds
- **Error Rate**: > 5% over 5 minutes
- **Duration**: > 25s (p99)
- **Throttles**: > 10 over 5 minutes

## Maintenance Windows

### Regular tasks
- **Weekly**: Review CloudWatch metrics and error logs
- **Monthly**: Update dependencies and redeploy
- **Quarterly**: Review and optimize slow queries

### Breaking change deployment
1. Announce maintenance window
2. Deploy to staging first
3. Run full E2E test suite
4. Deploy to production during low-traffic period
5. Monitor for 1 hour post-deployment
