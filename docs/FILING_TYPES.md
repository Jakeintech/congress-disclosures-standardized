# House Financial Disclosure Filing Types

**Generated**: 2025-11-24
**Sources**:
- Official 2025 FD Instruction Guide (House Ethics Committee)
- Analysis of 2025 filing data (1,616 documents)
- Sample PDF analysis (22 documents)

## Overview

House financial disclosures use single-letter codes to indicate filing type. Based on our analysis of 2025 filings and official documentation, we've identified 12 distinct filing types.

## Official Form Types

### Form A vs Form B

According to the House Ethics Committee:

- **Form A**: Used by Annual Filers, Termination Filers, Officers, and Employees
- **Form B**: Used by New Members, New Officers/Employees, and Candidates

## Filing Type Codes

| Code | Name | Form | Frequency | % of Total | Text-Based | Priority |
|------|------|------|-----------|------------|------------|----------|
| **C** | Candidate Report | Form B | 563 | 35% | ✅ Yes | **CRITICAL** |
| **P** | Periodic Transaction Report (PTR) | Special | 467 | 29% | ❌ No (OCR) | **CRITICAL** |
| **X** | Extension Request | N/A | 361 | 22% | ✅ Yes | HIGH |
| **A** | Annual Report or Amendment | Form A | 95 | 6% | ✅ Yes | HIGH |
| **T** | Termination Report | Form A | 45 | 3% | ✅ Yes | MEDIUM |
| **G** | Gift Report (?) | Unknown | 21 | 1% | ❌ No (OCR) | LOW |
| **E** | ? | Unknown | 19 | 1% | ⚠️ Mixed | LOW |
| **H** | ? | Unknown | 16 | 1% | ✅ Yes | LOW |
| **D** | Delegation/Duplicate (?) | Unknown | 14 | <1% | ✅ Yes | LOW |
| **O** | ? | Unknown | 11 | <1% | ❌ No (OCR) | LOW |
| **B** | Blind Trust Report | Special | 2 | <1% | ❌ No (OCR) | LOW |
| **W** | Waiver Request | Unknown | 2 | <1% | ✅ Yes | LOW |

**Total**: 1,616 documents analyzed from 2025

## Detailed Descriptions

### C - Candidate Report (Form B) - 35% of filings

**Official Definition**: Candidates for U.S. House of Representatives must file Form B once they "qualify" as a candidate (typically when they raise or spend $5,000 in their campaign).

**Key Characteristics**:
- Uses Form B structure
- Filed once during candidacy
- Covers period from January 1 of preceding year through filing date
- Candidates are NOT required to file PTRs
- Text-based PDF (regex extractable)

**Structure**: Standard Form B with Schedules A, C, D, E, F, J

**Sample**: C_10072579.pdf (Mike Croley, TN06)

### P - Periodic Transaction Report (PTR) - 29% of filings ⚠️ CRITICAL

**Official Definition**: Members, Officers, and Employees (paid above senior staff rate $150,160 in 2025) must file PTRs within 30-45 days of certain financial transactions.

**Key Characteristics**:
- Separate form from Form A/B
- Reports individual transactions (stocks, bonds, property, etc.)
- Required within 30 days for Members, 45 days for Staff
- Most common filing type after Candidate reports
- **IMAGE-BASED PDF** (requires OCR) - This is a major blocker!

**Structure**: Transaction-focused (different from FD forms)

**Blank Form**: Available at ethics.house.gov (PTR_Blank_Form.pdf)

**Samples**: P_20033421.pdf, P_20033446.pdf (both image-based)

### X - Extension Request - 22% of filings

**Characteristics**:
- Third most common filing type
- Text-based PDF (regex extractable)
- Short documents (typically 1-2 pages)

**Sample**: X_30025539.pdf

### A - Annual Report or Amendment - 6% of filings

**Official Definition**:
- **Annual**: Incumbent Members, Officers, and Employees file Form A by May 15 each year
- **Amendment**: Corrections to previously filed reports

**Key Characteristics**:
- Uses Form A structure
- Covers preceding calendar year (Jan 1 - Dec 31)
- Most comprehensive disclosure (all schedules A-J)
- Text-based PDF (regex extractable)

