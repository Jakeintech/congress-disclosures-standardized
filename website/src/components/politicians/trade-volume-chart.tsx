'use client';

import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from 'recharts';
import { fetchMemberTrades } from '@/lib/api';
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
        color: 'hsl(var(--chart-2))', // Emerald/Green if configured, else default chart-2
    },
    sell: {
        label: 'Sell',
        color: 'hsl(var(--chart-1))', // Orange/Red if configured, else default chart-1
    },
} satisfies ChartConfig;

export function TradeVolumeChart({ bioguideId }: TradeVolumeChartProps) {
    const [data, setData] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadTrades() {
            try {
                const trades = await fetchMemberTrades(bioguideId, 500);

                const fullData: Record<string, { year: string, buy: number, sell: number }> = {};

                trades.forEach((trade: any) => {
                    const year = new Date(trade.transaction_date).getFullYear().toString();
                    if (!fullData[year]) {
                        fullData[year] = { year, buy: 0, sell: 0 };
                    }

                    let amount = 0;
                    if (trade.amount) {
                        const clean = trade.amount.replace(/[$,]/g, '');
                        // Parse range '1001-15000' -> take average for better visual or max?
                        const parts = clean.split('-');
                        if (parts.length > 1) {
                            amount = (parseFloat(parts[0]) + parseFloat(parts[1])) / 2;
                        } else {
                            amount = parseFloat(parts[0]);
                        }
                    }
                    if (isNaN(amount)) amount = 0;

                    if (trade.transaction_type?.toLowerCase().includes('purchase')) {
                        fullData[year].buy += amount;
                    } else if (trade.transaction_type?.toLowerCase().includes('sale')) {
                        fullData[year].sell += amount;
                    }
                });

                const chartData = Object.values(fullData).sort((a, b) => parseInt(a.year) - parseInt(b.year));
                setData(chartData);
            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        }
        loadTrades();
    }, [bioguideId]);

    const formatYAxis = (value: number) => {
        if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
        if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
        return `$${value}`;
    };

    if (loading) return <Skeleton className="w-full h-[300px]" />;

    if (data.length === 0) return <div className="flex items-center justify-center h-[300px] text-muted-foreground">No trading data available</div>;

    return (
        <ChartContainer config={chartConfig} className="min-h-[300px] w-full">
            <BarChart accessibilityLayer data={data}>
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
    );
}
