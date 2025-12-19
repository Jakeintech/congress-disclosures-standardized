'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { TradingNetworkGraph } from '@/components/analysis/trading-network-graph';
import { useNetworkGraph } from '@/hooks/use-api';
import { DataContainer } from '@/components/ui/data-container';
import { AlertCircle } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

export default function TradingNetworkPage() {
    const { data, isLoading, isError, error, refetch } = useNetworkGraph({});

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Trading Network Analysis</h1>
                <p className="text-muted-foreground mt-2">
                    Interactive visualization of congressional member trading connections with hierarchical aggregation.
                    Explore by party, chamber, state, or trading volume.
                </p>
            </div>

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
                    <DataContainer
                        isLoading={isLoading}
                        isError={isError}
                        error={error}
                        data={data}
                        onRetry={() => refetch()}
                        loadingSkeleton={<Skeleton className="h-[700px] w-full" />}
                        emptyMessage="No network data available at this time."
                    >
                        {(networkData) => (
                            <TradingNetworkGraph data={networkData} />
                        )}
                    </DataContainer>
                </CardContent>
            </Card>

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
