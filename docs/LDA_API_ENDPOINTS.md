# LDA (Lobbying Disclosure Act) API Endpoints

The Senate LDA API provides 13 endpoints for lobbying disclosure data.

Base URL: `https://lda.senate.gov/api/v1`

## Coverage Status

### ✅ Fully Implemented (12/13)

#### Filing Endpoints
1. **`/filings/`** - Main lobbying disclosure filings (LD-1, LD-2)
   - Status: ✅ Implemented in `lda_ingest_filings/handler.py::ingest_filings()`
   - Bronze: `bronze/lobbying/filings/year={year}/filing_uuid={uuid}.json.gz`
   - Pagination: Yes (100 per page)
   - Filter: `filing_year`, `filing_type`

2. **`/contributions/`** - Political contributions (LD-203)
   - Status: ✅ Implemented in `lda_ingest_filings/handler.py::ingest_contributions()`
   - Bronze: `bronze/lobbying/contributions/year={year}/contribution_id={id}.json.gz`
   - Pagination: Yes (100 per page)
   - Filter: `filing_year`

#### Entity Endpoints
3. **`/registrants/`** - Lobbying firms and organizations
   - Status: ✅ Implemented in `lda_ingest_filings/handler.py::ingest_registrants()`
   - Bronze: `bronze/lobbying/registrants/registrant_id={id}.json.gz`
   - Pagination: Yes (100 per page)

4. **`/clients/`** - Organizations being represented
   - Status: ✅ Implemented in `lda_ingest_filings/handler.py::ingest_clients()`
   - Bronze: `bronze/lobbying/clients/client_id={id}.json.gz`
   - Pagination: Yes (100 per page)

5. **`/lobbyists/`** - Individual lobbyists
   - Status: ✅ Implemented in `lda_ingest_filings/handler.py::ingest_lobbyists()`
   - Bronze: `bronze/lobbying/lobbyists/lobbyist_id={id}.json.gz`
   - Pagination: Yes (100 per page)

#### Constants Endpoints (Reference Data)
6. **`/constants/filing/filingtypes/`** - Filing type codes (LD-1, LD-2, etc.)
   - Status: ✅ Implemented in `lda_ingest_filings/handler.py::ingest_constants()`
   - Bronze: `bronze/lobbying/constants/filingtypes/snapshot_date={date}/snapshot.json.gz`

7. **`/constants/filing/lobbyingactivityissues/`** - Issue area codes (DEF, HCR, TRD, etc.)
   - Status: ✅ Implemented in `lda_ingest_filings/handler.py::ingest_constants()`
   - Bronze: `bronze/lobbying/constants/lobbyingactivityissues/snapshot_date={date}/snapshot.json.gz`

8. **`/constants/filing/governmententities/`** - Government agencies and committees
   - Status: ✅ Implemented in `lda_ingest_filings/handler.py::ingest_constants()`
   - Bronze: `bronze/lobbying/constants/governmententities/snapshot_date={date}/snapshot.json.gz`

9. **`/constants/general/countries/`** - Country codes and names
   - Status: ✅ Implemented in `lda_ingest_filings/handler.py::ingest_constants()`
   - Bronze: `bronze/lobbying/constants/countries/snapshot_date={date}/snapshot.json.gz`

10. **`/constants/general/states/`** - US state codes and names
    - Status: ✅ Implemented in `lda_ingest_filings/handler.py::ingest_constants()`
    - Bronze: `bronze/lobbying/constants/states/snapshot_date={date}/snapshot.json.gz`

11. **`/constants/lobbyist/prefixes/`** - Name prefixes (Mr., Ms., Dr., etc.)
    - Status: ✅ Implemented in `lda_ingest_filings/handler.py::ingest_constants()`
    - Bronze: `bronze/lobbying/constants/prefixes/snapshot_date={date}/snapshot.json.gz`

12. **`/constants/lobbyist/suffixes/`** - Name suffixes (Jr., Sr., III, etc.)
    - Status: ✅ Implemented in `lda_ingest_filings/handler.py::ingest_constants()`
    - Bronze: `bronze/lobbying/constants/suffixes/snapshot_date={date}/snapshot.json.gz`

### ❌ Missing (1/13)

13. **`/constants/contribution/itemtypes/`** - Contribution item type codes
    - Status: ❌ **NOT IMPLEMENTED**
    - Should be: `bronze/lobbying/constants/itemtypes/snapshot_date={date}/snapshot.json.gz`
    - Fix: Add to `ingest_constants()` in `lda_ingest_filings/handler.py`

## Usage

### Ingest Filings
```bash
# Ingest all 2025 filings
python3 scripts/trigger_lda_ingestion.py --year 2025 --type filing

# Ingest all 2025 contributions
python3 scripts/trigger_lda_ingestion.py --year 2025 --type contribution
```

### Ingest Entities
```bash
# Ingest all registrants (lobbying firms)
python3 scripts/trigger_lda_ingestion.py --entity-type registrant

# Ingest all clients
python3 scripts/trigger_lda_ingestion.py --entity-type client

# Ingest all lobbyists
python3 scripts/trigger_lda_ingestion.py --entity-type lobbyist
```

### Ingest Constants
```bash
# Ingest all reference data
python3 scripts/trigger_lda_ingestion.py --entity-type constants
```

## Data Flow

```
LDA Senate API
  ↓
Lambda: lda_ingest_filings
  ↓
Bronze: s3://bucket/bronze/lobbying/...
  ↓
Scripts: lobbying_build_silver_*.py
  ↓
Silver: s3://bucket/silver/lobbying/...
  ↓
Scripts: lobbying_build_dim_*.py, lobbying_build_fact_*.py
  ↓
Gold: s3://bucket/gold/lobbying/...
  ↓
API Lambdas (get_lobbying_filings, etc.)
  ↓
Website: lobbying-explorer.html
```

## API Details

- **Base URL**: https://lda.senate.gov/api/v1
- **Authentication**: None required (public API)
- **Rate Limiting**: Yes (429 responses with Retry-After header)
- **Pagination**: `?page=N&page_size=100`
- **Default Page Size**: 100 (max: 250)
- **Response Format**: JSON

## Next Steps

1. **Add missing endpoint**: Implement `/constants/contribution/itemtypes/` in `ingest_constants()`
2. **Verify constants usage**: Use constants data to enrich Silver tables with display names
3. **Add validation**: Cross-reference codes in filings against constants tables
4. **Schedule updates**: Constants change rarely, but should be refreshed quarterly
