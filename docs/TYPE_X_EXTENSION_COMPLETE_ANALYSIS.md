# Type X (Extension Request) Complete Data Point Analysis

**Filing Type**: Extension Request (Type X in Bronze layer)
**Form Title**: CANDIDATE FINANCIAL DISCLOSURE EXTENSION REQUEST FORM
**Based on visual inspection of 3 Type X filings (2025)**

---

## KEY FINDING: Simple Metadata-Only Form

**CRITICAL DISCOVERY**: Type X is a **simple one-page form** with only administrative metadata. No financial schedules or complex data structures.

**Complexity**: MINIMAL - ~10 data fields total
**Extraction Strategy**: Simple key-value extraction (no table parsing needed)
**Estimated Implementation Time**: 30-60 minutes

---

## Complete Field Inventory

### Header
- **Form Title**: "CANDIDATE FINANCIAL DISCLOSURE EXTENSION REQUEST FORM"
- **Committee Logo**: "COMMITTEE ON ETHICS" (visual element only)

### Filer Information

1. **Name of Requestor**:
   - Format: Full name (text field)
   - Examples: "Brendan Boyle", "Hazik Moudi"
   - Can be handwritten or typed

2. **Date** (of request):
   - Format: MM/DD/YYYY or written out
   - Examples: "4/30/2025", "August 19, 2025"

3. **Date of Primary/Special Election**:
   - Format: Month Day, Year
   - Examples: "June 2, 2026", "June 2, 2025"

4. **State/District of Election**:
   - Format: State name/abbreviation + district number
   - Examples: "Wisconsin - 41", "California 48th District"

### Extension Request Details

5. **Financial Disclosure Statement Type** (checkboxes):
   - ☐ Statement due in 2024
   - ☐ Amendment
   - ☐/☑ Other: ____________
     - Example values when "Other" checked:
       - "Statement due January 1, 2025"
       - "Statement due in 2025 year"

6. **The length of time for which extension is requested** (checkboxes):
   - ☐ 30 days
   - ☐ 60 days
   - ☐/☑ 90 days
   - ☐ Other: ____________

### For Ethics Committee Use Only

7. **Days granted**:
   - Format: Number
   - Example: "90"
   - Note: "days granted differ from days requested"

8. **Reason** (checkboxes):
   - ☐ Total days requested exceeds 90
   - ☐ Would result in a due date within 30 days of an election

9. **Committee Decision Date**:
   - Format: M/D/YYYY
   - Examples: "5/7/2025", "8/25/2025"

### Signature Section

10. **Chairman signature** (visual element):
    - Text: "Chairman" and "Ranking Member"
    - Signature lines
    - Text: "Copy to: Legislative Resource Center, B-81 CHoB"
    - Footer: "This page will be posted as directed."

---

## Document Variations Observed

### Handwritten vs Typed:
- **Sample 1** (8220892): Handwritten on printed form (scanned)
- **Sample 2** (9115627): Typed/digital form
- **Sample 3** (8221211): Typed/digital form

### Field Values:
- Extension length: Most request 90 days
- Statement type: Usually "Other - Statement due in [year]"
- Days granted: Matches requested (90 days in samples)

---

## Extraction Strategy

### Approach: Simple Key-Value Extractor

**No complex parsing required** - this is a straightforward form with labeled fields.

### Implementation Plan:

```python
class ExtensionRequestExtractor:
    """Extractor for Type X - Extension Request forms."""

    def extract_from_textract(self, doc_id: str, year: int, textract_blocks: List[Dict]) -> Dict:
        """Extract extension request metadata."""

        # Build key-value map from Textract
        kv_pairs = self._extract_key_value_pairs(textract_blocks)

        return {
            "doc_id": doc_id,
            "filing_year": year,
            "filing_type": "Extension Request",
            "filer_info": {
                "name_of_requestor": self._find_value(kv_pairs, "Name of Requestor"),
                "request_date": self._parse_date(self._find_value(kv_pairs, "Date")),
                "election_date": self._find_value(kv_pairs, "Date of Primary/Special Election"),
                "state_district": self._find_value(kv_pairs, "State/District of Election")
            },
            "extension_details": {
                "statement_type": self._extract_statement_type(textract_blocks),
                "days_requested": self._extract_days_requested(textract_blocks),
                "days_granted": self._find_value(kv_pairs, "Days granted"),
                "committee_decision_date": self._parse_date(self._find_value(kv_pairs, "Date"))
            },
            "metadata": {
                "extraction_method": "textract",
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "confidence_score": 0.95  # High confidence for simple form
            }
        }
```

