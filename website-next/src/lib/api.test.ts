
import { fetchBillDetail, fetchMembers, fetchTransactions } from './api';

// Mock global fetch
global.fetch = jest.fn();

describe('API Client', () => {
    beforeEach(() => {
        (global.fetch as jest.Mock).mockClear();
    });

    describe('fetchBillDetail', () => {
        it('fetches from correct ISR path for archived congress', async () => {
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                json: async () => ({ title: 'Test Bill' }),
            });

            const data = await fetchBillDetail('115-hr-1234');
            expect(global.fetch).toHaveBeenCalledWith('/data/bill_details/115/hr/1234.json');
            expect(data).toEqual({ title: 'Test Bill' });
        });

        it('fetches from API for current congress', async () => {
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                json: async () => ({ data: { bill: { title: 'Current Bill' } } }),
            });

            const data = await fetchBillDetail('119-s-5678');
            expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/v1/congress/bills/119-s-5678'));
            expect(data.bill.title).toEqual('Current Bill');
            expect(data.actions).toEqual([]);
        });

        it('sanitizes incomplete API response (repro 119-sconres-23)', async () => {
            // Raw partial response observed from curl
            const partialResponse = {
                bill: {
                    bill_id: "119-sconres-23",
                    congress: 119,
                    bill_type: "sconres",
                    bill_number: 23,
                    title: "A concurrent resolution...",
                    sponsor_bioguide_id: "B001303",
                    sponsor_name: "Sen. Blunt Rochester, Lisa [D-DE]",
                    cosponsors_count: null
                }
            };

            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                json: async () => partialResponse, // Note: no { data: ... } wrapper in this specific legacy endpoint? Or maybe my curl missed it? 
                // Wait, curl output was just {"bill": ...}. So sanitize logic needs to handle that.
            });

            const data = await fetchBillDetail('119-sconres-23');

            // Expect defaults to be filled in
            expect(data.cosponsors).toEqual([]);
            expect(data.actions_recent).toEqual([]);
            expect(data.industry_tags).toEqual([]);
            expect(data.trade_correlations).toEqual([]);
            // Expect sponsor to be constructed from bill fields if missing
            expect(data.sponsor).toEqual({
                bioguide_id: "B001303",
                name: "Sen. Blunt Rochester, Lisa [D-DE]",
                party: "D",
                state: "DE"
            });
        });
    });

    describe('fetchMembers', () => {
        it('constructs query parameters correctly and handles wrapped response', async () => {
            // Wrapped response
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                json: async () => ({ data: [{ name: 'Member A' }] }),
            });

            const data = await fetchMembers({ party: 'D', state: 'CA', limit: 5 });
            expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('party=D'));
            expect(data).toEqual([{ name: 'Member A' }]);
        });

        it('handles direct array response (legacy)', async () => {
            // Unwrapped response
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                json: async () => [{ name: 'Member B' }],
            });

            const data = await fetchMembers({});
            expect(data).toEqual([{ name: 'Member B' }]);
        });
    });

    describe('fetchBills', () => {
        it('handles wrapped response', async () => {
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                json: async () => ({ data: [{ bill_id: '118-hr-1' }] }),
            });
            const data = await import('./api').then(m => m.fetchBills());
            expect(data).toEqual([{ bill_id: '118-hr-1' }]);
        });
    });

    describe('fetchDashboardSummary', () => {
        it('correctly maps nested API response to flat DashboardData', async () => {
            const apiResponse = {
                data: {
                    members: { total: 535 },
                    trades: { total: 100 },
                    filings: { total: 50 },
                }
            };
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                json: async () => apiResponse,
            });

            const data = await import('./api').then(m => m.fetchDashboardSummary());

            expect(data).toEqual({
                totalMembers: 535,
                totalTransactions: 100,
                totalFilings: 50,
                totalBills: 0,
            });
        });
    });

    describe('fetchTrendingStocks', () => {
        it('extracts trending_stocks array from nested response', async () => {
            const apiResponse = {
                data: {
                    trending_stocks: [{ ticker: 'AAPL', count: 10 }]
                }
            };
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                json: async () => apiResponse,
            });

            const data = await import('./api').then(m => m.fetchTrendingStocks());
            expect(data).toEqual([{ ticker: 'AAPL', count: 10 }]);
        });

        it('returns empty array if data missing', async () => {
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                json: async () => ({ data: {} }),
            });
            const data = await import('./api').then(m => m.fetchTrendingStocks());
            expect(data).toEqual([]);
        });
    });

    describe('fetchTopTraders', () => {
        it('extracts top_traders array from nested response', async () => {
            const apiResponse = {
                data: {
                    top_traders: [{ name: 'Nancy Pelosi', count: 50 }]
                }
            };
            (global.fetch as jest.Mock).mockResolvedValueOnce({
                ok: true,
                json: async () => apiResponse,
            });

            const data = await import('./api').then(m => m.fetchTopTraders());
            expect(data).toEqual([{ name: 'Nancy Pelosi', count: 50 }]);
        });
    });
});
