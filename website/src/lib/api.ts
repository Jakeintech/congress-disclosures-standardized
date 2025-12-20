/**
 * API Client for Congress Financial Disclosures
 *
 * Handles all API calls to the Lambda backend with ISR fallback
 * for archived congress data.
 *
 * All functions use strict TypeScript types from src/types/api.ts
 */

import type {
    ApiResponse,
    DashboardSummary,
    TrendingStock,
    TopTrader,
    CongressMember,
    MemberProfile,
    MembersParams,
    Bill,
    BillDetail,
    BillsParams,
    Transaction,
    TransactionsParams,
    TripleCorrelation,
    TripleCorrelationsParams,
    NetworkGraphData,
    PortfolioHolding,
    BillAction,
    Cosponsor,
    Subject,
    BillSummary,
    Amendment,
    RelatedBill,
    SectorData,
    TimingData,
    PatternInsights,
    PatternInsight,
    Conflict,
    ConflictSummary,
    LobbyingActivity,
    PortfolioData,
    AlphaData,
    MemberPortfolio,
    Committee,
    PaginationMeta,
    PaginatedBillActions,
    PaginatedBillCosponsors,
    PaginatedBillSubjects,
    PaginatedBillSummaries,
    PaginatedBillTitles,
    PaginatedBillAmendments,
    PaginatedRelatedBills,
    PaginatedBillCommittees,
    TradingTimelineData,
} from '@/types/api';

// Re-export types for convenience
export type {
    MembersParams,
    BillsParams,
    TransactionsParams,
    TripleCorrelationsParams,
    CongressMember,
    Bill,
    Transaction,
    TrendingStock,
    TopTrader,
};

// API base URL - set via environment or default to production
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com';

// Archived congress threshold - use ISR files for these
const ARCHIVED_CONGRESS_THRESHOLD = 118;

/**
 * Generic fetch wrapper with error handling and type safety
 */
async function fetchApi<T>(url: string): Promise<T> {
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
}

/**
 * Fetch bill details with ISR fallback for archived congresses
 */
export async function fetchBillDetail(billId: string) {
    const parts = billId.toLowerCase().split('-');
    if (parts.length !== 3) {
        throw new Error('Invalid bill ID format');
    }

    const congress = parseInt(parts[0], 10);
    const billType = parts[1];
    const billNumber = parts[2];

    // For archived congresses, try ISR file first
    if (congress <= ARCHIVED_CONGRESS_THRESHOLD) {
        try {
            const isrUrl = `/data/bill_details/${congress}/${billType}/${billNumber}.json`;
            const response = await fetch(isrUrl);
            if (response.ok) {
                console.log(`[ISR] Loaded from static file: ${isrUrl}`);
                return response.json();
            }
        } catch (e) {
            console.log('[ISR] Static file not found, falling back to API');
        }
    }

    // Fallback to API
    const url = `${API_BASE}/v1/congress/bills/${congress}/${billType}/${billNumber}`;
    const rawData = await fetchApi<{ data?: any }>(url);
    const result = rawData.data || rawData;

    // Sanitize response to ensure no missing fields crash the UI
    // API v1 sometimes returns partial data for new bills (119th congress)
    return {
        bill: {
            ...result.bill,
            congress: result.bill?.congress || congress,
            bill_type: result.bill?.bill_type || billType,
            bill_number: result.bill?.bill_number || billNumber,
            title: result.bill?.title || `Bill ${billType.toUpperCase()} ${billNumber}`,
            latest_action_date: result.bill?.latest_action_date || null,
            latest_action_text: result.bill?.latest_action_text || null,
        },
        sponsor: result.sponsor || {
            bioguide_id: result.bill?.sponsor_bioguide_id,
            name: result.bill?.sponsor_name,
            party: result.bill?.sponsor_party || result.bill?.sponsor_name?.match(/\[(\w)-/)?.[1] || 'Unknown',
            state: result.bill?.sponsor_state || result.bill?.sponsor_name?.match(/-(\w{2})\]/)?.[1] || 'US'
        },
        cosponsors: result.cosponsors || [],
        cosponsors_count: result.cosponsors_count || result.bill?.cosponsors_count || 0,
        actions_recent: result.actions_recent || [],
        actions: result.actions || [],
        actions_count_total: result.actions_count_total || (result.actions_recent?.length || 0),
        industry_tags: result.industry_tags || [],
        trade_correlations: result.trade_correlations || [],
        trade_correlations_count: result.trade_correlations_count || 0,
        summary: result.summary,
        text_versions: result.text_versions,
        subjects: result.subjects,
        titles: result.titles,
        committees: result.committees,
        related_bills: result.related_bills,
        congress_gov_url: result.congress_gov_url || `https://www.congress.gov/bill/${result.bill?.congress}th-congress/${result.bill?.bill_type === 'hr' ? 'house-bill' : 'senate-bill'}/${result.bill?.bill_number}`
    };
}

