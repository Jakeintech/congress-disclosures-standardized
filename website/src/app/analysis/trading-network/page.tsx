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
                const response = await fetch('/api/analytics/network-graph');
                if (!response.ok) {
                    throw new Error('Failed to fetch network data');
                }
                const result = await response.json();
                setData(result.data || result);
            } catch (err: any) {
                console.error('Error loading network:', err);
                setError(err.message || 'Failed to load network data');
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
