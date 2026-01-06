"""Terraform configuration auto-detection utility.

This module reads Terraform outputs to avoid hardcoding AWS resource names
and account IDs in scripts. It's safe for open-source repositories.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TerraformConfig:
    """Read configuration from Terraform outputs or environment variables."""

    def __init__(self, terraform_dir: Optional[Path] = None):
        """Initialize config reader.

        Args:
            terraform_dir: Path to Terraform directory. If None, auto-detects.
        """
        self._config_cache = None

        if terraform_dir is None:
            # Auto-detect terraform directory
            script_dir = Path(__file__).parent.parent.parent
            terraform_dir = script_dir / "infra" / "terraform"

        self.terraform_dir = Path(terraform_dir)

    def get_config(self) -> Dict[str, Any]:
        """Get AWS configuration from Terraform outputs or environment variables.

        Returns:
            Dict with keys: s3_bucket_id, s3_region, sqs_extraction_queue_url, etc.
        """
        if self._config_cache is not None:
            return self._config_cache

        # Try Terraform outputs first
        try:
            config = self._read_terraform_outputs()
            if config:
                logger.info("Loaded configuration from Terraform outputs")
                self._config_cache = config
                return config
        except Exception as e:
            logger.warning(f"Failed to read Terraform outputs: {e}")

        # Fallback to environment variables
        config = self._read_from_env()
        logger.info("Loaded configuration from environment variables")
        self._config_cache = config
        return config

    def _read_terraform_outputs(self) -> Dict[str, Any]:
        """Read Terraform outputs JSON.

        Returns:
            Dict with configuration values

        Raises:
            Exception: If Terraform command fails
        """
        if not self.terraform_dir.exists():
            raise FileNotFoundError(f"Terraform directory not found: {self.terraform_dir}")

        # Run terraform output -json
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=self.terraform_dir,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            raise RuntimeError(f"Terraform output failed: {result.stderr}")

        outputs = json.loads(result.stdout)

        # Extract values from Terraform output format
        config = {}

        # S3 bucket
        if "s3_bucket_id" in outputs:
            config["s3_bucket_id"] = outputs["s3_bucket_id"]["value"]

        # S3 region
        if "s3_region" in outputs:
            config["s3_region"] = outputs["s3_region"]["value"]
        elif "aws_region" in outputs:
            config["s3_region"] = outputs["aws_region"]["value"]
        else:
            config["s3_region"] = "us-east-1"  # Default

        # SQS queue URLs
        if "sqs_extraction_queue_url" in outputs:
            config["sqs_extraction_queue_url"] = outputs["sqs_extraction_queue_url"]["value"]

        if "sqs_extraction_dlq_url" in outputs:
            config["sqs_extraction_dlq_url"] = outputs["sqs_extraction_dlq_url"]["value"]

        # Lambda function names
        if "lambda_extract_function_name" in outputs:
            config["lambda_extract_function_name"] = outputs["lambda_extract_function_name"]["value"]

        if "lambda_ingest_function_name" in outputs:
            config["lambda_ingest_function_name"] = outputs["lambda_ingest_function_name"]["value"]

        if "lambda_index_function_name" in outputs:
            config["lambda_index_function_name"] = outputs["lambda_index_function_name"]["value"]

        return config

    def _read_from_env(self) -> Dict[str, Any]:
        """Read configuration from environment variables.

        Returns:
            Dict with configuration values
        """
        config = {
            "s3_bucket_id": os.environ.get("S3_BUCKET_ID"),
            "s3_region": os.environ.get("S3_REGION", os.environ.get("AWS_REGION", "us-east-1")),
            "sqs_extraction_queue_url": os.environ.get("SQS_EXTRACTION_QUEUE_URL"),
            "sqs_extraction_dlq_url": os.environ.get("SQS_EXTRACTION_DLQ_URL"),
            "lambda_extract_function_name": os.environ.get("LAMBDA_EXTRACT_FUNCTION_NAME"),
            "lambda_ingest_function_name": os.environ.get("LAMBDA_INGEST_FUNCTION_NAME"),
            "lambda_index_function_name": os.environ.get("LAMBDA_INDEX_FUNCTION_NAME"),
        }

        # Remove None values
        config = {k: v for k, v in config.items() if v is not None}

        return config


# Global instance for easy access
_global_config = None


def get_aws_config() -> Dict[str, Any]:
    """Get AWS configuration (global singleton).

    Returns:
        Dict with keys: s3_bucket_id, s3_region, sqs_extraction_queue_url, etc.

    Example:
        >>> from lib.terraform_config import get_aws_config
        >>> config = get_aws_config()
        >>> s3_bucket = config['s3_bucket_id']
        >>> sqs_url = config['sqs_extraction_queue_url']
    """
    global _global_config
    if _global_config is None:
        _global_config = TerraformConfig()
    return _global_config.get_config()


def get_value(key: str, required: bool = True) -> Optional[str]:
    """Get a single configuration value.

    Args:
        key: Configuration key (e.g., 's3_bucket_id')
        required: If True, raises error if key not found

    Returns:
        Configuration value or None

    Raises:
        KeyError: If required=True and key not found
    """
    config = get_aws_config()
    if required and key not in config:
        raise KeyError(
            f"Required configuration '{key}' not found. "
            "Please run 'terraform apply' or set environment variable."
        )
    return config.get(key)
