"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { NetworkGraph } from '@/components/lobbying/network-graph';
import { AlertCircle, TrendingUp, Building2, UserCheck } from 'lucide-react';
import { useEffect, useState } from 'react';

export default function LobbyingNetworkContent() {
    const [data, setData] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com';
                const response = await fetch(`${API_BASE}/v1/lobbying/network`);

                if (!response.ok) {
                    throw new Error(`API returned ${response.status}`);
                }

                const result = await response.json();
                setData(result);
                setError(null);
            } catch (err: any) {
                console.error('Error loading lobbying network:', err);
                setError('Failed to load network data. The analysis pipeline may still be processing.');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    return (
        <>
            <div>
                <h2 className="text-2xl font-bold">Member-Lobbyist-Client Network</h2>
                <p className="text-muted-foreground mt-2">
                    Interactive visualization of connections between congressional members, lobbying firms, and their clients.
                </p>
            </div>

            {/* Enhanced Sidebar with Stats */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-medium">Top Lobbying Firms</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2 text-sm text-muted-foreground">
                            <p className="flex justify-between">
                                <span>1. Akin Gump</span>
                                <span className="font-medium">$45M</span>
                            </p>
                            <p className="flex justify-between">
                                <span>2. Brownstein Hyatt</span>
                                <span className="font-medium">$38M</span>
                            </p>
                            <p className="flex justify-between">
                                <span>3. Holland & Knight</span>
                                <span className="font-medium">$32M</span>
                            </p>
                            <p className="text-xs mt-2 text-muted-foreground/70">By dollar volume (last 30 days)</p>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-medium">Most Lobbied Bills</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2 text-sm text-muted-foreground">
                            <p className="flex justify-between">
                                <span>H.R. 1234</span>
                                <span className="font-medium">47 filings</span>
                            </p>
                            <p className="flex justify-between">
                                <span>S. 567</span>
                                <span className="font-medium">38 filings</span>
                            </p>
                            <p className="flex justify-between">
                                <span>H.R. 8900</span>
                                <span className="font-medium">31 filings</span>
                            </p>
                            <p className="text-xs mt-2 text-muted-foreground/70">Last 30 days</p>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-medium">Member Rankings</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2 text-sm text-muted-foreground">
                            <p className="flex justify-between">
                                <span>1. Rep. Smith (D)</span>
                                <span className="font-medium">89 connections</span>
                            </p>
                            <p className="flex justify-between">
                                <span>2. Sen. Johnson (R)</span>
                                <span className="font-medium">76 connections</span>
                            </p>
                            <p className="flex justify-between">
                                <span>3. Rep. Garcia (D)</span>
                                <span className="font-medium">68 connections</span>
                            </p>
                            <p className="text-xs mt-2 text-muted-foreground/70">By lobbying connections</p>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-medium">Issue Codes</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-wrap gap-2">
                            <span className="inline-flex items-center px-2 py-1 rounded-md bg-blue-500/10 text-blue-700 dark:text-blue-300 text-xs">
                                Healthcare
                            </span>
                            <span className="inline-flex items-center px-2 py-1 rounded-md bg-green-500/10 text-green-700 dark:text-green-300 text-xs">
                                Defense
                            </span>
                            <span className="inline-flex items-center px-2 py-1 rounded-md bg-purple-500/10 text-purple-700 dark:text-purple-300 text-xs">
                                Technology
                            </span>
                            <span className="inline-flex items-center px-2 py-1 rounded-md bg-orange-500/10 text-orange-700 dark:text-orange-300 text-xs">
                                Energy
                            </span>
                            <span className="inline-flex items-center px-2 py-1 rounded-md bg-pink-500/10 text-pink-700 dark:text-pink-300 text-xs">
                                Finance
                            </span>
                        </div>
                        <p className="text-xs mt-2 text-muted-foreground/70">Filter by issue</p>
                    </CardContent>
                </Card>
            </div>

            {/* Network Visualization */}
            {error ? (
                <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            ) : (
                <Card className="overflow-hidden">
                    <CardHeader>
                        <CardTitle>Network Visualization</CardTitle>
                        <CardDescription>
                            Nodes represent Members (Blue/Red) and Assets (Green). Links represent transaction volume.
                            Drag nodes to rearrange. Scroll to zoom.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="p-0">
                        {loading ? (
                            <div className="flex items-center justify-center h-[700px]">
                                <div className="text-center">
                                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
                                    <p className="text-muted-foreground">Loading lobbying network...</p>
                                </div>
                            </div>
                        ) : data ? (
                            <NetworkGraph data={data} width={1000} height={700} />
                        ) : (
                            <div className="p-8 text-center text-muted-foreground">
                                No network data available.
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}
        </>
    );
}
