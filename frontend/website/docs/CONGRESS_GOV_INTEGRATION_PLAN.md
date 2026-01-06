# Congress.gov API Integration Plan

## Overview
Complete integration of Congress.gov API to provide comprehensive legislative tracking, bill lifecycle visualization, and member activity analysis.

## Issues Identified
1. ✅ **Politician profile pictures FIXED** - Congress.gov bioguide photos with fallback to initials
2. ✅ **Politician loading pages FIXED** - Proper loading states and error boundaries implemented
3. ✅ **Bill lifecycle pages IMPLEMENTED** - Actions, cosponsors, subjects, summaries, titles tabs added
4. ✅ **Data presentation IMPROVED** - Modern tabbed interface with responsive design
5. 🚧 **Advanced features IN PROGRESS** - Amendments, committees, text versions, related bills (partial)

## Available Congress.gov Endpoints

### Bills (`/bill`)
- ✅ `/bill/{congress}/{billType}/{billNumber}` - Basic details (already implemented)
- 🆕 `/bill/{congress}/{billType}/{billNumber}/actions` - Full action history
- 🆕 `/bill/{congress}/{billType}/{billNumber}/amendments` - All amendments
- 🆕 `/bill/{congress}/{billType}/{billNumber}/committees` - Committee referrals
- 🆕 `/bill/{congress}/{billType}/{billNumber}/cosponsors` - All cosponsors with dates
- 🆕 `/bill/{congress}/{billType}/{billNumber}/relatedbills` - Related legislation
- 🆕 `/bill/{congress}/{billType}/{billNumber}/subjects` - Policy subjects
- 🆕 `/bill/{congress}/{billType}/{billNumber}/summaries` - CRS summaries
- 🆕 `/bill/{congress}/{billType}/{billNumber}/text` - Text versions (PDF, XML, HTML)
- 🆕 `/bill/{congress}/{billType}/{billNumber}/titles` - All bill titles

### Members (`/member`)
- ✅ `/member/{bioguideId}` - Basic member info (already implemented)
- 🆕 `/member/{bioguideId}/sponsored-legislation` - Bills authored by member
- 🆕 `/member/{bioguideId}/cosponsored-legislation` - Bills supported by member
- 🆕 Member photos from: `https://bioguide.congress.gov/bioguide/photo/{firstLetter}/{bioguideId}.jpg`

### Amendments (`/amendment`)
- 🆕 `/amendment/{congress}/{type}/{number}` - Amendment details
- 🆕 `/amendment/{congress}/{type}/{number}/actions` - Amendment actions
- 🆕 `/amendment/{congress}/{type}/{number}/cosponsors` - Amendment sponsors
- 🆕 `/amendment/{congress}/{type}/{number}/text` - Amendment text

### Committees (`/committee`)
- 🆕 `/committee/{chamber}/{committeeCode}` - Committee details
- 🆕 `/committee/{chamber}/{committeeCode}/bills` - Bills referred to committee
- 🆕 `/committee/{chamber}/{committeeCode}/reports` - Committee reports
- 🆕 `/committee/{chamber}/{committeeCode}/nominations` - Nominations

### Additional
- 🆕 `/congress` - Congress sessions
- 🆕 `/summaries/{congress}/{billType}/{billNumber}` - Bill summaries
- 🆕 `/law/{congress}` - Public laws

## Implementation Phases

### Phase 1: Fix Critical Issues ⚠️ (IMMEDIATE)
**Goal:** Fix broken features

#### 1.1 Fix Politician Profile Images
- Add Congress.gov bioguide photo URL construction
- Fallback to initials avatar if photo fails
- Update MemberProfile component

#### 1.2 Fix Loading States
- Fix politician page loading spinner
- Add proper error boundaries
- Handle API failures gracefully

### Phase 2: Enhanced Bill Detail Pages 📜
**Goal:** Show complete bill lifecycle

#### 2.1 Bill Actions Tab
- Timeline view of all actions
- Committee actions highlighted
- Floor votes with results
- Presidential actions

#### 2.2 Bill Amendments Tab
- List all amendments
- Amendment sponsors
- Amendment status
- Link to amendment details

#### 2.3 Bill Committees Tab
- All committee referrals
- Committee reports
- Hearing schedules
- Committee votes

#### 2.4 Bill Text & Versions Tab
- All text versions (Introduced, Engrossed, Enrolled, etc.)
- PDF/HTML/XML download links
- Version comparison view
- Full-text search

#### 2.5 Bill Relationships Tab
- Related bills
- Companion bills
- Superseded bills
- Similar legislation

### Phase 3: Enhanced Member Profiles 👥
**Goal:** Comprehensive member activity tracking

