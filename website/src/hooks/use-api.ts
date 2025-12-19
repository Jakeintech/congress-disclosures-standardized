'use client';

import { useQuery } from '@tanstack/react-query';
import {
    fetchMemberProfile,
    fetchMemberTrades,
    fetchNetworkGraph,
    fetchTopTraders,
    fetchMemberAssets,
    fetchTrendingStocks,
    fetchSectorActivity,
    fetchPatternInsights,
    fetchDashboardSummary,
    fetchCongressionalAlpha,
    fetchConflicts,
    fetchPortfolios,
    fetchBills,
    fetchBillDetail,
    fetchBillText,
    fetchBillActions,
    fetchBillCosponsors,
    fetchBillSummaries,
    fetchBillCommittees,
    fetchBillSubjects,
    fetchBillTitles,
    fetchBillAmendments,
    fetchBillRelated,
    fetchMembers,
    fetchLobbyingNetwork,
    fetchTripleCorrelations,
} from '@/lib/api';
import type {
    BillsParams,
    NetworkGraphData,
    MembersParams,
    BillAction,
    BillSummary,
    Cosponsor,
    Subject,
    BillTitle,
    Amendment,
    RelatedBill,
} from '@/types/api';

/**
 * Hook to fetch members list.
 */
export function useMembers(params: MembersParams = {}) {
    return useQuery({
        queryKey: ['members', params],
        queryFn: () => fetchMembers(params),
    });
}

/**
 * Hook to fetch a member's profile data.
 */
export function useMemberProfile(bioguideId: string) {
    return useQuery({
        queryKey: ['member', bioguideId],
        queryFn: () => fetchMemberProfile(bioguideId),
        enabled: !!bioguideId,
    });
}

/**
 * Hook to fetch a member's trading history.
 */
export function useMemberTrades(bioguideId: string, limit?: number) {
    return useQuery({
        queryKey: ['trades', bioguideId, limit],
        queryFn: () => fetchMemberTrades(bioguideId, limit),
        enabled: !!bioguideId,
    });
}

/**
 * Hook to fetch a member's asset holdings.
 */
export function useMemberAssets(bioguideId: string) {
    return useQuery({
        queryKey: ['assets', bioguideId],
        queryFn: () => fetchMemberAssets(bioguideId),
        enabled: !!bioguideId,
    });
}

/**
 * Hook to fetch network graph data.
 */
export function useNetworkGraph(params: {
    year?: number;
    view_mode?: 'aggregate' | 'member_detail';
    bioguide_id?: string;
    congress?: number;
    limit?: number;
} = {}) {
    return useQuery({
        queryKey: ['network-graph', params],
        queryFn: () => fetchNetworkGraph(params),
    });
}

/**
 * Hook to fetch top traders list.
 */
export function useTopTraders(days?: number) {
    return useQuery({
        queryKey: ['top-traders', days],
        queryFn: () => fetchTopTraders(days),
    });
}

/**
 * Hook to fetch dashboard summary statistics.
 */
export function useDashboardSummary() {
    return useQuery({
        queryKey: ['dashboard-summary'],
        queryFn: () => fetchDashboardSummary(),
    });
}

/**
 * Hook to fetch trending stocks.
 */
export function useTrendingStocks(limit?: number) {
    return useQuery({
        queryKey: ['trending-stocks', limit],
        queryFn: () => fetchTrendingStocks(limit),
    });
}

/**
 * Hook to fetch sector activity.
 */
export function useSectorActivity() {
    return useQuery({
        queryKey: ['sector-activity'],
        queryFn: () => fetchSectorActivity(),
    });
}

/**
 * Hook to fetch pattern insights.
 */
export function usePatternInsights(type: 'trending' | 'timing' | 'sector' = 'trending') {
    return useQuery({
        queryKey: ['pattern-insights', type],
        queryFn: () => fetchPatternInsights(type),
    });
}

/**
 * Hook to fetch congressional alpha data.
 */
export function useCongressionalAlpha(type: 'member' | 'party' | 'sector_rotation' = 'member', limit = 10) {
    return useQuery({
        queryKey: ['congressional-alpha', type, limit],
        queryFn: () => fetchCongressionalAlpha(type, limit),
    });
}

/**
 * Hook to fetch conflict of interest data.
 */
export function useConflicts(severity = 'all', limit = 10) {
    return useQuery({
        queryKey: ['conflicts', severity, limit],
        queryFn: () => fetchConflicts(severity, limit),
    });
}

/**
 * Hook to fetch portfolios.
 */