import { parseAPIResponse, type BillsResponse } from './api-types';

// ... (keep existing imports)

/**
 * Fetch bills list with filters
 */
export async function fetchBills(params: BillsParams = {}): Promise<Bill[]> {
    const searchParams = new URLSearchParams();

    if (params.congress) searchParams.set('congress', params.congress.toString());
    if (params.billType) searchParams.set('bill_type', params.billType);
    if (params.sponsor) searchParams.set('sponsor', params.sponsor);
    if (params.industry) searchParams.set('industry', params.industry);
    if (params.hasTradeCorrelations !== undefined) {
        searchParams.set('has_trade_correlations', params.hasTradeCorrelations.toString());
    }
    if (params.sortBy) searchParams.set('sort_by', params.sortBy);
    if (params.sortOrder) searchParams.set('sort_order', params.sortOrder);
    if (params.limit) searchParams.set('limit', params.limit.toString());
    if (params.offset) searchParams.set('offset', params.offset.toString());

    const url = `${API_BASE}/v1/congress/bills?${searchParams.toString()}`;
    const raw = await fetchApi(url);

    // Use type-safe parser with explicit typing
    return parseAPIResponse<Bill>(raw, {
        expectPaginated: true
    }) as Bill[];
}

/**
 * Fetch members list
 */
export async function fetchMembers(params: MembersParams = {}): Promise<{ data: CongressMember[], pagination: PaginationMeta }> {
    const searchParams = new URLSearchParams();

    if (params.congress) searchParams.set('congress', params.congress.toString());
    if (params.chamber) searchParams.set('chamber', params.chamber);
    if (params.party) searchParams.set('party', params.party);
    if (params.state) searchParams.set('state', params.state);
    if (params.sortBy) searchParams.set('sort_by', params.sortBy);
    if (params.sortOrder) searchParams.set('sort_order', params.sortOrder);
    if (params.limit) searchParams.set('limit', params.limit.toString());
    if (params.offset) searchParams.set('offset', params.offset.toString());

    const url = `${API_BASE}/v1/congress/members?${searchParams.toString()}`;
    const raw = await fetchApi<any>(`${url}`);

    const items = parseAPIResponse<CongressMember>(raw, { expectPaginated: true }) as CongressMember[];
    const pagination = (raw.data?.pagination || raw.pagination || { total: items.length, count: items.length, limit: 50, offset: 0 }) as PaginationMeta;

    return {
        data: items,
        pagination
    };
}

/**
 * Fetch member profile
 */
export async function fetchMemberProfile(bioguideId: string): Promise<MemberProfile> {
    const raw = await fetchApi<any>(`${API_BASE}/v1/congress/members/${bioguideId}`);
    return parseAPIResponse<MemberProfile>(raw) as MemberProfile;
}

/**
 * Fetch member trades
 */
