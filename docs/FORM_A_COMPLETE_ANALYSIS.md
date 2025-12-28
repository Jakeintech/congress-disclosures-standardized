# Form A/B Complete Data Point Analysis

**Based on visual inspection of actual 2025 Form A filings**

## Document Structure

### Header Section

**Filer Information:**
- Filing ID (e.g., #10071566)
- Name (full name)
- Status (Congressional Candidate, Member, etc.)
- State/District (e.g., PA07, NJ07)

**Filing Information:**
- Filing Type (Amendment Report, Annual Report, New Filer Report)
- Filing Year
- Filing Date (MM/DD/YYYY)
- Period Covered (MM/DD/YYYY - MM/DD/YYYY)

## Schedule A: Assets and "Unearned" Income

**Critical Data Points (Per Asset):**

1. **Asset Name/Description** (text, may be multi-line)
   - Often includes ticker symbol in parentheses: e.g., "AbbVie Inc. Common Stock (ABBV)"
   - May include account grouping notation: e.g., "IRA 1 ⇒"

2. **Asset Type Code** (in square brackets)
   - Examples: [OT], [5F], [BA], [ST], [IH]
   - Reference URL: https://fd.house.gov/reference/asset-type-codes.aspx
   - **BA** = Bank Account
   - **RP** = Real Property
   - **ST** = Stock
   - **IH** = Investment/Hedge Fund
   - **OT** = Other
   - **5F** = 529 Plan

3. **DESCRIPTION Field** (freeform text under asset name)
   - Examples: "Spouse's simple IRA from work.", "401K account from work", "TSP account"
   - **MUST CAPTURE** - contains crucial context

4. **Owner Code**
   - **SP** = Spouse
   - **DC** = Dependent Child
   - **JT** = Joint
   - **(blank)** = Filer

5. **LOCATION** (for some assets, especially real property)
   - Examples: "PA", "VA"
   - City and/or State

6. **Value of Asset** (range)
   - Examples: "$250,001 - $500,000", "$15,001 - $50,000", "$1,001 - $15,000"
   - Can be "None" for some asset types

7. **Income Type(s)** - MULTIPLE PER ASSET
   - None
   - Interest
   - Dividends
   - Capital Gains
   - Dividends, Interest (can be comma-separated)
   - Capital Gains, Dividends (multiple)
   - Capital Gains, Dividends, Interest

8. **Income - Current Year to Filing** (range or exact amount)
   - Examples: "$201 - $1,000", "$1 - $200", "None"

9. **Income - Preceding Year** (range or exact amount)
   - Examples: "$201 - $1,000", "$1 - $200", "$1,001 - $2,500", "None"

**Special Notations:**
- Account groupings: "IRA 1 ⇒", "529 Plan ⇒", "Janney 529 Daughter", "Janney 529 Son"
- Multiple assets may be listed under same account group

**Footer Note:**
- "* For the complete list of asset type abbreviations, please visit https://fd.house.gov/reference/asset-type-codes.aspx"

## Schedule C: Earned Income

**Per Source:**

1. **Source** (employer/payer name)
   - Examples: "PPL Electric Utilities", "CHA Consulting", "D'Huy Engineering", "PPL Services Corp"

2. **Type**
   - salary
   - spouse salary
   - honoraria
   - fees

3. **Amount - Current Year to Filing**
   - Exact dollar amounts: "$44,410.00", "$38,533.00"
   - Can be: "N/A", "$.00"

4. **Amount - Preceding Year**
   - Exact dollar amounts: "$69,181.00", "$65,475.00", "$319,138.00"
   - Can be: "N/A", "$.00"

## Schedule D: Liabilities

**Per Liability:**

1. **Owner Code** (SP/DC/JT or blank)
2. **Creditor** (name of lender)
3. **Date Incurred** (month/year or full date)
4. **Type/Description** (mortgage, loan, etc.)
5. **Amount** (range)

**Special Case:**
- "None disclosed." - explicitly stated when no liabilities

## Schedule E: Positions

**Per Position:**

1. **Position** (title/role)
   - Examples: "Employee", "Board of Directors", "Chair", "Board of Governors"

2. **Name of Organization**
   - Examples: "PPL", "Ben Franklin Technology Partners of Northeaster Pennsylvania", "Latinas in Tech, Philadelphia Chapter", "Greater Lehigh Valley Chamber of Commerce"

**Special Case:**
- Can list multiple positions for same filer

## Schedule F: Agreements

**Per Agreement:**

1. **Parties involved**
2. **Date of agreement**
3. **Terms/Description**
4. **Status** (active/terminated)

**Special Case:**
- "None disclosed." - explicitly stated when no agreements

## Schedule J: Compensation in Excess of $5,000 Paid by One Source

**Per Compensation:**

1. **Source Name** (organization)
2. **Source Address** (full address)
3. **Brief Description** (of duties/services)

**Special Case:**
- "None disclosed." - explicitly stated

## Exclusions of Spouse, Dependent, or Trust Information

**Two separate Yes/No questions:**

1. **Trusts**:
   - Full question: "Details regarding "Qualified Blind Trusts" approved by the Committee on Ethics and certain other "excepted trusts" need not be disclosed. Have you excluded from this report details of such a trust benefiting you, your spouse, or dependent child?"
   - Radio buttons: ⭕ Yes ⭕ No

2. **Exemption**:
   - Full question: "Have you excluded from this report any other assets, "unearned" income, transactions, or liabilities of a spouse or dependent child because they meet all three tests for exemption?"
   - Radio buttons: ⭕ Yes ⭕ No

## Certification and Signature

1. **Certification Checkbox State**
   - Checked ☑ or Unchecked ☐
   - Text: "I CERTIFY that the statements I have made on the attached Financial Disclosure Report are true, complete, and correct to the best of my knowledge and belief."

2. **Digital Signature**
   - Signer name: "Carol Obando-Derstine"
   - Date: "06/15/2025"
   - Format: "Digitally Signed: [Name], [Date]"

## Data Extraction Priorities

### CRITICAL (Must Capture):
1. Asset type codes [XX]
2. DESCRIPTION fields under assets
3. LOCATION fields
4. Multiple income types per asset
5. Stock tickers in parentheses
6. Account grouping notations
7. Exclusions Yes/No answers
8. Certification checkbox state
9. Digital signature and date
10. "None disclosed" vs empty distinction

### IMPORTANT:
11. Exact dollar amounts in Schedule C (not ranges)
12. N/A vs $.00 distinction
13. Freeform text descriptions
14. Multi-line asset names

### ENHANCEMENT:
15. Asset type code lookups/enrichment
16. Ticker symbol extraction and validation
17. Organization name standardization
18. Address parsing (for Schedule J)

## Observed Variations

1. **Asset Names:**
   - Simple: "American Funds Simple IRA"
   - With ticker: "AbbVie Inc. Common Stock (ABBV)"
   - With notation: "IRA 1 ⇒ Alphabet Inc. - Class A Common Stock (GOOGL)"
   - With description below: Asset name followed by "DESCRIPTION: [text]"

2. **Value Ranges:**
   - Standard: "$250,001 - $500,000"
   - Lower: "$1,001 - $15,000"
   - Upper: "$50,001 - $100,000"
   - None: "None" (literal text)

3. **Income:**
   - Single type: "Interest"
   - Multiple: "Dividends, Interest"
   - Multiple: "Capital Gains, Dividends"
   - Multiple: "Capital Gains, Dividends, Interest"
   - None: "None"

4. **Schedule C Amounts:**
   - Precise: "$44,410.00"
   - Zero: "$.00"
   - Not applicable: "N/A"

## Extraction Strategy

1. **Parse header** for filing metadata
2. **Identify schedule boundaries** (look for "SCHEDULE X:" headers)
3. **For Schedule A**:
   - Extract table rows
   - Parse asset name, extract type code from brackets
   - Look for DESCRIPTION: line below asset
   - Extract ticker from parentheses if present
   - Extract LOCATION: line if present
   - Parse owner, value, income types (comma-separated), income amounts
4. **For Schedule C**: Parse table with exact amounts (not ranges)
5. **For Schedules D/E/F/J**: Check for "None disclosed." vs actual data
6. **Parse Exclusions section**: Extract two Yes/No answers
7. **Parse Certification**: Extract checkbox state and signature/date

## Regex Patterns Needed

```python
# Asset type code
ASSET_TYPE_CODE = r'\[([A-Z0-9]{2,3})\]'

# Stock ticker
STOCK_TICKER = r'\(([A-Z]{1,5})\)'

# Account notation
ACCOUNT_NOTATION = r'(IRA \d+ ⇒|529 Plan ⇒|ROTH IRA ⇒)'

# DESCRIPTION line
DESCRIPTION_LINE = r'DESCRIPTION:\s*(.+?)(?=\n|$)'

# LOCATION line
LOCATION_LINE = r'LOCATION:\s*(.+?)(?=\n|$)'

# Value range
VALUE_RANGE = r'\$?([\d,]+)\s*-\s*\$?([\d,]+)'

# Income types (comma-separated)
INCOME_TYPES = r'(None|Interest|Dividends|Capital Gains|[A-Za-z,\s]+)'

# Exact amount (Schedule C)
EXACT_AMOUNT = r'\$?([\d,]+\.\d{2}|N/A|\$\.00)'

# Digital signature
DIGITAL_SIG = r'Digitally Signed:\s*(.+?),\s*(\d{2}/\d{2}/\d{4})'
```

## Testing Checklist

- [ ] Extract all 9+ assets from sample 1
- [ ] Capture "DESCRIPTION:" fields
- [ ] Extract asset type codes [OT], [5F], etc.
- [ ] Extract stock tickers (ABBV), (GOOGL), (AMZN)
- [ ] Parse multiple income types per asset
- [ ] Capture "None disclosed." for empty schedules
- [ ] Extract Schedule C exact amounts ($44,410.00)
- [ ] Handle N/A and $.00 in Schedule C
- [ ] Extract all 4 positions from Schedule E
- [ ] Parse Exclusions Yes/No answers
- [ ] Extract certification checkbox and signature
