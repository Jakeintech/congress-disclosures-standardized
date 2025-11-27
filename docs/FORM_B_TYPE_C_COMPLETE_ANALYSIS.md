# Form B (Type C) Complete Data Point Analysis

**Filing Type**: Candidate Report (Type C in Bronze layer)
**Form Designation**: FORM B - For New Members, Candidates, and New Employees
**Based on visual inspection of 5 diverse 2025 Type C filings**

---

## KEY FINDING: Form B = Form A Structure

**CRITICAL DISCOVERY**: Form B (Candidate Report) uses **IDENTICAL schedule structure** to Form A (Annual Report).

**Implication**: The existing `FormABExtractor` can handle Type C with minimal or no modifications!

---

## Document Structure Comparison

### Header Section - DIFFERENCES from Form A

**Form B Specific Fields:**

1. **Filing Status** (checkbox selection):
   - ☐/☑ New Member of or Candidate for U.S. House of Representatives
     - State: ____________
     - District: ____________
     - Candidates - Date of Election: ____________
   - ☐/☑ New Officer or Employee
     - Employing Office: ____________
     - Staff Filer Type: ☐ Shared ☐ Principal Assistant ☐ to ____________

2. **Period Covered**:
   - Format: "January 1, YYYY to [Filing Date]"
   - Examples: "01/01/2024 - 07/14/2025", "01/01/2023 - 12/19/2024"

**Same as Form A:**
- Filer Name
- Status (Congressional Candidate)
- State/District
- Filing Type (Candidate Report)
- Filing Year
- Filing Date

### Part I - Preliminary Information (6 Questions)

**IDENTICAL to Form A** - Questions A through J:
- A. Assets over $1,000
- B. Income over $200
- C. "Earned" income over $200
- D. Liabilities over $10,000
- E. Reportable positions
- F. Reportable agreements
- J. Compensation over $5,000

**Format**: Yes/No checkboxes (same as Form A)

### Exclusions Section

**IDENTICAL to Form A** - Two Yes/No questions:
1. **Trusts**: "Qualified Blind Trusts" exclusion
2. **Exemption**: Three tests for exemption

---

## Schedule A: Assets and "Unearned" Income

**STRUCTURE**: 100% IDENTICAL to Form A

**All Critical Fields Present:**

1. **Asset Name** (with possible ticker):
   - "Evercore Inc. Class A Common Stock (EVR)"
   - "Amazon.com, Inc. - Common Stock (AMZN)"
   - "Apple Inc. - Common Stock (AAPL)"

2. **Asset Type Code** [XX] - Same codes as Form A:
   - [ST] = Stock
   - [BA] = Bank Account
   - [HE] = Hedge Fund
   - [OL] = Other Liability
   - [RP] = Real Property
   - [5F] = 529 Plan
   - [IH] = Investment/Hedge Fund
   - [PS] = Private Sector
   - [EF] = Exchange Traded Fund

3. **DESCRIPTION Field** (separate line below asset):
   - "DESCRIPTION: Healthcare management platform."
   - "DESCRIPTION: Owns and operates restaurant"
   - "DESCRIPTION: Art gallery business."
   - "DESCRIPTION: Food manufacturer, Chicago, IL."
   - "DESCRIPTION: College savings plan"

4. **LOCATION Field** (separate line for some assets):
   - "LOCATION: New York, NY, US"
   - "LOCATION: Los Angeles, CA, US"
   - "LOCATION: Tustin, CA, US"
   - "LOCATION: TX"

5. **Owner Code**:
   - SP = Spouse
   - JT = Joint
   - DC = Dependent Child
   - (blank) = Filer

6. **Value of Asset** (ranges):
   - "$15,001 - $50,000"
   - "$250,001 - $500,000"
   - "$1,000,001 - $5,000,000"
   - "$5,000,001 - $25,000,000"
   - "None" (for some stock positions)

7. **Income Type(s)** - Can be multiple:
   - "None"
   - "Interest"
   - "Dividends"
   - "Capital Gains"
   - "Capital Gains, Dividends" (comma-separated)
   - "Capital Gains, Rent"
   - "Business income"
   - "Rent"
   - "Tax-Deferred"

8. **Income - Current Year to Filing** (ranges):
   - "$1 - $200"
   - "$1,001 - $2,500"
   - "$5,001 - $15,000"
   - "$1,000,001 - $5,000,000"
   - "None"

9. **Income - Preceding Year** (ranges):
   - "$50,001 - $100,000"
   - "$100,001 - $1,000,000"
   - "$1,000,001 - $5,000,000"
   - "None"

**Special Patterns Observed:**

- **Account Groupings**:
  - "Brokerage Account ⇒" followed by multiple stocks
  - "AMERA C FINNIE ROTH IRA BRKG ⇒" followed by holdings
  - "Amera Finnie 529 ⇒" followed by funds
  - "Climate Avengers Fund, LP ⇒" followed by portfolio companies

- **Investment Vehicle Footer**:
  - "* Investment Vehicle details available at the bottom of this form. For the complete list of asset type abbreviations, please visit https://fd.house.gov/reference/asset-type-codes.aspx"

---

## Schedule C: Earned Income

**STRUCTURE**: 100% IDENTICAL to Form A

**Fields:**
1. Source (employer/payer name)
2. Type (salary, spouse salary, fees, etc.)
3. Amount - Current Year to Filing (exact or "None disclosed.")
4. Amount - Preceding Year (exact or "None disclosed.")

**Note**: May show "None disclosed." instead of actual data

---