export async function fetchMemberTrades(bioguideId: string, limit = 50): Promise<Transaction[]> {
    const raw = await fetchApi<{ data?: Transaction[] }>(
        `${API_BASE}/v1/members/${bioguideId}/trades?limit=${limit}`
    );
    const data = (Array.isArray(raw) ? raw : raw.data) || [];
    return data as Transaction[];
}

/**
 * Fetch transactions
 */
export async function fetchTransactions(params: TransactionsParams = {}): Promise<Transaction[]> {
    const searchParams = new URLSearchParams();

    if (params.ticker) searchParams.set('ticker', params.ticker);
    if (params.member) searchParams.set('member', params.member);
    if (params.tradeType) searchParams.set('trade_type', params.tradeType);
    if (params.minAmount) searchParams.set('min_amount', params.minAmount);
    if (params.limit) searchParams.set('limit', params.limit.toString());
    if (params.offset) searchParams.set('offset', params.offset.toString());

    const url = `${API_BASE}/v1/trades?${searchParams.toString()}`;
    const raw = await fetchApi<any>(`${url}`);
    return parseAPIResponse<Transaction>(raw, { expectPaginated: true }) as Transaction[];
}

/**
 * Fetch trending stocks
 */
export async function fetchTrendingStocks(limit = 10): Promise<TrendingStock[]> {
    try {
        const raw = await fetchApi<{ stocks?: TrendingStock[], trending_stocks?: TrendingStock[] }>(
            `${API_BASE}/v1/analytics/trending-stocks?limit=${limit}`
        );
        // Handle both legacy (trending_stocks) and standardized (stocks) formats
        return raw.stocks || raw.trending_stocks || [];
    } catch (e) {
        console.warn("Failed to fetch trending stocks", e);
        return [];
    }
}

/**
 * Fetch top traders
 */
export async function fetchTopTraders(limit = 10): Promise<TopTrader[]> {
    try {
        const raw = await fetchApi<{ traders?: TopTrader[], top_traders?: TopTrader[] }>(
            `${API_BASE}/v1/analytics/top-traders?limit=${limit}`
        );
        // Handle both legacy (top_traders) and standardized (traders) formats
        return raw.traders || raw.top_traders || [];
    } catch (e) {
        console.warn("Failed to fetch top traders", e);
        return [];
    }
}

/**
 * Fetch lobbying activity for a bill
 */
export async function fetchBillLobbyingActivity(billId: string): Promise<LobbyingActivity | null> {
    const raw = await fetchApi<{ data?: LobbyingActivity }>(
        `${API_BASE}/v1/congress/bills/${billId}/lobbying`
    );
    return raw.data || (raw as unknown as LobbyingActivity) || null;
}

/**
 * Fetch lobbying network graph data
 */
export async function fetchLobbyingNetwork() {
    try {
        const raw = await fetchApi<{ data?: any }>(
            `${API_BASE}/v1/lobbying/network`
        );
        return raw.data || raw;
    } catch (e) {
        console.warn("Failed to fetch lobbying network", e);
        return null;
    }
}

/**
 * Fetch triple correlations (trade-bill-lobbying)
 */

export async function fetchTripleCorrelations(params: {
    year?: string;
    min_score?: number;
    member_bioguide?: string;
    ticker?: string;
    bill_id?: string;
    limit?: number;
} = {}) {
    try {
        const searchParams = new URLSearchParams();
        if (params.year) searchParams.append('year', params.year);
        if (params.min_score) searchParams.append('min_score', params.min_score.toString());
        if (params.member_bioguide) searchParams.append('member_bioguide', params.member_bioguide);
        if (params.ticker) searchParams.append('ticker', params.ticker.toUpperCase());
        if (params.bill_id) searchParams.append('bill_id', params.bill_id.toLowerCase());
        if (params.limit) searchParams.append('limit', params.limit.toString());

        const url = `${API_BASE}/v1/correlations/triple?${searchParams.toString()}`;
        const raw = await fetchApi<{ data?: any }>(url);
        return raw.data || raw;
    } catch (e) {
        console.warn("Failed to fetch triple correlations", e);
        return { correlations: [] };
    }
}

