'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Users, TrendingUp, FileText, FolderOpen } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { fetchDashboardSummary, fetchTrendingStocks, fetchTopTraders } from '@/lib/api';
import { ErrorBoundary, ApiError } from '@/components/ErrorBoundary';
import { StatCardEnhanced } from '@/components/dashboard/stat-card-enhanced';
import { TradingVolumeChart } from '@/components/dashboard/trading-volume-chart';
import { TopStocksChart } from '@/components/dashboard/top-stocks-chart';

interface DashboardData {
  totalMembers?: number;
  totalTransactions?: number;
  totalBills?: number;
  totalFilings?: number;
}

interface TrendingStock {
  ticker: string;
  company_name?: string;
  trade_count: number;
  net_direction?: string;
}

interface TopTrader {
  name: string;
  bioguide_id: string;
  party?: string;
  state?: string;
  trade_count: number;
  total_volume?: string;
}

function StatCard({
  title,
  value,
  icon,
  loading
}: {
  title: string;
  value: string | number;
  icon: string;
  loading?: boolean;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <span className="text-2xl">{icon}</span>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-24" />
        ) : (
          <div className="text-2xl font-bold">{value?.toLocaleString()}</div>
        )}
      </CardContent>
    </Card>
  );
}

function DashboardPage() {
  const [summary, setSummary] = useState<DashboardData>({});
  const [trendingStocks, setTrendingStocks] = useState<TrendingStock[]>([]);
  const [topTraders, setTopTraders] = useState<TopTrader[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const [summaryData, stocksData, tradersData] = await Promise.allSettled([
          fetchDashboardSummary(),
          fetchTrendingStocks(5),
          fetchTopTraders(5),
        ]);

        if (summaryData.status === 'fulfilled') {
          setSummary(summaryData.value as DashboardData);
        }
        if (stocksData.status === 'fulfilled') {
          setTrendingStocks(stocksData.value as TrendingStock[]);
        }
        if (tradersData.status === 'fulfilled') {
          setTopTraders(tradersData.value as TopTrader[]);
        }
      } catch (err) {
        setError('Failed to load dashboard data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Congressional financial disclosures and transparency analytics
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild>
            <Link href="/transactions">View All Transactions</Link>
          </Button>
        </div>
      </div>

      {/* Error State */}
      {error && <ApiError error={error} onRetry={() => window.location.reload()} />}

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCardEnhanced
          title="Total Members"
          value={summary.totalMembers || 535}
          subtitle="Congress members tracked"
          icon={Users}
          loading={loading}
          trend="neutral"
        />
        <StatCardEnhanced
          title="Transactions"
          value={summary.totalTransactions || 0}
          subtitle="Financial disclosures filed"
          icon={TrendingUp}
          loading={loading}
          change="+423 this quarter"
          trend="up"
        />
        <StatCardEnhanced
          title="Bills Tracked"
          value={summary.totalBills || 0}
          subtitle="Active legislation monitored"
          icon={FileText}
          loading={loading}
          trend="neutral"
        />
        <StatCardEnhanced
          title="Filings Processed"
          value={summary.totalFilings || 0}
          subtitle="Total documents analyzed"
          icon={FolderOpen}
          loading={loading}
          change="+1.2K this month"
          trend="up"
        />
      </div>

      {/* Charts Section */}
      <div className="grid gap-6 lg:grid-cols-2">
        <TradingVolumeChart loading={loading} />
        <TopStocksChart data={trendingStocks} loading={loading} />
      </div>

      {/* Two Column Layout */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Trending Stocks List */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <span>📈</span>
              Trending Stocks
            </CardTitle>
            <CardDescription>
              Most traded stocks by Congress members
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : trendingStocks.length > 0 ? (
              <div className="space-y-2">
                {trendingStocks.map((stock, i) => (
                  <div
                    key={stock.ticker}
                    className="flex items-center justify-between p-2 rounded-md hover:bg-muted"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-semibold text-muted-foreground">
                        #{i + 1}
                      </span>
                      <div>
                        <p className="font-medium">{stock.ticker}</p>
                        <p className="text-sm text-muted-foreground">
                          {stock.company_name || stock.ticker}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <Badge variant={stock.net_direction === 'buy' ? 'default' : 'secondary'}>
                        {stock.trade_count} trades
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground text-center py-4">
                No trending stocks data available
              </p>
            )}
          </CardContent>
        </Card>

        {/* Top Traders */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <span>🏆</span>
              Top Traders
            </CardTitle>
            <CardDescription>
              Most active members by transaction count
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : topTraders.length > 0 ? (
              <div className="space-y-2">
                {topTraders.filter(t => t.bioguide_id && t.name).map((trader, i) => (
                  <Link
                    key={trader.bioguide_id}
                    href={`/politician/${trader.bioguide_id}`}
                    className="flex items-center justify-between p-2 rounded-md hover:bg-muted transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-semibold text-muted-foreground">
                        #{i + 1}
                      </span>
                      <div>
                        <p className="font-medium">{trader.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {trader.party ? `${trader.party}-${trader.state}` : trader.state}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <Badge>{trader.trade_count} trades</Badge>
                      {trader.total_volume && (
                        <p className="text-xs text-muted-foreground mt-1">
                          {trader.total_volume}
                        </p>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground text-center py-4">
                No trader data available
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Links */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Links</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-4">
            <Button variant="outline" asChild className="h-auto py-4 flex-col">
              <Link href="/bills">
                <span className="text-2xl mb-2">📜</span>
                <span>Browse Bills</span>
              </Link>
            </Button>
            <Button variant="outline" asChild className="h-auto py-4 flex-col">
              <Link href="/members">
                <span className="text-2xl mb-2">👥</span>
                <span>View Members</span>
              </Link>
            </Button>
            <Button variant="outline" asChild className="h-auto py-4 flex-col">
              <Link href="/lobbying">
                <span className="text-2xl mb-2">💼</span>
                <span>Lobbying Data</span>
              </Link>
            </Button>
            <Button variant="outline" asChild className="h-auto py-4 flex-col">
              <Link href="/influence">
                <span className="text-2xl mb-2">⚡</span>
                <span>Influence Tracker</span>
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Export wrapped in ErrorBoundary
export default function DashboardWithErrorBoundary() {
  return (
    <ErrorBoundary>
      <DashboardPage />
    </ErrorBoundary>
  );
}
