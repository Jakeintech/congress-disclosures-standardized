"""
Integration test for reprocessing Lambda (STORY-055)

Tests end-to-end reprocessing workflow with real AWS services.
"""

import pytest
import json
import boto3
import os
from datetime import datetime
from typing import Dict, Any

# Skip integration tests if AWS credentials not available
pytestmark = pytest.mark.skipif(
    not os.environ.get('AWS_REGION'),
    reason="AWS credentials not configured"
)


@pytest.fixture
def s3_client():
    """Get S3 client."""
    return boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'us-east-1'))


@pytest.fixture
def lambda_client():
    """Get Lambda client."""
    return boto3.client('lambda', region_name=os.environ.get('AWS_REGION', 'us-east-1'))


@pytest.fixture
def dynamodb_client():
    """Get DynamoDB client."""
    return boto3.client('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))


@pytest.fixture
def test_bucket():
    """Get test S3 bucket name."""
    return os.environ.get('S3_BUCKET_NAME', 'congress-disclosures-standardized')


@pytest.fixture
def versions_table():
    """Get extraction versions table name."""
    return os.environ.get('DYNAMODB_VERSIONS_TABLE', 'congress-disclosures-extraction-versions')


class TestReprocessingE2E:
    """End-to-end integration tests for reprocessing."""
    
    def test_dry_run_reprocessing(self, lambda_client):
        """Test dry run mode to validate without processing."""
        payload = {
            'filing_type': 'type_p',
            'year_range': [2024, 2024],
            'extractor_version': '1.1.0',
            'dry_run': True
        }
        
        response = lambda_client.invoke(
            FunctionName='congress-disclosures-reprocess-filings',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        assert result['status'] == 'dry_run'
        assert 'pdfs_found' in result
        assert result['filing_type'] == 'type_p'
        assert result['extractor_version'] == '1.1.0'
    
    def test_reprocess_small_batch(self, lambda_client, s3_client, test_bucket):
        """Test reprocessing a small batch of PDFs."""
        # First, verify we have some Bronze PDFs to reprocess
        prefix = 'bronze/house/financial/year=2024/filing_type=type_p/pdfs/'
        
        response = s3_client.list_objects_v2(
            Bucket=test_bucket,
            Prefix=prefix,
            MaxKeys=5
        )
        
        if not response.get('Contents'):
            pytest.skip("No Bronze PDFs found for testing")
        
        # Invoke reprocessing with small batch
        payload = {
            'filing_type': 'type_p',
            'year_range': [2024, 2024],
            'extractor_version': '1.1.0-test',
            'comparison_mode': True,
            'batch_size': 5,
            'overwrite': True  # Force reprocessing
        }
        
        response = lambda_client.invoke(
            FunctionName='congress-disclosures-reprocess-filings',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        # Verify response structure
        assert result['status'] == 'completed'
        assert 'summary' in result
        assert result['summary']['pdfs_reprocessed'] > 0
        
        # Verify new extractions were created
        new_prefix = 'silver/house/financial/objects/year=2024/filing_type=type_p/extractor_version=1.1.0-test/'
        
        response = s3_client.list_objects_v2(
            Bucket=test_bucket,
            Prefix=new_prefix,
            MaxKeys=1
        )
        
        assert response.get('KeyCount', 0) > 0, "No new extractions found"
    
    def test_version_registry_updated(self, lambda_client, dynamodb_client, versions_table):
        """Test that version registry is updated after reprocessing."""
        # Reprocess with new version
        payload = {
            'filing_type': 'type_p',
            'year_range': [2024, 2024],
            'extractor_version': '1.2.0-test',
            'comparison_mode': True,
            'batch_size': 2,
            'overwrite': True
        }
        
        response = lambda_client.invoke(
            FunctionName='congress-disclosures-reprocess-filings',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        assert result['status'] == 'completed'
        
        # Check DynamoDB for version entry
        response = dynamodb_client.get_item(
            TableName=versions_table,
            Key={
                'extractor_class': {'S': 'PTRExtractor'},
                'extractor_version': {'S': '1.2.0-test'}
            }
        )
        
        assert 'Item' in response, "Version not registered in DynamoDB"
        
        item = response['Item']
        assert item['extractor_class']['S'] == 'PTRExtractor'
        assert item['extractor_version']['S'] == '1.2.0-test'
        assert item['is_production']['BOOL'] is False  # Should not auto-promote
    
    def test_comparison_report_generated(self, lambda_client, s3_client, test_bucket):
        """Test that comparison report is generated and saved to S3."""
        payload = {
            'filing_type': 'type_p',
            'year_range': [2024, 2024],
            'extractor_version': '1.3.0-test',
            'comparison_mode': True,
            'batch_size': 3,
            'overwrite': True
        }
        
        response = lambda_client.invoke(
            FunctionName='congress-disclosures-reprocess-filings',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        assert result['status'] == 'completed'
        
        # Verify comparison report exists
        if result.get('comparison'):
            comparison = result['comparison']
            
            assert 'baseline_version' in comparison
            assert 'new_version' in comparison
            assert 'quality_improvements' in comparison
            assert 'recommendation' in comparison
            
            # Check S3 for report
            report_path = result['s3_paths'].get('comparison_report')
            if report_path:
                # Extract bucket and key from s3:// URL
                key = report_path.replace(f's3://{test_bucket}/', '')
                
                response = s3_client.head_object(Bucket=test_bucket, Key=key)
                assert response['ContentType'] == 'application/json'


class TestVersionPromotion:
    """Test version promotion and rollback."""
    
    def test_promote_version_to_production(self, dynamodb_client, versions_table):
        """Test promoting a version to production."""
        # First, register a test version
        dynamodb_client.put_item(
            TableName=versions_table,
            Item={
                'extractor_class': {'S': 'PTRExtractor'},
                'extractor_version': {'S': '1.5.0-test'},
                'deployment_date': {'S': datetime.utcnow().isoformat() + 'Z'},
                'is_production': {'BOOL': False},
                'updated_at': {'S': datetime.utcnow().isoformat() + 'Z'}
            }
        )
        
        # Import promotion utility
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../ingestion'))
        from lib.version_utils import ExtractionVersionRegistry
        
        registry = ExtractionVersionRegistry(versions_table, dynamodb_client)
        
        # Promote version
        registry.promote_to_production('PTRExtractor', '1.5.0-test')
        
        # Verify it's now production
        version_info = registry.get_version('PTRExtractor', '1.5.0-test')
        assert version_info['is_production'] is True
    
    def test_rollback_version(self, dynamodb_client, versions_table):
        """Test rolling back to a previous version."""
        # Setup: Create two versions
        dynamodb_client.put_item(
            TableName=versions_table,
            Item={
                'extractor_class': {'S': 'PTRExtractor'},
                'extractor_version': {'S': '1.6.0-test'},
                'deployment_date': {'S': datetime.utcnow().isoformat() + 'Z'},
                'is_production': {'BOOL': True},
                'updated_at': {'S': datetime.utcnow().isoformat() + 'Z'}
            }
        )
        
        dynamodb_client.put_item(
            TableName=versions_table,
            Item={
                'extractor_class': {'S': 'PTRExtractor'},
                'extractor_version': {'S': '1.5.0-test'},
                'deployment_date': {'S': datetime.utcnow().isoformat() + 'Z'},
                'is_production': {'BOOL': False},
                'updated_at': {'S': datetime.utcnow().isoformat() + 'Z'}
            }
        )
        
        # Import rollback utility
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../ingestion'))
        from lib.version_utils import ExtractionVersionRegistry
        
        registry = ExtractionVersionRegistry(versions_table, dynamodb_client)
        
        # Rollback to 1.5.0-test
        registry.rollback_version('PTRExtractor', '1.5.0-test')
        
        # Verify 1.5.0-test is now production
        old_version = registry.get_version('PTRExtractor', '1.5.0-test')
        assert old_version['is_production'] is True
        
        # Verify 1.6.0-test is no longer production
        new_version = registry.get_version('PTRExtractor', '1.6.0-test')
        assert new_version['is_production'] is False


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