/**
 * Fetch dashboard summary
 */
export async function fetchDashboardSummary(): Promise<{
    totalMembers: number;
    totalTransactions: number;
    totalFilings: number;
    totalBills: number;
}> {
    const data = await fetchApi<ApiResponse<DashboardSummary>>(`${API_BASE}/v1/analytics/summary`);
    const result = data.data || (data as unknown as DashboardSummary);

    // Map to frontend interface
    return {
        totalMembers: result.members?.total || 0,
        totalTransactions: result.trades?.total || 0,
        totalFilings: result.filings?.total || 0,
        totalBills: result.bills?.total || 0
    };
}

/**
 * Fetch sector trading activity
 */
export async function fetchSectorActivity(): Promise<SectorData[]> {
    try {
        const raw = await fetchApi<{ sectors?: SectorData[], message?: string }>(
            `${API_BASE}/v1/analytics/sector-activity`
        );
        return raw.sectors || [];
    } catch (e) {
        console.warn("Failed to fetch sector activity", e);
        return [];
    }
}

/**
 * Fetch congressional alpha data
 */
export async function fetchCongressionalAlpha(type: 'member' | 'party' | 'sector_rotation' = 'member', limit = 10): Promise<AlphaData[]> {
    try {
        const raw = await fetchApi<{ data?: AlphaData[] }>(
            `${API_BASE}/v1/analytics/alpha?type=${type}&limit=${limit}`
        );
        return raw.data || (Array.isArray(raw) ? raw : []);
    } catch (e) {
        console.warn(`Failed to fetch ${type} alpha`, e);
        return [];
    }
}
export async function fetchPatternInsights(type: 'trending' | 'timing' | 'sector' = 'trending'): Promise<PatternInsights | null> {
    try {
        const raw = await fetchApi<PatternInsights>(
            `${API_BASE}/v1/analytics/insights?type=${type}`
        );
        return raw;
    } catch (e) {
        console.warn(`Failed to fetch ${type} insights`, e);
        return null;
    }
}

/**
 * Fetch conflict of interest detection data
 */
export async function fetchConflicts(severity = 'all', limit = 10): Promise<{ conflicts: Conflict[], summary: ConflictSummary | null }> {
    try {
        const raw = await fetchApi<{ conflicts?: Conflict[], summary?: ConflictSummary }>(
            `${API_BASE}/v1/analytics/conflicts?severity=${severity}&limit=${limit}`
        );
        return {
            conflicts: raw.conflicts || [],
            summary: raw.summary || null
        };
    } catch (e) {
        console.warn("Failed to fetch conflicts", e);
        return { conflicts: [], summary: null };
    }
}

/**
 * Fetch portfolio reconstruction data
 */
export async function fetchPortfolios(params: {
    member_id?: string;
    limit?: number;
    include_holdings?: boolean;
} = {}): Promise<PortfolioData[]> {
    try {
        const searchParams = new URLSearchParams();
        if (params.member_id) searchParams.set('member_id', params.member_id);
        if (params.limit) searchParams.set('limit', String(params.limit));
        if (params.include_holdings) searchParams.set('include_holdings', 'true');

        const raw = await fetchApi<{ portfolios?: PortfolioData[] }>(
            `${API_BASE}/v1/analytics/portfolio?${searchParams.toString()}`
        );
        return raw.portfolios || (Array.isArray(raw) ? raw : []);
    } catch (e) {
        console.warn("Failed to fetch portfolios", e);
        return [];
    }
}

// Network graph types are imported from @/types/api

/**
 * Fetch Network Graph
 */
