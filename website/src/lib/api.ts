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
    BillTitle,
    Amendment,
    RelatedBill,
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
    const rawData = await fetchApi<{ data?: any }>(`${API_BASE}/v1/congress/bills/${billId}`);
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
        congress_gov_url: result.congress_gov_url || `https://www.congress.gov/bill/${result.bill?.congress}th-congress/${result.bill?.bill_type === 'hr' ? 'house-bill' : 'senate-bill'}/${result.bill?.bill_number}`
    };
}

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
    // API returns { data: [...] } or just [...]
    const raw = await fetchApi<{ data?: any[] }>(`${url}`);
    const data = (Array.isArray(raw) ? raw : raw.data) || [];
    return data;
}

/**
 * Fetch members list
 */
export async function fetchMembers(params: MembersParams = {}): Promise<CongressMember[]> {
    const searchParams = new URLSearchParams();

    if (params.congress) searchParams.set('congress', params.congress.toString());
    if (params.chamber) searchParams.set('chamber', params.chamber);
    if (params.party) searchParams.set('party', params.party);
    if (params.state) searchParams.set('state', params.state);
    if (params.limit) searchParams.set('limit', params.limit.toString());
    if (params.offset) searchParams.set('offset', params.offset.toString());

    const url = `${API_BASE}/v1/congress/members?${searchParams.toString()}`;
    const raw = await fetchApi<{ data?: any[] }>(`${url}`);
    const data = (Array.isArray(raw) ? raw : raw.data) || [];
    return data;
}

/**
 * Fetch member profile
 */
export async function fetchMemberProfile(bioguideId: string): Promise<MemberProfile> {
    const raw = await fetchApi<ApiResponse<MemberProfile>>(`${API_BASE}/v1/members/${bioguideId}`);
    return raw.data || (raw as unknown as MemberProfile);
}

/**
 * Fetch member trades
 */
export async function fetchMemberTrades(bioguideId: string, limit = 50) {
    const raw = await fetchApi<{ data?: any[] }>(
        `${API_BASE}/v1/members/${bioguideId}/trades?limit=${limit}`
    );
    const data = (Array.isArray(raw) ? raw : raw.data) || [];
    return data;
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
    const raw = await fetchApi<{ data?: any[] }>(`${url}`);
    const data = (Array.isArray(raw) ? raw : raw.data) || [];
    return data;
}

/**
 * Fetch trending stocks
 */
export async function fetchTrendingStocks(limit = 10): Promise<TrendingStock[]> {
    const data = await fetchApi<ApiResponse<{ trending_stocks: TrendingStock[] }>>(
        `${API_BASE}/v1/analytics/trending-stocks?limit=${limit}`
    );
    const result = data.data || (data as { trending_stocks: TrendingStock[] });
    return result.trending_stocks || [];
}

/**
 * Fetch top traders
 */
export async function fetchTopTraders(limit = 10): Promise<TopTrader[]> {
    const data = await fetchApi<ApiResponse<{ top_traders: TopTrader[] }>>(
        `${API_BASE}/v1/analytics/top-traders?limit=${limit}`
    );
    const result = data.data || (data as { top_traders: TopTrader[] });
    return result.top_traders || [];
}

/**
 * Fetch lobbying activity for a bill
 */
export async function fetchBillLobbyingActivity(billId: string) {
    const raw = await fetchApi<{ data?: unknown }>(
        `${API_BASE}/v1/lobbying/bills/${billId}/lobbying-activity`
    );
    return raw.data || raw;
}

/**
 * Fetch triple correlations (trade-bill-lobbying)
 */
