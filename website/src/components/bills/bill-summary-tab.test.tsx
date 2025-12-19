import { render, screen } from '@testing-library/react';
import { BillSummary } from './bill-summary-tab';
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

describe('BillSummary', () => {
    it('renders summary from MSW', async () => {
        const { asFragment } = render(
            <BillSummary billId="119-hr-1" />,
            { wrapper: createQueryClientWrapper() }
        );

        await screen.findByText(/This bill provides for the common defense/i);
        expect(asFragment()).toMatchSnapshot();
    });

    it('uses initial data if provided', () => {
        const { asFragment } = render(
            <BillSummary billId="119-hr-1" initialData={{ text: "Initial summary" } as any} />,
            { wrapper: createQueryClientWrapper() }
        );

        expect(screen.getByText(/Initial summary/i)).toBeDefined();
        expect(asFragment()).toMatchSnapshot();
    });
});
