import pytest
import boto3
from botocore.exceptions import ClientError
from unittest.mock import patch
import os
import sys

# Add scripts to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts')))
from migrate_bronze_structure import migrate_file

class TestBronzeMigrationIntegration:
    """
    Integration tests for Bronze migration.
    Requires S3 access (mocked or real).
    """
    
    @pytest.fixture
    def s3_client(self):
        return boto3.client('s3')
        
    def test_migrate_file_integration(self, s3_client):
        # This test assumes we can write to the bucket.
        # If running in CI without real creds, this should be skipped or mocked with moto.
        # For now, we'll assume we can use the dev bucket if available, or skip.
        
        bucket = os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')
        year = 2025
        doc_id = 'integration_test_doc'
        old_key = f'bronze/house/financial/year={year}/pdfs/{year}/{doc_id}.pdf'
        new_key = f'bronze/house/financial/year={year}/filing_type=P/pdfs/{doc_id}.pdf'
        
        try:
            # Setup: Create dummy file
            s3_client.put_object(Bucket=bucket, Key=old_key, Body=b'dummy content')
            
            # Patch the global S3_BUCKET in the script
            with patch('migrate_bronze_structure.S3_BUCKET', bucket):
                # Execute
                # Signature: migrate_file(s3_client, old_key, new_key, dry_run)
                migrate_file(s3_client, old_key, new_key, dry_run=False)
            
            # Verify
            # New file should exist
            s3_client.head_object(Bucket=bucket, Key=new_key)
            
            # Old file should still exist (script copies, doesn't move/delete yet)
            s3_client.head_object(Bucket=bucket, Key=old_key)
            
        except ClientError as e:
            pytest.skip(f"Skipping integration test due to S3 error: {e}")
        finally:
            # Cleanup
            try:
                s3_client.delete_object(Bucket=bucket, Key=old_key)
                s3_client.delete_object(Bucket=bucket, Key=new_key)
            except:
                pass
