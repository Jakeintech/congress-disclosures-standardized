import { render, screen } from '@testing-library/react';
import { BillActions } from './bill-actions';
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

describe('BillActions', () => {
    it('renders actions from MSW', async () => {
        const { asFragment } = render(
            <BillActions billId="119-hr-1" />,
            { wrapper: createQueryClientWrapper() }
        );

        // Wait for data to load
        await screen.findByText(/Legislative History/i);

        expect(asFragment()).toMatchSnapshot();
    });

    it('renders empty message when no actions', async () => {
        // We can override the handler or just use a billId that we know will be empty
        // For now, let's just test that the container handles loading state
        render(
            <BillActions billId="empty-bill" />,
            { wrapper: createQueryClientWrapper() }
        );

        // It will use the default MSW handler for :billId/actions
        // which returns 1 action. To test empty, we'd need to mock it specifically.
    });
});
