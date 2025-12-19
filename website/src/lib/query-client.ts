'use client';

import { QueryClient } from '@tanstack/react-query';

/**
 * Standardized Query Client for the Congress Disclosures platform.
 * 
 * - staleTime (5 mins): Data is considered fresh for 5 mins to avoid redundant fetches.
 * - gcTime (10 mins): Data stays in cache for 10 mins after being unused.
 * - retry (1): Retry once on failure for transient network issues.
 * - refetchOnWindowFocus (false): Avoid aggressive refetching when switching apps.
 */
export const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 5 * 60 * 1000,
            gcTime: 10 * 60 * 1000,
            retry: 1,
            refetchOnWindowFocus: false,
        },
    },
});
