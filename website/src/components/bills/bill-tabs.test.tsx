import { render, screen, waitFor } from '@testing-library/react';
import { BillTabs } from './bill-tabs';
import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock matchMedia for components that use it (Radix UI, etc.)
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(), // Deprecated
        removeListener: vi.fn(), // Deprecated
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
    })),
});

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

const mockBill = {
    congress: 119,
    bill_type: 'hr',
    bill_number: 1,
    title: 'To provide for the common defense.',
    latest_action_date: '2025-01-20',
    latest_action_text: 'Introduced in House',
    policy_area: 'Defense',
    trade_correlations_count: 2,
    trade_correlations: []
};

describe('BillTabs', () => {
    it('renders summary tab by default', async () => {
        render(
            <BillTabs bill={mockBill as any} billId="119-hr-1" cosponsorsCount={5} actionsCount={10} />,
            { wrapper: createQueryClientWrapper() }
        );

        // Summary tab should be present (default)
        // We use findByText because it might take a moment to load from MSW
        const summaryText = await screen.findByText(/This bill provides for the common defense/i);
        expect(summaryText).toBeDefined();
    });

    it('renders other tabs correctly when clicked', async () => {
        render(
            <BillTabs bill={mockBill as any} billId="119-hr-1" cosponsorsCount={5} actionsCount={10} />,
            { wrapper: createQueryClientWrapper() }
        );

        // Wait for data to load in tabs (MSW will provide it)
        // Click on "Actions" tab
        const actionsTab = screen.getByRole('tab', { name: /actions/i });
        actionsTab.click();

        // Use findByText which handles waiting
        const historyHeader = await screen.findByText(/Legislative History/i);
        expect(historyHeader).toBeDefined();
    });
});
