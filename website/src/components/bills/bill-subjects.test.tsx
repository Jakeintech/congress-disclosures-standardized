import { render, screen } from '@testing-library/react';
import { BillSubjects } from './bill-subjects';
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

describe('BillSubjects', () => {
    it('renders subjects from MSW', async () => {
        const { asFragment } = render(
            <BillSubjects billId="119-hr-1" />,
            { wrapper: createQueryClientWrapper() }
        );

        await screen.findByText(/Defense spending/i);
        expect(asFragment()).toMatchSnapshot();
    });
});
