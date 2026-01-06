# API Documentation

This directory contains the Swagger UI for the Congressional Trading Data API.

## Viewing the Documentation

### Local Development

1. Serve the website locally:
   ```bash
   cd website
   python3 -m http.server 8000
   ```

2. Open in browser:
   ```
   http://localhost:8000/api-docs/
   ```

### After Deployment

Once the website is deployed to S3, the API documentation will be available at:
```
https://your-bucket-name.s3.amazonaws.com/api-docs/index.html
```

Or if using CloudFront/custom domain:
```
https://your-domain.com/api-docs/
```

## Files

- **`index.html`** - Swagger UI HTML page with custom styling
- **`../../docs/openapi.yaml`** - OpenAPI 3.0 specification (referenced by Swagger UI)

## Features

- ✅ Interactive API documentation for all 17 endpoints
- ✅ Try-it-out functionality to test endpoints
- ✅ Request/response examples
- ✅ Schema definitions
- ✅ Comprehensive parameter documentation
- ✅ Custom branding and styling
- ✅ Fully responsive design

## Navigation

The API Docs page is integrated into the main website navigation. Users can access it from any page via the "API Docs" link in the header.

## OpenAPI Spec

The OpenAPI 3.0 specification is located at:
```
docs/openapi.yaml
```

It contains:
- Complete endpoint definitions
- Request/response schemas
- Parameter specifications
- Example requests and responses
- Error response schemas

## Customization

The Swagger UI is customized with:
- Custom color scheme matching the website branding
- Feature cards highlighting API capabilities
- Quick action buttons (Back to Dashboard, Download Spec, GitHub)
- Removed default Swagger topbar
- Enhanced mobile responsiveness

## Deployment

When deploying the website to S3:

1. Upload the entire `website/` directory including `api-docs/`
2. Upload the `docs/openapi.yaml` file
3. Ensure the bucket policy or CloudFront provides public access (ACLs disabled on BucketOwnerEnforced buckets)
4. The Swagger UI will automatically load the OpenAPI spec via relative path

```bash
aws s3 sync website/ s3://your-bucket/website/
aws s3 cp docs/openapi.yaml s3://your-bucket/docs/openapi.yaml --content-type application/x-yaml
```

Note: If your bucket uses Object Ownership (BucketOwnerEnforced), ACLs are not allowed. Use a bucket policy for public read or serve through CloudFront with an Origin Access Control.
