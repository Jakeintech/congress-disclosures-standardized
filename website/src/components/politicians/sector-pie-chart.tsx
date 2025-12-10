'use client';

import { useEffect, useState } from 'react';
import { Pie, PieChart } from 'recharts';
import { fetchMemberAssets } from '@/lib/api';
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
    const [data, setData] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [config, setConfig] = useState<ChartConfig>({});

    useEffect(() => {
        async function loadData() {
            try {
                // Fetch holdings
                const holdings = await fetchMemberAssets(bioguideId);

                // Aggregate by Sector
                const sectorCounts: Record<string, number> = {};
                holdings.forEach((h: any) => {
                    // Try sector, fallback to 'Other' or 'Unclassified'
                    // Asset holdings usually have 'sector' or 'industry'
                    const sector = h.sector || h.industry || 'Other';

                    // Value logic: asset_value (exact) or midpoint of asset_value_range
                    let value = h.asset_value || 0;
                    if (!value && h.asset_value_range) {
                        // Ranges like "$15,001 - $50,000"
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

                // Sort and Top 5 + Other
                let sorted = Object.entries(sectorCounts)
                    .map(([name, value]) => ({ name, value }))
                    .sort((a, b) => b.value - a.value);

                // If no data, maybe empty or just cash?
                if (sorted.length === 0) {
                    // Fallback check if trading data provided sector but it likely doesn't.
                    setData([]);
                    setLoading(false);
                    return;
                }

                // Limit slices
                const top5 = sorted.slice(0, 5);
                const other = sorted.slice(5).reduce((acc, curr) => acc + curr.value, 0);
                if (other > 0) top5.push({ name: 'Other', value: other });

                // Construct Chart Data & Config
                const chartData = top5.map((item, index) => ({
                    sector: item.name,
                    value: item.value,
                    fill: sectorColors[index % sectorColors.length]
                }));

                const newConfig: ChartConfig = {};
                chartData.forEach((item, index) => {
                    newConfig[item.sector] = {
                        label: item.sector,
                        color: sectorColors[index % sectorColors.length]
                    };
                });
                newConfig['value'] = { label: 'Value' }; // Tooltip label

                setData(chartData);
                setConfig(newConfig);

            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, [bioguideId]);

    if (loading) return <Skeleton className="w-full h-[300px]" />;

    if (data.length === 0) return <div className="flex items-center justify-center h-[300px] text-muted-foreground">No sector data</div>;

    return (
        <ChartContainer config={config} className="min-h-[300px] w-full">
            <PieChart>
                <ChartTooltip content={<ChartTooltipContent hideLabel />} />
                <Pie
                    data={data}
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
    );
}
