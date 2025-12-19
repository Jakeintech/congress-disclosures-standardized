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
    fetchPortfolios
} from '@/lib/api';

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
export function useNetworkGraph(params: any) {
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
 * Hook to fetch portfolio reconstruction data.
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
