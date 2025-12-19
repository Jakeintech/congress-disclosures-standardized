'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { DataContainer } from '@/components/ui/data-container';
import { usePatternInsights } from '@/hooks/use-api';
import { SectorData } from '@/types/api';
import { PieChart } from 'lucide-react';

export function SectorAnalysis() {
    const sectorQuery = usePatternInsights('sector');

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

    return (
        <DataContainer
            isLoading={sectorQuery.isLoading}
            isError={sectorQuery.isError}
            data={sectorQuery.data}
            onRetry={() => sectorQuery.refetch()}
        >
            {(data) => {
                const sectorSummary = (data as any)?.sector_summary || [];
                const partyPrefs = (data as any)?.party_preferences || [];

                return (
                    <Card className="border-none shadow-none bg-accent/5">
                        <CardHeader className="px-0 pt-0">
                            <CardTitle className="flex items-center gap-2">
                                <PieChart className="h-5 w-5" />
                                <span>Congressional Sector Exposure</span>
                            </CardTitle>
                            <CardDescription>
                                Concentration of legislative trading activity across industrial sectors
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="px-0 space-y-4">
                            <div className="bg-background rounded-xl border divide-y shadow-sm overflow-hidden">
                                {sectorSummary.length === 0 ? (
                                    <div className="text-center text-muted-foreground py-12">
                                        No sector data available
                                    </div>
                                ) : (
                                    sectorSummary.slice(0, 10).map((sector: SectorData, idx: number) => (
                                        <div key={idx} className="flex items-center justify-between p-4 hover:bg-accent/5 transition-colors">
                                            <div className="flex items-center gap-3">
                                                <div className="w-2 h-2 rounded-full bg-primary/40" />
                                                <span className="font-semibold text-sm">{sector.sector}</span>
                                                {sector.flow_signal && (
                                                    <Badge className={`${getSignalColor(sector.flow_signal)} h-4 text-[9px] uppercase`}>
                                                        {sector.flow_signal.replace('_', ' ')}
                                                    </Badge>
                                                )}
                                            </div>
                                            <div className="text-right">
                                                <div className="text-sm font-bold">{formatVolume(sector.total_volume)}</div>
                                                <div className="text-[10px] text-muted-foreground font-mono uppercase">
                                                    {sector.pct_of_total?.toFixed(1)}% Weight
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>

                            {partyPrefs.length > 0 && (
                                <div className="bg-background p-6 rounded-xl border shadow-sm">
                                    <h4 className="text-xs font-bold mb-4 text-muted-foreground uppercase tracking-widest">Partisan Sector Concentration</h4>
                                    <div className="space-y-4">
                                        {partyPrefs.slice(0, 5).map((pref: SectorData, idx: number) => (
                                            <div key={idx} className="space-y-1.5">
                                                <div className="flex items-center justify-between text-xs">
                                                    <span className="font-medium">{pref.sector}</span>
                                                    <Badge variant="outline" className="text-[10px] h-4 py-0 uppercase border-primary/20">
                                                        {pref.party_lean} Lean
                                                    </Badge>
                                                </div>
                                                <div className="flex h-1.5 rounded-full overflow-hidden bg-muted">
                                                    <div
                                                        className="bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]"
                                                        style={{ width: `${pref.d_pct || 0}%` }}
                                                    />
                                                    <div
                                                        className="bg-red-500 shadow-[0_0_8px_rgba(239,44,44,0.5)]"
                                                        style={{ width: `${pref.r_pct || 0}%` }}
                                                    />
                                                </div>
                                                <div className="flex justify-between text-[9px] text-muted-foreground font-mono">
                                                    <span>D: {pref.d_pct}%</span>
                                                    <span>R: {pref.r_pct}%</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                );
            }}
        </DataContainer>
    );
}
