import { Metadata } from "next";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Activity, TrendingUp, AlertTriangle, Network } from "lucide-react";

export const metadata: Metadata = {
    title: "Analytics Dashboard | Congress Transparency",
    description: "Comprehensive analytics on congressional trading patterns, conflicts of interest, and market correlations",
};

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
                            Trading Clusters
                        </CardTitle>
                        <Network className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">12</div>
                        <p className="text-xs text-muted-foreground">
                            Coordinated trading patterns
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Main Analytics Tabs */}
            <Tabs defaultValue="leaderboard" className="space-y-4">
                <TabsList>
                    <TabsTrigger value="leaderboard">Performance Leaderboard</TabsTrigger>
                    <TabsTrigger value="sectors">Sector Analysis</TabsTrigger>
                    <TabsTrigger value="conflicts">Conflicts</TabsTrigger>
                    <TabsTrigger value="patterns">Trading Patterns</TabsTrigger>
                </TabsList>

                <TabsContent value="leaderboard" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Congressional Alpha Leaderboard</CardTitle>
                            <CardDescription>
                                Top performing members vs S&P 500 benchmark (last 12 months)
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="rounded-md border">
                                <div className="p-8 text-center text-sm text-muted-foreground">
                                    <TrendingUp className="mx-auto h-12 w-12 mb-4 opacity-50" />
                                    <p className="font-medium">Performance data coming soon</p>
                                    <p className="mt-2 text-xs">
                                        This feature requires Gold layer aggregation script: <code className="text-xs bg-muted px-1 py-0.5 rounded">compute_agg_congressional_alpha.py</code>
                                    </p>
                                    <p className="mt-2 text-xs">
                                        Will show: Individual member alpha, Sharpe ratios, win rates, and benchmark comparisons
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="sectors" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Sector Trading Heatmap</CardTitle>
                            <CardDescription>
                                Which sectors are seeing the most congressional activity
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="rounded-md border">
                                <div className="p-8 text-center text-sm text-muted-foreground">
                                    <Activity className="mx-auto h-12 w-12 mb-4 opacity-50" />
                                    <p className="font-medium">Sector analysis coming soon</p>
                                    <p className="mt-2 text-xs">
                                        This feature requires Gold layer aggregation: <code className="text-xs bg-muted px-1 py-0.5 rounded">compute_agg_sector_analysis.py</code>
                                    </p>
                                    <p className="mt-2 text-xs">
                                        Will show: Sector rotation patterns, party-specific trends, and timing analysis
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="conflicts" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Potential Conflicts of Interest</CardTitle>
                            <CardDescription>
                                Automated detection of bill-trade-lobbying correlations
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="rounded-md border">
                                <div className="p-8 text-center text-sm text-muted-foreground">
                                    <AlertTriangle className="mx-auto h-12 w-12 mb-4 opacity-50" />
                                    <p className="font-medium">Conflict detection engine coming soon</p>
                                    <p className="mt-2 text-xs">
                                        Phase 3 feature: Automated pattern recognition with conflict scoring (0-100)
                                    </p>
                                    <p className="mt-2 text-xs">
                                        Will show: Committee membership + bill votes + trade timing + lobbying connections
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="patterns" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Unusual Trading Patterns</CardTitle>
                            <CardDescription>
                                Anomaly detection and coordinated trading activity
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="rounded-md border">
                                <div className="p-8 text-center text-sm text-muted-foreground">
                                    <Network className="mx-auto h-12 w-12 mb-4 opacity-50" />
                                    <p className="font-medium">Pattern detection coming soon</p>
                                    <p className="mt-2 text-xs">
                                        Phase 3 feature: Anomaly detection and trading clique identification
                                    </p>
                                    <p className="mt-2 text-xs">
                                        Will show: Volume spikes, coordinated trades, first-time purchases, and unusual timing
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>

            {/* Coming Soon Notice */}
            <Card className="border-dashed">
                <CardHeader>
                    <CardTitle className="text-base">🚀 More Analytics Coming Soon</CardTitle>
                    <CardDescription>
                        Phase 2-3 will add: Trading volume timeseries • Bill-trade correlations • Portfolio reconstruction • Timing heatmaps • Predictive indicators
                    </CardDescription>
                </CardHeader>
            </Card>
        </div>
    );
}
