# House Financial Disclosure Field Mapping

**Generated**: 2025-11-24
**Source**: Analysis of 2025 sample PDFs

## Overview

House financial disclosure forms have a consistent structure across filing types with standardized sections. All text-based PDFs (Types A, C, D, T, W, X) follow this format.

## Common Header Fields

All filing types share these header fields:

| Field Name | Location | Required | Example | Notes |
|------------|----------|----------|---------|-------|
| filing_id | Top of page 1 | Yes | "10072874" | Numeric ID |
| filer_name_first | Filer Info section | Yes | "Clinton Gene" | |
| filer_name_last | Filer Info section | Yes | "Twedt-Ball" | |
| filer_status | Filer Info section | Yes | "Congressional Candidate" | Or "Member" |
| filer_state_district | Filer Info section | Yes | "IA02" | State code + district |
| filing_type | Filing Info section | Yes | "Amendment Report" | See Filing Type Codes |
| filing_year | Filing Info section | Yes | "2025" | 4-digit year |
| filing_date | Filing Info section | Yes | "11/19/2025" | MM/DD/YYYY |
| period_covered_start | Filing Info section | Yes | "01/01/2024" | MM/DD/YYYY |
| period_covered_end | Filing Info section | Yes | "10/20/2025" | MM/DD/YYYY |

## Filing Type Codes

| Code | Name | Description | Frequency (2025) |
|------|------|-------------|------------------|
| A | Annual Report | Annual filing or amendment | 95 (6%) |
| P | Periodic Transaction | PTR - transactions within 45 days | 467 (29%) ⚠️ CRITICAL |
| C | Candidate Report | New candidate filing | 563 (35%) |
| D | ? | Unknown - small filing | 14 (<1%) |
| X | Extension | Extension request | 361 (22%) |
| T | Termination | Termination report | 45 (3%) |
| W | Waiver | Waiver request | 2 (<1%) |
| G | ? | Unknown - image-based | 21 (1%) |
| E | ? | Unknown | 19 (1%) |
| B | Blind Trust | Blind trust report | 2 (<1%) |
| O | ? | Unknown - image-based | 11 (<1%) |
| H | ? | Unknown | 16 (1%) |

## Section A: Assets

Assets reported with the following fields per entry:

| Field Name | Required | Format | Example | Notes |
|------------|----------|--------|---------|-------|
| asset_name | Yes | String | "Ball Farm [RP]" | Includes type code in brackets |
| asset_type_code | Yes | 2-letter code | "RP" | See Asset Type Codes |
| asset_owner | Yes | Code | "JT", "SP", "DC" | JT=Joint, SP=Spouse, DC=Child |
| asset_value_low | No | Integer | 100001 | Lower bound of range |
| asset_value_high | No | Integer | 250000 | Upper bound of range |
| asset_location | No | String | "Bloomfield/Davis, IA, US" | Free text |
| asset_description | No | String | "Retirement savings..." | Free text notes |

**Income sub-fields** (per asset):

| Field Name | Required | Format | Example |
|------------|----------|--------|---------|
| income_type | No | String | "Rent", "Interest", "Dividends" |
| income_current_year_low | No | Integer | 5001 |
| income_current_year_high | No | Integer | 15000 |
| income_preceding_year_low | No | Integer | 5001 |
| income_preceding_year_high | No | Integer | 15000 |

### Asset Type Codes
- RP = Real Property
- BA = Bank Account
- OT = Other (retirement accounts, etc.)
- [Full list at https://fd.house.gov/reference/asset-type-codes.aspx]

## Section C: Employment Income

Employment entries with fields:

| Field Name | Required | Format | Example |
|------------|----------|--------|---------|
| employment_source | Yes | String | "Matthew 25" |
| employment_type | Yes | String | "Salary", "Spouse Salary" |
| employment_amount_current | No | Decimal | 38380.00 |
| employment_amount_preceding | No | Decimal | 70827.00 |
| employment_description | No | String | "Spouses salary for teaching..." |

## Section D: Liabilities

Liability entries:

| Field Name | Required | Format | Example |
|------------|----------|--------|---------|
| liability_owner | Yes | Code | "JT", "SP", "DC" |
| liability_creditor | Yes | String | "Iowa Mortgage" |
| liability_date_incurred | Yes | String | "July 2013" |
| liability_type | Yes | String | "Mortgage on rental property" |
| liability_amount_low | No | Integer | 15001 |
| liability_amount_high | No | Integer | 50000 |

## Section E: Positions

Position entries:

| Field Name | Required | Format | Example |
|------------|----------|--------|---------|
| position_title | Yes | String | "Trustee" |
| position_organization | Yes | String | "Cedar Rapids Library Board" |

## Section F: Agreements

| Field Name | Required | Format | Example |
|------------|----------|--------|---------|
| agreements_disclosed | Yes | Boolean | false |
| agreements_details | No | String | None |

## Section J: Compensation Over $5,000

| Field Name | Required | Format | Example |
|------------|----------|--------|---------|
| compensation_source_name | No | String | "NOAA" |
| compensation_source_address | No | String | "Washington, DC, US" |
| compensation_description | No | String | "Performed federal duties..." |

## Certification Section

| Field Name | Required | Format | Example |
|------------|----------|--------|---------|
| certification_trusts_excluded | Yes | Boolean | false |
| certification_exemption_claimed | Yes | Boolean | false |
| certification_signature | Yes | String | "Clinton Gene Twedt-Ball" |
| certification_date | Yes | Date | "11/19/2025" |
| certification_digital | Yes | Boolean | true |

## Special Cases

### None Disclosed Sections
When a section shows "None disclosed.", the section should be present but empty in the structured data.

### Range Values
Financial amounts are reported in ranges. Store both low and high bounds:
- "$1 - $1,000" → {low: 1, high: 1000}
- "$100,001 - $250,000" → {low: 100001, high: 250000}

### Multiple Income Sources Per Asset
An asset can have multiple income types (e.g., "Rent" + "$1-$200"). Store as array of income objects.

## Notes for Implementation

1. **Regex Extraction**: Text-based PDFs can use regex patterns to extract fields
2. **OCR Required**: Types P, B, G, O are image-based and need OCR first
3. **Validation**: Cross-reference against official schemas
4. **Parsing Challenges**:
   - Asset values and income ranges span multiple lines
   - Owner codes (JT, SP, DC) may be on separate lines
   - Asset type codes are in brackets [XX]
   - Descriptions can be multi-line

## Next Steps

1. Create JSON schemas based on this mapping
2. Implement extraction library with regex patterns
3. Test against all 22 sample PDFs
4. Validate accuracy >= 90%
