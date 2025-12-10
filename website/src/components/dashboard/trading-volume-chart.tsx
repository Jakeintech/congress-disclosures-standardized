'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

interface TradingVolumeChartProps {
  data?: Array<{
    date: string;
    volume: number;
    count: number;
  }>;
  loading?: boolean;
}

export function TradingVolumeChart({ data, loading }: TradingVolumeChartProps) {
  // Mock data for now - will be replaced with real API data
  const mockData = [
    { date: 'Jan', volume: 45000, count: 234 },
    { date: 'Feb', volume: 52000, count: 289 },
    { date: 'Mar', volume: 48000, count: 256 },
    { date: 'Apr', volume: 61000, count: 312 },
    { date: 'May', volume: 55000, count: 278 },
    { date: 'Jun', volume: 67000, count: 345 },
    { date: 'Jul', volume: 58000, count: 298 },
    { date: 'Aug', volume: 71000, count: 367 },
    { date: 'Sep', volume: 64000, count: 321 },
    { date: 'Oct', volume: 78000, count: 389 },
    { date: 'Nov', volume: 69000, count: 354 },
    { date: 'Dec', volume: 82000, count: 412 },
  ];

  const chartData = data || mockData;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Trading Volume Over Time</CardTitle>
        <CardDescription>
          Monthly trading activity by Congress members
        </CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-[300px] w-full" />
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="date"
                className="text-xs"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <YAxis
                className="text-xs"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
                tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px',
                }}
                labelStyle={{ color: 'hsl(var(--foreground))' }}
                formatter={(value: number, name: string) => {
                  if (name === 'volume') {
                    return [`$${value.toLocaleString()}`, 'Volume'];
                  }
                  return [value, 'Trades'];
                }}
              />
              <Area
                type="monotone"
                dataKey="volume"
                stroke="hsl(var(--primary))"
                fillOpacity={1}
                fill="url(#colorVolume)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
