"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { TradingNetworkGraph } from '@/components/analysis/trading-network-graph';
import { useNetworkGraph } from '@/hooks/use-api';
import { DataContainer } from '@/components/ui/data-container';
import { Skeleton } from '@/components/ui/skeleton';

export default function TradingNetworkContent() {
    const { data, isLoading, isError, error, refetch } = useNetworkGraph({
        view_mode: 'aggregate'
    });

    const loadingSkeleton = (
        <Card>
            <CardHeader>
                <CardTitle>Interactive Graph</CardTitle>
                <CardDescription>
                    Nodes represent congressional members and assets they trade.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="flex flex-col items-center justify-center h-[700px] space-y-4">
                    <Skeleton className="h-12 w-12 rounded-full" />
                    <Skeleton className="h-4 w-48" />
                    <div className="w-full h-full bg-muted/20 animate-pulse rounded-lg" />
                </div>
            </CardContent>
        </Card>
    );

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold">Member-Asset Trading Network</h2>
                <p className="text-muted-foreground mt-2">
                    Interactive visualization of congressional member trading connections with hierarchical aggregation.
                    Explore by party, chamber, state, or trading volume.
                </p>
            </div>

            <DataContainer
                isLoading={isLoading}
                isError={isError}
                error={error}
                data={data}
                onRetry={() => refetch()}
                loadingSkeleton={loadingSkeleton}
            >
                {(graphData: any) => (
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
                            <TradingNetworkGraph data={graphData} />
                        </CardContent>
                    </Card>
                )}
            </DataContainer>

            {/* Feature explanation cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="bg-accent/5 border-none shadow-none">
                    <CardHeader>
                        <CardTitle className="text-lg">Aggregation Modes</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ul className="grid grid-cols-2 gap-4 text-sm text-muted-foreground">
                            <li><strong className="text-foreground">Party:</strong> Group members by political party</li>
                            <li><strong className="text-foreground">Chamber:</strong> Group by House or Senate</li>
                            <li><strong className="text-foreground">State:</strong> Aggregate activity by state</li>
                            <li><strong className="text-foreground">Volume:</strong> Group by volume tiers</li>
                            <li><strong className="text-foreground">Households:</strong> Group members with family filers</li>
                            <li><strong className="text-foreground">None:</strong> Show all individual members</li>
                        </ul>
                    </CardContent>
                </Card>

                <Card className="bg-accent/5 border-none shadow-none">
                    <CardHeader>
                        <CardTitle className="text-lg">Interaction Guide</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ul className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm text-muted-foreground">
                            <li><strong>Click</strong> aggregates to expand</li>
                            <li><strong>Click</strong> nodes for details</li>
                            <li><strong>Drag</strong> nodes to position</li>
                            <li><strong>Scroll</strong> to zoom in/out</li>
                            <li><strong>Hover</strong> to highlight links</li>
                            <li><strong>Double-click</strong> to reset</li>
                        </ul>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
