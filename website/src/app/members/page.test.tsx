import { render, screen, waitFor } from '@testing-library/react';
import MembersPage from './page';
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

describe('MembersPage', () => {
    it('renders members list from MSW', async () => {
        render(
            <MembersPage />,
            { wrapper: createQueryClientWrapper() }
        );

        expect(screen.getByText('Members of Congress')).toBeDefined();

        await waitFor(() => {
            expect(screen.getByText('Nancy Pelosi')).toBeDefined();
            expect(screen.getByText('John R. Moolenaar')).toBeDefined();
            expect(screen.getByText('Elizabeth Warren')).toBeDefined();
        });
    });

    it('matches snapshot after loading', async () => {
        const { asFragment } = render(
            <MembersPage />,
            { wrapper: createQueryClientWrapper() }
        );

        await waitFor(() => {
            expect(screen.getByText('Nancy Pelosi')).toBeDefined();
        });

        expect(asFragment()).toMatchSnapshot();
    });
});
