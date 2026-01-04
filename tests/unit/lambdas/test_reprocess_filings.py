"""
Unit tests for reprocess_filings Lambda (STORY-055)

Tests selective reprocessing logic, batch processing, and comparison reporting.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
import json
import sys
import os

# Add ingestion directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../ingestion'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../ingestion/lambdas/reprocess_filings'))

# Mock environment variables before importing handler
os.environ['S3_BUCKET_NAME'] = 'test-bucket'
os.environ['DYNAMODB_VERSIONS_TABLE'] = 'test-versions-table'
os.environ['SNS_ALERTS_ARN'] = 'arn:aws:sns:us-east-1:123456789012:test-topic'

from handler import (
    validate_reprocessing_request,
    get_bronze_pdfs,
    process_batch,
    construct_versioned_path,
    get_extractor_class_name,
    s3_object_exists
)


class TestValidateReprocessingRequest:
    """Test request validation."""
    
    def test_valid_request(self):
        """Test that valid request passes validation."""
        event = {
            'filing_type': 'type_p',
            'year_range': [2024, 2025],
            'extractor_version': '1.1.0'
        }
        
        # Should not raise exception
        validate_reprocessing_request(event)
    
    def test_missing_required_field(self):
        """Test that missing required field raises error."""
        event = {
            'year_range': [2024, 2025],
            'extractor_version': '1.1.0'
        }
        
        with pytest.raises(ValueError, match="Missing required field"):
            validate_reprocessing_request(event)
    
    def test_unsupported_filing_type(self):
        """Test that unsupported filing type raises error."""
        event = {
            'filing_type': 'type_z',  # Invalid
            'year_range': [2024, 2025],
            'extractor_version': '1.1.0'
        }
        
        with pytest.raises(ValueError, match="Unsupported filing type"):
            validate_reprocessing_request(event)
    
    def test_invalid_year_range(self):
        """Test that invalid year range raises error."""
        event = {
            'filing_type': 'type_p',
            'year_range': [2025, 2024],  # End before start
            'extractor_version': '1.1.0'
        }
        
        with pytest.raises(ValueError, match="Invalid year range"):
            validate_reprocessing_request(event)
    
    def test_invalid_version_format(self):
        """Test that invalid version format raises error."""
        event = {
            'filing_type': 'type_p',
            'year_range': [2024, 2025],
            'extractor_version': 'not-a-version'
        }
        
        with pytest.raises(ValueError, match="Invalid extractor_version"):
            validate_reprocessing_request(event)


class TestGetBronzePdfs:
    """Test Bronze PDF listing."""
    
    @patch('handler.s3')
    def test_get_bronze_pdfs_single_year(self, mock_s3):
        """Test getting PDFs for single year."""
        # Mock S3 paginator
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        
        mock_paginator.paginate.return_value = [
            {
                'Contents': [
                    {'Key': 'bronze/house/financial/year=2024/filing_type=type_p/pdfs/10063228.pdf'},
                    {'Key': 'bronze/house/financial/year=2024/filing_type=type_p/pdfs/10074539.pdf'}
                ]
            }
        ]
        
        pdfs = get_bronze_pdfs('type_p', [2024, 2024])
        
        assert len(pdfs) == 2
        assert pdfs[0]['doc_id'] == '10063228'
        assert pdfs[0]['year'] == 2024
        assert pdfs[0]['filing_type'] == 'type_p'
        assert pdfs[1]['doc_id'] == '10074539'
    
    @patch('handler.s3')
    def test_get_bronze_pdfs_year_range(self, mock_s3):
        """Test getting PDFs for year range."""
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        
        def paginate_side_effect(Bucket, Prefix):
            if 'year=2024' in Prefix:
                return [{'Contents': [
                    {'Key': 'bronze/house/financial/year=2024/filing_type=type_p/pdfs/10001.pdf'}
                ]}]
            elif 'year=2025' in Prefix:
                return [{'Contents': [
                    {'Key': 'bronze/house/financial/year=2025/filing_type=type_p/pdfs/10002.pdf'}
                ]}]
            return [{}]
        
        mock_paginator.paginate.side_effect = paginate_side_effect
        
        pdfs = get_bronze_pdfs('type_p', [2024, 2025])
        
        assert len(pdfs) == 2
        assert any(pdf['year'] == 2024 for pdf in pdfs)
        assert any(pdf['year'] == 2025 for pdf in pdfs)
    
    @patch('handler.s3')
    def test_get_bronze_pdfs_empty(self, mock_s3):
        """Test getting PDFs when none exist."""
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{}]
        
        pdfs = get_bronze_pdfs('type_p', [2024, 2024])
        
        assert len(pdfs) == 0


class TestProcessBatch:
    """Test batch processing."""
    
    @patch('handler.s3')
    @patch('handler.s3_object_exists')
    @patch('handler.download_pdf')
    @patch('handler.PTRExtractor')
    def test_process_batch_success(self, mock_extractor_class, mock_download, mock_exists, mock_s3):
        """Test successful batch processing."""
        # Setup
        mock_exists.return_value = False  # No existing extraction
        mock_download.return_value = b'PDF content'
        
        # Mock extractor instance
        mock_extractor = MagicMock()
        mock_extractor_class.return_value = mock_extractor
        mock_extractor.extract_with_fallback.return_value = {
            'extraction_metadata': {
                'confidence_score': 0.92,
                'field_confidence': {'transaction_date': 0.95}
            }
        }
        
        pdfs = [
            {
                'doc_id': '10063228',
                'year': 2024,
                'filing_type': 'type_p',
                's3_key': 'bronze/year=2024/10063228.pdf'
            }
        ]
        
        results = process_batch(pdfs, 'type_p', '1.1.0', overwrite=False)
        
        assert len(results) == 1
        assert results[0]['status'] == 'success'
        assert results[0]['doc_id'] == '10063228'
        assert 'extraction_metadata' in results[0]
        
        # Verify S3 put was called
        mock_s3.put_object.assert_called_once()
    
    @patch('handler.s3')
    @patch('handler.s3_object_exists')
    def test_process_batch_skip_existing(self, mock_exists, mock_s3):
        """Test that existing extractions are skipped."""
        mock_exists.return_value = True  # Extraction exists
        
        pdfs = [
            {
                'doc_id': '10063228',
                'year': 2024,
                'filing_type': 'type_p',
                's3_key': 'bronze/year=2024/10063228.pdf'
            }
        ]
        
        results = process_batch(pdfs, 'type_p', '1.1.0', overwrite=False)
        
        # Should return empty (skipped)
        assert len(results) == 0
        
        # S3 put should not be called
        mock_s3.put_object.assert_not_called()
    
    @patch('handler.s3')
    @patch('handler.s3_object_exists')
    @patch('handler.download_pdf')
    def test_process_batch_extraction_failure(self, mock_download, mock_exists, mock_s3):
        """Test handling of extraction failures."""
        mock_exists.return_value = False
        mock_download.side_effect = Exception("Download failed")
        
        pdfs = [
            {
                'doc_id': '10063228',
                'year': 2024,
                'filing_type': 'type_p',
                's3_key': 'bronze/year=2024/10063228.pdf'
            }
        ]
        
        results = process_batch(pdfs, 'type_p', '1.1.0', overwrite=False)
        
        assert len(results) == 1
        assert results[0]['status'] == 'failed'
        assert 'error' in results[0]


class TestConstructVersionedPath:
    """Test versioned path construction."""
    
    def test_construct_versioned_path(self):
        """Test S3 path construction with versioning."""
        path = construct_versioned_path(
            filing_type='type_p',
            extractor_version='1.1.0',
            year=2024,
            doc_id='10063228'
        )
        
        expected = "silver/house/financial/objects/year=2024/filing_type=type_p/extractor_version=1.1.0/doc_id=10063228/extraction.json"
        assert path == expected


class TestGetExtractorClassName:
    """Test extractor class name lookup."""
    
    def test_get_extractor_class_name_valid(self):
        """Test getting extractor class name for valid filing type."""
        assert get_extractor_class_name('type_p') == 'PTRExtractor'
        assert get_extractor_class_name('type_a') == 'TypeABAnnualExtractor'
        assert get_extractor_class_name('type_t') == 'TypeTTerminationExtractor'
    
    def test_get_extractor_class_name_invalid(self):
        """Test getting extractor class name for invalid filing type."""
        assert get_extractor_class_name('type_z') == 'UnknownExtractor'


class TestS3ObjectExists:
    """Test S3 object existence check."""
    
    @patch('handler.s3')
    def test_s3_object_exists_true(self, mock_s3):
        """Test checking existence of existing object."""
        mock_s3.head_object.return_value = {}
        
        exists = s3_object_exists('test-bucket', 'test-key')
        
        assert exists is True
    
    @patch('handler.s3')
    def test_s3_object_exists_false(self, mock_s3):
        """Test checking existence of non-existent object."""
        from botocore.exceptions import ClientError
        
        mock_s3.head_object.side_effect = ClientError(
            {'Error': {'Code': '404'}},
            'HeadObject'
        )
        
        exists = s3_object_exists('test-bucket', 'test-key')
        
        assert exists is False


class TestLambdaHandler:
    """Test Lambda handler end-to-end."""
    
    @patch('handler.s3')
    @patch('handler.dynamodb')
    @patch('handler.ExtractionVersionRegistry')
    @patch('handler.get_bronze_pdfs')
    @patch('handler.process_batch')
    @patch('handler.QualityMetricsCalculator')
    def test_lambda_handler_dry_run(
        self, mock_calculator, mock_process, mock_get_pdfs,
        mock_registry_class, mock_dynamodb, mock_s3
    ):
        """Test Lambda handler in dry run mode."""
        from handler import lambda_handler
        
        event = {
            'filing_type': 'type_p',
            'year_range': [2024, 2025],
            'extractor_version': '1.1.0',
            'dry_run': True
        }
        
        mock_get_pdfs.return_value = [
            {'doc_id': '10001', 'year': 2024},
            {'doc_id': '10002', 'year': 2024}
        ]
        
        context = MagicMock()
        result = lambda_handler(event, context)
        
        assert result['status'] == 'dry_run'
        assert result['pdfs_found'] == 2
        
        # Process should not be called in dry run
        mock_process.assert_not_called()
    
    @patch('handler.s3')
    @patch('handler.dynamodb')
    @patch('handler.ExtractionVersionRegistry')
    @patch('handler.get_bronze_pdfs')
    @patch('handler.process_batch')
    @patch('handler.QualityMetricsCalculator')
    def test_lambda_handler_invalid_request(
        self, mock_calculator, mock_process, mock_get_pdfs,
        mock_registry_class, mock_dynamodb, mock_s3
    ):
        """Test Lambda handler with invalid request."""
        from handler import lambda_handler
        
        event = {
            'filing_type': 'type_p',
            # Missing year_range and extractor_version
        }
        
        context = MagicMock()
        result = lambda_handler(event, context)
        
        assert result['status'] == 'error'
        assert 'error' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
