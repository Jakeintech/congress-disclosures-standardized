"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Minus, Users, Building, ArrowUpRight } from "lucide-react";
import { useCongressionalAlpha } from "@/hooks/use-api";
import { DataContainer } from "@/components/ui/data-container";
import { AlphaData } from "@/types/api";

interface CongressionalAlphaCardProps {
    type?: 'member' | 'party' | 'sector_rotation';
    limit?: number;
}

export function CongressionalAlphaCard({
    type = 'member',
    limit = 10
}: CongressionalAlphaCardProps) {
    const { data = [], isLoading, error, refetch } = useCongressionalAlpha(type, limit);

    const formatAlpha = (alpha: number | undefined) => {
        if (alpha === undefined || alpha === null) return '--';
        const pct = (alpha * 100).toFixed(2);
        return alpha >= 0 ? `+${pct}%` : `${pct}%`;
    };

    const formatVolume = (vol: number | undefined) => {
        if (!vol) return '--';
        if (vol >= 1_000_000) return `$${(vol / 1_000_000).toFixed(1)}M`;
        if (vol >= 1_000) return `$${(vol / 1_000).toFixed(0)}K`;
        return `$${vol.toFixed(0)}`;
    };

    const getAlphaColor = (alpha: number | undefined) => {
        if (alpha === undefined || alpha === null) return 'text-muted-foreground';
        if (alpha > 0.01) return 'text-green-600';
        if (alpha < -0.01) return 'text-red-600';
        return 'text-muted-foreground';
    };

    const getSignalBadge = (signal: string | undefined) => {
        switch (signal) {
            case 'STRONG_BUY':
                return <Badge className="bg-green-600">Strong Buy</Badge>;
            case 'BUY':
                return <Badge className="bg-green-500">Buy</Badge>;
            case 'STRONG_SELL':
                return <Badge className="bg-red-600">Strong Sell</Badge>;
            case 'SELL':
                return <Badge className="bg-red-500">Sell</Badge>;
            default:
                return <Badge variant="secondary">Neutral</Badge>;
        }
    };

    return (
        <DataContainer
            isLoading={isLoading}
            isError={!!error}
            error={error}
            data={data}
            onRetry={() => refetch()}
            loadingSkeleton={
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <TrendingUp className="h-5 w-5" />
                            Congressional Alpha
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center justify-center py-8">
                            <div className="animate-pulse text-muted-foreground">Loading alpha data...</div>
                        </div>
                    </CardContent>
                </Card>
            }
        >
            {(data) => (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            {type === 'member' && <Users className="h-5 w-5" />}
                            {type === 'party' && <Building className="h-5 w-5" />}
                            {type === 'sector_rotation' && <ArrowUpRight className="h-5 w-5" />}
                            Congressional Alpha
                            <Badge variant="outline" className="ml-2">
                                {type === 'member' ? 'By Member' : type === 'party' ? 'By Party' : 'Sector Rotation'}
                            </Badge>
                        </CardTitle>
                        <CardDescription>
                            {type === 'member' && 'Trading performance vs S&P 500 benchmark'}
                            {type === 'party' && 'Aggregate alpha by political party'}
                            {type === 'sector_rotation' && 'Sector flow signals based on congressional trading'}
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            {(Array.isArray(data) ? data : []).map((item: AlphaData, idx: number) => (
                                <div
                                    key={idx}
                                    className="flex items-center justify-between py-2 border-b last:border-0"
                                >
                                    <div className="flex items-center gap-3">
                                        <span className="text-muted-foreground text-sm w-6">#{idx + 1}</span>
                                        <div>
                                            {type === 'member' && (
                                                <>
                                                    <span className="font-medium">{item.name || item.member_key}</span>
                                                    {item.party && (
                                                        <Badge variant="outline" className="ml-2 text-xs">
                                                            {item.party}
                                                        </Badge>
                                                    )}
                                                </>
                                            )}
                                            {type === 'party' && (
                                                <span className="font-medium">
                                                    {item.party === 'D' ? 'Democrats' : item.party === 'R' ? 'Republicans' : item.party}
                                                </span>
                                            )}
                                            {type === 'sector_rotation' && (
                                                <div className="flex items-center gap-2">
                                                    <span className="font-medium">{item.sector}</span>
                                                    {getSignalBadge(item.rotation_signal)}
                                                </div>
                                            )}
                                            <div className="text-xs text-muted-foreground">
                                                {item.total_trades && `${item.total_trades} trades`}
                                                {item.total_volume && ` • ${formatVolume(item.total_volume)}`}
                                                {item.unique_members && ` • ${item.unique_members} members`}
                                            </div>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        {type !== 'sector_rotation' ? (
                                            <div className={`font-mono font-semibold ${getAlphaColor(item.alpha)}`}>
                                                {formatAlpha(item.alpha)}
                                                {item.alpha !== undefined && (
                                                    item.alpha > 0 ? (
                                                        <TrendingUp className="inline ml-1 h-4 w-4" />
                                                    ) : item.alpha < 0 ? (
                                                        <TrendingDown className="inline ml-1 h-4 w-4" />
                                                    ) : (
                                                        <Minus className="inline ml-1 h-4 w-4" />
                                                    )
                                                )}
                                            </div>
                                        ) : (
                                            <div className="font-mono text-sm">
                                                {item.net_flow != null && (
                                                    <span className={item.net_flow > 0 ? 'text-green-600' : 'text-red-600'}>
                                                        {formatVolume(Math.abs(item.net_flow))}
                                                        {item.net_flow > 0 ? ' inflow' : ' outflow'}
                                                    </span>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}
        </DataContainer>
    );
}
