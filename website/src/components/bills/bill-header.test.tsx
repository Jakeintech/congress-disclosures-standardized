import { render, screen } from '@testing-library/react';
import { BillHeader } from './bill-header';
import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

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
    trade_correlations_count: 2
};

const mockSponsor = {
    bioguide_id: 'D000123',
    name: 'John Doe',
    party: 'D',
    state: 'CA'
};

describe('BillHeader', () => {
    it('renders bill information correctly', () => {
        const { asFragment } = render(
            <BillHeader bill={mockBill as any} sponsor={mockSponsor as any} />,
            { wrapper: createQueryClientWrapper() }
        );

        expect(screen.getByText('119th Congress')).toBeDefined();
        expect(screen.getByText(/To provide for the common defense/i)).toBeDefined();
        expect(screen.getByText('John Doe')).toBeDefined();
        expect(screen.getByText('(D-CA)')).toBeDefined();

        expect(asFragment()).toMatchSnapshot();
    });

    it('shows trade alert when trade_correlations_count > 0', () => {
        render(
            <BillHeader bill={mockBill as any} sponsor={mockSponsor as any} />,
            { wrapper: createQueryClientWrapper() }
        );

        expect(screen.getByText(/Trade Activity Detected/i)).toBeDefined();
    });
});
