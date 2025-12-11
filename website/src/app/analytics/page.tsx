"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Activity, TrendingUp, AlertTriangle, Network, Wallet, Sparkles } from "lucide-react";
import {
    CongressionalAlphaCard,
    ConflictDetectionCard,
    PortfolioReconstructionCard,
    PatternInsightsCard
} from "@/components/analytics";

export default function AnalyticsPage() {
    return (
        <div className="space-y-8">
            {/* Page Header */}
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Analytics Dashboard</h1>
                <p className="text-muted-foreground mt-2">
                    Deep insights into congressional trading patterns, performance metrics, and conflict detection
                </p>
            </div>

            {/* Quick Stats */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">
                            Total Volume (90d)
                        </CardTitle>
                        <Activity className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">$2.4B</div>
                        <p className="text-xs text-muted-foreground">
                            +20.1% from previous period
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">
                            Congressional Alpha
                        </CardTitle>
                        <TrendingUp className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">+12.4%</div>
                        <p className="text-xs text-muted-foreground">
                            vs S&P 500 benchmark
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">
                            Active Conflicts
                        </CardTitle>
                        <AlertTriangle className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">47</div>
                        <p className="text-xs text-muted-foreground">
                            23 high-severity detected
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">
                            Portfolios Tracked
                        </CardTitle>
                        <Wallet className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">535</div>
                        <p className="text-xs text-muted-foreground">
                            Full Congress coverage
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Main Analytics Tabs */}
            <Tabs defaultValue="alpha" className="space-y-4">
                <TabsList className="flex-wrap">
                    <TabsTrigger value="alpha">
                        <TrendingUp className="h-4 w-4 mr-2" />
                        Alpha
                    </TabsTrigger>
                    <TabsTrigger value="conflicts">
                        <AlertTriangle className="h-4 w-4 mr-2" />
                        Conflicts
                    </TabsTrigger>
                    <TabsTrigger value="portfolios">
                        <Wallet className="h-4 w-4 mr-2" />
                        Portfolios
                    </TabsTrigger>
                    <TabsTrigger value="insights">
                        <Sparkles className="h-4 w-4 mr-2" />
                        Insights
                    </TabsTrigger>
                    <TabsTrigger value="sectors">
                        <Activity className="h-4 w-4 mr-2" />
                        Sectors
                    </TabsTrigger>
                </TabsList>

                {/* Alpha Tab */}
                <TabsContent value="alpha" className="space-y-4">
                    <div className="grid gap-4 md:grid-cols-2">
                        <CongressionalAlphaCard type="member" limit={10} />
                        <CongressionalAlphaCard type="party" limit={5} />
                    </div>
                    <CongressionalAlphaCard type="sector_rotation" limit={10} />
                </TabsContent>

                {/* Conflicts Tab */}
                <TabsContent value="conflicts" className="space-y-4">
                    <ConflictDetectionCard severity="all" limit={15} showSummary={true} />
                </TabsContent>

                {/* Portfolios Tab */}
                <TabsContent value="portfolios" className="space-y-4">
                    <PortfolioReconstructionCard limit={10} />
                </TabsContent>

                {/* Insights Tab */}
                <TabsContent value="insights" className="space-y-4">
                    <div className="grid gap-4 md:grid-cols-2">
                        <PatternInsightsCard type="trending" />
                        <PatternInsightsCard type="timing" />
                    </div>
                </TabsContent>

                {/* Sectors Tab */}
                <TabsContent value="sectors" className="space-y-4">
                    <PatternInsightsCard type="sector" />
                </TabsContent>
            </Tabs>

            {/* Feature Legend */}
            <Card className="border-dashed">
                <CardHeader>
                    <CardTitle className="text-base">🚀 God Mode Analytics</CardTitle>
                    <CardDescription>
                        <span className="text-green-600">✓ Congressional Alpha</span> •{" "}
                        <span className="text-green-600">✓ Conflict Detection</span> •{" "}
                        <span className="text-green-600">✓ Portfolio Reconstruction</span> •{" "}
                        <span className="text-green-600">✓ Pattern Insights</span> •{" "}
                        <span className="text-green-600">✓ Sector Analysis</span>
                    </CardDescription>
                </CardHeader>
            </Card>
        </div>
    );
}

