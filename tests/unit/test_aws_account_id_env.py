#!/usr/bin/env python3
"""
Test that scripts properly require and use AWS_ACCOUNT_ID environment variable.
Related to STORY-009: Remove Hardcoded AWS Account IDs
"""
import os
import sys
import pytest
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent


class TestAWSAccountIDEnvironment:
    """Test AWS_ACCOUNT_ID environment variable handling in scripts."""

    def test_run_congress_pipeline_requires_account_id(self):
        """Test that run_congress_pipeline.py requires AWS_ACCOUNT_ID."""
        script_path = REPO_ROOT / "scripts" / "run_congress_pipeline.py"
        
        # Remove AWS_ACCOUNT_ID if it exists
        env = os.environ.copy()
        env.pop('AWS_ACCOUNT_ID', None)
        
        # Script should exit with error when AWS_ACCOUNT_ID is missing
        result = subprocess.run(
            [sys.executable, str(script_path), '--help'],
            env=env,
            capture_output=True,
            text=True
        )
        
        # Should fail due to missing AWS_ACCOUNT_ID
        assert result.returncode != 0 or 'AWS_ACCOUNT_ID' in result.stderr

    def test_get_pipeline_status_requires_account_id(self):
        """Test that get_pipeline_status.py requires AWS_ACCOUNT_ID."""
        script_path = REPO_ROOT / "scripts" / "get_pipeline_status.py"
        
        # Remove AWS_ACCOUNT_ID if it exists
        env = os.environ.copy()
        env.pop('AWS_ACCOUNT_ID', None)
        
        # Script should exit with error when AWS_ACCOUNT_ID is missing
        result = subprocess.run(
            [sys.executable, str(script_path)],
            env=env,
            capture_output=True,
            text=True
        )
        
        # Should fail due to missing AWS_ACCOUNT_ID
        assert result.returncode != 0
        assert 'AWS_ACCOUNT_ID' in result.stderr

    def test_scripts_use_dynamic_queue_urls(self):
        """Test that scripts use dynamic queue URLs with AWS_ACCOUNT_ID."""
        scripts = [
            "scripts/run_congress_pipeline.py",
            "scripts/get_pipeline_status.py",
            "scripts/reprocess_ptr_filings.py",
            "scripts/reprocess_annual_filings.py",
            "scripts/trigger_extraction_batch.py",
            "scripts/backfill_silver_layer.py",
        ]
        
        for script_path in scripts:
            full_path = REPO_ROOT / script_path
            content = full_path.read_text()
            
            # Should NOT contain hardcoded account ID
            assert "464813693153" not in content, \
                f"{script_path} still contains hardcoded account ID"
            
            # Should contain reference to AWS_ACCOUNT_ID environment variable
            # (either os.environ.get or os.getenv)
            assert "AWS_ACCOUNT_ID" in content, \
                f"{script_path} does not reference AWS_ACCOUNT_ID"

    def test_terraform_uses_caller_identity(self):
        """Test that Terraform files use data.aws_caller_identity."""
        tf_files = [
            "infra/terraform/lambda.tf",
            "infra/terraform/lambda_congress.tf",
            "infra/terraform/api_lambdas.tf",
        ]
        
        for tf_path in tf_files:
            full_path = REPO_ROOT / tf_path
            content = full_path.read_text()
            
            # Should NOT contain hardcoded account ID in active code
            # (comments are OK)
            lines = [line for line in content.split('\n') if not line.strip().startswith('#')]
            non_comment_content = '\n'.join(lines)
            assert "464813693153" not in non_comment_content, \
                f"{tf_path} still contains hardcoded account ID in active code"
            
            # Should contain reference to aws_caller_identity
            assert "aws_caller_identity" in content or "AWS_ACCOUNT_ID" in content, \
                f"{tf_path} does not reference aws_caller_identity or AWS_ACCOUNT_ID"

    def test_env_example_has_account_id(self):
        """Test that .env.example includes AWS_ACCOUNT_ID."""
        env_example = REPO_ROOT / ".env.example"
        content = env_example.read_text()
        
        # Should contain AWS_ACCOUNT_ID
        assert "AWS_ACCOUNT_ID" in content
        
        # Should NOT contain hardcoded value
        assert "464813693153" not in content

    def test_queue_url_format_with_account_id(self):
        """Test that queue URLs are formatted correctly with variables."""
        script_path = REPO_ROOT / "scripts" / "run_congress_pipeline.py"
        content = script_path.read_text()
        
        # Should use f-string with AWS_ACCOUNT_ID for queue URLs
        assert "{AWS_ACCOUNT_ID}" in content or "AWS_ACCOUNT_ID}" in content
        assert "{AWS_REGION}" in content or "AWS_REGION}" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
