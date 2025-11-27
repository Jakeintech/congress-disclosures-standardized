"""
Data Quality Validator Lambda.
"""

import json
import logging
import os
import boto3
from datetime import datetime, timezone
from typing import Dict, Any, List

# Import validators
from ingestion.lib.validators.schema_validator import SchemaValidator
from ingestion.lib.validators.date_validator import DateValidator
from ingestion.lib.validators.amount_validator import AmountValidator
from ingestion.lib.validators.completeness_validator import CompletenessValidator
from ingestion.lib.validators.anomaly_detector import AnomalyDetector

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

S3_BUCKET = os.environ.get("S3_BUCKET_NAME")
S3_SILVER_PREFIX = os.environ.get("S3_SILVER_PREFIX", "silver")

s3_client = boto3.client("s3")

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler.
    Triggered by SQS message containing extraction result location or payload.
    """
    try:
        for record in event.get('Records', []):
            body = json.loads(record['body'])
            doc_id = body.get('doc_id')
            year = body.get('year')
            
            # Assume body contains the extracted data or a pointer to it
            # For now, let's assume we fetch the extracted JSON from S3
            # The extraction Lambda should have saved it to silver/house/financial/year={YEAR}/json/{doc_id}.json
            # Or maybe it's passed in the payload?
            # Let's assume we fetch it.
            
            s3_key = f"{S3_SILVER_PREFIX}/house/financial/year={year}/json/{doc_id}.json"
            
            logger.info(f"Validating {doc_id} from {s3_key}")
            
            try:
                response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
                data = json.loads(response['Body'].read())
            except Exception as e:
                logger.error(f"Failed to fetch data for {doc_id}: {e}")
                continue
                
            # Run validators
            validators = [
                # SchemaValidator needs schema path. Assuming it's packaged with Lambda.
                # SchemaValidator(os.path.join(os.path.dirname(__file__), '../../schemas/house_fd_schema.json')),
                # For now, skip SchemaValidator if schema not available, or use a default one.
                DateValidator(),
                AmountValidator(),
                CompletenessValidator(),
                AnomalyDetector()
            ]
            
            results = []
            overall_status = "PASS"
            total_issues = 0
            
            for validator in validators:
                issues = validator.validate(data)
                status = "PASS"
                if any(i['severity'] == 'error' for i in issues):
                    status = "FAIL"
                    overall_status = "FAIL"
                elif issues and overall_status != "FAIL":
                    status = "WARNING"
                    if overall_status == "PASS":
                        overall_status = "WARNING"
                        
                results.append({
                    "validator_name": validator.__class__.__name__,
                    "status": status,
                    "issues": issues
                })
                total_issues += len(issues)
                
            # Create report
            report = {
                "doc_id": doc_id,
                "year": year,
                "validation_timestamp": datetime.now(timezone.utc).isoformat(),
                "overall_status": overall_status,
                "issue_count": total_issues,
                "validator_results": results
            }
            
            # Save report to S3
            report_key = f"{S3_SILVER_PREFIX}/data_quality/year={year}/{doc_id}_report.json"
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=report_key,
                Body=json.dumps(report, indent=2),
                ContentType="application/json"
            )
            
            logger.info(f"Saved quality report to {report_key} (Status: {overall_status})")
            
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        raise e
