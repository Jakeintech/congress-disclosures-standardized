import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
    useDashboardSummary,
    usePatternInsights,
    useCongressionalAlpha,
    useBills,
    useBillDetail,
    useBillText,
    useBillActions
} from './use-api';
import React from 'react';

const createQueryClientWrapper = () => {
    const queryClient = new QueryClient({
        defaultOptions: {
            queries: {
                retry: false,
            },
        },
    });
    return ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
};

describe('use-api hooks', () => {
    it('useDashboardSummary returns mocked data', async () => {
        const { result } = renderHook(() => useDashboardSummary(), {
            wrapper: createQueryClientWrapper(),
        });

        await waitFor(() => expect(result.current.isSuccess).toBe(true));

        expect(result.current.data).toEqual({
            totalMembers: 535,
            totalTransactions: 12450,
            totalFilings: 8900,
            totalBills: 4200
        });
    });

    it('usePatternInsights returns mocked trending data', async () => {
        const { result } = renderHook(() => usePatternInsights('trending'), {
            wrapper: createQueryClientWrapper(),
        });

        await waitFor(() => expect(result.current.isSuccess).toBe(true));

        expect(result.current.data?.sector_rotation).toHaveLength(2);
        expect(result.current.data?.sector_rotation?.[0].sector).toBe('Energy');
    });

    it('usePatternInsights returns mocked timing data', async () => {
        const { result } = renderHook(() => usePatternInsights('timing'), {
            wrapper: createQueryClientWrapper(),
        });

        await waitFor(() => expect(result.current.isSuccess).toBe(true));

        expect(result.current.data?.day_of_week).toHaveLength(2);
        expect(result.current.data?.day_of_week?.[0].day_name).toBe('Monday');
    });

    it('useCongressionalAlpha returns mocked alpha data', async () => {
        const { result } = renderHook(() => useCongressionalAlpha('member'), {
            wrapper: createQueryClientWrapper(),
        });

        await waitFor(() => expect(result.current.isSuccess).toBe(true));

        expect(result.current.data).toHaveLength(2);
        expect(result.current.data?.[0].name).toBe('Nancy Pelosi');
    });

    it('useBills returns mocked bills list', async () => {
        const { result } = renderHook(() => useBills(), {
            wrapper: createQueryClientWrapper(),
        });

        await waitFor(() => expect(result.current.isSuccess).toBe(true));

        expect(result.current.data).toHaveLength(1);
        expect(result.current.data?.[0].bill_number).toBe(1);
    });

    it('useBillDetail returns mocked bill detail', async () => {
        const { result } = renderHook(() => useBillDetail('119-hr-1'), {
            wrapper: createQueryClientWrapper(),
        });

        await waitFor(() => expect(result.current.isSuccess).toBe(true));

        expect(result.current.data?.bill.bill_number).toBe(1);
        expect(result.current.data?.sponsor.name).toBe('John Doe');
    });

    it('useBillText returns mocked text versions', async () => {
        const { result } = renderHook(() => useBillText('119-hr-1'), {
            wrapper: createQueryClientWrapper(),
        });

        await waitFor(() => expect(result.current.isSuccess).toBe(true));

        expect(result.current.data).toHaveLength(2);
        expect((result.current.data as any)?.[0].format).toBe('PDF');
    });

    it('useBillActions returns mocked actions', async () => {
        const { result } = renderHook(() => useBillActions('119-hr-1'), {
            wrapper: createQueryClientWrapper(),
        });

        await waitFor(() => expect(result.current.isSuccess).toBe(true));

        expect((result.current.data as any)?.actions).toHaveLength(1);
        expect((result.current.data as any)?.actions[0].action_text).toBe('Introduced in House');
    });
});
