'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { DataContainer } from '@/components/ui/data-container';
import { usePatternInsights } from '@/hooks/use-api';
import { TimingData } from '@/types/api';
import { Clock } from 'lucide-react';

export function TradingTiming() {
    const timingQuery = usePatternInsights('timing');

    return (
        <DataContainer
            isLoading={timingQuery.isLoading}
            isError={timingQuery.isError}
            data={timingQuery.data}
            onRetry={() => timingQuery.refetch()}
        >
            {(data) => {
                const dayData = (data as any)?.day_of_week || [];
                const monthData = (data as any)?.month_of_year || [];

                return (
                    <Card className="border-none shadow-none bg-accent/5">
                        <CardHeader className="px-0 pt-0">
                            <CardTitle className="flex items-center gap-2 overflow-hidden">
                                <Clock className="h-5 w-5 shrink-0" />
                                <span>Legislative Trading Timing</span>
                            </CardTitle>
                            <CardDescription>
                                Analysis of congressional trade synchronization with legislative calendar
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="px-0 space-y-6">
                            <div className="bg-background p-6 rounded-xl border shadow-sm">
                                <h4 className="text-sm font-semibold mb-4 text-muted-foreground uppercase tracking-wider">Activity by Day of Week</h4>
                                <div className="grid grid-cols-7 gap-2">
                                    {dayData.map((day: TimingData, idx: number) => {
                                        const intensity = Math.min((day.pct_of_volume || 0) / 25, 1);
                                        return (
                                            <div
                                                key={idx}
                                                className="text-center p-3 rounded-lg border transition-all hover:scale-105"
                                                style={{
                                                    backgroundColor: `rgba(59, 130, 246, ${intensity * 0.15})`,
                                                    borderColor: intensity > 0.4 ? 'rgb(59, 130, 246, 0.5)' : 'rgba(0,0,0,0.1)'
                                                }}
                                            >
                                                <div className="text-[10px] font-bold text-muted-foreground uppercase">{day.day_name?.slice(0, 3)}</div>
                                                <div className="text-lg font-black text-primary">{day.pct_of_volume?.toFixed(0)}%</div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>

                            <div className="bg-background p-6 rounded-xl border shadow-sm">
                                <h4 className="text-sm font-semibold mb-4 text-muted-foreground uppercase tracking-wider">Seasonal Volume Distribution</h4>
                                <div className="grid grid-cols-4 md:grid-cols-6 gap-2">
                                    {monthData.slice(0, 12).map((month: TimingData, idx: number) => {
                                        const intensity = Math.min((month.pct_of_volume || 0) / 12, 1);
                                        return (
                                            <div
                                                key={idx}
                                                className="text-center p-2 rounded-lg border transition-all"
                                                style={{
                                                    backgroundColor: `rgba(34, 197, 94, ${intensity * 0.15})`,
                                                    borderColor: intensity > 0.4 ? 'rgb(34, 197, 94, 0.5)' : 'rgba(0,0,0,0.1)'
                                                }}
                                            >
                                                <div className="text-[9px] font-bold text-muted-foreground uppercase truncate">{month.month_name?.slice(0, 3)}</div>
                                                <div className="text-sm font-bold text-emerald-600">{month.pct_of_volume?.toFixed(1)}%</div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                );
            }}
        </DataContainer>
    );
}
