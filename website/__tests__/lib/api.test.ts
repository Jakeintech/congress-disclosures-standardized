/**
 * API Integration Tests
 *
 * These tests verify that all API endpoints return valid data
 * and that the response structures match our TypeScript interfaces.
 */

import {
    fetchDashboardSummary,
    fetchMembers,
    fetchBills,
    fetchTransactions,
    fetchTrendingStocks,
    fetchTopTraders,
    fetchTripleCorrelations,
    fetchBillDetail,
    fetchMemberProfile,
    fetchMemberTrades,
    API_BASE
} from '@/lib/api';

// Increase timeout for API calls
jest.setTimeout(30000);

describe('API Integration Tests', () => {
    describe('Dashboard Endpoints', () => {
        it('fetchDashboardSummary should return valid summary data', async () => {
            const data = await fetchDashboardSummary();

            expect(data).toBeDefined();
            expect(typeof data.totalMembers).toBe('number');
            expect(typeof data.totalTransactions).toBe('number');
            expect(typeof data.totalFilings).toBe('number');
            expect(typeof data.totalBills).toBe('number');

            // Check reasonable values
            expect(data.totalMembers).toBeGreaterThan(0);
            expect(data.totalMembers).toBeLessThan(1000); // Sanity check
        });

        it('fetchTrendingStocks should return array of stocks', async () => {
            const data = await fetchTrendingStocks(5);

            expect(Array.isArray(data)).toBe(true);
            expect(data.length).toBeGreaterThan(0);
            expect(data.length).toBeLessThanOrEqual(5);

            if (data.length > 0) {
                const stock = data[0];
                expect(stock).toHaveProperty('ticker');
                expect(stock).toHaveProperty('trade_count');
                expect(typeof stock.ticker).toBe('string');
                expect(typeof stock.trade_count).toBe('number');
            }
        });

        it('fetchTopTraders should return array of traders', async () => {
            const data = await fetchTopTraders(5);

            expect(Array.isArray(data)).toBe(true);
            expect(data.length).toBeGreaterThan(0);
            expect(data.length).toBeLessThanOrEqual(5);

            if (data.length > 0) {
                const trader = data[0];
                expect(trader).toHaveProperty('name');
                expect(trader).toHaveProperty('bioguide_id');
                expect(trader).toHaveProperty('trade_count');
                expect(typeof trader.name).toBe('string');
                expect(typeof trader.trade_count).toBe('number');
            }
        });
    });

    describe('Members Endpoints', () => {
        it('fetchMembers should return array of members', async () => {
            const data = await fetchMembers({ limit: 10 });

            expect(Array.isArray(data)).toBe(true);
            expect(data.length).toBeGreaterThan(0);
            expect(data.length).toBeLessThanOrEqual(10);

            if (data.length > 0) {
                const member = data[0];
                expect(member).toHaveProperty('bioguide_id');
                expect(typeof member.bioguide_id).toBe('string');
            }
        });

        it('fetchMembers should filter by party', async () => {
            const democrats = await fetchMembers({ party: 'D', limit: 5 });

            expect(Array.isArray(democrats)).toBe(true);
            if (democrats.length > 0) {
                democrats.forEach(member => {
                    expect(member.party).toBe('D');
                });
            }
        });

        it('fetchMemberProfile should return member details', async () => {
            // First get a member to test with
            const members = await fetchMembers({ limit: 1 });
            expect(members.length).toBeGreaterThan(0);

            const bioguideId = members[0].bioguide_id;
            const profile = await fetchMemberProfile(bioguideId);

            expect(profile).toBeDefined();
            expect(profile.bioguide_id).toBe(bioguideId);
        });

        it('fetchMemberTrades should return array of trades', async () => {
            // First get a member to test with
            const members = await fetchMembers({ limit: 10 });
            expect(members.length).toBeGreaterThan(0);

            const bioguideId = members[0].bioguide_id;
            const trades = await fetchMemberTrades(bioguideId, 5);

            expect(Array.isArray(trades)).toBe(true);
            // Trades array may be empty if member has no trades
        });
    });

    describe('Bills Endpoints', () => {
        it('fetchBills should return array of bills', async () => {
            const data = await fetchBills({ limit: 10 });

            expect(Array.isArray(data)).toBe(true);
            expect(data.length).toBeGreaterThan(0);
            expect(data.length).toBeLessThanOrEqual(10);

            if (data.length > 0) {
                const bill = data[0];
                expect(bill).toHaveProperty('bill_id');
                expect(typeof bill.bill_id).toBe('string');
            }
        });

        it('fetchBills should filter by congress', async () => {
            const bills = await fetchBills({ congress: 119, limit: 5 });

            expect(Array.isArray(bills)).toBe(true);
            if (bills.length > 0) {
                bills.forEach(bill => {
                    expect(bill.congress).toBe(119);
                });
            }
        });

        it('fetchBillDetail should return bill details', async () => {
            // First get a bill to test with
            const bills = await fetchBills({ limit: 1 });
            expect(bills.length).toBeGreaterThan(0);

            const billId = bills[0].bill_id;
            const detail = await fetchBillDetail(billId);

            expect(detail).toBeDefined();
            expect(detail.bill).toBeDefined();
            expect(detail.bill.bill_id || `${detail.bill.congress}-${detail.bill.bill_type}-${detail.bill.bill_number}`).toBe(billId);
        });
    });

    describe('Transactions Endpoints', () => {
        it('fetchTransactions should return array of transactions', async () => {
            const data = await fetchTransactions({ limit: 10 });

            expect(Array.isArray(data)).toBe(true);
            expect(data.length).toBeGreaterThan(0);
            expect(data.length).toBeLessThanOrEqual(10);

            if (data.length > 0) {
                const transaction = data[0];
                expect(transaction).toHaveProperty('ticker');
                expect(transaction).toHaveProperty('transaction_date');
            }
        });

        it('fetchTransactions should filter by ticker', async () => {
            const transactions = await fetchTransactions({ ticker: 'AAPL', limit: 5 });

            expect(Array.isArray(transactions)).toBe(true);
            // May be empty if no AAPL trades
        });
    });

    describe('Lobbying Endpoints', () => {
        it('fetchTripleCorrelations should return correlations data', async () => {
            const data = await fetchTripleCorrelations({ limit: 10 });

            expect(Array.isArray(data)).toBe(true);
            // May be empty depending on data availability
        });
    });

    describe('Error Handling', () => {
        it('should throw error for invalid bill ID', async () => {
            await expect(fetchBillDetail('invalid-bill-id')).rejects.toThrow();
        });

        it('should throw error for non-existent member', async () => {
            await expect(fetchMemberProfile('INVALID999')).rejects.toThrow();
        });
    });

    describe('API Base URL', () => {
        it('should use correct API base URL', () => {
            expect(API_BASE).toContain('execute-api');
            expect(API_BASE).toContain('amazonaws.com');
        });
    });
});
