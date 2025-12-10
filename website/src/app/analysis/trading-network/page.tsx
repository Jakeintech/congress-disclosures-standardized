'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { TradingNetworkGraph } from '@/components/analysis/trading-network-graph';
import { AlertCircle } from 'lucide-react';
import { useEffect, useState } from 'react';

export default function TradingNetworkPage() {
    const [data, setData] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                // Try the API gateway endpoint first
                const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com';
                const response = await fetch(`${API_BASE}/v1/analytics/network-graph`);

                if (!response.ok) {
                    throw new Error(`API returned ${response.status}`);
                }

                const result = await response.json();
                const networkData = result.data || result;

                // Validate data structure
                if (!networkData.nodes || !networkData.links) {
                    throw new Error('Invalid network data structure');
                }

                setData(networkData);
                setError(null);
            } catch (err: any) {
                console.error('Error loading network:', err);

                // Use mock data for development
                console.log('Loading mock network data for development');
                setData(getMockNetworkData());
                setError('Using mock data - API endpoint not yet available. See docs/BACKEND_TODO.md for implementation details.');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Trading Network Analysis</h1>
                <p className="text-muted-foreground mt-2">
                    Interactive visualization of congressional member trading connections with hierarchical aggregation.
                    Explore by party, chamber, state, or trading volume.
                </p>
            </div>

            {error ? (
                <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            ) : (
                <Card>
                    <CardHeader>
                        <CardTitle>Member-Asset Trading Network</CardTitle>
                        <CardDescription>
                            Nodes represent congressional members and assets they trade.
                            Size indicates trading volume. Click aggregate nodes to expand/collapse.
                            Drag nodes to rearrange, scroll to zoom.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {loading ? (
                            <div className="flex items-center justify-center h-[700px]">
                                <div className="text-center">
                                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
                                    <p className="text-muted-foreground">Loading network data...</p>
                                </div>
                            </div>
                        ) : data ? (
                            <TradingNetworkGraph data={data} />
                        ) : (
                            <div className="text-center text-muted-foreground py-12">
                                No network data available.
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}

            {/* Feature explanation cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Aggregation Modes</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ul className="space-y-2 text-sm text-muted-foreground">
                            <li><strong>Party:</strong> Group members by political party (Democrat/Republican)</li>
                            <li><strong>Chamber:</strong> Group by House or Senate</li>
                            <li><strong>State:</strong> Aggregate trading activity by state</li>
                            <li><strong>Volume:</strong> Group by trading volume tiers (High/Medium/Low)</li>
                            <li><strong>None:</strong> Show all individual members</li>
                        </ul>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Interaction Guide</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ul className="space-y-2 text-sm text-muted-foreground">
                            <li><strong>Click</strong> aggregated nodes (outlined circles) to expand</li>
                            <li><strong>Click</strong> individual nodes to see detailed stats</li>
                            <li><strong>Drag</strong> nodes to manually position them</li>
                            <li><strong>Scroll</strong> to zoom in/out</li>
                            <li><strong>Hover</strong> to highlight connections</li>
                            <li><strong>Double-click</strong> background to reset all expansions</li>
                        </ul>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}

// Mock data for development
function getMockNetworkData() {
    // Generate mock members
    const members = [
        { id: 'P000197', party: 'Democrat', chamber: 'House', state: 'CA', value: 5000000, transaction_count: 45 },
        { id: 'M001143', party: 'Republican', chamber: 'House', state: 'MN', value: 3000000, transaction_count: 32 },
        { id: 'S000510', party: 'Democrat', chamber: 'House', state: 'WA', value: 2500000, transaction_count: 28 },
        { id: 'T000193', party: 'Republican', chamber: 'Senate', state: 'TX', value: 4500000, transaction_count: 38 },
    ];

    const assets = [
        { id: 'AAPL', value: 8000000, transaction_count: 85, degree: 12 },
        { id: 'MSFT', value: 6500000, transaction_count: 72, degree: 10 },
        { id: 'NVDA', value: 5500000, transaction_count: 65, degree: 9 },
        { id: 'TSLA', value: 4000000, transaction_count: 48, degree: 8 },
    ];

    const nodes = [
        ...members.map(m => ({ ...m, group: 'member' })),
        ...assets.map(a => ({ ...a, group: 'asset' }))
    ];

    const links = [];
    members.forEach(member => {
        assets.slice(0, 2 + Math.floor(Math.random() * 3)).forEach(asset => {
            links.push({
                source: member.id,
                target: asset.id,
                value: Math.floor(Math.random() * 500000) + 100000,
                count: Math.floor(Math.random() * 10) + 1,
                type: Math.random() > 0.5 ? 'purchase' : 'sale'
            });
        });
    });

    // Add aggregated nodes
    const aggregated_nodes = [
        {
            id: 'Democrat',
            group: 'party_agg',
            value: 7500000,
            transaction_count: 73,
            party: 'Democrat'
        },
        {
            id: 'Republican',
            group: 'party_agg',
            value: 7500000,
            transaction_count: 70,
            party: 'Republican'
        }
    ];

    // Add aggregated links
    const aggregated_links = assets.map(asset => ([
        {
            source: 'Democrat',
            target: asset.id,
            value: Math.floor(Math.random() * 2000000) + 500000,
            count: Math.floor(Math.random() * 30) + 10,
            is_aggregated: true
        },
        {
            source: 'Republican',
            target: asset.id,
            value: Math.floor(Math.random() * 2000000) + 500000,
            count: Math.floor(Math.random() * 30) + 10,
            is_aggregated: true
        }
    ])).flat();

    return {
        nodes,
        links,
        aggregated_nodes,
        aggregated_links,
        summary_stats: {
            total_transactions: 145,
            total_volume: 24500000
        }
    };
}
