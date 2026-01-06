'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

interface TopStocksChartProps {
  data?: Array<{
    ticker: string;
    trade_count: number;
    company_name?: string;
  }>;
  loading?: boolean;
}

export function TopStocksChart({ data, loading }: TopStocksChartProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Top 10 Traded Stocks</CardTitle>
          <CardDescription>Most actively traded by Congress members</CardDescription>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Top 10 Traded Stocks</CardTitle>
          <CardDescription>Most actively traded by Congress members</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            No trading data available
          </p>
        </CardContent>
      </Card>
    );
  }

  // Sort and take top 10
  const chartData = [...data]
    .sort((a, b) => b.trade_count - a.trade_count)
    .slice(0, 10);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Top 10 Traded Stocks</CardTitle>
        <CardDescription>
          Most actively traded by Congress members
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis type="number" className="text-xs" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
            <YAxis
              type="category"
              dataKey="ticker"
              className="text-xs font-mono"
              tick={{ fill: 'hsl(var(--muted-foreground))' }}
              width={60}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--background))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '6px',
              }}
              labelStyle={{ color: 'hsl(var(--foreground))' }}
              formatter={(value: number) => [`${value} trades`, 'Count']}
              labelFormatter={(label) => {
                const stock = chartData.find(s => s.ticker === label);
                return stock?.company_name || label;
              }}
            />
            <Bar dataKey="trade_count" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