export function usePortfolios(params: {
    member_id?: string;
    limit?: number;
    include_holdings?: boolean;
} = {}) {
    return useQuery({
        queryKey: ['portfolios', params],
        queryFn: () => fetchPortfolios(params),
    });
}

/**
 * Hook to fetch bills list with filters.
 */
export function useBills(params: BillsParams = {}) {
    return useQuery({
        queryKey: ['filtered-bills', params],
        queryFn: () => fetchBills(params),
    });
}

/**
 * Hook to fetch detailed bill data.
 */
export function useBillDetail(billId: string) {
    return useQuery({
        queryKey: ['bill', billId],
        queryFn: () => fetchBillDetail(billId),
        enabled: !!billId,
    });
}

/**
 * Hook to fetch bill text.
 */
export function useBillText(billId: string) {
    return useQuery({
        queryKey: ['bill-text', billId],
        queryFn: () => fetchBillText(billId),
        enabled: !!billId,
    });
}

/**
 * Hook to fetch bill actions.
 */
export function useBillActions(billId: string, initialData?: BillAction[]) {
    return useQuery({
        queryKey: ['bill-actions', billId],
        queryFn: () => fetchBillActions(billId),
        enabled: !!billId,
        initialData: initialData ? { actions: initialData, count: initialData.length } : undefined,
    });
}

/**
 * Hook to fetch bill summaries.
 */
export function useBillSummaries(billId: string, initialData?: BillSummary[]) {
    return useQuery({
        queryKey: ['bill-summaries', billId],
        queryFn: () => fetchBillSummaries(billId),
        enabled: !!billId,
        initialData: initialData ? { summaries: Array.isArray(initialData) ? initialData : [initialData], count: Array.isArray(initialData) ? initialData.length : 1 } : undefined,
    });
}

/**
 * Hook to fetch bill committees.
 */
export function useBillCommittees(billId: string) {
    return useQuery({
        queryKey: ['bill-committees', billId],
        queryFn: () => fetchBillCommittees(billId),
        enabled: !!billId,
    });
}

/**
 * Hook to fetch bill cosponsors.
 */
export function useBillCosponsors(billId: string, initialData?: Cosponsor[]) {
    return useQuery({
        queryKey: ['bill-cosponsors', billId],
        queryFn: () => fetchBillCosponsors(billId),
        enabled: !!billId,
        initialData: initialData ? { cosponsors: initialData, count: initialData.length } : undefined,
    });
}

/**
 * Hook to fetch bill subjects.
 */
export function useBillSubjects(billId: string, initialData?: Subject[]) {
    return useQuery({
        queryKey: ['bill-subjects', billId],
        queryFn: () => fetchBillSubjects(billId),
        enabled: !!billId,
        initialData: initialData ? { subjects: initialData, count: initialData.length } : undefined,
    });
}

/**
 * Hook to fetch bill titles.
 */
export function useBillTitles(billId: string, initialData?: BillTitle[]) {
    return useQuery({
        queryKey: ['bill-titles', billId],
        queryFn: () => fetchBillTitles(billId),
        enabled: !!billId,
        initialData: initialData ? { titles: initialData, count: initialData.length } : undefined,
    });
}

/**
 * Hook to fetch bill amendments.
 */
export function useBillAmendments(billId: string, initialData?: Amendment[]) {
    return useQuery({
        queryKey: ['bill-amendments', billId],
        queryFn: () => fetchBillAmendments(billId),
        enabled: !!billId,
        initialData: initialData ? { amendments: initialData, count: initialData.length } : undefined,
    });
}

/**
 * Hook to fetch related bills.
 */
export function useBillRelated(billId: string, initialData?: RelatedBill[]) {
    return useQuery({
        queryKey: ['bill-related', billId],
        queryFn: () => fetchBillRelated(billId),
        enabled: !!billId,
        initialData: initialData ? { relatedBills: initialData, count: initialData.length } : undefined,
    });
}

/**
 * Hook to fetch lobbying network graph data.
 */
export function useLobbyingNetwork() {
    return useQuery({
        queryKey: ['lobbying-network'],
        queryFn: () => fetchLobbyingNetwork(),
    });
}

/**
 * Hook to fetch triple correlations (trade-bill-lobbying).
 */
export function useTripleCorrelations(params: {
    year?: string;
    min_score?: number;
    member_bioguide?: string;
    ticker?: string;
    bill_id?: string;
    limit?: number;
} = {}) {
    return useQuery({
        queryKey: ['triple-correlations', params],
        queryFn: () => fetchTripleCorrelations(params),
    });
}
