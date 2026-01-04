"""
Unit tests for version utilities (STORY-055)

Tests version comparison, registry management, and quality metrics tracking.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import json

# Import modules to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../ingestion'))

from lib.version_utils import (
    compare_versions,
    is_newer_version,
    parse_version,
    ExtractionVersionRegistry
)
from lib.version_comparison import (
    QualityMetricsCalculator,
    VersionComparison,
    generate_comparison_report
)


class TestVersionComparison:
    """Test version comparison functions."""
    
    def test_compare_versions_newer(self):
        """Test that newer version is detected correctly."""
        assert compare_versions("1.1.0", "1.0.0") == 1
        assert compare_versions("2.0.0", "1.9.9") == 1
        assert compare_versions("1.0.1", "1.0.0") == 1
    
    def test_compare_versions_older(self):
        """Test that older version is detected correctly."""
        assert compare_versions("1.0.0", "1.1.0") == -1
        assert compare_versions("1.9.9", "2.0.0") == -1
        assert compare_versions("1.0.0", "1.0.1") == -1
    
    def test_compare_versions_equal(self):
        """Test that equal versions are detected correctly."""
        assert compare_versions("1.0.0", "1.0.0") == 0
        assert compare_versions("2.5.3", "2.5.3") == 0
    
    def test_compare_versions_different_lengths(self):
        """Test version comparison with different segment counts."""
        assert compare_versions("1.0", "1.0.0") == 0
        assert compare_versions("1.0.1", "1.0") == 1
        assert compare_versions("1.0", "1.0.1") == -1
    
    def test_is_newer_version(self):
        """Test is_newer_version helper function."""
        assert is_newer_version("1.1.0", "1.0.0") is True
        assert is_newer_version("1.0.0", "1.1.0") is False
        assert is_newer_version("1.0.0", "1.0.0") is False
    
    def test_parse_version(self):
        """Test version parsing into components."""
        assert parse_version("1.2.3") == (1, 2, 3)
        assert parse_version("2.0.0") == (2, 0, 0)
        assert parse_version("1.0") == (1, 0, 0)
        assert parse_version("3") == (3, 0, 0)
    
    def test_invalid_version_format(self):
        """Test that invalid version format raises error."""
        with pytest.raises(ValueError):
            compare_versions("1.0.0", "invalid")
        
        with pytest.raises(ValueError):
            parse_version("not.a.version")


class TestExtractionVersionRegistry:
    """Test ExtractionVersionRegistry class."""
    
    @pytest.fixture
    def mock_dynamodb(self):
        """Create mock DynamoDB client."""
        return MagicMock()
    
    @pytest.fixture
    def registry(self, mock_dynamodb):
        """Create registry with mock client."""
        return ExtractionVersionRegistry("test-table", mock_dynamodb)
    
    def test_register_version(self, registry, mock_dynamodb):
        """Test registering a new version."""
        registry.register_version(
            extractor_class="PTRExtractor",
            extractor_version="1.1.0",
            changelog="Improved amount parsing",
            is_production=False
        )
        
        # Verify put_item was called
        mock_dynamodb.put_item.assert_called_once()
        call_args = mock_dynamodb.put_item.call_args[1]
        
        assert call_args['TableName'] == "test-table"
        assert call_args['Item']['extractor_class']['S'] == "PTRExtractor"
        assert call_args['Item']['extractor_version']['S'] == "1.1.0"
        assert call_args['Item']['is_production']['BOOL'] is False
    
    def test_get_version_exists(self, registry, mock_dynamodb):
        """Test retrieving existing version."""
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'extractor_class': {'S': 'PTRExtractor'},
                'extractor_version': {'S': '1.0.0'},
                'is_production': {'BOOL': True},
                'deployment_date': {'S': '2025-01-01T00:00:00Z'}
            }
        }
        
        result = registry.get_version("PTRExtractor", "1.0.0")
        
        assert result is not None
        assert result['extractor_class'] == 'PTRExtractor'
        assert result['extractor_version'] == '1.0.0'
        assert result['is_production'] is True
    
    def test_get_version_not_exists(self, registry, mock_dynamodb):
        """Test retrieving non-existent version."""
        mock_dynamodb.get_item.return_value = {}
        
        result = registry.get_version("PTRExtractor", "9.9.9")
        
        assert result is None
    
    def test_get_production_version(self, registry, mock_dynamodb):
        """Test getting current production version."""
        mock_dynamodb.query.return_value = {
            'Items': [
                {
                    'extractor_class': {'S': 'PTRExtractor'},
                    'extractor_version': {'S': '1.0.0'},
                    'is_production': {'BOOL': True}
                }
            ]
        }
        
        result = registry.get_production_version("PTRExtractor")
        
        assert result is not None
        assert result['extractor_version'] == '1.0.0'
        assert result['is_production'] is True
    
    def test_promote_to_production(self, registry, mock_dynamodb):
        """Test promoting version to production."""
        # Mock get_production_version to return current production
        mock_dynamodb.query.return_value = {
            'Items': [
                {
                    'extractor_class': {'S': 'PTRExtractor'},
                    'extractor_version': {'S': '1.0.0'},
                    'is_production': {'BOOL': True}
                }
            ]
        }
        
        # Promote new version
        registry.promote_to_production("PTRExtractor", "1.1.0")
        
        # Verify update_item was called twice (demote old, promote new)
        assert mock_dynamodb.update_item.call_count == 2
    
    def test_rollback_version(self, registry, mock_dynamodb):
        """Test rolling back to previous version."""
        mock_dynamodb.query.return_value = {
            'Items': [
                {
                    'extractor_class': {'S': 'PTRExtractor'},
                    'extractor_version': {'S': '1.1.0'},
                    'is_production': {'BOOL': True}
                }
            ]
        }
        
        registry.rollback_version("PTRExtractor", "1.0.0")
        
        # Should call update_item to demote current and promote target
        assert mock_dynamodb.update_item.call_count == 2


class TestQualityMetricsCalculator:
    """Test QualityMetricsCalculator class."""
    
    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return QualityMetricsCalculator()
    
    def test_calculate_metrics_empty(self, calculator):
        """Test calculating metrics from empty results."""
        metrics = calculator.calculate_metrics([])
        
        assert metrics['sample_size'] == 0
        assert metrics['avg_confidence_score'] == 0.0
        assert metrics['extraction_success_rate'] == 0.0
    
    def test_calculate_metrics_successful(self, calculator):
        """Test calculating metrics from successful extractions."""
        results = [
            {
                'status': 'success',
                'extraction_metadata': {
                    'confidence_score': 0.9,
                    'field_confidence': {
                        'transaction_date': 0.95,
                        'amount_low': 0.85
                    }
                }
            },
            {
                'status': 'success',
                'extraction_metadata': {
                    'confidence_score': 0.8,
                    'field_confidence': {
                        'transaction_date': 0.90,
                        'amount_low': 0.80
                    }
                }
            }
        ]
        
        metrics = calculator.calculate_metrics(results)
        
        assert metrics['sample_size'] == 2
        assert metrics['avg_confidence_score'] == 0.85
        assert metrics['extraction_success_rate'] == 1.0
        assert metrics['successful_extractions'] == 2
        assert metrics['failed_extractions'] == 0
        
        # Check field-level metrics
        assert metrics['field_confidence']['transaction_date'] == 0.925
        assert metrics['field_confidence']['amount_low'] == 0.825
    
    def test_calculate_metrics_mixed(self, calculator):
        """Test calculating metrics with mixed success/failure."""
        results = [
            {
                'status': 'success',
                'extraction_metadata': {'confidence_score': 0.9}
            },
            {
                'status': 'failed',
                'error': 'Extraction failed'
            }
        ]
        
        metrics = calculator.calculate_metrics(results)
        
        assert metrics['sample_size'] == 2
        assert metrics['extraction_success_rate'] == 0.5
        assert metrics['successful_extractions'] == 1
        assert metrics['failed_extractions'] == 1


class TestVersionComparison:
    """Test VersionComparison class."""
    
    def test_generate_report_improvements(self):
        """Test generating comparison report with improvements."""
        baseline = {
            'avg_confidence_score': 0.87,
            'field_confidence': {
                'transaction_date': 0.96,
                'amount_low': 0.87
            },
            'extraction_success_rate': 0.95,
            'successful_extractions': 100
        }
        
        new = {
            'avg_confidence_score': 0.94,
            'field_confidence': {
                'transaction_date': 0.98,
                'amount_low': 0.94
            },
            'extraction_success_rate': 0.97,
            'successful_extractions': 105
        }
        
        comparison = VersionComparison(baseline, new)
        report = comparison.generate_report("1.0.0", "1.1.0")
        
        assert report['baseline_version'] == "1.0.0"
        assert report['new_version'] == "1.1.0"
        assert report['new_extractions'] == 5
        
        # Check improvements
        improvements = report['quality_improvements']
        assert improvements['avg_confidence_score']['old'] == 0.87
        assert improvements['avg_confidence_score']['new'] == 0.94
        assert '+' in improvements['avg_confidence_score']['delta']
        
        # Should recommend promotion
        assert report['recommendation'] == 'PROMOTE'
        assert len(report['regressions']) == 0
    
    def test_generate_report_regressions(self):
        """Test generating comparison report with regressions."""
        baseline = {
            'avg_confidence_score': 0.95,
            'field_confidence': {
                'transaction_date': 0.98
            },
            'extraction_success_rate': 0.97,
            'successful_extractions': 100
        }
        
        new = {
            'avg_confidence_score': 0.85,  # Regression
            'field_confidence': {
                'transaction_date': 0.90  # Regression
            },
            'extraction_success_rate': 0.95,
            'successful_extractions': 95
        }
        
        comparison = VersionComparison(baseline, new)
        report = comparison.generate_report("1.0.0", "1.1.0")
        
        # Should detect regressions
        assert len(report['regressions']) > 0
        assert report['recommendation'] == 'REVIEW_REQUIRED'
        
        # Check regression details
        regression_fields = [r['field'] for r in report['regressions']]
        assert 'avg_confidence_score' in regression_fields
        assert 'transaction_date' in regression_fields
    
    def test_generate_report_neutral(self):
        """Test generating comparison report with no significant changes."""
        baseline = {
            'avg_confidence_score': 0.90,
            'field_confidence': {},
            'extraction_success_rate': 0.95,
            'successful_extractions': 100
        }
        
        new = {
            'avg_confidence_score': 0.905,  # Very minor improvement
            'field_confidence': {},
            'extraction_success_rate': 0.95,
            'successful_extractions': 100
        }
        
        comparison = VersionComparison(baseline, new)
        report = comparison.generate_report("1.0.0", "1.0.1")
        
        # Should be neutral (no significant improvements or regressions)
        assert report['recommendation'] == 'NEUTRAL'
        assert len(report['regressions']) == 0


class TestGenerateComparisonReport:
    """Test generate_comparison_report convenience function."""
    
    def test_generate_comparison_report_function(self):
        """Test convenience function for generating comparison report."""
        baseline = {
            'avg_confidence_score': 0.80,
            'field_confidence': {},
            'extraction_success_rate': 0.90,
            'successful_extractions': 100
        }
        
        new = {
            'avg_confidence_score': 0.90,
            'field_confidence': {},
            'extraction_success_rate': 0.95,
            'successful_extractions': 110
        }
        
        report = generate_comparison_report(baseline, new, "1.0.0", "1.1.0")
        
        assert report['baseline_version'] == "1.0.0"
        assert report['new_version'] == "1.1.0"
        assert report['recommendation'] in ['PROMOTE', 'NEUTRAL', 'REVIEW_REQUIRED']
        assert 'comparison_timestamp' in report


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
