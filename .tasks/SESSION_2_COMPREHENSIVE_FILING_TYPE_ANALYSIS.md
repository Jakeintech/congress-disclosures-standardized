# Comprehensive Filing Type Analysis Plan

**Goal**: Analyze EVERY filing type structure and build complete extractors

## Filing Types in 2025 Bronze Layer

| Type | Count | Priority | Description | Status |
|------|-------|----------|-------------|--------|
| **C** | 563 | 🔴 CRITICAL | Candidate/New Filer | ⏸️ TODO |
| **X** | 361 | 🔴 CRITICAL | Extension Request | ⏸️ TODO |
| **D** | 99 | 🟡 HIGH | Duplicate Filing | ⏸️ TODO |
| **T** | 49 | 🟡 HIGH | Termination Report | ⏸️ TODO |
| **A** | 32 | ✅ DONE | Annual Report | ✅ 70% Complete |
| **W** | 27 | 🟢 MEDIUM | Unknown (needs research) | ⏸️ TODO |
| **G** | 5 | 🟢 MEDIUM | Gift/Travel | ⏸️ TODO |
| **E** | 5 | 🟢 LOW | Electronic Copy | ⏸️ TODO |
| **B** | 2 | 🟢 LOW | Blind Trust | ⏸️ TODO |
| **H** | 1 | 🟢 LOW | Unknown | ⏸️ TODO |
| **O** | 1 | 🟢 LOW | Unknown | ⏸️ TODO |

**Total Types**: 11 distinct filing types
**Total Files**: 1,145 files

## Analysis Plan Per Filing Type

### Template for Each Type:

```markdown
## Filing Type X: [Name]

### Step 1: Sample Collection
- [ ] Download 3-5 diverse samples
- [ ] Note file sizes (small/medium/large)
- [ ] Note different years if available

### Step 2: Visual Inspection
- [ ] Convert PDFs to images (first 3-5 pages each)
- [ ] Screenshot all unique sections
- [ ] Identify all schedules present

### Step 3: Field Inventory
- [ ] Document header fields
- [ ] Document all schedule types
- [ ] Document special sections (certifications, exclusions, etc.)
- [ ] Note freeform text fields
- [ ] Identify codes/brackets/special formats

### Step 4: Extraction Strategy
- [ ] Identify reusable patterns from other extractors
- [ ] Document unique parsing requirements
- [ ] Define regex patterns needed
- [ ] Plan table parsing approach

### Step 5: Implementation
- [ ] Build/update extractor class
- [ ] Add to Lambda routing
- [ ] Package and deploy
- [ ] Test on samples

### Step 6: Validation
- [ ] Test on 10+ real filings
- [ ] Verify all fields captured
- [ ] Measure extraction completeness
- [ ] Document known issues
```

## Execution Order

### Phase 1: Critical Types (Week 1)
1. **Type C** (563 files) - Candidate/New Filer
   - Similar to Form A but for new candidates
   - Likely has all 9 schedules
   - **Time**: 4-6 hours

2. **Type X** (361 files) - Extension Request
   - Simpler form (metadata only)
   - Reason for extension, new due date
   - **Time**: 2-3 hours

### Phase 2: High Priority (Week 1-2)
3. **Type D** (99 files) - Duplicate Filing
   - Reference to original filing
   - Metadata extraction
   - **Time**: 1-2 hours

4. **Type T** (49 files) - Termination Report
   - Similar to Form A (final report)
   - All schedules like Form A
   - **Time**: 3-4 hours (can reuse Form A extractor)

### Phase 3: Medium Priority (Week 2)
5. **Type W** (27 files) - Unknown
   - Need to identify what this is
   - **Time**: 2-4 hours

6. **Type G** (5 files) - Gift/Travel
   - Schedules G & H only
   - **Time**: 2-3 hours

### Phase 4: Low Priority (Week 2)
7. **Type E, B, H, O** (9 files total)
   - Various special cases
   - **Time**: 3-4 hours total

## Enhanced Form A (Already Started)
- **Time**: 2-3 hours to complete enhancements
- Add missing fields documented in FORM_A_COMPLETE_ANALYSIS.md

## Total Estimated Time

- **Form A Enhancement**: 3 hours
- **Phase 1 (C + X)**: 9 hours
- **Phase 2 (D + T)**: 6 hours
- **Phase 3 (W + G)**: 6 hours
- **Phase 4 (E/B/H/O)**: 4 hours

**Total**: ~28 hours = 3-4 full sessions

## Revised Session Plan

### Session 2: Form A/B Core (Current)
- ✅ Basic Form A extractor built (70% complete)
- ⏸️ Enhancement needed

### Session 2.5: Complete Form A + Type C
- Complete Form A enhancements (3 hours)
- Analyze and build Type C extractor (6 hours)

### Session 2.75: Type X + Type D
- Extension Request extractor (3 hours)
- Duplicate Filing handler (2 hours)

### Session 3: All Remaining Types
- Complete T, W, G, E, B, H, O
- Final testing across all types

## Success Metrics Per Type

For each filing type, achieve:
- ✅ 95%+ field capture rate
- ✅ All schedules identified and extracted
- ✅ Special sections handled (certifications, etc.)
- ✅ Tested on 10+ real filings
- ✅ Documentation complete

## Current Status

**Types Analyzed**: 1 (Form A - 70% complete)
**Types To Go**: 10
**Completion**: 9% (1/11 types analyzed)

**Recommendation**: Systematically work through all types before declaring Session 2 complete.
