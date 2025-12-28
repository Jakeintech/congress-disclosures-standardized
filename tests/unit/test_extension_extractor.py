"""Unit tests for Extension Extractor."""

import pytest
from ingestion.lib.extractors.extension_extractor import ExtensionExtractor


@pytest.fixture
def extractor():
    return ExtensionExtractor()


def test_extension_extraction(extractor):
    """Test extraction of extension details."""
    # Mock Textract blocks for Key-Value pairs
    # We need to simulate the structure: KEY_VALUE_SET (KEY) -> KEY_VALUE_SET (VALUE)
    
    def make_kv_pair(key_text, value_text, start_id):
        k_id = str(start_id)
        v_id = str(start_id + 1)
        k_child_id = str(start_id + 2)
        v_child_id = str(start_id + 3)
        
        blocks = [
            {
                "Id": k_id,
                "BlockType": "KEY_VALUE_SET",
                "EntityTypes": ["KEY"],
                "Relationships": [
                    {"Type": "CHILD", "Ids": [k_child_id]},
                    {"Type": "VALUE", "Ids": [v_id]}
                ]
            },
            {
                "Id": v_id,
                "BlockType": "KEY_VALUE_SET",
                "EntityTypes": ["VALUE"],
                "Relationships": [{"Type": "CHILD", "Ids": [v_child_id]}]
            },
            {
                "Id": k_child_id,
                "BlockType": "WORD",
                "Text": key_text
            },
            {
                "Id": v_child_id,
                "BlockType": "WORD",
                "Text": value_text
            }
        ]
        return blocks

    blocks = []
    blocks.extend(make_kv_pair("Name", "John Doe", 10))
    blocks.extend(make_kv_pair("New Due Date", "11/10/2025", 20))
    blocks.extend(make_kv_pair("Extension Length", "90 days", 30))
    
    result = extractor.extract_from_textract("DOC_EXT_1", 2025, blocks)
    
    assert result["filing_type"] == "Extension Request"
    assert result["filer_info"]["name"] == "John Doe"
    assert result["extension_details"]["new_due_date"] == "11/10/2025"
    assert result["extension_details"]["extension_length"] == "90 days"
    assert result["extraction_metadata"]["overall_confidence"] == 1.0
