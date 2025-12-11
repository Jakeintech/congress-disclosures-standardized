"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { TradingNetworkGraph } from '@/components/analysis/trading-network-graph';
import { AlertCircle } from 'lucide-react';
import { useEffect, useState } from 'react';

export default function TradingNetworkContent() {
    const [data, setData] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com';
                const response = await fetch(`${API_BASE}/v1/analytics/network-graph`);

                if (!response.ok) {
                    throw new Error(`API returned ${response.status}`);
                }

                const result = await response.json();
                const networkData = result.data || result;

                if (!networkData.nodes || !networkData.links) {
                    throw new Error('Invalid network data structure');
                }

                setData(networkData);
                setError(null);
            } catch (err: any) {
                console.error('Error loading network:', err);
                setError(`Failed to load network data: ${err.message}`);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    return (
        <>
            <div>
                <h2 className="text-2xl font-bold">Member-Asset Trading Network</h2>
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
                        <CardTitle>Interactive Graph</CardTitle>
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
        </>
    );
}