**Structure**: Form A with full Schedules A-J:
- Schedule A: Assets and "Unearned" Income
- Schedule C: Earned Income
- Schedule D: Liabilities
- Schedule E: Positions Held Outside U.S. Government
- Schedule F: Agreements
- Schedule J: Compensation Over $5,000 from One Source

**Sample**: A_10072874.pdf (Clinton Gene Twedt-Ball, IA02)

### T - Termination Report - 3% of filings

**Official Definition**: Members, Officers, and Employees who leave House employment must file Form A as a Termination Report within 30 days.

**Key Characteristics**:
- Uses Form A structure
- Reporting period depends on termination date
  - Before May 15: Jan 1 of prior year through termination date
  - After May 15: Jan 1 of current year through termination date
- Text-based PDF (regex extractable)

**Sample**: T_10063342.pdf

### B - Blind Trust Report - <1% of filings

**Official Definition**: Qualified Blind Trusts approved by the Committee on Ethics have special reporting requirements.

**Key Characteristics**:
- Rare (only 2 in 2025)
- Image-based PDF (requires OCR)
- Special disclosure rules apply

**Samples**: B_8220735.pdf (1 page), B_8220736.pdf (46 pages)

### W - Waiver Request - <1% of filings

**Characteristics**:
- Very rare (only 2 in 2025)
- Text-based PDF
- Short documents (~1 page)

**Sample**: W_8026.pdf

### G, E, D, O, H - Unknown Types

These filing type codes appear in the data but are not explicitly defined in the 2025 Instruction Guide. They may be:
- Internal/administrative codes
- Legacy codes
- Specific report types not documented in public instructions

**Needs Research**:
- Check with House Clerk or Ethics Committee
- Review older instruction guides
- Examine actual filed documents for clues

## PDF Structure Analysis

### Text-Based (✅ Regex Extractable)
- **A** (Annual/Amendment): 100% text-based
- **C** (Candidate): 100% text-based
- **D**: 100% text-based
- **E**: 50% text-based (mixed)
- **H**: 100% text-based
- **T** (Termination): 100% text-based
- **W** (Waiver): 100% text-based
- **X** (Extension): 100% text-based

### Image-Based (❌ Requires OCR)
- **P** (PTR): 100% image-based ⚠️ **CRITICAL** - 29% of all filings!
- **B** (Blind Trust): 100% image-based
- **G**: 100% image-based
- **O**: 100% image-based

## Implementation Strategy

### Phase 1: Text-Based Extraction (Types A, C, D, T, W, X)
- Use `pdftotext` + regex patterns
- Covers 68% of filings (excluding P and X which are extensions)
- Faster, cheaper, more reliable

### Phase 2: OCR Pipeline (Type P - CRITICAL)
- Type P represents 29% of all filings
- Must implement Tesseract OCR or AWS Textract
- Higher cost and complexity but essential for completeness

### Phase 3: OCR for Remaining Types (B, G, O, E)
- Only 3% of filings combined
- Lower priority but needed for 100% coverage

## References

- **Official Instruction Guide**: [2025 FD Instruction Guide](https://ethics.house.gov/wp-content/uploads/2025/04/2024-Final-Instruction-Guide-4-15-2025.pdf)
- **PTR Blank Form**: [PTR Form with Instructions](https://ethics.house.gov/wp-content/uploads/2024/11/Final-PTR-Form-CY-2022_0.pdf)
- **House Ethics Committee**: https://ethics.house.gov/financial-disclosure/
- **Filing Portal**: https://fd.house.gov
- **Asset Type Codes**: https://fd.house.gov/reference/asset-type-codes.aspx

## Next Steps

1. ✅ Download official forms and instruction guide
2. ⏳ Extract complete field mappings from Form A and Form B
3. ⏳ Create JSON schemas for each filing type
4. ⏳ Build regex extraction library for text-based types
5. ⏳ Implement OCR pipeline for Type P (PTR) documents
6. ⏳ Test extraction accuracy on all 22 sample PDFs
