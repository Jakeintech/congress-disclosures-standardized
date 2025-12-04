// S3 Configuration
const S3_BUCKET = "congress-disclosures-standardized";
const S3_REGION = "us-east-1";
const API_BASE = `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com/website/api/v1`;

// API Gateway Configuration (deployed infrastructure)
const API_GATEWAY_URL = "https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com";

// API Endpoints
const MANIFEST_URL = `${API_BASE}/documents/manifest.json`;
const PTR_TRANSACTIONS_URL = `${API_BASE}/schedules/b/transactions.json`;
const SILVER_DOCUMENTS_API_URL = `${API_BASE}/documents/silver/manifest.json`;
const ITEMS_PER_PAGE = 50;
