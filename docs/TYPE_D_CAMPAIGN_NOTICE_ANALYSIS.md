# Type D (Campaign Notice) Complete Data Point Analysis

**Filing Type**: Campaign Notice (Type D in Bronze layer)
**Form Title**: CAMPAIGN NOTICE REGARDING FINANCIAL DISCLOSURE REQUIREMENT
**Based on visual inspection of 3 Type D filings (2025)**

---

## KEY FINDING: Simple Notice Form (No Disclosure Required)

**CRITICAL DISCOVERY**: Type D is **NOT a duplicate filing**. It's a notice form filed by candidates who have **not yet raised or spent $5,000** for their campaign, indicating they are not required to file a full Financial Disclosure Statement yet.

**Purpose**: To notify the Clerk that the candidate has not reached the $5,000 threshold requiring full disclosure.

**Complexity**: MINIMAL - Only 5 data fields
**Extraction Strategy**: Simple key-value extraction
**Estimated Implementation Time**: 20-30 minutes

---

## Complete Field Inventory

### Header
- **Form Title**: "CAMPAIGN NOTICE REGARDING FINANCIAL DISCLOSURE REQUIREMENT"
- **Eagle Logo**: Visual element only

### Notice Text (Standard Boilerplate)
"This is to notify you that I have not yet raised (either through contributions or loans from myself or others) or spent in excess of $5,000 for my campaign for the U.S. House of Representatives.

I understand that when I do raise or spend in excess of $5,000 for my campaign, I must file a Financial Disclosure Statement with the Clerk of the House of Representatives according to the deadlines set out on pages 2 and 3 of the Financial Disclosure Instruction booklet, a copy of which has been provided to me by the Clerk."

### Filer Information

1. **Name**:
   - Format: Full name
   - Examples: "Shohreh Y. Fontaine", "Anthony Tomkins", "John Thomas Croisant"

2. **Status**:
   - Value: "Congressional Candidate" (always)

3. **State/District**:
   - Format: State code + district number
   - Examples: "FL06", "UT01", "OK01"

### Signature Section

4. **Digital Signature**:
   - Format: "Digitally Signed: [Name], [MM/DD/YYYY]"
   - Examples:
     - "Digitally Signed: Shohreh Y. Fontaine, 01/21/2025"
     - "Digitally Signed: Anthony Tomkins, 01/29/2025"
     - "Digitally Signed: John Thomas Croisant, 01/30/2025"

5. **Filing ID** (top right):
   - Format: Filing ID #XXXXXXXX
   - Examples: "#40003715", "#40003718", "#40003719"

---

## Document Characteristics

- **Page Count**: 1 page only
- **Consistency**: All samples are identical in structure
- **File Size**: ~47KB (very small)
- **Addressee**: "The Honorable Kevin F. McCumber, Acting Clerk, Office of the Clerk, U.S. House of Representatives, Legislative Resource Center, B81 Cannon House Office Building, Washington, DC20515-6601"

---

## Extraction Strategy

### Approach: Minimal Metadata Extractor

```python
class CampaignNoticeExtractor:
    """Extractor for Type D - Campaign Notice forms."""

    def extract_from_textract(self, doc_id: str, year: int, textract_blocks: List[Dict]) -> Dict:
        """Extract campaign notice metadata."""

        # Build key-value map
        kv_pairs = self._extract_key_value_pairs(textract_blocks)

        # Extract digital signature
        signature_info = self._extract_digital_signature(textract_blocks)

        return {
            "doc_id": doc_id,
            "filing_year": year,
            "filing_type": "Campaign Notice",
            "notice_type": "below_threshold",  # Haven't raised/spent $5,000
            "filer_info": {
                "name": self._find_value(kv_pairs, "Name"),
                "status": "Congressional Candidate",
                "state_district": self._find_value(kv_pairs, "State/District")
            },
            "signature": {
                "digitally_signed_by": signature_info.get("name"),
                "signature_date": signature_info.get("date")
            },
            "metadata": {
                "extraction_method": "textract",
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "confidence_score": 0.98  # Very simple form
            }
        }
```

### Key Methods Needed:

1. **`_extract_key_value_pairs()`**: Standard Textract KEY_VALUE_SET
2. **`_extract_digital_signature()`**: Parse "Digitally Signed: Name, Date" line
3. **`_find_value()`**: Simple key lookup

---

## Structured Output Schema

```json
{
  "doc_id": "40003715",
  "filing_year": 2025,
  "filing_type": "Campaign Notice",
  "notice_type": "below_threshold",
  "filer_info": {
    "name": "Shohreh Y. Fontaine",
    "status": "Congressional Candidate",
    "state_district": "FL06"
  },
  "signature": {
    "digitally_signed_by": "Shohreh Y. Fontaine",
    "signature_date": "2025-01-21"
  },
  "metadata": {
    "extraction_method": "textract",
    "extraction_timestamp": "2025-11-26T...",
    "confidence_score": 0.98
  }
}
```

---

## Testing Checklist

- [ ] Extract name from all 3 samples
- [ ] Extract state/district codes
- [ ] Parse digital signature line
- [ ] Extract signature date in ISO format
- [ ] Verify all samples have identical structure
- [ ] Test on 10+ Type D samples

---

## Comparison to Other Filing Types

| Feature | Type X (Extension) | **Type D (Notice)** | Type C (Candidate) |
|---------|-------------------|---------------------|-------------------|
| **Purpose** | Request more time | Below $5K threshold | Full disclosure |
| **Complexity** | LOW (10 fields) | **MINIMAL (5 fields)** | HIGH (40+ fields) |
| **Financial Data** | None | None | All schedules A-J |
| **Page Count** | 1 | 1 | 2-20+ pages |
| **Extraction Time** | 30-60 min | **20-30 min** | Reuse FormABExtractor |

---

## Samples Analyzed

1. **40003715** - Shohreh Y. Fontaine (FL06)
2. **40003718** - Anthony Tomkins (UT01)
3. **40003719** - John Thomas Croisant (OK01)

**Note**: All Type D samples in 2025 have Filing IDs starting with "40..." (40003xxx range)

---

## Recommendations

### Priority: MEDIUM (99 files = 8.6% of filings)

While Type D represents a decent volume, the filings contain minimal data (no financial information). Implement after more complex types.

### Implementation Approach:

1. **Create simple extractor** (~50 lines of code)
2. **Use Textract KEY_VALUE_SET** for field extraction
3. **Add to Lambda routing** in handler.py
4. **Test on 5-10 samples**
5. **Deploy and process all 99 Type D filings**

### Estimated Time:
- **Implementation**: 20-30 minutes
- **Testing**: 15 minutes
- **Deployment**: 15 minutes
- **Total**: 1 hour

---

## Business Value

**Low Financial Data Value**: These filings contain no financial disclosure information (that's the whole point - they're below the threshold).

**Tracking Value**: Useful for:
- Tracking which candidates haven't filed full disclosures yet
- Identifying timing of when candidates cross the $5,000 threshold
- Campaign activity monitoring

---

**Status**: ✅ ANALYSIS COMPLETE
**Complexity**: MINIMAL (5 fields, no financial data)
**Recommendation**: Low priority - implement after financial disclosure types
**Next Step**: Create `CampaignNoticeExtractor` class
**Date**: 2025-11-26
