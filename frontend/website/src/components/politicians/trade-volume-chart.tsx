import { useMemo } from 'react';
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from 'recharts';
import { useMemberTrades } from '@/hooks/use-api';
import { DataContainer } from '@/components/ui/data-container';
import { Skeleton } from '@/components/ui/skeleton';
import {
    ChartConfig,
    ChartContainer,
    ChartLegend,
    ChartLegendContent,
    ChartTooltip,
    ChartTooltipContent,
} from '@/components/ui/chart';

interface TradeVolumeChartProps {
    bioguideId: string;
}

const chartConfig = {
    buy: {
        label: 'Buy',
        color: 'hsl(var(--chart-2))',
    },
    sell: {
        label: 'Sell',
        color: 'hsl(var(--chart-1))',
    },
} satisfies ChartConfig;

export function TradeVolumeChart({ bioguideId }: TradeVolumeChartProps) {
    const { data: trades, isLoading, isError, error, refetch } = useMemberTrades(bioguideId, 500);

    const chartData = useMemo(() => {
        if (!trades) return [];

        const fullData: Record<string, { year: string, buy: number, sell: number }> = {};

        trades.forEach((trade: any) => {
            const dateStr = trade.transaction_date || trade.disclosure_date;
            if (!dateStr) return;

            const year = new Date(dateStr).getFullYear().toString();
            if (!fullData[year]) {
                fullData[year] = { year, buy: 0, sell: 0 };
            }

            let amount = 0;
            if (trade.amount) {
                const clean = trade.amount.replace(/[$,]/g, '');
                const parts = clean.split('-');
                if (parts.length > 1) {
                    amount = (parseFloat(parts[0]) + parseFloat(parts[1])) / 2;
                } else {
                    amount = parseFloat(parts[0]);
                }
            }
            if (isNaN(amount)) amount = 0;

            const type = (trade.transaction_type || '').toLowerCase();
            if (type.includes('purchase')) {
                fullData[year].buy += amount;
            } else if (type.includes('sale')) {
                fullData[year].sell += amount;
            }
        });

        return Object.values(fullData).sort((a, b) => parseInt(a.year) - parseInt(b.year));
    }, [trades]);

    const formatYAxis = (value: number) => {
        if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
        if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
        return `$${value}`;
    };

    return (
        <DataContainer
            isLoading={isLoading}
            isError={isError}
            error={error}
            data={trades}
            onRetry={() => refetch()}
            loadingSkeleton={<Skeleton className="w-full h-[300px]" />}
            emptyMessage="No trading data available for this member."
        >
            {() => (
                chartData.length > 0 ? (
                    <ChartContainer config={chartConfig} className="min-h-[300px] w-full">
                        <BarChart accessibilityLayer data={chartData}>
                            <CartesianGrid vertical={false} />
                            <XAxis
                                dataKey="year"
                                tickLine={false}
                                tickMargin={10}
                                axisLine={false}
                            />
                            <YAxis
                                tickFormatter={formatYAxis}
                                tickLine={false}
                                axisLine={false}
                                tickMargin={10}
                            />
                            <ChartTooltip content={<ChartTooltipContent indicator="dashed" />} />
                            <ChartLegend content={<ChartLegendContent />} />
                            <Bar dataKey="buy" fill="var(--color-buy)" radius={4} />
                            <Bar dataKey="sell" fill="var(--color-sell)" radius={4} />
                        </BarChart>
                    </ChartContainer>
                ) : (
                    <div className="flex items-center justify-center h-[300px] text-muted-foreground border-2 border-dashed rounded-lg">
                        No significant trading history found.
                    </div>
                )
            )}
        </DataContainer>
    );
}