export async function fetchNetworkGraph(params: {
    year?: number;
    view_mode?: 'aggregate' | 'member_detail';
    bioguide_id?: string;
    congress?: number;
    limit?: number;
} = {}): Promise<NetworkGraphData> {
    const searchParams = new URLSearchParams();
    if (params.year) searchParams.set('year', params.year.toString());
    if (params.view_mode) searchParams.set('view_mode', params.view_mode);
    if (params.bioguide_id) searchParams.set('bioguide_id', params.bioguide_id);
    if (params.congress) searchParams.set('congress', params.congress.toString());
    if (params.limit) searchParams.set('limit', params.limit.toString());

    try {
        const res = await fetch(`${API_BASE}/v1/analytics/network-graph?${searchParams.toString()}`);
        if (!res.ok) {
            console.warn(`Network graph API error: ${res.status}`);
            return { nodes: [], links: [] };
        }
        const json = await res.json();
        const apiData = json.data || json;

        // Handle both nested and flat responses for backward compatibility
        const graphData = apiData.graph || apiData;

        return {
            nodes: graphData.nodes || [],
            links: graphData.links || [],
            aggregated_nodes: apiData.aggregated_nodes,
            aggregated_links: apiData.aggregated_links,
            summary_stats: apiData.summary_stats,
            metadata: apiData.metadata
        };
    } catch (e) {
        console.error("Fetch network graph failed", e);
        throw e;
    }
}

/**
 * Fetch member assets (portfolio)
 */
export async function fetchMemberAssets(bioguideId: string): Promise<PortfolioHolding[]> {
    const raw = await fetchApi<{ data?: { holdings: PortfolioHolding[] } }>(`${API_BASE}/v1/members/${bioguideId}/portfolio`);
    const result = raw.data || (raw as any);
    return result.holdings || [];
}

/**
 * Fetch bill text content
 */
export async function fetchBillText(billId: string) {
    try {
        const [congress, billType, billNumber] = billId.toLowerCase().split('-');
        const raw = await fetchApi<{
            data?: {
                text_url?: string,
                content?: string,
                format?: string,
                text_versions?: Array<{
                    type: string,
                    date: string,
                    formats: Array<{ type: string, url: string }>
                }>,
                content_url?: string
            }
        }>(
            `${API_BASE}/v1/congress/bills/${congress}/${billType}/${billNumber}/text`
        );
        const result = raw.data || raw;
        // @ts-ignore - handling both wrapped and unwrapped
        return result;
    } catch (e) {
        console.warn("Failed to fetch bill text", e);
        return null;
    }
}

/**
 * Fetch all congressional committees
 */
export async function fetchCommittees(congress = 119): Promise<Committee[]> {
    try {
        const raw = await fetchApi<any>(
            `${API_BASE}/v1/congress/committees?congress=${congress}`
        );
        return parseAPIResponse<Committee>(raw, { expectPaginated: true }) as Committee[];
    } catch (e) {
        console.warn("Failed to fetch committees", e);
        return [];
    }
}

/**
 * Fetch committee details
 */
export async function fetchCommitteeDetail(chamber: string, committeeCode: string, congress = 119) {
    try {
        const raw = await fetchApi<any>(
            `${API_BASE}/v1/congress/committees/${chamber}/${committeeCode}?congress=${congress}`
        );
        // Standardized response is flattened
        return raw.data || raw;
    } catch (e) {
        console.warn(`Failed to fetch committee ${chamber}/${committeeCode}`, e);
        return null;
    }
}

/**
 * Fetch committee bills
 */
export async function fetchCommitteeBills(chamber: string, committeeCode: string, limit = 50, offset = 0) {
    try {
        const raw = await fetchApi<any>(
            `${API_BASE}/v1/congress/committees/${chamber}/${committeeCode}/bills?limit=${limit}&offset=${offset}`
        );
        return raw.bills || raw.data?.bills || [];
    } catch (e) {
        console.warn(`Failed to fetch bills for committee ${chamber}/${committeeCode}`, e);
        return [];
    }
}

/**
 * Fetch committee members
 */
