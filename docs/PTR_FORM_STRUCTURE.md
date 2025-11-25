# PTR Form Structure - Visual Field Mapping

**Source**: Official PTR Blank Form (docs/PTR_Blank_Form.pdf)
**Form**: Ethics in Government Act Periodic Transaction Report
**Updated**: 2025-11-24

---

## Form Overview

The PTR form consists of:
1. **Certification Page** (Page 1) - Filer information and signatures
2. **Transaction Pages** (Pages 2+) - Tabular listing of transactions

---

## Page 1: Certification & Filer Information

### Header
```
UNITED STATES HOUSE OF REPRESENTATIVES
ETHICS IN GOVERNMENT ACT
PERIODIC TRANSACTION REPORT
Page ___ of ___
```

### Filer Information Section
**Note**: "Your address and signature WILL NOT be made available to the public."

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| Full Name | Text | Yes | Print full name |
| Daytime Telephone | Text | Yes | |
| Complete Address | Text | Yes | Office or home - NOT PUBLIC |
| Filer Status | Radio | Yes | Choose: Member OR Officer or Employee |
| **If Member:** | | | |
| └─ State | Text | Yes | 2-letter code |
| └─ District | Text | Yes | District number |
| **If Officer/Employee:** | | | |
| └─ Employing Office | Text | Yes | Office name |

### Report Type
| Field | Type | Required |
|-------|------|----------|
| Initial Report | Checkbox | Yes (one must be selected) |
| Amendment | Checkbox | Yes (one must be selected) |
| Date of Report Being Amended | Date | Only if Amendment |

### IPO Question
```
Did you purchase any shares that were allocated as a part of an Initial Public Offering?
☐ Yes  ☐ No

If you answered "yes" to this question, please contact the Committee on Ethics for further guidance.
```

### Certification Section

**Warning Box**: "A $200 penalty shall be assessed against anyone who files more than 30 days late."

**Filer Certification**:
```
I CERTIFY that the statements I have made on the attached Periodic Transaction
Report are true, complete, and correct to the best of my knowledge and belief.

Further, I CERTIFY that I have disclosed all transactions as required by the
STOCK Act.

Signature of Reporting Individual: ________________  Date: ________
```

**Official Certification** (FOR OFFICIAL USE ONLY):
```
It is my opinion, based on the information contained in this Periodic
Transaction Report, that the reporting individual is in compliance
with title I of the Ethics in Government Act (5 U.S.C. app. §§ 101-111).

Signature of Certifying Official: ________________  Date: ________
```

---

## Page 2+: Transaction Table

### Table Columns (Left to Right)

| Column | Width | Header | Description | Values |
|--------|-------|--------|-------------|--------|
| 1 | Narrow | SP/DC/JT | Owner indicator | SP, DC, JT, or blank |
| 2 | Wide | FULL ASSET NAME | Complete name of asset | Text (NOT ticker symbol) |
| 3 | Med | TYPE OF TRANSACTION | Transaction type checkboxes | ☐ Purchase<br>☐ Sale<br>☐ Partial Sale<br>☐ Exchange |
| 4 | Med | DATE OF TRANSACTION | Transaction date | MM/DD/YY |
| 5 | Med | DATE NOTIFIED OF TRANSACTION | Notification date | MM/DD/YY |
| 6-16 | Wide | AMOUNT OF TRANSACTION | Value range columns A-K | (See below) |

### Amount of Transaction Columns (A-K)

Each transaction has 11 possible value range checkboxes:

| Column | Amount Range | Typical Usage |
|--------|-------------|---------------|
| A | $1,001-$15,000 | Small transactions |
| B | $15,001-$50,000 | Medium transactions |
| C | $50,001-$100,000 | |
| D | $100,001-$250,000 | Large transactions |
| E | $250,001-$500,000 | |
| F | $500,001-$1,000,000 | |
| G | $1,000,001-$5,000,000 | Very large transactions |
| H | $5,000,001-$25,000,000 | |
| I | $25,000,001-$50,000,000 | Extremely large |
| J | Over $50,000,000 | Mega transactions |
| K | Transaction in Spouse or Dependent Child Asset over $1,000,000 | **Special column** |

**Note**: Column K is specifically for transactions in assets owned solely by spouse/dependent child (where filer has no interest) exceeding $1M.

### Example Row (from form)
```
JT | Example: Mega Corp. Common Stock | X(Purchase) | 02/05/20 | 03/07/20 | X(Column B) |
```

### Filer Notes Section (Bottom of each page)

```
NOTE NUMBER | FILER NOTES
------------|-------------
            |
            |
```

Optional section for filers to provide additional context or explanations for specific transactions.

---

## Key Form Rules

### Asset Names
- **MUST** use full name (e.g., "Apple Inc. Common Stock")
- **DO NOT** use ticker symbols (e.g., "AAPL")
- Include type of security (Common Stock, Preferred Stock, Bond, etc.)

