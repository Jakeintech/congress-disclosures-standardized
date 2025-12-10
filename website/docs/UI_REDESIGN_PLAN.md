# UI Redesign Plan - Congress Transparency Platform

## Design Philosophy

**Goal**: Create a modern, analytics-focused platform for Congress transparency that makes complex financial and legislative data easily accessible and understandable.

**Inspiration**: Quiver Quant's congressional trading dashboard + shadcn/ui modern blocks

## Core User Flows

1. **Discover** → Find trending stocks, active traders, suspicious correlations
2. **Investigate** → Deep dive into specific members, bills, or trades
3. **Analyze** → Track patterns, correlations, and legislative lifecycle
4. **Export** → Download data for research/journalism

## New Navigation Structure

### Main Sidebar Navigation (Always Visible)

```
🏛️ Congress Transparency

📊 Dashboard (Home)
   ├─ Overview metrics
   ├─ Trending stocks
   ├─ Top traders
   └─ Recent activity

👥 Members
   ├─ All Members (grid view with photos)
   ├─ Trading Leaderboard
   ├─ By Committee
   └─ Performance Metrics

💼 Trading Activity
   ├─ Recent Trades (live table)
   ├─ By Stock
   ├─ By Industry
   └─ Correlations

📜 Bills & Legislation
   ├─ Active Bills
   ├─ Bill-Trade Correlations
   ├─ By Committee
   └─ Policy Areas

🔗 Lobbying Network
   ├─ Network Graph
   ├─ Top Clients
   └─ Influence Tracker

📈 Analytics
   ├─ Congressional Alpha
   ├─ Sector Analysis
   ├─ Timeline Analysis
   └─ Portfolio Tracking

⚙️ Settings
```

## Page Redesigns

### 1. Dashboard (Home) - NEW DESIGN

**Layout**: Modern dashboard with sidebar + main content area

**Top Section** - Key Metrics (4 cards)
```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ Total       │ Active      │ Total       │ Avg Trade   │
│ Members     │ Traders     │ Disclosures │ Volume      │
│ 535         │ 298         │ 24,531      │ $4.2M       │
│ +0 vs Q4    │ +12 vs Q4   │ +423 vs Q4  │ +8.3%       │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

**Middle Section** - Dual Charts
```
┌────────────────────────────────────┬──────────────────────────┐
│ Trading Volume Over Time (Line)    │ Top 10 Traded Stocks     │
│ [Interactive Recharts area chart]  │ [Horizontal bar chart]   │
│ - Filter by party                  │ - AAPL, MSFT, NVDA...   │
│ - Filter by chamber                │ - Click to see details   │
└────────────────────────────────────┴──────────────────────────┘
```

**Bottom Section** - Recent Activity Table
```
Recent High-Value Trades (Last 7 Days)
┌────────────┬─────────────┬────────────┬───────────┬──────────┐
│ Member     │ Stock       │ Type       │ Amount    │ Returns  │
│ (Photo)    │ (Ticker)    │ (Buy/Sell) │ ($Range)  │ (+/-%%)  │
├────────────┼─────────────┼────────────┼───────────┼──────────┤
│ Jane Doe   │ NVDA        │ Purchase   │ $500K-1M  │ +12.3%   │
│ D-CA       │ NVIDIA Corp │ 3d ago     │           │ 🔥       │
└────────────┴─────────────┴────────────┴───────────┴──────────┘
[View all trades →]
```

### 2. Members Page - ENHANCED

**Top Bar** - Search & Filters
```
┌─────────────────────────────────────────────────────────────┐
│ 🔍 Search members...   [Party ▼] [Chamber ▼] [State ▼]    │
│                        [Sort by: Trade Volume ▼]            │
└─────────────────────────────────────────────────────────────┘
```

**View Modes**
- Grid View (current) - Cards with photos
- Table View (new) - Sortable data table with metrics
- Leaderboard View (new) - Ranked by trading activity

**Leaderboard View** (New)
```
Top Traders - Last 365 Days
┌────┬──────────────────┬────────────┬───────────┬────────────┐
│ #  │ Member           │ Trades     │ Volume    │ Alpha      │
├────┼──────────────────┼────────────┼───────────┼────────────┤
│ 1  │ [Photo] Jane Doe │ 156 trades │ $12.3M    │ +23.4%     │
│    │ D-CA, House      │            │           │ 📈 Beating │
├────┼──────────────────┼────────────┼───────────┼────────────┤
│ 2  │ [Photo] John Doe │ 142 trades │ $9.8M     │ +18.2%     │
│    │ R-TX, Senate     │            │           │ 📈 Beating │
└────┴──────────────────┴────────────┴───────────┴────────────┘
```

### 3. Trading Activity Page - NEW PAGE

**Hero Section**
```
Congressional Trading Activity
Real-time tracking of stock trades by U.S. Congress members

