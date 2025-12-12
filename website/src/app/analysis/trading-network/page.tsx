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
                setError(`Failed to load network data: ${err.message}`);
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
                            <div className="flex items-center justify-center h-[700px]">
                                <div className="text-center">
                                    <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                                    <p className="text-muted-foreground">No network data available</p>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}

            {/* Help/Instructions Card */}
            <div className="grid gap-6 md:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">Understanding the Network</CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm space-y-2">
                        <p><strong>Nodes:</strong></p>
                        <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                            <li><strong>Individual Members:</strong> Circles colored by party (blue = Democrat, red = Republican)</li>
                            <li><strong>Assets/Stocks:</strong> Diamond shapes, sized by trading volume</li>
                            <li><strong>Aggregate Nodes:</strong> Larger nodes representing groups (Party, Chamber, State)</li>
                        </ul>
                        <p className="mt-3"><strong>Links:</strong></p>
                        <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                            <li>Width represents transaction volume</li>
                            <li>Color indicates net direction (green = buy, red = sell)</li>
                        </ul>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">Interaction Guide</CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm">
                        <ul className="space-y-1 text-muted-foreground list-disc list-inside">
                            <li><strong>Click</strong> aggregate nodes to expand/collapse</li>
                            <li><strong>Drag</strong> nodes to rearrange the layout</li>
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
