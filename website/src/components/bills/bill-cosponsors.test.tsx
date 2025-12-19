import { render, screen } from '@testing-library/react';
import { BillCosponsors } from './bill-cosponsors';
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

describe('BillCosponsors', () => {
    it('renders cosponsors from MSW', async () => {
        const { asFragment } = render(
            <BillCosponsors billId="119-hr-1" />,
            { wrapper: createQueryClientWrapper() }
        );

        await screen.findByText(/Jane Smith/i);
        expect(asFragment()).toMatchSnapshot();
    });
});