export async function fetchTripleCorrelations(params: TripleCorrelationsParams = {}): Promise<TripleCorrelation[]> {
    const searchParams = new URLSearchParams();

    if (params.minScore) searchParams.set('min_score', params.minScore.toString());
    if (params.year) searchParams.set('year', params.year.toString());
    if (params.limit) searchParams.set('limit', params.limit.toString());

    const url = `${API_BASE}/v1/correlations/triple?${searchParams.toString()}`;
    const raw = await fetchApi<{ data?: any[] }>(`${url}`);
    const data = (Array.isArray(raw) ? raw : raw.data) || [];
    return data;
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

// Network graph types are imported from @/types/api

/**
 * Fetch Network Graph
 */
export async function fetchNetworkGraph(year: number = 2025): Promise<NetworkGraphData> {
    try {
        const res = await fetch(`${API_BASE}/v1/lobbying/network-graph?year=${year}`);
        if (!res.ok) {
            console.warn(`Network graph API error: ${res.status}`);
            return { nodes: [], links: [] };
        }
        const json = await res.json();
        const apiData = json.data || json;
        // Legacy API returns { graph: { nodes, links }, metadata: ... }
        // or sometimes flattened. Let's handle both.
        const graphData = apiData.graph || apiData;

        return {
            nodes: graphData.nodes || [],
            links: graphData.links || [],
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
export async function fetchMemberAssets(bioguideId: string) {
    const raw = await fetchApi<{ data?: { holdings: any[] } }>(`${API_BASE}/v1/members/${bioguideId}/portfolio`);
    const result = raw.data || raw;
    // @ts-expect-error - Runtime check
    return result.holdings || [];
}

/**
 * Fetch bill text content
 */
export async function fetchBillText(billId: string) {
    try {
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
            `${API_BASE}/v1/congress/bills/${billId}/text`
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
 * Fetch bill committees
 */
export async function fetchBillCommittees(billId: string) {
    try {
        const raw = await fetchApi<{ data?: { committees: any[], count: number } }>(
            `${API_BASE}/v1/congress/bills/${billId}/committees`
        );
        return raw.data || raw;
    } catch (e) {
        console.warn("Failed to fetch bill committees", e);
        return null;
    }
}

/**
 * Fetch bill cosponsors
 */
export async function fetchBillCosponsors(billId: string) {
    try {
        const raw = await fetchApi<{ data?: { cosponsors: any[], count: number } }>(
            `${API_BASE}/v1/congress/bills/${billId}/cosponsors`
        );
        return raw.data || raw;
    } catch (e) {
        console.warn("Failed to fetch bill cosponsors", e);
        return null;
    }
}

/**
 * Fetch bill subjects
 */
export async function fetchBillSubjects(billId: string) {
    try {
        const raw = await fetchApi<{ data?: { subjects: any[], count: number } }>(
            `${API_BASE}/v1/congress/bills/${billId}/subjects`
        );
        return raw.data || raw;
    } catch (e) {
        console.warn("Failed to fetch bill subjects", e);
        return null;
    }
}

/**
 * Fetch bill summaries
 */
export async function fetchBillSummaries(billId: string) {
    try {
        const raw = await fetchApi<{ data?: { summaries: any[], count: number } }>(
            `${API_BASE}/v1/congress/bills/${billId}/summaries`
        );
        return raw.data || raw;
    } catch (e) {
        console.warn("Failed to fetch bill summaries", e);
        return null;
    }
}

/**
 * Fetch bill titles
 */
export async function fetchBillTitles(billId: string) {
    try {
        const raw = await fetchApi<{ data?: { titles: any[], count: number } }>(
            `${API_BASE}/v1/congress/bills/${billId}/titles`
        );
        return raw.data || raw;
    } catch (e) {
        console.warn("Failed to fetch bill titles", e);
        return null;
    }
}

/**
 * Fetch bill amendments
 */
export async function fetchBillAmendments(billId: string) {
    try {
        const raw = await fetchApi<{ data?: { amendments: any[], count: number } }>(
            `${API_BASE}/v1/congress/bills/${billId}/amendments`
        );
        return raw.data || raw;
    } catch (e) {
        console.warn("Failed to fetch bill amendments", e);
        return null;
    }
}

/**
 * Fetch related bills
 */
export async function fetchBillRelated(billId: string) {
    try {
        const raw = await fetchApi<{ data?: { relatedBills: any[], count: number } }>(
            `${API_BASE}/v1/congress/bills/${billId}/related`
        );
        return raw.data || raw;
    } catch (e) {
        console.warn("Failed to fetch related bills", e);
        return null;
    }
}

/**
 * Fetch bill actions
 */
export async function fetchBillActions(billId: string) {
    try {
        const raw = await fetchApi<{ data?: { actions: any[], count: number } }>(
            `${API_BASE}/v1/congress/bills/${billId}/actions`
        );
        return raw.data || raw;
    } catch (e) {
        console.warn("Failed to fetch bill actions", e);
        return null;
    }
}