[Search by stock ▼] [Search by member ▼] [Export Data →]
```

**Filters Bar** (Sticky)
```
Date: [Last 7 Days ▼]  Party: [All ▼]  Chamber: [All ▼]
Type: [All ▼]  Amount: [All ▼]  Industry: [All ▼]
[Clear Filters] [Save View]
```

**Main Table** (Sortable, Infinite Scroll)
```
┌──────────────┬─────────────┬────────────┬──────────┬──────────┬─────────┐
│ Date         │ Member      │ Stock      │ Type     │ Amount   │ Returns │
├──────────────┼─────────────┼────────────┼──────────┼──────────┼─────────┤
│ 2025-12-08   │ Jane Doe    │ NVDA       │ Purchase │ $500K-1M │ +12.3%  │
│ (3 days ago) │ D-CA        │ NVIDIA     │          │          │ 🔥      │
├──────────────┼─────────────┼────────────┼──────────┼──────────┼─────────┤
│ 2025-12-08   │ John Smith  │ AAPL       │ Sale     │ $250K-   │ -3.2%   │
│ (3 days ago) │ R-TX        │ Apple Inc  │          │ 500K     │         │
└──────────────┴─────────────┴────────────┴──────────┴──────────┴─────────┘
```

### 4. Member Profile Page - REDESIGNED

**Hero Section** (Full Width, Enhanced)
```
┌─────────────────────────────────────────────────────────────────┐
│ [Photo]  Jane Doe                                    [Follow]   │
│ 160x160  Democrat • California • House District 12   [Export]   │
│                                                                  │
│ Serving since 2019 • Financial Services Committee               │
│                                                                  │
│ ┌──────────┬──────────┬──────────┬──────────┬──────────┐       │
│ │ Net Worth│ Trades   │ Volume   │ Alpha    │ Last Trade│       │
│ │ $4.2M    │ 156      │ $12.3M   │ +23.4%   │ 3 days ago│       │
│ │ Est.     │ in 2024  │ in 2024  │ vs SPY   │           │       │
│ └──────────┴──────────┴──────────┴──────────┴──────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

**Tabs** (Enhanced)
1. **Overview** - Summary cards + recent activity
2. **Trading Activity** - All trades with charts
3. **Sponsored Bills** (NEW) - Bills authored by member
4. **Cosponsored Bills** (NEW) - Bills supported
5. **Committee Activity** (NEW) - Committee work
6. **Correlations** (NEW) - Bill-trade timing analysis
7. **Performance** (NEW) - Trading performance metrics

**Overview Tab Content**
```
┌─────────────────────────────────┬──────────────────────────────┐
│ Trading Volume by Month (Chart) │ Top Holdings (Pie Chart)     │
│ [Line chart showing trends]     │ [Sector breakdown]           │
└─────────────────────────────────┴──────────────────────────────┘

Recent Trades (Last 30 Days)
[Table with 10 most recent trades]

Sponsored Legislation (Last 6 Months)
[Cards showing 5 most recent bills with status]
```

### 5. Bill Detail Page - ENHANCED

**Hero Section** (Redesigned)
```
┌───────────────────────────────────────────────────────────────┐
│ 119-HR-1234: Infrastructure Investment Act                    │
│                                                                │
│ Sponsor: Jane Doe (D-CA) • Introduced: Jan 15, 2025          │
│                                                                │
│ Status: [Timeline visualization here]                         │
│ Introduced → Committee → Reported → House Passed → Senate...  │
│    ✓          ✓           ✓            ✓            ⏳        │
│                                                                │
│ ⚠️ TRADING ALERT: 12 members traded related stocks within     │
│    30 days of committee markup                                │
└───────────────────────────────────────────────────────────────┘
```

**Tabs** (Reorganized)
1. **Summary** - Quick overview + CRS summary
2. **Timeline** (NEW) - Visual lifecycle with dates
3. **Sponsors** - Sponsor + all cosponsors
4. **Content** - Text, titles, subjects
5. **Committee Work** - Referrals, hearings, reports
6. **Amendments** - All proposed changes
7. **Related Bills** - Companion & similar bills
8. **Trade Correlations** (ENHANCED) - Member trades + timing analysis

**Timeline Tab** (NEW - Priority)
```
Bill Lifecycle Timeline
[Visual timeline with interactive nodes]

Jan 15, 2025  ● Introduced in House
              Rep. Jane Doe (D-CA)

Jan 18, 2025  ● Referred to Committee on Transportation

Feb 3, 2025   ● Committee Hearing Held
              23 witnesses testified

Feb 10, 2025  ● Reported by Committee (Amended)
              Vote: 28-15 along party lines

Mar 1, 2025   ● Passed House
              Vote: 232-203
              ⚠️ 8 members traded infrastructure stocks
                 within 7 days

Mar 5, 2025   ● Received in Senate

Mar 8, 2025   ⏳ Pending in Senate Committee
              Expected markup: TBD
```

