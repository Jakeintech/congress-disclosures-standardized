"use client"

import { Suspense } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Network, GitBranch, Radar, Info } from "lucide-react";
import { useSearchParams } from "next/navigation";

// Import existing components
import TradingNetworkContent from "./trading-network-tab";
import LobbyingNetworkContent from "./lobbying-network-tab";
import InfluenceNetworkContent from "./influence-network-tab";

function NetworkTabsWithParams() {
    const searchParams = useSearchParams();
    const defaultTab = searchParams.get("tab") || "trading";

    return (
        <Tabs defaultValue={defaultTab} className="space-y-6">
            <TabsList className="grid w-full md:w-auto grid-cols-3 md:inline-grid">
                <TabsTrigger value="trading" className="flex items-center gap-2">
                    <GitBranch className="h-4 w-4" />
                    <span>Trading Network</span>
                </TabsTrigger>
                <TabsTrigger value="lobbying" className="flex items-center gap-2">
                    <Network className="h-4 w-4" />
                    <span>Lobbying Network</span>
                </TabsTrigger>
                <TabsTrigger value="influence" className="flex items-center gap-2">
                    <Radar className="h-4 w-4" />
                    <span>Influence Network</span>
                </TabsTrigger>
            </TabsList>

            {/* Trading Network Tab */}
            <TabsContent value="trading" className="space-y-6">
                <TradingNetworkContent />
            </TabsContent>

            {/* Lobbying Network Tab */}
            <TabsContent value="lobbying" className="space-y-6">
                <LobbyingNetworkContent />
            </TabsContent>

            {/* Influence Network Tab */}
            <TabsContent value="influence" className="space-y-6">
                <InfluenceNetworkContent />
            </TabsContent>
        </Tabs>
    );
}

export default function UnifiedNetworksPage() {
    return (
        <div className="space-y-8">
            {/* Page Header */}
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Network Analysis</h1>
                <p className="text-muted-foreground mt-2">
                    Explore connections between members, assets, bills, and lobbying activity through interactive network visualizations
                </p>
            </div>

            {/* Info Alert */}
            <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                    These network visualizations use force-directed graphs to reveal hidden patterns.
                    Drag nodes to rearrange, scroll to zoom, and click to interact with the data.
                </AlertDescription>
            </Alert>

            {/* Unified Tabs - Wrapped in Suspense for useSearchParams */}
            <Suspense fallback={
                <Tabs defaultValue="trading" className="space-y-6">
                    <TabsList className="grid w-full md:w-auto grid-cols-3 md:inline-grid">
                        <TabsTrigger value="trading">Trading Network</TabsTrigger>
                        <TabsTrigger value="lobbying">Lobbying Network</TabsTrigger>
                        <TabsTrigger value="influence">Influence Network</TabsTrigger>
                    </TabsList>
                    <div className="flex items-center justify-center h-[400px]">
                        <p className="text-muted-foreground">Loading...</p>
                    </div>
                </Tabs>
            }>
                <NetworkTabsWithParams />
            </Suspense>

            {/* Network Analysis Guide */}
            <Card className="border-dashed">
                <CardHeader>
                    <CardTitle className="text-base">Network Analysis Features</CardTitle>
                    <CardDescription>
                        Understanding the power of network visualization
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
                        <div>
                            <h4 className="font-medium mb-2">Trading Network</h4>
                            <p className="text-muted-foreground">
                                Reveals which members trade similar assets, identifying trading cliques and coordinated patterns.
                                Aggregation modes help simplify complex networks.
                            </p>
                        </div>
                        <div>
                            <h4 className="font-medium mb-2">Lobbying Network</h4>
                            <p className="text-muted-foreground">
                                Shows connections between members, lobbying firms, and clients. Helps identify potential
                                influence pathways and concentrated lobbying efforts.
                            </p>
                        </div>
                        <div>
                            <h4 className="font-medium mb-2">Influence Network</h4>
                            <p className="text-muted-foreground">
                                Triple correlation analysis linking bills, trades, and lobbying. The most powerful tool for
                                detecting potential conflicts of interest.
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
