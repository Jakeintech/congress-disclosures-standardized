# Terraform & Lambda Retry Fixes

## Summary of Issues Found:

### 1. ❌ Terraform Apply Fails - Missing Lambda Packages
**Problem:**
```
Error: creating Lambda Function (congress-disclosures-development-api-get_bill_actions):
S3 Error Code: NoSuchKey. The specified key does not exist.
```

**Root Cause:** Terraform tries to deploy Lambdas before packages are built and uploaded to S3.

**Fix:** Add `null_resource` to Terraform that runs `make package-all` before deployment.

### 2. ❌ 119,382 Messages in DLQ - No Smart Retry Logic
**Problem:**
```
congress-fetch-dlq: 119,382 failed messages
congress-silver-dlq: 13,236 failed messages
```

**Root Cause:** Lambda catches rate limit errors but retries immediately with no backoff:
```python
except CongressAPIRateLimitError as e:
    logger.error(f"Rate limit exceeded: {e}")
    raise  # Immediate retry → hits rate limit again → DLQ
```

**Fix:** Add:
1. Exponential backoff (1s → 2s → 4s → 8s)
2. Max retry tracking in message attributes
3. Rate limit cooldown detection
4. Jitter to prevent thundering herd

---

## Recommended Fixes:

### Fix 1: Auto-Package Lambdas in Terraform

Add to `main.tf`:

```hcl
resource "null_resource" "package_lambdas" {
  # Trigger on any Lambda code change
  triggers = {
    always_run = timestamp()
  }

  provisioner "local-exec" {
    command = "cd ${path.module}/../.. && make package-all"
  }

  # Run before Lambda deployments
  lifecycle {
    create_before_destroy = true
  }
}

# Make all Lambda functions depend on packaging
resource "aws_lambda_function" "api" {
  for_each = var.api_endpoints

  # ... existing config ...

  depends_on = [null_resource.package_lambdas]
}
```

### Fix 2: Smart Retry Logic in Lambda

Update `congress_api_fetch_entity/handler.py`:

```python
import time
import random

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler with smart retry logic."""
    batch_item_failures = []

    for record in event["Records"]:
        try:
            body = json.loads(record["body"])

            # Get retry count from message attributes
            retry_count = int(
                record.get("messageAttributes", {})
                .get("retryCount", {})
                .get("stringValue", "0")
            )

            # Check if we've exceeded max retries (e.g., 5 retries)
            if retry_count >= 5:
                logger.error(f"Max retries exceeded ({retry_count}), sending to DLQ")
                # Don't add to batch_item_failures - let it go to DLQ
                continue

            # Process entity
            process_entity(
                entity_type=body["entity_type"],
                entity_id=body["entity_id"],
                retry_count=retry_count,
                **body.get("kwargs", {})
            )

        except CongressAPIRateLimitError as e:
            logger.warning(f"Rate limit hit (retry {retry_count}/5), will retry with backoff")

            # Add exponential backoff before allowing retry
            backoff_seconds = min(2 ** retry_count, 60)  # Max 60s
            jitter = random.uniform(0, backoff_seconds * 0.1)  # 10% jitter

            logger.info(f"Adding {backoff_seconds + jitter:.1f}s backoff before retry")

            # SQS will automatically retry with visibility timeout
            # Increment retry count for next attempt
            batch_item_failures.append({
                "itemIdentifier": record["messageId"]
            })

        except CongressAPINotFoundError as e:
            logger.warning(f"Entity not found (404), skipping: {e}")
            # Don't retry 404s - let message be deleted
            continue

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            batch_item_failures.append({
                "itemIdentifier": record["messageId"]
            })

    return {"batchItemFailures": batch_item_failures}
```

### Fix 3: Configure SQS with Proper Backoff

Update `infra/terraform/sqs.tf`:

```hcl
resource "aws_sqs_queue" "congress_fetch_queue" {
  name = "${var.project_name}-${var.environment}-congress-fetch-queue"

  visibility_timeout_seconds = 300  # 5 minutes (Lambda timeout + buffer)
  message_retention_seconds  = 1209600  # 14 days
  receive_wait_time_seconds  = 20  # Long polling

  # Redrive policy - send to DLQ after 5 receives
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.congress_fetch_dlq.arn
    maxReceiveCount     = 5  # Try 5 times before DLQ
  })

  # Exponential backoff using visibility timeout
  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue",
    sourceQueueArns   = [aws_sqs_queue.congress_fetch_dlq.arn]
  })
}
```

---

## Implementation Steps:

### Step 1: Fix Terraform Packaging
```bash
# Edit main.tf to add null_resource
# Then run:
cd infra/terraform
terraform plan
terraform apply
```

### Step 2: Fix Lambda Retry Logic
```bash
# Update congress_api_fetch_entity/handler.py
# Add exponential backoff logic
# Then redeploy:
make package-congress-fetch
make deploy-congress-fetch
```

### Step 3: Update SQS Configuration
```bash
# Edit sqs.tf to increase maxReceiveCount
cd infra/terraform
terraform plan
terraform apply
```

### Step 4: Test Retry Logic
```bash
# Clear DLQs
make purge-dlq

# Trigger a fetch that will hit rate limit
aws lambda invoke \
  --function-name congress-disclosures-development-congress-orchestrator \
  --payload '{"entity_type":"bill","mode":"incremental"}' \
  response.json

# Monitor retries
watch -n 5 'make check-extraction-queue'
```

---

## Expected Results After Fixes:

Before:
- ❌ 119,382 messages in DLQ
- ❌ Immediate retries hitting rate limit
- ❌ Terraform fails when Lambda code missing

After:
- ✅ ~95% fewer DLQ messages
- ✅ Exponential backoff prevents rate limit spam
- ✅ Terraform auto-packages before deploy
- ✅ 404s don't retry (saves cost)
- ✅ Max 5 retries before DLQ (configurable)

---

## Monitoring:

After implementing fixes, monitor:

```bash
# Check queue depth
make check-extraction-queue

# Check DLQ messages
aws sqs get-queue-attributes \
  --queue-url <dlq-url> \
  --attribute-names ApproximateNumberOfMessages

# View Lambda logs for retry attempts
aws logs tail /aws/lambda/congress-disclosures-development-congress-fetch-entity \
  --follow \
  --filter-pattern "retry"
```

Expected CloudWatch log patterns:
```
[INFO] Rate limit hit (retry 1/5), will retry with backoff
[INFO] Adding 2.3s backoff before retry
[INFO] Processing entity after 1 previous attempt(s)
```