### 6. Analytics Dashboard - NEW PAGE

**Section 1** - Congressional Alpha
```
Congressional Trading Performance vs Market
[Large line chart comparing Congressional trades to S&P 500]

Key Metrics:
- 1Y Return: +18.2% (vs SPY +12.4%)
- Sharpe Ratio: 1.34
- Win Rate: 64.2%
- Average Hold Time: 47 days
```

**Section 2** - Sector Analysis
```
Most Traded Sectors (Last 365 Days)
[Horizontal bar chart]
- Technology: 2,834 trades ($1.2B)
- Healthcare: 1,923 trades ($890M)
- Finance: 1,567 trades ($670M)
```

**Section 3** - Timing Analysis
```
Trade Timing Relative to Market Events
[Heatmap showing trades before earnings, before bills, etc.]
```

## New Components to Build

### 1. AppSidebar Component
- Collapsible navigation
- Icon-only collapsed state
- Active route highlighting
- User profile at bottom

### 2. StatCard Component
```tsx
<StatCard
  title="Total Trades"
  value="24,531"
  change="+423 vs Q4"
  trend="up"
  icon={TrendingUpIcon}
/>
```

### 3. MemberLeaderboard Component
- Sortable ranking table
- Member photos + party colors
- Trading metrics
- Link to profiles

### 4. TradeTable Component (Enhanced)
- Sortable columns
- Filterable by all dimensions
- Infinite scroll
- Export functionality
- Real-time updates

### 5. BillTimeline Component (NEW - Priority)
- Visual timeline with milestones
- Interactive nodes
- Trade correlation markers
- Expandable details

### 6. PerformanceChart Component
- Line chart comparing congressional trades to market
- Multiple timeframes (1W, 1M, 3M, 1Y, All)
- Tooltip with detailed metrics

### 7. SearchCommand Component
- Cmd+K quick search
- Search members, bills, stocks
- Recent searches
- Keyboard navigation

## Color Scheme

**Primary Colors**
- Blue (Democrats): `hsl(217, 91%, 60%)`
- Red (Republicans): `hsl(0, 84%, 60%)`
- Purple (Independents): `hsl(280, 70%, 60%)`

**Semantic Colors**
- Success/Profit: `hsl(142, 76%, 36%)`
- Warning/Alert: `hsl(38, 92%, 50%)`
- Danger/Loss: `hsl(0, 84%, 60%)`
- Neutral: `hsl(240, 5%, 65%)`

**Data Visualization Palette**
- Chart colors from Recharts default palette
- High contrast for accessibility

## Typography

- **Headings**: Inter or system font stack
- **Body**: Inter or system font stack
- **Monospace** (tickers, amounts): JetBrains Mono or system monospace

## Responsive Design

**Desktop** (>1024px)
- Sidebar always visible
- Multi-column layouts
- Large charts

**Tablet** (768px - 1024px)
- Collapsible sidebar
- 2-column layouts
- Medium charts

**Mobile** (<768px)
- Hidden sidebar (hamburger menu)
- Single column
- Compact cards
- Swipeable tabs

## Implementation Priority

### Phase 1: Core Layout (IMMEDIATE)
1. ✅ Install shadcn/ui sidebar
2. Create AppSidebar component
3. Create root layout with sidebar
4. Migrate navigation structure

### Phase 2: Dashboard Redesign
1. Create StatCard component
2. Add Recharts area/line charts
3. Create MemberLeaderboard
4. Enhance recent trades table

### Phase 3: Enhanced Tables
1. Build advanced TradeTable
2. Add sorting/filtering
3. Add infinite scroll
4. Add export functionality

### Phase 4: Bill Timeline (NEW FEATURE)
1. Create BillTimeline component
2. Parse action data into timeline format
3. Add trade correlation markers
4. Make interactive

### Phase 5: Member Legislation Views
1. Add "Sponsored Bills" tab
2. Add "Cosponsored Bills" tab
3. Create legislation summary cards
4. Add success rate metrics

### Phase 6: Analytics Dashboard
1. Create Congressional Alpha metrics
2. Build performance comparison chart
3. Add sector analysis
4. Create timing analysis heatmap

## Technical Stack

- **UI Components**: shadcn/ui (Radix UI + Tailwind)
- **Charts**: Recharts
- **Icons**: Lucide React
- **State**: React hooks + Context
- **Data Fetching**: Existing API client
- **Styling**: Tailwind CSS

## Accessibility

- WCAG 2.1 AA compliance
- Keyboard navigation
- Screen reader support
- High contrast mode
- Focus indicators

---

**Next Steps**: Start with Phase 1 - implement sidebar navigation and new layout structure.
