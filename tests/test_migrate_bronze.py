import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add scripts directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))
from migrate_bronze_structure import get_filing_type_map, migrate_file

class TestBronzeMigration:
    
    @patch('boto3.client')
    def test_get_filing_type_map(self, mock_boto):
        # Mock S3 response for XML
        mock_s3 = MagicMock()
        xml_content = """
        <FinancialDisclosure>
            <Member>
                <DocID>1001</DocID>
                <FilingType>P</FilingType>
            </Member>
            <Member>
                <DocID>1002</DocID>
                <FilingType>A</FilingType>
            </Member>
        </FinancialDisclosure>
        """
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: xml_content.encode('utf-8'))
        }
        
        mapping = get_filing_type_map(2025, mock_s3)
        
        assert mapping['1001'] == 'P'
        assert mapping['1002'] == 'A'
        mock_s3.get_object.assert_called_with(
            Bucket='congress-disclosures-standardized',
            Key='bronze/house/financial/year=2025/index/2025FD.xml'
        )

    def test_migrate_file_dry_run(self):
        mock_s3 = MagicMock()
        result = migrate_file(mock_s3, 'old/path.pdf', 'new/path.pdf', dry_run=True)
        
        assert result is True
        mock_s3.copy_object.assert_not_called()

    def test_migrate_file_execute(self):
        mock_s3 = MagicMock()
        result = migrate_file(mock_s3, 'old/path.pdf', 'new/path.pdf', dry_run=False)
        
        assert result is True
        mock_s3.copy_object.assert_called_with(
            Bucket='congress-disclosures-standardized',
            CopySource={'Bucket': 'congress-disclosures-standardized', 'Key': 'old/path.pdf'},
            Key='new/path.pdf'
        )