### Transaction Types
- **Purchase**: Buying new securities (includes reinvestment of dividends >$1,000)
- **Sale**: Selling securities
- **Partial Sale**: Selling only portion of holdings (check "Partial Sale" box)
- **Exchange**: Stock certificate exchanges after merger/acquisition (rare, requires Committee guidance)

### Dates
- **Transaction Date**: Date the security was traded
- **Notification Date**: Date filer was notified of transaction
  - For self-directed: Usually same as transaction date
  - For managed accounts: When filer received statement/notice

### Ownership Codes
- **(blank)**: Transaction by filer only
- **SP**: Transaction in asset held by spouse only
- **DC**: Transaction in asset held by dependent child only
- **JT**: Transaction in jointly-held asset

### Amount Reporting
- Use **gross amount** of transaction (not gain/loss)
- Example: Sell stock for $5,000 that was purchased for $7,000 → Report Column A ($1,001-$15,000), even though $2,000 loss
- For partial sales: Report value of portion sold, not total holdings

---

## Exclusions (NOT Reported on PTR)

The following DO NOT require PTR filing:
- ❌ Real property transactions
- ❌ Widely held mutual funds (if publicly traded or widely diversified)
- ❌ ETFs (Exchange Traded Funds)
- ❌ TSP (Thrift Savings Plan) transactions
- ❌ Stock splits
- ❌ Bequests or inheritances
- ❌ Bank account deposits/withdrawals
- ❌ Certificates of deposit
- ❌ Retirement account rollovers
- ❌ Transactions between filer, spouse, and dependent child

**Note**: Some excluded PTR transactions may still be reported on annual FD Statement.

---

## Filing Deadlines & Penalties

### Due Date
PTR must be filed by **earlier of**:
- (a) 30 days from being made aware of transaction, OR
- (b) 45 days from transaction date

### Late Penalties
- **$200 penalty** assessed for filing more than 30 days late
- Extensions **NOT granted** for PTRs
- Weekend/holiday deadline: Can file electronically, but paper submissions must be received/postmarked by last business day before

### Copies Required
- **Members**: 1 original (with original signature) + 2 photocopies
- **Officers/Employees**: 1 original (with original signature) + 1 photocopy

### Where to File
```
Clerk of the House of Representatives
Legislative Resource Center
Room B-81 Cannon House Office Building
Washington, DC 20515
```

Or electronically via: https://fd.house.gov

---

## Schema Implementation Notes

### OCR Challenges
PTR forms are typically **image-based PDFs**, requiring OCR:

1. **Tabular Structure**: Table cells with checkboxes
2. **Handwriting**: Many fields handwritten (name, dates, asset names)
3. **Checkboxes**: Need to detect checked vs unchecked boxes
4. **Date Format**: MM/DD/YY format (need to expand to full year)
5. **Asset Names**: Often abbreviated or unclear handwriting

### Recommended OCR Approach
1. **AWS Textract**: Best for forms/tables, understands checkbox states
2. **Tesseract**: Free alternative, requires preprocessing
3. **Hybrid**: Use table detection + OCR + validation

### Data Validation Rules
After extraction, validate:
- [ ] Transaction date < Notification date (usually)
- [ ] Only one transaction type checked per row
- [ ] Only one amount column checked per row
- [ ] Owner code is valid (SP/DC/JT or blank)
- [ ] Asset name is not a ticker symbol (heuristic: <6 chars, all caps)
- [ ] Dates are valid and reasonable (not future, not before 1970)
- [ ] Certification signatures present
- [ ] Filer name matches certification signature

---

## Example Structured Output

```json
{
  "filing_id": "20033421",
  "page_count": 2,
  "filer_info": {
    "full_name": "John Doe",
    "filer_type": "Member",
    "state": "CA",
    "district": "12"
  },
  "report_type": {
    "is_initial": true,
    "is_amendment": false
  },
  "ipo_shares_allocated": false,
  "transactions": [
    {
      "owner_code": "JT",
      "asset_name": "Mega Corp. Common Stock",
      "transaction_type": "Purchase",
      "transaction_date": "2020-02-05",
      "notification_date": "2020-03-07",
      "amount_column": "B",
      "amount_range": "$15,001-$50,000",
      "amount_low": 15001,
      "amount_high": 50000
    }
  ],
  "certification": {
    "filer_certified": true,
    "filer_signature_date": "2020-03-15",
    "stock_act_certified": true
  },
  "extraction_metadata": {
    "extraction_method": "ocr_textract",
    "confidence_score": 0.92,
    "pdf_type": "image"
  }
}
```

---

## References

- **Official PTR Form**: docs/PTR_Blank_Form.pdf
- **PTR Instructions**: Pages 1-3 of PTR_Blank_Form.pdf
- **JSON Schema**: ingestion/schemas/house_fd_ptr.json
- **House Ethics Committee**: https://ethics.house.gov/financial-disclosure/
- **Filing Portal**: https://fd.house.gov
