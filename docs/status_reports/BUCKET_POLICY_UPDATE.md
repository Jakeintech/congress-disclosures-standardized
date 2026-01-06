# Bucket Policy Update - File Access

## ✅ Completed

Updated S3 bucket policy to allow public read access to:

1. **Bronze Layer PDFs**: `bronze/*`
   - Example: `https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/bronze/house/financial/year=2025/pdfs/2025/10063228.pdf`
   - Status: ✅ HTTP 200

2. **Silver Layer JSON**: `silver/*`
   - Structured JSON: `silver/house/financial/structured/year=2025/doc_id=10063228.json`
   - Metadata JSON: `silver/house/financial/documents/year=2025/10063228/metadata.json`
   - Status: ✅ HTTP 200

3. **Silver Layer Text Files**: `silver/*`
   - Current location: `silver/house/financial/text/extraction_method=pypdf/year=2025/doc_id=10063228/raw_text.txt.gz`
   - Status: ✅ HTTP 200 (compressed)

## ⚠️ Note on Text Files

The user requested access to:
```
silver/house/financial/documents/year=2025/10063228/text.txt
```

**Current Situation:**
- Text files are stored as **compressed** `.gz` files in a different path structure
- Actual path: `silver/house/financial/text/extraction_method=pypdf/year=2025/doc_id=10063228/raw_text.txt.gz`
- The requested `text.txt` path doesn't exist yet

**Options:**
1. **Access compressed files directly** (current):
   - URL: `https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/silver/house/financial/text/extraction_method=pypdf/year=2025/doc_id=10063228/raw_text.txt.gz`
   - Requires client-side decompression

2. **Create uncompressed text.txt files** (future enhancement):
   - Add Lambda/post-processing step to extract and save uncompressed text
   - Save to: `silver/house/financial/documents/year=2025/10063228/text.txt`
   - Would require updating extraction Lambda or adding a new processing step

## Updated Bucket Policy

The bucket policy now includes:
```json
{
  "Resource": [
    "arn:aws:s3:::congress-disclosures-standardized/website/*",
    "arn:aws:s3:::congress-disclosures-standardized/website/api/*",
    "arn:aws:s3:::congress-disclosures-standardized/favicon.ico",
    "arn:aws:s3:::congress-disclosures-standardized/robots.txt",
    "arn:aws:s3:::congress-disclosures-standardized/manifest.json",
    "arn:aws:s3:::congress-disclosures-standardized/bronze/*",
    "arn:aws:s3:::congress-disclosures-standardized/silver/*"
  ]
}
```

## Terraform Update

The Terraform file `infra/terraform/bucket_policy.tf` has been updated to match. To apply:

```bash
cd infra/terraform
terraform apply -target=aws_s3_bucket_policy.public_read_access
```

## Verification

All file types are now publicly accessible:

- ✅ Bronze PDFs: HTTP 200
- ✅ Silver JSON files: HTTP 200
- ✅ Silver metadata: HTTP 200
- ✅ Silver compressed text: HTTP 200
- ⚠️ Silver uncompressed text.txt: HTTP 403 (file doesn't exist at that path)

## Next Steps (Optional)

If uncompressed `text.txt` files are needed in the `documents/` path:

1. **Option A**: Update extraction Lambda to also save uncompressed text
2. **Option B**: Create post-processing script to extract and copy text files
3. **Option C**: Use compressed files and handle decompression client-side
