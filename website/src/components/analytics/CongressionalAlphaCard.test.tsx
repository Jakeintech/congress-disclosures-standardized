import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CongressionalAlphaCard } from './CongressionalAlphaCard';
import React from 'react';
import { describe, it, expect } from 'vitest';

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

describe('CongressionalAlphaCard', () => {
    it('renders loading state initially', () => {
        render(<CongressionalAlphaCard />, { wrapper: createQueryClientWrapper() });
        expect(screen.getByText(/Loading/i)).toBeInTheDocument();
    });

    it('renders alpha data after loading', async () => {
        render(<CongressionalAlphaCard />, { wrapper: createQueryClientWrapper() });

        await waitFor(() => {
            expect(screen.getByText('Nancy Pelosi')).toBeInTheDocument();
        });

        expect(screen.getByText('Markwayne Mullin')).toBeInTheDocument();
        // Check if chart elements exist from our mock
        expect(document.querySelector('.bar-chart')).toBeInTheDocument();
    });

    it('matches snapshot', async () => {
        const { asFragment } = render(<CongressionalAlphaCard />, { wrapper: createQueryClientWrapper() });

        await waitFor(() => {
            expect(screen.getByText('Nancy Pelosi')).toBeInTheDocument();
        });

        expect(asFragment()).toMatchSnapshot();
    });
});
