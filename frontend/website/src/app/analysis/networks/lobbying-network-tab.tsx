"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { NetworkGraph } from '@/components/lobbying/network-graph';
import { Building2, Info } from 'lucide-react';
import { useLobbyingNetwork } from '@/hooks/use-api';
import { DataContainer } from '@/components/ui/data-container';
import { Skeleton } from '@/components/ui/skeleton';

export default function LobbyingNetworkContent() {
    const { data, isLoading, isError, error, refetch } = useLobbyingNetwork();

    const loadingSkeleton = (
        <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                {[...Array(4)].map((_, i) => (
                    <Skeleton key={i} className="h-32 w-full" />
                ))}
            </div>
            <Skeleton className="h-[700px] w-full" />
        </div>
    );

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold">Member-Lobbyist-Client Network</h2>
                    <p className="text-muted-foreground mt-2">
                        Interactive visualization of connections between congressional members, lobbying firms, and their clients.
                    </p>
                </div>
                <div className="flex gap-2">
                    <Building2 className="h-10 w-10 text-primary/20" />
                </div>
            </div>

            {/* Enhanced Sidebar with Stats (Mocked for now, but in standardized cards) */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                <Card className="bg-accent/5 border-none shadow-none">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Top Lobbying Firms</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2 text-sm">
                            <p className="flex justify-between">
                                <span className="font-medium">1. Akin Gump</span>
                                <span className="text-emerald-600 font-mono">$45M</span>
                            </p>
                            <p className="flex justify-between">
                                <span className="font-medium">2. Brownstein Hyatt</span>
                                <span className="text-emerald-600 font-mono">$38M</span>
                            </p>
                        </div>
                    </CardContent>
                </Card>

                <Card className="bg-accent/5 border-none shadow-none">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Most Lobbied Bills</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2 text-sm">
                            <p className="flex justify-between">
                                <span className="font-medium">H.R. 1234</span>
                                <span className="text-primary font-mono">47 Filings</span>
                            </p>
                            <p className="flex justify-between">
                                <span className="font-medium">S. 567</span>
                                <span className="text-primary font-mono">38 Filings</span>
                            </p>
                        </div>
                    </CardContent>
                </Card>

                <Card className="bg-accent/5 border-none shadow-none">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Member Connectivity</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2 text-sm">
                            <p className="flex justify-between">
                                <span className="font-medium">Rep. Smith (D)</span>
                                <span className="text-orange-600 font-mono">89 Linked</span>
                            </p>
                            <p className="flex justify-between">
                                <span className="font-medium">Sen. Johnson (R)</span>
                                <span className="text-orange-600 font-mono">76 Linked</span>
                            </p>
                        </div>
                    </CardContent>
                </Card>

                <Card className="bg-accent/5 border-none shadow-none">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Primary Issue Codes</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-wrap gap-1">
                            {['Healthcare', 'Defense', 'Tech', 'Energy'].map(tag => (
                                <span key={tag} className="px-2 py-0.5 rounded bg-background text-[10px] font-bold border">
                                    {tag}
                                </span>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>

            <DataContainer
                isLoading={isLoading}
                isError={isError}
                error={error}
                data={data}
                onRetry={() => refetch()}
                loadingSkeleton={loadingSkeleton}
            >
                {(networkData: any) => (
                    <Card className="overflow-hidden border-none shadow-none bg-accent/5">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <Info className="h-4 w-4 text-primary" />
                                <CardTitle className="text-lg">Network Visualization</CardTitle>
                            </div>
                            <CardDescription>
                                Connections between Members, Lobbying Firms, and Clients. Size indicates filing volume.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="p-0 bg-background m-4 rounded-xl border">
                            <NetworkGraph data={networkData} width={1000} height={700} />
                        </CardContent>
                    </Card>
                )}
            </DataContainer>
        </div>
    );
}