#### 3.1 Member Photo Integration
```typescript
function getMemberPhotoUrl(bioguideId: string): string {
  const firstLetter = bioguideId.charAt(0);
  return `https://bioguide.congress.gov/bioguide/photo/${firstLetter}/${bioguideId}.jpg`;
}
```

#### 3.2 Sponsored Legislation Tab
- All bills sponsored by member
- Success rate (bills passed)
- Policy areas of focus
- Bipartisan score

#### 3.3 Cosponsored Legislation Tab
- Bills member supports
- Cosponsor frequency by member
- Cosponsor network visualization

#### 3.4 Committee Assignments Tab
- Current committees
- Subcommittees
- Leadership positions
- Committee voting record

### Phase 4: Bill Lifecycle Visualization 📊
**Goal:** Interactive timeline showing bill progress

#### 4.1 Timeline Component
- Introduction → Committee → Floor → Passage → Law
- Visual indicators for current stage
- Click to see details at each stage
- Predicted next steps

#### 4.2 Status Indicators
- In Committee (with days)
- Awaiting Floor Vote
- Passed Chamber
- Sent to President
- Became Law / Vetoed

### Phase 5: Committee Explorer 🏛️
**Goal:** Browse and analyze committees

#### 5.1 Committee List Page
- All House/Senate committees
- Member counts
- Bill referrals count
- Activity indicators

#### 5.2 Committee Detail Page
- Committee members with photos
- Recent bills referred
- Committee reports
- Hearing schedules

### Phase 6: Advanced Search & Filters 🔍
**Goal:** Find bills and members easily

#### 6.1 Bill Search Enhancements
- Full-text search across titles/summaries
- Filter by status (introduced, passed chamber, enacted)
- Filter by committee
- Filter by policy area
- Date range filters

#### 6.2 Member Search Enhancements
- Search by name, state, party
- Filter by committee membership
- Filter by legislative effectiveness
- Sort by bills sponsored, passed

## Data Structures

### Bill Lifecycle State Machine
```typescript
enum BillStatus {
  Introduced = 'introduced',
  ReferredToCommittee = 'referred',
  ReportedByCommittee = 'reported',
  PassedChamber = 'passed_chamber',
  PassedBothChambers = 'passed_both',
  PresentedToPresident = 'presented',
  BecameLaw = 'became_law',
  Vetoed = 'vetoed',
  Failed = 'failed'
}

interface BillLifecycleStage {
  status: BillStatus;
  date: string;
  details: string;
  isComplete: boolean;
  isCurrent: boolean;
}
```

### Member Photo URLs
```typescript
// Pattern: https://bioguide.congress.gov/bioguide/photo/{firstLetter}/{bioguideId}.jpg
// Example: https://bioguide.congress.gov/bioguide/photo/P/P000197.jpg (Nancy Pelosi)
```

## UI/UX Improvements

### Bill Detail Page Structure
```
/bills/{congress}/{type}/{number}
├── Overview (existing)
├── 🆕 Lifecycle (timeline visualization)
├── 🆕 Actions (full history)
├── 🆕 Cosponsors (with party/state)
├── 🆕 Committees (referrals & reports)
├── 🆕 Amendments (list with status)
├── 🆕 Related Bills (companions, similar)
├── 🆕 Text Versions (PDF/HTML downloads)
├── 🆕 Summaries (CRS summaries)
└── Trading Correlations (existing)
```

### Member Profile Page Structure
```
/politician/{bioguideId}
├── Overview (with photo!)
├── Trading Activity (existing)
├── 🆕 Sponsored Bills (sortable)
├── 🆕 Cosponsored Bills (with analysis)
├── 🆕 Committee Assignments
├── 🆕 Voting Record
└── 🆕 Network Analysis (cosponsor relationships)
```

## API Rate Limiting Strategy
- Cache Congress.gov responses (24 hours for bills, 7 days for members)
- Use ISR (Incremental Static Regeneration) for bill pages
- Implement request batching for multiple bills
- Add retry logic with exponential backoff

## Success Metrics
- ✅ All politician photos load
- ✅ Zero loading state errors
- ✅ Bill lifecycle visible on every bill page
- ✅ All Congress.gov endpoints integrated
- ✅ <3s page load times
- ✅ Mobile responsive
- ✅ Lighthouse score >85

## Implementation Priority
1. ✅ **COMPLETED:** Fix politician photos & loading states
2. ✅ **COMPLETED:** Add bill actions/cosponsors/subjects/summaries/titles tabs
3. ✅ **COMPLETED:** Add bill lifecycle timeline visualization (BillTimeline component)
4. ✅ **COMPLETED:** Add member sponsored/cosponsored legislation tabs
5. ✅ **COMPLETED:** Amendments tab with sponsor details and descriptions
6. ✅ **COMPLETED:** Related bills tab with relationship types
7. ✅ **COMPLETED:** Text versions tab with PDF/HTML downloads
8. ✅ **COMPLETED:** Network analysis visualizations
   - Trading Network (member-asset connections with aggregation)
   - Influence Tracker (bill-trade-lobbying correlations)
   - Lobbying Network (basic relationships)
9. 🚧 **IN PROGRESS:** Build committee explorer (placeholder page created)
10. 🚧 **IN PROGRESS:** Advanced search filters (partial filtering implemented)
11. ❌ **PENDING:** Committee detail pages with rosters and bills

---

**Next Steps:**
1. Create comprehensive TypeScript types for all Congress.gov endpoints
2. Update API client with new fetcher functions
3. Fix politician profile images
4. Build bill detail tabs (actions, amendments, committees, etc.)
5. Create bill lifecycle timeline component