### Key Methods Needed:

1. **`_extract_key_value_pairs()`**: Use Textract's KEY_VALUE_SET blocks
2. **`_extract_statement_type()`**: Check which checkbox is selected
3. **`_extract_days_requested()`**: Check 30/60/90/Other checkboxes
4. **`_parse_date()`**: Handle various date formats (MM/DD/YYYY, written out)

### Challenges:
- **Handwritten text**: OCR accuracy may vary for handwritten forms
- **Checkbox detection**: Need to detect checked vs unchecked boxes
- **Date formats**: Multiple formats ("4/30/2025" vs "August 19, 2025")

---

## Structured Output Schema

```json
{
  "doc_id": "8220892",
  "filing_year": 2025,
  "filing_type": "Extension Request",
  "filer_info": {
    "name_of_requestor": "Brendan Boyle",
    "request_date": "2025-04-30",
    "election_date": "June 2, 2026",
    "state_district": "Wisconsin - 41"
  },
  "extension_details": {
    "statement_type": "Other - Statement due January 1, 2025",
    "days_requested": 90,
    "days_granted": 90,
    "committee_decision_date": "2025-05-07"
  },
  "metadata": {
    "extraction_method": "textract",
    "extraction_timestamp": "2025-11-26T...",
    "confidence_score": 0.95
  }
}
```

---

## Testing Checklist

- [ ] Extract name from handwritten form (Sample 1)
- [ ] Extract name from typed form (Samples 2-3)
- [ ] Parse various date formats (MM/DD/YYYY, written)
- [ ] Detect "Other" checkbox and extract custom text
- [ ] Detect 30/60/90 days checkboxes
- [ ] Extract "Days granted" from Ethics Committee section
- [ ] Handle missing or unclear fields
- [ ] Test on 10+ Type X samples for accuracy

---

## Comparison to Other Filing Types

| Feature | Type P (PTR) | Type A (Annual) | Type C (Candidate) | **Type X (Extension)** |
|---------|--------------|-----------------|-------------------|----------------------|
| **Complexity** | HIGH | HIGH | HIGH | **MINIMAL** |
| **Schedules** | A,B (transactions) | A-J (all schedules) | A-J (all schedules) | **None** |
| **Data Fields** | 20+ per transaction | 40+ across schedules | 40+ across schedules | **~10 total** |
| **Table Parsing** | Required | Required | Required | **Not needed** |
| **Extraction Time** | 2-3 hours | 3-4 hours | 0 hours (reuse A) | **30-60 min** |

---

## Samples Analyzed

1. **X_sample1_8220892.pdf** (16KB) - Handwritten form for Brendan Boyle
2. **X_sample2_9115627.pdf** (20KB) - Typed form for Hazik Moudi
3. **X_sample3_8221211.pdf** (24KB) - Typed form (to be reviewed)

---

## Recommendations

### Priority: HIGH (361 files = 31.5% of all 2025 filings)

Despite being simple, Type X represents a large volume of filings and should be implemented soon.

### Implementation Approach:

1. **Create simple extractor** (~100 lines of code)
2. **Use Textract KEY_VALUE_SET** for field extraction
3. **Add to Lambda routing** in handler.py
4. **Test on 10 samples** (mix of handwritten and typed)
5. **Deploy and process all 361 Type X filings**

### Estimated Time:
- **Implementation**: 30-60 minutes
- **Testing**: 30 minutes
- **Deployment**: 15 minutes
- **Total**: 1.5-2 hours

---

## Notes

- **No financial data** - This is purely administrative
- **High OCR accuracy expected** for typed forms
- **Lower OCR accuracy** for handwritten forms (but still manageable)
- **Simple validation**: Check that dates are valid, days granted ≤ 90
- **Potential enhancement**: Extract signature/approval status

---

**Status**: ✅ ANALYSIS COMPLETE
**Complexity**: MINIMAL (10 fields, no schedules)
**Recommendation**: Quick implementation - high value for low effort
**Next Step**: Create `ExtensionRequestExtractor` class
**Date**: 2025-11-26
