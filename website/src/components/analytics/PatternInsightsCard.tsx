"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Clock, PieChart, TrendingUp, BarChart3 } from "lucide-react";
import { usePatternInsights } from "@/hooks/use-api";

interface TimingData {
    day_name?: string;
    month_name?: string;
    total_volume: number;
    pct_of_volume: number;
    deviation?: number;
    trade_count: number;
}

interface SectorData {
    sector: string;
    total_volume: number;
    pct_of_total: number;
    flow_signal?: string;
    party_lean?: string;
    d_pct?: number;
    r_pct?: number;
}

interface PatternInsightsCardProps {
    type?: 'timing' | 'sector' | 'trending';
}

export function PatternInsightsCard({
    type = 'trending'
}: PatternInsightsCardProps) {
    const { data, isLoading, error } = usePatternInsights(type);
    const errorMessage = error instanceof Error ? error.message : error ? String(error) : null;

    const formatVolume = (val: number | undefined) => {
        if (!val) return '--';
        if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`;
        if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`;
        return `$${val.toFixed(0)}`;
    };

    const getSignalColor = (signal: string | undefined) => {
        switch (signal) {
            case 'STRONG_BUY': return 'bg-green-600';
            case 'BUY': return 'bg-green-500';
            case 'STRONG_SELL': return 'bg-red-600';
            case 'SELL': return 'bg-red-500';
            default: return 'bg-gray-500';
        }
    };

    if (isLoading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Sparkles className="h-5 w-5" />
                        Pattern Insights
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center justify-center py-8">
                        <div className="animate-pulse text-muted-foreground">Analyzing patterns...</div>
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (errorMessage) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Pattern Insights</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="text-destructive py-4">Error: {errorMessage}</div>
                </CardContent>
            </Card>
        );
    }

    // Render based on type
    if (type === 'timing') {
        const dayData = data?.day_of_week || [];
        const monthData = data?.month_of_year || [];

        return (
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Clock className="h-5 w-5" />
                        Trading Timing Patterns
                    </CardTitle>
                    <CardDescription>
                        When does Congress trade?
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-6">
                        {/* Day of Week */}
                        <div>
                            <h4 className="text-sm font-medium mb-2">By Day of Week</h4>
                            <div className="grid grid-cols-7 gap-1">
                                {dayData.map((day: TimingData, idx: number) => {
                                    const intensity = Math.min(day.pct_of_volume / 25, 1);
                                    return (
                                        <div
                                            key={idx}
                                            className="text-center p-2 rounded"
                                            style={{
                                                backgroundColor: `rgba(59, 130, 246, ${intensity})`,
                                                color: intensity > 0.5 ? 'white' : 'inherit'
                                            }}
                                        >
                                            <div className="text-xs font-medium">{day.day_name?.slice(0, 3)}</div>
                                            <div className="text-sm font-bold">{day.pct_of_volume?.toFixed(1)}%</div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Month of Year */}
                        <div>
                            <h4 className="text-sm font-medium mb-2">By Month</h4>
                            <div className="grid grid-cols-6 gap-1">
                                {monthData.slice(0, 12).map((month: TimingData, idx: number) => {
                                    const intensity = Math.min(month.pct_of_volume / 12, 1);
                                    return (
                                        <div
                                            key={idx}
                                            className="text-center p-2 rounded"
                                            style={{
                                                backgroundColor: `rgba(34, 197, 94, ${intensity})`,
                                                color: intensity > 0.5 ? 'white' : 'inherit'
                                            }}
                                        >
                                            <div className="text-xs font-medium">{month.month_name}</div>
                                            <div className="text-sm font-bold">{month.pct_of_volume?.toFixed(1)}%</div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (type === 'sector') {
        const sectorSummary = data?.sector_summary || [];
        const partyPrefs = data?.party_preferences || [];

        return (
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <PieChart className="h-5 w-5" />
                        Sector Analysis
                    </CardTitle>
                    <CardDescription>
                        Trading activity by sector with party breakdown
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {sectorSummary.length === 0 ? (
                            <div className="text-center text-muted-foreground py-8">
                                No sector data available
                            </div>
                        ) : (
                            sectorSummary.slice(0, 8).map((sector: SectorData, idx: number) => (
                                <div key={idx} className="flex items-center justify-between py-2 border-b last:border-0">
                                    <div className="flex items-center gap-3">
                                        <span className="font-medium">{sector.sector}</span>
                                        {sector.flow_signal && (
                                            <Badge className={getSignalColor(sector.flow_signal)}>
                                                {sector.flow_signal.replace('_', ' ')}
                                            </Badge>
                                        )}
                                    </div>
                                    <div className="text-right">
                                        <div className="font-mono">{formatVolume(sector.total_volume)}</div>
                                        <div className="text-xs text-muted-foreground">
                                            {sector.pct_of_total?.toFixed(1)}% of total
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}

                        {/* Party Preferences */}
                        {partyPrefs.length > 0 && (
                            <div className="mt-4 pt-4 border-t">
                                <h4 className="text-sm font-medium mb-2">Party Sector Preferences</h4>
                                <div className="space-y-2">
                                    {partyPrefs.slice(0, 5).map((pref: SectorData, idx: number) => (
                                        <div key={idx} className="flex items-center gap-3">
                                            <span className="text-sm w-32">{pref.sector}</span>
                                            <div className="flex-1 flex h-4 rounded overflow-hidden">
                                                <div
                                                    className="bg-blue-500"
                                                    style={{ width: `${pref.d_pct || 0}%` }}
                                                    title={`D: ${pref.d_pct}%`}
                                                />
                                                <div
                                                    className="bg-red-500"
                                                    style={{ width: `${pref.r_pct || 0}%` }}
                                                    title={`R: ${pref.r_pct}%`}
                                                />
                                            </div>
                                            <Badge variant="outline" className="text-xs">
                                                {pref.party_lean}
                                            </Badge>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>
        );
    }

    // Default: trending
    const rotation = data?.sector_rotation || [];
    const topStocks = data?.top_stocks || [];

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5" />
                    What&apos;s Trending
                </CardTitle>
                <CardDescription>
                    Current trading trends and momentum signals
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="space-y-6">
                    {/* Sector Rotation Signals */}
                    <div>
                        <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                            <BarChart3 className="h-4 w-4" />
                            Sector Rotation Signals
                        </h4>
                        <div className="grid grid-cols-2 gap-2">
                            {rotation.slice(0, 6).map((item: any, idx: number) => (
                                <div
                                    key={idx}
                                    className="p-2 rounded border flex items-center justify-between"
                                >
                                    <span className="text-sm">{item.sector}</span>
                                    <Badge className={getSignalColor(item.rotation_signal)}>
                                        {item.rotation_signal?.replace('_', ' ') || 'NEUTRAL'}
                                    </Badge>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Top Traded Stocks */}
                    <div>
                        <h4 className="text-sm font-medium mb-2">Top Traded Stocks</h4>
                        <div className="flex flex-wrap gap-2">
                            {topStocks.slice(0, 10).map((stock: any, idx: number) => (
                                <Badge key={idx} variant="secondary" className="py-1">
                                    <span className="font-mono">{stock.ticker}</span>
                                    <span className="ml-1 text-muted-foreground">
                                        {formatVolume(stock.total_volume)}
                                    </span>
                                </Badge>
                            ))}
                        </div>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
