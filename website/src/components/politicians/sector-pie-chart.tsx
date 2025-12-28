'use client';

import { useMemo } from 'react';
import { Pie, PieChart } from 'recharts';
import { useMemberAssets } from '@/hooks/use-api';
import { DataContainer } from '@/components/ui/data-container';
import { Skeleton } from '@/components/ui/skeleton';
import {
    ChartConfig,
    ChartContainer,
    ChartTooltip,
    ChartTooltipContent,
    ChartLegend,
    ChartLegendContent
} from '@/components/ui/chart';

interface SectorPieChartProps {
    bioguideId: string;
}

const sectorColors = [
    'hsl(var(--chart-1))',
    'hsl(var(--chart-2))',
    'hsl(var(--chart-3))',
    'hsl(var(--chart-4))',
    'hsl(var(--chart-5))',
    'hsl(var(--chart-6))',
];

export function SectorPieChart({ bioguideId }: SectorPieChartProps) {
    const { data: holdings, isLoading, isError, error, refetch } = useMemberAssets(bioguideId);

    const { chartData, config } = useMemo(() => {
        if (!holdings) return { chartData: [], config: {} as ChartConfig };

        const sectorCounts: Record<string, number> = {};
        holdings.forEach((h: any) => {
            const sector = h.sector || h.industry || 'Other';
            let value = h.asset_value || 0;
            if (!value && h.asset_value_range) {
                const clean = h.asset_value_range.replace(/[$,]/g, '');
                const parts = clean.split('-');
                if (parts.length > 1) {
                    value = (parseFloat(parts[0]) + parseFloat(parts[1])) / 2;
                } else {
                    value = parseFloat(parts[0]);
                }
            }
            if (isNaN(value)) value = 0;
            sectorCounts[sector] = (sectorCounts[sector] || 0) + value;
        });

        let sorted = Object.entries(sectorCounts)
            .map(([name, value]) => ({ name, value }))
            .sort((a, b) => b.value - a.value);

        if (sorted.length === 0) return { chartData: [], config: {} as ChartConfig };

        const top5 = sorted.slice(0, 5);
        const other = sorted.slice(5).reduce((acc, curr) => acc + curr.value, 0);
        if (other > 0) top5.push({ name: 'Other', value: other });

        const finalizedData = top5.map((item, index) => ({
            sector: item.name,
            value: item.value,
            fill: sectorColors[index % sectorColors.length]
        }));

        const newConfig: ChartConfig = {};
        finalizedData.forEach((item, index) => {
            newConfig[item.sector] = {
                label: item.sector,
                color: sectorColors[index % sectorColors.length]
            };
        });
        newConfig['value'] = { label: 'Value' };

        return { chartData: finalizedData, config: newConfig };
    }, [holdings]);

    return (
        <DataContainer
            isLoading={isLoading}
            isError={isError}
            error={error}
            data={holdings}
            onRetry={() => refetch()}
            loadingSkeleton={<Skeleton className="w-full h-[300px]" />}
            emptyMessage="No sector data available for this member's assets."
        >
            {() => (
                chartData.length > 0 ? (
                    <ChartContainer config={config} className="min-h-[300px] w-full">
                        <PieChart>
                            <ChartTooltip content={<ChartTooltipContent hideLabel />} />
                            <Pie
                                data={chartData}
                                dataKey="value"
                                nameKey="sector"
                                innerRadius={60}
                                strokeWidth={5}
                            />
                            <ChartLegend
                                content={<ChartLegendContent nameKey="sector" />}
                                className="-translate-y-2 flex-wrap gap-2 [&>*]:basis-1/4 [&>*]:justify-center"
                            />
                        </PieChart>
                    </ChartContainer>
                ) : (
                    <div className="flex items-center justify-center h-[300px] text-muted-foreground border-2 border-dashed rounded-lg">
                        No significant asset sectors identified.
                    </div>
                )
            )}
        </DataContainer>
    );
}
