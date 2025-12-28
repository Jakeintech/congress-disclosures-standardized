# Ingestion Pipeline Details

This document details the initial ingestion phase of the pipeline, specifically how the XML manifest serves as the "source of truth" for retrieving and organizing Bronze layer files.

## Overview

The ingestion process is triggered by the `house_fd_ingest_zip` Lambda function. This function is responsible for:
1.  Downloading the annual zip file from the House Clerk's website.
2.  Extracting the XML manifest (`YEARFD.xml`).
3.  Parsing the XML to identify all filings.
4.  Extracting individual PDF files from the zip.
5.  Uploading PDFs to the Bronze layer in S3 with deterministic paths.

## The XML Manifest (Source of Truth)

The `YEARFD.xml` file inside the downloaded zip contains metadata for every filing in that year. This file is the authoritative source for linking a Member to their specific disclosure document (`DocID`).

### XML Structure

Each filing is represented by a `<Member>` element.

```xml
<FinancialDisclosure>
  <Member>
    <Prefix>Hon.</Prefix>
    <Last>Aderholt</Last>
    <First>Robert B.</First>
    <Suffix />
    <FilingType>P</FilingType>
    <StateDst>AL04</StateDst>
    <Year>2025</Year>
    <FilingDate>9/10/2025</FilingDate>
    <DocID>20032062</DocID>
  </Member>
  <!-- ... more members ... -->
</FinancialDisclosure>
```

### Key Fields

| Field | Description | Example | Usage in Pipeline |
| :--- | :--- | :--- | :--- |
| `DocID` | Unique Document ID | `20032062` | Used for S3 filename (`20032062.pdf`) and database primary key. |
| `FilingType` | Type of filing | `P` (Periodic), `A` (Annual), etc. | Used for tagging S3 objects and routing extraction logic. |
| `Year` | Filing Year | `2025` | Used for S3 partitioning (`year=2025`). |
| `Last`, `First` | Member Name | `Aderholt`, `Robert B.` | Metadata for the filing record. |
| `StateDst` | State & District | `AL04` | Metadata for the filing record. |

## Bronze Layer Organization

The pipeline uses the metadata from the XML to organize files in the Bronze layer.

### S3 Path Construction

The S3 path for each PDF is constructed deterministically:

`s3://congress-disclosures-standardized/bronze/house/financial/year={Year}/pdfs/{Year}/{DocID}.pdf`

*   **Bucket**: `congress-disclosures-standardized`
*   **Prefix**: `bronze/house/financial/`
*   **Partition**: `year={Year}` (e.g., `year=2025`)
*   **Sub-path**: `pdfs/{Year}/` (e.g., `pdfs/2025/`)
*   **Filename**: `{DocID}.pdf` (e.g., `20032062.pdf`)

### Metadata Tagging

When the PDF is uploaded to S3, the following metadata tags are applied based on the XML:

*   `filing_type`: The value from `<FilingType>` (e.g., `P`, `A`, `T`).
*   `filer_name`: Constructed from `<Last>, <First>`.
*   `state_district`: The value from `<StateDst>`.
*   `filing_date`: The value from `<FilingDate>`.

This ensures that the object itself carries its critical metadata, allowing downstream consumers to process it without needing to look up the XML again.

## Ingestion Output

The `house_fd_ingest_zip` Lambda returns a JSON summary of the operation.

**Example Output:**

```json
{
    "status": "success",
    "year": 2025,
    "zip_url": "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/2025FD.zip",
    "raw_zip_s3_key": "bronze/house/financial/year=2025/raw_zip/2025FD.zip",
    "index_files": [
        "bronze/house/financial/year=2025/index/2025FD.txt",
        "bronze/house/financial/year=2025/index/2025FD.xml"
    ],
    "pdfs_uploaded": 150,
    "sqs_messages_sent": 150,
    "timestamp": "2025-11-29T21:14:05.746474+00:00"
}
```

## Step-by-Step Workflow

1.  **Download Zip**: The Lambda downloads `https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{YEAR}FD.zip`.
2.  **Upload Raw Zip**: The intact zip is uploaded to `bronze/house/financial/year={YEAR}/raw_zip/`.
3.  **Extract Index**: `2025FD.xml` is extracted from the zip and uploaded to `bronze/house/financial/year={YEAR}/index/`.
4.  **Parse XML**: The Lambda parses the XML to build a map of `DocID` -> `Metadata`.
5.  **Process PDFs**:
    *   Iterate through all files in the zip.
    *   If a file matches `{DocID}.pdf`:
        *   Retrieve metadata from the XML map.
        *   Upload to S3 with the deterministic path and metadata tags.
        *   Send a message to the `house-fd-extract-queue` SQS queue to trigger extraction.

This process ensures that every PDF in the Bronze layer is directly traceable to an entry in the official XML manifest.
