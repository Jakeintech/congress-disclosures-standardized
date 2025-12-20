'use client';

import Link from 'next/link';
import { Users, TrendingUp, FileText, FolderOpen } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorBoundary, ApiError } from '@/components/ErrorBoundary';
import { StatCardEnhanced } from '@/components/dashboard/stat-card-enhanced';
import { TradingVolumeChart } from '@/components/dashboard/trading-volume-chart';
import { TopStocksChart } from '@/components/dashboard/top-stocks-chart';
import { StockLogo } from '@/components/ui/stock-logo';
import { useDashboardSummary, useTrendingStocks, useTopTraders } from '@/hooks/use-api';
import { DataContainer } from '@/components/ui/data-container';
import { RecentActivityFeed } from '@/components/dashboard/recent-activity-feed';

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
  const summaryQuery = useDashboardSummary();
  const trendingQuery = useTrendingStocks(5);
  const tradersQuery = useTopTraders(5);

  const loading = summaryQuery.isLoading || trendingQuery.isLoading || tradersQuery.isLoading;
  const isError = summaryQuery.isError || trendingQuery.isError || tradersQuery.isError;
  const summary = (summaryQuery.data || {}) as DashboardData;
  const trendingStocks = trendingQuery.data || [];
  const topTraders = tradersQuery.data || [];

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

      <DataContainer
        isLoading={loading}
        isError={isError}
        error={summaryQuery.error || trendingQuery.error || tradersQuery.error}
        data={summaryQuery.data}
        onRetry={() => {
          summaryQuery.refetch();
          trendingQuery.refetch();
          tradersQuery.refetch();
        }}
        loadingSkeleton={<div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-32 w-full" />)}
        </div>}
      >
        {(data) => (
          <>
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

            {/* Recent Activity Section */}
            <div>
              <RecentActivityFeed />
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
                  {trendingStocks.length > 0 ? (
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
                            <StockLogo ticker={stock.ticker} size="md" />
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
                  {topTraders.length > 0 ? (
                    <div className="space-y-2">
                      {topTraders.map((trader, i) => {
                        // Skip invalid traders
                        if (!trader.bioguide_id || !trader.name) {
                          console.warn('[Dashboard] Skipping invalid trader:', trader);
                          return null;
                        }
                        return (
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
                        );
                      })}
                    </div>
                  ) : (
                    <div className="text-center py-4">
                      <p className="text-muted-foreground">No trader data available</p>
                      <p className="text-xs text-muted-foreground mt-2">
                        The analytics pipeline may still be processing data.
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </>
        )}
      </DataContainer>

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
