import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ingestion/lib')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts')))

from metadata_tagger import tag_bronze_pdf, calculate_quality_score
from bulk_tag_bronze_pdfs import process_file

class TestMetadataTagging:
    
    def test_calculate_quality_score(self):
        # Perfect score
        assert calculate_quality_score(True, 10, '2025-01-01', 'Smith, John') == 1.0
        
        # No text layer (-0.5)
        assert calculate_quality_score(False, 10, '2025-01-01', 'Smith, John') == 0.5
        
        # High page count (30-100 -> +0.1 instead of +0.2) -> -0.1
        assert calculate_quality_score(True, 50, '2025-01-01', 'Smith, John') == 0.9
        
        # Very high page count (>100 -> +0.0) -> -0.2
        assert calculate_quality_score(True, 150, '2025-01-01', 'Smith, John') == 0.8
        
        # Old date (<2020 -> +0.0) -> -0.15
        assert calculate_quality_score(True, 10, '2019-01-01', 'Smith, John') == 0.85
        
        # Unknown member -> -0.15
        assert calculate_quality_score(True, 10, '2025-01-01', 'Unknown') == 0.85

    @patch('metadata_tagger.logger')
    def test_tag_bronze_pdf(self, mock_logger):
        mock_s3 = MagicMock()
        mock_s3.head_object.return_value = {'Metadata': {'old': 'value'}, 'ContentType': 'application/pdf'}
        
        success = tag_bronze_pdf(mock_s3, 'bucket', 'key', {'new': 'meta'})
        
        assert success is True
        mock_s3.copy_object.assert_called_with(
            Bucket='bucket',
            Key='key',
            CopySource={'Bucket': 'bucket', 'Key': 'key'},
            Metadata={'old': 'value', 'new': 'meta'},
            MetadataDirective='REPLACE',
            ContentType='application/pdf'
        )

    @patch('bulk_tag_bronze_pdfs.analyze_pdf')
    @patch('bulk_tag_bronze_pdfs.tag_bronze_pdf')
    def test_process_file(self, mock_tag, mock_analyze):
        mock_s3 = MagicMock()
        mock_analyze.return_value = (10, True)
        mock_tag.return_value = True
        
        metadata_map = {
            '123': {
                'filing_type': 'P',
                'member_name': 'Smith',
                'state_district': 'CA-01',
                'filing_date': '2025-01-01'
            }
        }
        
        process_file(mock_s3, 'path/123.pdf', metadata_map, dry_run=False)
        
        mock_tag.assert_called()
        call_args = mock_tag.call_args
        tags = call_args[0][3]
        
        assert tags['filing_type'] == 'P'
        assert tags['quality_score'] == '1.0'
