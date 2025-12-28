# Bronze Layer Schema

## Path Structure

The Bronze layer stores raw PDF files downloaded from the Clerk of the House website.

**Pattern**:
`bronze/house/financial/year={YEAR}/filing_type={TYPE}/pdfs/{DocID}.pdf`

**Variables**:
- `{YEAR}`: The filing year (e.g., 2024, 2025)
- `{TYPE}`: The filing type code (see below)
- `{DocID}`: The unique document ID assigned by the Clerk's office (e.g., 10056789)

## Filing Types

| Code | Description |
|------|-------------|
| P    | Periodic Transaction Report (PTR) |
| A    | Annual Report |
| C    | Candidate Report |
| T    | Termination Report |
| X    | Extension |
| D    | Amendment (generic) |
| E    | Blind Trust |
| N    | New Filer |
| B    | Blind Trust Amendment |
| F    | Final Report |
| G    | Gift Waiver |
| U    | Unknown/Other |

## Metadata

S3 Object Metadata is used to store key information about each file to avoid needing to parse the filename or look up the index for basic operations.

- `x-amz-meta-filing-type`: The filing type code (P, A, etc.)
- `x-amz-meta-member-name`: Name of the member
- `x-amz-meta-state-district`: State and district (e.g., CA-12)
- `x-amz-meta-quality-score`: Calculated quality score (0.0-1.0)
- `x-amz-meta-has-issues`: Boolean flag if validation issues found
- `x-amz-meta-extraction-method`: Method used to extract data (e.g., text, ocr)
- `x-amz-meta-page-count`: Number of pages in the PDF
