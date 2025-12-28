# Filing Types Explained

Comprehensive guide to House financial disclosure filing types and their structures.

## Overview

House financial disclosures use single-letter codes to indicate filing type. Based on analysis of 2025 filings and official documentation, we've identified 12 distinct filing types.

## Filing Type Summary

| Code | Name | Frequency | Text-Based | Priority |
|------|------|-----------|------------|----------|
| **P** | Periodic Transaction Report (PTR) | 29% | ❌ No (OCR) | CRITICAL |
| **C** | Candidate Report | 35% | ✅ Yes | CRITICAL |
| **A** | Annual Report | 6% | ✅ Yes | HIGH |
| **X** | Extension Request | 22% | ✅ Yes | HIGH |
| **T** | Termination Report | 3% | ✅ Yes | MEDIUM |
| **G** | Gift Report | 1% | ❌ No | LOW |
| **E** | Unknown | 1% | ⚠️ Mixed | LOW |
| **H** | Unknown | 1% | ✅ Yes | LOW |
| **D** | Delegation/Duplicate | <1% | ✅ Yes | LOW |
| **O** | Unknown | <1% | ❌ No | LOW |
| **B** | Blind Trust Report | <1% | ❌ No | LOW |
| **W** | Waiver Request | <1% | ✅ Yes | LOW |

## Detailed Descriptions

### P - Periodic Transaction Report (PTR)

**Most Common** - 29% of filings

**Purpose**: Members, Officers, and Employees must file PTRs within 30-45 days of certain financial transactions.

**Key Characteristics**:
- Reports individual stock/bond/property transactions
- Required within 30 days for Members, 45 days for Staff
- **IMAGE-BASED PDF** (requires OCR)
- Different form structure than Form A/B

**Sample**: Schedule B lists all transactions with:
- Transaction date
- Asset name/ticker
- Transaction type (Purchase, Sale, Exchange)
- Amount range ($1,001 - $15,000, etc.)
- Owner (Self, Spouse, Dependent Child, Joint)

See [[Data-Schemas#ptr-transactions]] for full schema.

### C - Candidate Report (Form B)

**Second Most Common** - 35% of filings

**Purpose**: Candidates for U.S. House must file Form B once they "qualify" as a candidate (typically when they raise or spend $5,000 in their campaign).

**Key Characteristics**:
- Uses Form B structure
- Filed once during candidacy
- Covers period from January 1 of preceding year through filing date
- Candidates are NOT required to file PTRs
- Text-based PDF (regex extractable)

**Structure**: Schedules A, C, D, E, F, J

### A - Annual Report (Form A)

**6% of filings**

**Purpose**: Incumbent Members, Officers, and Employees file Form A by May 15 each year.

**Key Characteristics**:
- Most comprehensive disclosure
- Covers preceding calendar year (Jan 1 - Dec 31)
- Text-based PDF (regex extractable)

**Schedules**:
- Schedule A: Assets and "Unearned" Income
- Schedule C: Earned Income
- Schedule D: Liabilities
- Schedule E: Positions Held Outside U.S. Government
- Schedule F: Agreements
- Schedule J: Compensation Over $5,000 from One Source

### X - Extension Request

**Third Most Common** - 22% of filings

**Purpose**: Request extension for filing deadline.

**Key Characteristics**:
- Short documents (1-2 pages)
- Text-based PDF
- Contains minimal data (name, filing type being extended, reason)

### T - Termination Report

**3% of filings**

**Purpose**: Members, Officers, and Employees who leave House employment must file Form A as a Termination Report within 30 days.

**Key Characteristics**:
- Uses Form A structure
- Reporting period depends on termination date
- Text-based PDF

### Other Types (B, W, G, E, D, O, H)

These are rare (<1% each) and may be:
- Internal/administrative codes
- Legacy codes
- Special report types

## Form Structures

### Form A vs Form B

**Form A**: Used by:
- Annual Filers
- Termination Filers
- Officers and Employees

**Form B**: Used by:
- New Members
- New Officers/Employees
- Candidates

## See Also

- [[Data-Schemas]] - Detailed field schemas
- [[Extraction-Architecture]] - How forms are extracted
- [Official Forms](https://ethics.house.gov/financial-disclosure/)