export async function fetchCommitteeMembers(chamber: string, committeeCode: string, limit = 250, offset = 0) {
    try {
        const raw = await fetchApi<any>(
            `${API_BASE}/v1/congress/committees/${chamber}/${committeeCode}/members?limit=${limit}&offset=${offset}`
        );
        return raw.members || raw.data?.members || [];
    } catch (e) {
        console.warn(`Failed to fetch members for committee ${chamber}/${committeeCode}`, e);
        return [];
    }
}

/**
 * Fetch committee reports
 */
export async function fetchCommitteeReports(chamber: string, committeeCode: string, limit = 50, offset = 0) {
    try {
        const raw = await fetchApi<any>(
            `${API_BASE}/v1/congress/committees/${chamber}/${committeeCode}/reports?limit=${limit}&offset=${offset}`
        );
        return raw.reports || raw.data?.reports || [];
    } catch (e) {
        console.warn(`Failed to fetch reports for committee ${chamber}/${committeeCode}`, e);
        return [];
    }
}

/**
 * Fetch bill committees
 */
export async function fetchBillCommittees(billId: string): Promise<PaginatedBillCommittees> {
    const [congress, billType, billNumber] = billId.toLowerCase().split('-');
    try {
        const raw = await fetchApi<{ data?: PaginatedBillCommittees } & Partial<PaginatedBillCommittees>>(
            `${API_BASE}/v1/congress/bills/${congress}/${billType}/${billNumber}/committees`
        );
        if (raw.data) return raw.data;
        if (raw.committees) return { committees: raw.committees, count: raw.count || 0 };
        return { committees: [], count: 0 };
    } catch (e) {
        console.warn("Failed to fetch bill committees", e);
        return { committees: [], count: 0 };
    }
}

/**
 * Fetch bill cosponsors
 */
export async function fetchBillCosponsors(billId: string): Promise<PaginatedBillCosponsors> {
    const [congress, billType, billNumber] = billId.toLowerCase().split('-');
    try {
        const raw = await fetchApi<{ data?: PaginatedBillCosponsors } & Partial<PaginatedBillCosponsors>>(
            `${API_BASE}/v1/congress/bills/${congress}/${billType}/${billNumber}/cosponsors`
        );
        if (raw.data) return raw.data;
        if (raw.cosponsors) return { cosponsors: raw.cosponsors, count: raw.count || 0 };
        return { cosponsors: [], count: 0 };
    } catch (e) {
        console.warn("Failed to fetch bill cosponsors", e);
        return { cosponsors: [], count: 0 };
    }
}

/**
 * Fetch bill subjects
 */
export async function fetchBillSubjects(billId: string): Promise<PaginatedBillSubjects> {
    const [congress, billType, billNumber] = billId.toLowerCase().split('-');
    try {
        const raw = await fetchApi<{ data?: PaginatedBillSubjects } & Partial<PaginatedBillSubjects>>(
            `${API_BASE}/v1/congress/bills/${congress}/${billType}/${billNumber}/subjects`
        );
        if (raw.data) return raw.data;
        if (raw.subjects) return { subjects: raw.subjects, count: raw.count || 0 };
        return { subjects: [], count: 0 };
    } catch (e) {
        console.warn("Failed to fetch bill subjects", e);
        return { subjects: [], count: 0 };
    }
}

/**
 * Fetch bill summaries
 */
export async function fetchBillSummaries(billId: string): Promise<PaginatedBillSummaries> {
    const [congress, billType, billNumber] = billId.toLowerCase().split('-');
    try {
        const raw = await fetchApi<{ data?: PaginatedBillSummaries } & Partial<PaginatedBillSummaries>>(
            `${API_BASE}/v1/congress/bills/${congress}/${billType}/${billNumber}/summaries`
        );
        if (raw.data) return raw.data;
        if (raw.summaries) return { summaries: raw.summaries, count: raw.count || 0 };
        return { summaries: [], count: 0 };
    } catch (e) {
        console.warn("Failed to fetch bill summaries", e);
        return { summaries: [], count: 0 };
    }
}

/**
 * Fetch bill titles
 */
