import { render, screen, waitFor } from '@testing-library/react';
import DashboardPage from './page';
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

// Mock Recharts to avoid JSDOM issues
vi.mock('recharts', () => ({
    ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
    LineChart: () => <div>LineChart</div>,
    AreaChart: () => <div>AreaChart</div>,
    BarChart: () => <div>BarChart</div>,
    PieChart: () => <div>PieChart</div>,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    Legend: () => null,
    Line: () => null,
    Area: () => null,
    Bar: () => null,
    Pie: () => null,
    Cell: () => null,
}));

describe('DashboardPage', () => {
    it('renders dashboard with summary stats from MSW', async () => {
        render(
            <DashboardPage />,
            { wrapper: createQueryClientWrapper() }
        );

        // Header should be present
        expect(screen.getByText('Dashboard')).toBeDefined();

        // Wait for MSW data to load
        await waitFor(() => {
            expect(screen.getByText('12,450')).toBeDefined(); // Transactions from MSW
            expect(screen.getByText('AAPL')).toBeDefined(); // Trending stock from MSW
            expect(screen.getByText('Nancy Pelosi')).toBeDefined(); // Top trader from MSW
        });
    });

    it('matches snapshot after loading', async () => {
        const { asFragment } = render(
            <DashboardPage />,
            { wrapper: createQueryClientWrapper() }
        );

        await waitFor(() => {
            expect(screen.getByText('Nancy Pelosi')).toBeDefined();
        });

        expect(asFragment()).toMatchSnapshot();
    });
});