## Schedule D: Liabilities

**STRUCTURE**: 100% IDENTICAL to Form A

**Fields:**
1. Owner (SP/DC/JT or blank)
2. Creditor (lender name)
   - Example: "JP Morgan Chase"
3. Date Incurred
   - Example: "April 2016"
4. Type/Description
   - Example: "Mortgage on residential property"
5. Amount of Liability (range)
   - Example: "$1,000,001 - $5,000,000"

**Note**: May show "None disclosed." if no liabilities

---

## Schedule E: Positions

**STRUCTURE**: 100% IDENTICAL to Form A

**Fields:**
1. Position (title)
   - Example: "Director"
2. Name of Organization
   - Example: "Food Access LA"

**Note**: May show "None disclosed."

---

## Schedule F: Agreements

**STRUCTURE**: 100% IDENTICAL to Form A

**Note**: All samples showed "None disclosed."

---

## Schedule J: Compensation in Excess of $5,000 Paid by One Source

**STRUCTURE**: 100% IDENTICAL to Form A

**Fields:**
1. Source (Name and Address)
   - Example: "TekSystems (Dublin, OH, US)"
2. Brief Description of Duties
   - Example: "Software Engineering"

**Note**: May show "None disclosed."

---

## Schedule A Investment Vehicle Details (NEW SECTION)

**UNIQUE TO FORM B** (not in Form A)

**Purpose**: Lists investment vehicles that contain multiple holdings

**Format**: Bulleted list
- "Brokerage Account (Owner: SP)"
- "Rosewood West LLC (Owner: JT)"
  - "LOCATION: US"
- "Climate Avengers Fund, LP (Owner: SP)"

**Note**: This section provides context for grouped assets shown in Schedule A

---

## Certification and Signature Section

**STRUCTURE**: 100% IDENTICAL to Form A

1. **Certification Checkbox**:
   - ☐/☑ "I CERTIFY that the statements I have made on the attached Financial Disclosure Report are true, complete, and correct to the best of my knowledge and belief."

2. **Digital Signature**:
   - Format: "Digitally Signed: [Name], [MM/DD/YYYY]"
   - Examples:
     - "Digitally Signed: Jerrad Shane Christian, 01/9/2025"
     - "Digitally Signed: Esther Kim Varet, 08/06/2025"

---

## Data Extraction Strategy

### Approach: REUSE FormABExtractor

Since Form B structure is identical to Form A, the existing `FormABExtractor` should handle Type C with **zero or minimal changes**.

**Required Updates:**

1. **Update Lambda routing** in `handler.py`:
   ```python
   if filing_type in ["Annual Report", "Candidate Report", "Form A", "Form B"]:
       extractor = FormABExtractor()
   ```

2. **Optional Enhancement** - Extract "Schedule A Investment Vehicle Details":
   - Add new method: `_extract_investment_vehicle_details()`
   - Parse bulleted list at end of document
   - Store in separate field

3. **Test on Type C samples** to verify all fields captured

### Testing Checklist

- [ ] Test FormABExtractor on Type C sample 1 (simple, "None disclosed")
- [ ] Test on Type C sample 2 (medium complexity with assets)
- [ ] Test on Type C sample 3 (large with dependent child accounts)
- [ ] Verify all DESCRIPTION fields captured
- [ ] Verify all LOCATION fields captured
- [ ] Verify asset type codes [XX] extracted
- [ ] Verify stock tickers extracted
- [ ] Verify account groupings preserved
- [ ] Verify Schedule A Investment Vehicle Details extracted (optional)
- [ ] Verify multiple income types parsed correctly

---

## Samples Analyzed

1. **C_small_8221216.pdf** (33KB) - Form B page 1 only
2. **C_typical_10063243.pdf** (63KB) - Simple filing with "None disclosed" for most schedules
3. **C_medium_10063302.pdf** (102KB) - Rich filing with 20+ assets, DESCRIPTION/LOCATION fields
4. **C_large_8220945.pdf** (250KB) - Form B page 1 (rotated/sideways)
5. **C_xlarge_10072676.pdf** (453KB) - Complex filing with dependent child (DC) accounts

---

## Key Differences Summary

| Feature | Form A (Type A) | Form B (Type C) |
|---------|----------------|----------------|
| **Form Name** | Annual Report | Candidate Report |
| **Header** | Standard filer info | Candidate-specific (date of election) |
| **Schedule A** | ✅ Identical | ✅ Identical |
| **Schedule C** | ✅ Identical | ✅ Identical |
| **Schedule D** | ✅ Identical | ✅ Identical |
| **Schedule E** | ✅ Identical | ✅ Identical |
| **Schedule F** | ✅ Identical | ✅ Identical |
| **Schedule J** | ✅ Identical | ✅ Identical |
| **Investment Vehicle Details** | ❌ Not present | ✅ Present (new section) |
| **Exclusions** | ✅ Identical | ✅ Identical |
| **Certification** | ✅ Identical | ✅ Identical |

**Extraction Complexity**: LOW - Can reuse FormABExtractor with 95%+ success

---

## Recommendation

**Immediate Action**: Test existing `FormABExtractor` on Type C samples.

**Expected Result**: 95%+ extraction success with current code (no modifications needed).

**Optional Enhancement**: Add extraction for "Schedule A Investment Vehicle Details" section.

**Time to Production**: <1 hour (testing + optional enhancement)

---

**Status**: ✅ ANALYSIS COMPLETE
**Next Step**: Test FormABExtractor on Type C samples
**Date**: 2025-11-26
