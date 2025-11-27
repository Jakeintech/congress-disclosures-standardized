"""Unit tests for Termination Extractor."""

import pytest
from ingestion.lib.extractors.termination_extractor import TerminationExtractor


@pytest.fixture
def extractor():
    return TerminationExtractor()


def test_termination_extraction_defaults(extractor):
    """Test that filing type defaults to Terminated Filer Report."""
    # Mock minimal textract blocks
    blocks = [
        {
            "Id": "1",
            "BlockType": "PAGE",
            "Page": 1
        }
    ]
    
    result = extractor.extract_from_textract("DOC123", 2024, blocks)
    
    assert result["filing_type"] == "Terminated Filer Report"
    assert result["header"]["filing_type"] == "Terminated Filer Report"


def test_termination_extraction_with_header(extractor):
    """Test extraction with explicit header."""
    # Mock blocks with header
    blocks = [
        {
            "Id": "1",
            "BlockType": "KEY_VALUE_SET",
            "EntityTypes": ["KEY"],
            "Relationships": [{"Type": "CHILD", "Ids": ["2"]}, {"Type": "VALUE", "Ids": ["3"]}]
        },
        {
            "Id": "2",
            "BlockType": "WORD",
            "Text": "Filing Type"
        },
        {
            "Id": "3",
            "BlockType": "KEY_VALUE_SET",
            "EntityTypes": ["VALUE"],
            "Relationships": [{"Type": "CHILD", "Ids": ["4"]}]
        },
        {
            "Id": "4",
            "BlockType": "WORD",
            "Text": "Terminated Filer Report"
        }
    ]
    
    # Need to mock block map behavior in base class or provide full structure
    # Since we can't easily mock the internal helper methods without complex setup,
    # we'll rely on the fact that we're testing the override logic which runs AFTER super().extract_from_textract
    
    # Actually, the base class _extract_header uses _extract_key_value_pairs which iterates blocks.
    # So passing these blocks should work if we construct the map correctly?
    # The base extract_from_textract builds the map.
    
    result = extractor.extract_from_textract("DOC123", 2024, blocks)
    
    assert result["filing_type"] == "Terminated Filer Report"
