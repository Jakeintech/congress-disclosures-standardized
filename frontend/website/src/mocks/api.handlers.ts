import { http, HttpResponse } from 'msw';
import { API_BASE } from '@/lib/api';

export const handlers = [
    // Dashboard Summary (Corrected endpoint)
    http.get(`${API_BASE}/v1/analytics/summary`, () => {
        return HttpResponse.json({
            members: { total: 535 },
            trades: { total: 12450 },
            filings: { total: 8900 },
            bills: { total: 4200 }
        });
    }),

    // Trending Stocks (Corrected endpoint)
    http.get(`${API_BASE}/v1/analytics/trending-stocks`, () => {
        return HttpResponse.json({
            stocks: [
                { ticker: 'AAPL', trade_count: 45, total_volume: 1200000, company_name: 'Apple Inc.', net_direction: 'buy' },
                { ticker: 'NVDA', trade_count: 38, total_volume: 950000, company_name: 'NVIDIA Corp.', net_direction: 'buy' },
                { ticker: 'MSFT', trade_count: 25, total_volume: 800000, company_name: 'Microsoft Corp.', net_direction: 'sell' }
            ]
        });
    }),

    // Top Traders
    http.get(`${API_BASE}/v1/analytics/top-traders`, () => {
        return HttpResponse.json({
            traders: [
                { bioguide_id: 'P000197', name: 'Nancy Pelosi', trade_count: 50, total_volume: '15.0M', party: 'D', state: 'CA' },
                { bioguide_id: 'M001194', name: 'John R. Moolenaar', trade_count: 42, total_volume: '0.8M', party: 'R', state: 'MI' }
            ]
        });
    }),

    // Members
    http.get(`${API_BASE}/v1/congress/members`, ({ request }) => {
        const url = new URL(request.url);
        const party = url.searchParams.get('party');

        const allMembers = [
            { bioguide_id: 'P000197', first_name: 'Nancy', last_name: 'Pelosi', party: 'D', state: 'CA', chamber: 'house', total_volume: 15000000, total_trades: 50, last_trade_date: '2023-12-01' },
            { bioguide_id: 'M001194', first_name: 'John R.', last_name: 'Moolenaar', party: 'R', state: 'MI', chamber: 'house', total_volume: 800000, total_trades: 42, last_trade_date: '2023-11-28' },
            { bioguide_id: 'W000817', first_name: 'Elizabeth', last_name: 'Warren', party: 'D', state: 'MA', chamber: 'senate', total_volume: 0, total_trades: 0 }
        ];

        const filtered = party ? allMembers.filter(m => m.party === party) : allMembers;

        return HttpResponse.json({
            data: filtered,
            pagination: {
                total: filtered.length,
                count: filtered.length,
                limit: 50,
                offset: 0
            }
        });
    }),
    http.get(`${API_BASE}/v1/analytics/insights`, ({ request }) => {
        const url = new URL(request.url);
        const type = url.searchParams.get('type');

        if (type === 'timing') {
            return HttpResponse.json({
                day_of_week: [
                    { day_name: 'Monday', pct_of_volume: 22.5, trade_count: 120 },
                    { day_name: 'Tuesday', pct_of_volume: 18.2, trade_count: 95 }
                ],
                month_of_year: [
                    { month_name: 'January', pct_of_volume: 12.5, trade_count: 450 },
                    { month_name: 'February', pct_of_volume: 10.2, trade_count: 380 }
                ]
            });
        }

        if (type === 'sector') {
            return HttpResponse.json({
                sector_summary: [
                    { sector: 'Technology', total_volume: 2500000, pct_of_total: 35.5, flow_signal: 'BUY' },
                    { sector: 'Energy', total_volume: 1800000, pct_of_total: 25.2, flow_signal: 'SELL' }
                ],
                party_preferences: [
                    { sector: 'Technology', d_pct: 65, r_pct: 35, party_lean: 'D' },
                    { sector: 'Defense', d_pct: 30, r_pct: 70, party_lean: 'R' }
                ]
            });
        }

        // Default: trending
        return HttpResponse.json({
            sector_rotation: [
                { sector: 'Energy', rotation_signal: 'STRONG_BUY' },
                { sector: 'Financials', rotation_signal: 'SELL' }
            ],
            top_stocks: [
                { ticker: 'TSLA', total_volume: 500000 },
                { ticker: 'AMD', total_volume: 450000 }
            ]
        });
    }),

    // Congressional Alpha
    http.get(`${API_BASE}/v1/analytics/alpha`, () => {
        return HttpResponse.json({
            data: [
                { name: 'Nancy Pelosi', alpha: 0.15, total_trades: 12, party: 'D' },
                { name: 'Markwayne Mullin', alpha: 0.12, total_trades: 45, party: 'R' }
            ]
        });
    }),

    // Portfolio Reconstruction
    http.get(`${API_BASE}/v1/analytics/portfolio`, () => {
        return HttpResponse.json({
            portfolios: [
                {
                    member_key: 'P000197',
                    name: 'Nancy Pelosi',
                    estimated_portfolio_value: 15000000,
                    position_count: 24,
                    confidence_score: 0.85,
                    top_sector: 'Technology'
                }
            ]
        });
    }),

    // Conflict Detection
    http.get(`${API_BASE}/v1/analytics/conflicts`, () => {
        return HttpResponse.json({
            conflicts: [
                {
                    id: 'conf1',
                    member_name: 'John Doe',
                    ticker: 'LMT',
                    severity: 'HIGH',
                    bill_id: 'H.R.1234',
                    conflict_score: 85,
                    days_offset: 5
                }
            ],
            summary: {
                critical_count: 1,
                high_count: 2,
                medium_count: 5,
                low_count: 12
            }
        });
    }),

    // Bills List
    http.get(`${API_BASE}/v1/congress/bills`, () => {
        return HttpResponse.json([
            {
                congress: 119,
                bill_type: 'hr',
                bill_number: 1,
                title: 'To provide for the common defense.',
                latest_action_date: '2025-01-20',
                latest_action_text: 'Introduced in House',
                policy_area: 'Defense',
                sponsor_name: 'John Doe',
                cosponsors_count: 5,
                trade_correlations_count: 2
            }
        ]);
    }),

    // Bill Detail
    http.get(`${API_BASE}/v1/congress/bills/:billId`, ({ params }) => {
        const { billId } = params;
        return HttpResponse.json({
            bill: {
                congress: 119,
                bill_type: 'hr',
                bill_number: 1,
                title: `Detail for Bill ${billId}`,
                latest_action_date: '2025-01-20',
                latest_action_text: 'Introduced in House',
                policy_area: 'Defense'
            },
            sponsor: {
                bioguide_id: 'D000123',
                name: 'John Doe',
                party: 'D',
                state: 'CA'
            },
            cosponsors_count: 5,
            actions_count_total: 10,
            trade_correlations_count: 2,
            industry_tags: [{ industry: 'Defense', confidence: 0.95 }],
            trade_correlations: []
        });
    }),

    // Bill Summaries
    http.get(`${API_BASE}/v1/congress/bills/:billId/summaries`, () => {
        return HttpResponse.json({
            summaries: [
                { text: 'This bill provides for the common defense by increasing funding.' }
            ],
            count: 1
        });
    }),

    // Bill Text
    http.get(`${API_BASE}/v1/congress/bills/:billId/text`, () => {
        return HttpResponse.json([
            { format: 'PDF', url: 'https://example.com/bill.pdf' },
            { format: 'XML', url: 'https://example.com/bill.xml' }
        ]);
    }),

    // Bill Actions
    http.get(`${API_BASE}/v1/congress/bills/:billId/actions`, () => {
        return HttpResponse.json({
            actions: [
                { action_date: '2025-01-20', action_text: 'Introduced in House', chamber: 'House' }
            ],
            count: 1
        });
    }),

    // Bill Committees
    http.get(`${API_BASE}/v1/congress/bills/:billId/committees`, () => {
        return HttpResponse.json({
            committees: [
                { name: 'House Committee on Armed Services', system_code: 'HSAS' }
            ],
            count: 1
        });
    }),

    // Bill Cosponsors
    http.get(`${API_BASE}/v1/congress/bills/:billId/cosponsors`, () => {
        return HttpResponse.json({
            cosponsors: [
                { bioguide_id: 'S000123', name: 'Jane Smith', party: 'R', state: 'TX', sponsored_date: '2025-01-21' }
            ],
            count: 1
        });
    }),

    // Bill Subjects
    http.get(`${API_BASE}/v1/congress/bills/:billId/subjects`, () => {
        return HttpResponse.json({
            subjects: ['Defense spending', 'Military personnel'],
            count: 2
        });
    }),

    // Bill Titles
    http.get(`${API_BASE}/v1/congress/bills/:billId/titles`, () => {
        return HttpResponse.json({
            titles: [
                { title: 'Common Defense Act of 2025', title_type: 'Short Title' }
            ],
            count: 1
        });
    }),

    // Bill Amendments
    http.get(`${API_BASE}/v1/congress/bills/:billId/amendments`, () => {
        return HttpResponse.json({
            amendments: [
                { number: 'H.Amt.1', description: 'To increase funding for research.', submit_date: '2025-01-22' }
            ],
            count: 1
        });
    }),

    // Bill Related
    http.get(`${API_BASE}/v1/congress/bills/:billId/related`, () => {
        return HttpResponse.json({
            relatedBills: [
                { congress: 119, bill_type: 's', bill_number: 5, title: 'Senate companion bill', relationship_type: 'Identical' }
            ],
            count: 1
        });
    })
];
