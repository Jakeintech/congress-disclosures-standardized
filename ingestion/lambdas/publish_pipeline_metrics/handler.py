"""
Pipeline Metrics Publisher Lambda.

Publishes pipeline execution metrics to CloudWatch.
Called by Step Functions at the end of each pipeline execution.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

cloudwatch = boto3.client("cloudwatch")

# Metric namespace
NAMESPACE = os.environ.get("CLOUDWATCH_NAMESPACE", "CongressDisclosures/Pipeline")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Publish pipeline metrics to CloudWatch.
    
    Expected event structure:
    {
        "pipeline": "house_fd" | "congress" | "lobbying" | "cross_dataset_correlation",
        "status": "success" | "failure",
        "metrics": {
            "documents_processed": 10,
            "transactions_extracted": 150,
            ...
        },
        "execution_id": "arn:aws:states:...",
        "start_time": "2025-01-01T00:00:00Z",
        "duration_seconds": 120
    }
    """
    try:
        pipeline = event.get("pipeline", "unknown")
        status = event.get("status", "success")
        metrics = event.get("metrics", {})
        execution_id = event.get("execution_id", "")
        duration_seconds = event.get("duration_seconds", 0)
        
        logger.info(f"Publishing metrics for pipeline: {pipeline}, status: {status}")
        
        # Build metric data
        metric_data: List[Dict] = []
        
        # Common dimensions
        dimensions = [
            {"Name": "Pipeline", "Value": pipeline},
            {"Name": "Environment", "Value": os.environ.get("ENVIRONMENT", "development")}
        ]
        
        # Pipeline success/failure metric
        metric_data.append({
            "MetricName": "PipelineExecution",
            "Value": 1 if status == "success" else 0,
            "Unit": "Count",
            "Dimensions": dimensions + [{"Name": "Status", "Value": status}],
            "Timestamp": datetime.now(timezone.utc)
        })
        
        # Pipeline duration metric
        if duration_seconds > 0:
            metric_data.append({
                "MetricName": "PipelineDuration",
                "Value": duration_seconds,
                "Unit": "Seconds",
                "Dimensions": dimensions,
                "Timestamp": datetime.now(timezone.utc)
            })
        
        # Custom metrics from event
        for metric_name, value in metrics.items():
            if isinstance(value, (int, float)) and value >= 0:
                # Convert snake_case to PascalCase for metric names
                formatted_name = "".join(word.capitalize() for word in metric_name.split("_"))
                metric_data.append({
                    "MetricName": formatted_name,
                    "Value": value,
                    "Unit": "Count",
                    "Dimensions": dimensions,
                    "Timestamp": datetime.now(timezone.utc)
                })
        
        # Publish metrics in batches of 20 (CloudWatch limit)
        for i in range(0, len(metric_data), 20):
            batch = metric_data[i:i + 20]
            cloudwatch.put_metric_data(
                Namespace=NAMESPACE,
                MetricData=batch
            )
            logger.info(f"Published {len(batch)} metrics to CloudWatch")
        
        return {
            "statusCode": 200,
            "body": {
                "message": f"Published {len(metric_data)} metrics for {pipeline} pipeline",
                "pipeline": pipeline,
                "status": status,
                "metrics_count": len(metric_data)
            }
        }
        
    except ClientError as e:
        logger.error(f"CloudWatch API error: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Failed to publish metrics: {e}", exc_info=True)
        raise
