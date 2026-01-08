# Blob Tag Schema

This document defines the schema for S3 Object Metadata tags applied to Bronze layer PDFs.

## Tags

| Key | Description | Example | Source |
|-----|-------------|---------|--------|
| `filing_type` | Code indicating the type of filing | `P`, `A` | XML Index |
| `member_name` | Name of the member filing the report | `Pelosi, Nancy` | XML Index |
| `state_district` | State and district code | `CA-12` | XML Index |
| `quality_score` | Calculated quality score (0.0-1.0) | `0.85` | `metadata_tagger.py` |
| `has_issues` | Boolean flag if validation issues found | `false` | Validation Framework |
| `extraction_method` | Method used to extract data | `text`, `ocr` | Extraction Lambda |
| `page_count` | Number of pages in the PDF | `5` | PDF Analysis |
| `year` | Filing year | `2025` | Filename/Path |
| `doc_id` | Unique Document ID | `10056789` | Filename |
| `upload_timestamp` | ISO timestamp of upload | `2025-01-01T12:00:00Z` | System |

## Quality Score Calculation

The `quality_score` is a weighted sum of the following factors:

1. **Text Layer (50%)**:
   - +0.50 if the PDF has an extractable text layer.
   - +0.00 if OCR is required.

2. **Page Count (20%)**:
   - +0.20 if pages < 30 (typical for PTRs).
   - +0.10 if 30 <= pages < 100.
   - +0.00 if pages >= 100.

3. **Recency (15%)**:
   - +0.15 if filing year >= 2020.
   - +0.00 if older.

4. **Metadata Completeness (15%)**:
   - +0.15 if `member_name` is valid (not "Unknown").
   - +0.00 if missing or unknown.

**Max Score**: 1.0
**Threshold for Auto-Processing**: 0.7