export async function fetchBillTitles(billId: string): Promise<PaginatedBillTitles> {
    const [congress, billType, billNumber] = billId.toLowerCase().split('-');
    try {
        const raw = await fetchApi<{ data?: PaginatedBillTitles } & Partial<PaginatedBillTitles>>(
            `${API_BASE}/v1/congress/bills/${congress}/${billType}/${billNumber}/titles`
        );
        if (raw.data) return raw.data;
        if (raw.titles) return { titles: raw.titles, count: raw.count || 0 };
        return { titles: [], count: 0 };
    } catch (e) {
        console.warn("Failed to fetch bill titles", e);
        return { titles: [], count: 0 };
    }
}

/**
 * Fetch bill amendments
 */
export async function fetchBillAmendments(billId: string): Promise<PaginatedBillAmendments> {
    const [congress, billType, billNumber] = billId.toLowerCase().split('-');
    try {
        const raw = await fetchApi<{ data?: PaginatedBillAmendments } & Partial<PaginatedBillAmendments>>(
            `${API_BASE}/v1/congress/bills/${congress}/${billType}/${billNumber}/amendments`
        );
        if (raw.data) return raw.data;
        if (raw.amendments) return { amendments: raw.amendments, count: raw.count || 0 };
        return { amendments: [], count: 0 };
    } catch (e) {
        console.warn("Failed to fetch bill amendments", e);
        return { amendments: [], count: 0 };
    }
}

/**
 * Fetch related bills
 */
export async function fetchBillRelated(billId: string): Promise<PaginatedRelatedBills> {
    const [congress, billType, billNumber] = billId.toLowerCase().split('-');
    try {
        const raw = await fetchApi<{ data?: PaginatedRelatedBills } & Partial<PaginatedRelatedBills>>(
            `${API_BASE}/v1/congress/bills/${congress}/${billType}/${billNumber}/related`
        );
        if (raw.data) return raw.data;
        if (raw.relatedBills) return { relatedBills: raw.relatedBills, count: raw.count || 0 };
        return { relatedBills: [], count: 0 };
    } catch (e) {
        console.warn("Failed to fetch related bills", e);
        return { relatedBills: [], count: 0 };
    }
}

/**
 * Fetch bill actions
 */
export async function fetchBillActions(billId: string): Promise<PaginatedBillActions> {
    const [congress, billType, billNumber] = billId.toLowerCase().split('-');
    try {
        const raw = await fetchApi<{ data?: PaginatedBillActions } & Partial<PaginatedBillActions>>(
            `${API_BASE}/v1/congress/bills/${congress}/${billType}/${billNumber}/actions`
        );
        if (raw.data) return raw.data;
        if (raw.actions) return { actions: raw.actions, count: raw.count || 0 };
        return { actions: [], count: 0 };
    } catch (e) {
        console.warn("Failed to fetch bill actions", e);
        return { actions: [], count: 0 };
    }
}

export async function fetchRecentActivity(): Promise<any[]> {
    try {
        const raw = await fetchApi<{ activity?: any[] }>(
            `${API_BASE}/v1/analytics/activity`
        );
        return raw.activity || [];
    } catch (e) {
        console.warn("Failed to fetch recent activity", e);
        return [];
    }
}

export async function fetchTradingTimeline(days = 365): Promise<TradingTimelineData['timeline']> {
    try {
        const endDate = new Date().toISOString().split('T')[0];
        const startDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

        const raw = await fetchApi<any>(
            `${API_BASE}/v1/analytics/trading-timeline?start_date=${startDate}&end_date=${endDate}`
        );

        const timeline = raw.data?.timeline || raw.timeline || [];

        // Standardize to format expected by chart components: { date, volume, count }
        return timeline.map((entry: any) => ({
            date: entry.date || entry.transaction_date,
            volume: entry.total_volume_usd || entry.volume || 0,
            count: entry.trade_count || entry.count || 0
        }));
    } catch (e) {
        console.warn("Failed to fetch trading timeline", e);
        return [];
    }
}
