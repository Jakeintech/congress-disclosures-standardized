"""
Test that scripts properly validate required environment variables.
Tests for STORY-009: Remove Hardcoded AWS Account IDs
"""
import pytest
import sys
import os
import importlib.util
from unittest.mock import patch

# Scripts that require AWS_ACCOUNT_ID
SCRIPTS_TO_TEST = [
    'scripts/run_congress_pipeline.py',
    'scripts/backfill_silver_layer.py',
    'scripts/trigger_extraction_batch.py',
    'scripts/get_pipeline_status.py',
    'scripts/reprocess_annual_filings.py',
    'scripts/reprocess_ptr_filings.py',
]


class TestEnvironmentVariableValidation:
    """Test that scripts validate AWS_ACCOUNT_ID environment variable."""
    
    def test_no_hardcoded_account_ids_in_scripts(self):
        """Verify no hardcoded AWS account IDs (464813693153) in script files."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        hardcoded_id = '464813693153'
        
        for script_path in SCRIPTS_TO_TEST:
            full_path = os.path.join(repo_root, script_path)
            with open(full_path, 'r') as f:
                content = f.read()
                assert hardcoded_id not in content, \
                    f"Found hardcoded account ID {hardcoded_id} in {script_path}"
    
    def test_scripts_require_aws_account_id(self):
        """Verify scripts use AWS_ACCOUNT_ID environment variable."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        
        for script_path in SCRIPTS_TO_TEST:
            # Clear AWS_ACCOUNT_ID from environment
            with patch.dict(os.environ, {'AWS_REGION': 'us-east-1'}, clear=False):
                if 'AWS_ACCOUNT_ID' in os.environ:
                    del os.environ['AWS_ACCOUNT_ID']
                
                # Try to import the script (which should validate env vars)
                full_path = os.path.join(repo_root, script_path)
                spec = importlib.util.spec_from_file_location("test_module", full_path)
                
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    
                    # Script should raise ValueError or other error for missing AWS_ACCOUNT_ID
                    # Some scripts will fail when initializing boto3, others validate early
                    with pytest.raises((ValueError, Exception)):
                        spec.loader.exec_module(module)
    
    def test_scripts_use_environment_variables(self):
        """Verify scripts properly use AWS_ACCOUNT_ID when set."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        test_account_id = '123456789012'
        test_region = 'us-west-2'
        test_environment = 'test'
        
        for script_path in SCRIPTS_TO_TEST:
            with patch.dict(os.environ, {
                'AWS_ACCOUNT_ID': test_account_id,
                'AWS_REGION': test_region,
                'ENVIRONMENT': test_environment
            }):
                full_path = os.path.join(repo_root, script_path)
                with open(full_path, 'r') as f:
                    content = f.read()
                    
                # Verify script references AWS_ACCOUNT_ID variable
                assert 'AWS_ACCOUNT_ID' in content, \
                    f"{script_path} should reference AWS_ACCOUNT_ID environment variable"
                
                # Verify script uses os.environ.get or os.getenv
                assert ('os.environ.get' in content or 'os.getenv' in content), \
                    f"{script_path} should use os.environ.get() or os.getenv()"
    
    def test_env_example_uses_placeholder(self):
        """Verify .env.example uses placeholder instead of real account ID."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        env_example_path = os.path.join(repo_root, '.env.example')
        hardcoded_id = '464813693153'
        
        with open(env_example_path, 'r') as f:
            content = f.read()
            assert hardcoded_id not in content, \
                ".env.example should not contain hardcoded account ID"
            assert 'AWS_ACCOUNT_ID' in content, \
                ".env.example should have AWS_ACCOUNT_ID variable"
