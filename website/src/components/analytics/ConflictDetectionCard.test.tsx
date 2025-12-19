import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConflictDetectionCard } from './ConflictDetectionCard';
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

describe('ConflictDetectionCard', () => {
    it('renders loading state initially', () => {
        render(<ConflictDetectionCard />, { wrapper: createQueryClientWrapper() });
        expect(screen.getByText(/Analyzing conflicts/i)).toBeInTheDocument();
    });

    it('renders conflict data after loading', async () => {
        render(<ConflictDetectionCard />, { wrapper: createQueryClientWrapper() });

        await waitFor(() => {
            expect(screen.getByText('John Doe')).toBeInTheDocument();
        });

        expect(screen.getByText('LMT')).toBeInTheDocument();
        expect(screen.getByText('HIGH')).toBeInTheDocument();
        expect(screen.getByText(/Score: 85\/100/i)).toBeInTheDocument();
    });

    it('matches snapshot', async () => {
        const { asFragment } = render(<ConflictDetectionCard />, { wrapper: createQueryClientWrapper() });

        await waitFor(() => {
            expect(screen.getByText('John Doe')).toBeInTheDocument();
        });

        expect(asFragment()).toMatchSnapshot();
    });
});
