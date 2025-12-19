'use client';

import { useQuery } from '@tanstack/react-query';
import {
    fetchMemberProfile,
    fetchMemberTrades,
    fetchNetworkGraph,
    fetchTopTraders,
    fetchMemberAssets
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
