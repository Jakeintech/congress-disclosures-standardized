"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Wallet, PieChart, TrendingUp, Clock } from "lucide-react";
import { useState, useEffect } from "react";

interface PortfolioData {
    member_key: string;
    name?: string;
    party?: string;
    estimated_portfolio_value: number;
    portfolio_value_low?: number;
    portfolio_value_high?: number;
    position_count: number;
    top_5_concentration?: number;
    top_sector?: string;
    top_sector_pct?: number;
    confidence_score: number;
    total_trades?: number;
    last_trade_date?: string;
    sector_allocation?: Record<string, number>;
    top_holdings?: Array<{ ticker: string; value: number; sector: string }>;
}

interface PortfolioReconstructionCardProps {
    memberId?: string;
    limit?: number;
    apiBase?: string;
    showDetails?: boolean;
}

export function PortfolioReconstructionCard({
    memberId,
    limit = 10,
    apiBase = process.env.NEXT_PUBLIC_API_URL || '',
    showDetails = false
}: PortfolioReconstructionCardProps) {
    const [portfolios, setPortfolios] = useState<PortfolioData[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function fetchData() {
            try {
                setLoading(true);
                const params = new URLSearchParams({ limit: String(limit) });
                if (memberId) params.set('member_id', memberId);
                if (showDetails) params.set('include_holdings', 'true');

                const response = await fetch(
                    `${apiBase}/v1/analytics/portfolio?${params.toString()}`
                );

                if (!response.ok) throw new Error('Failed to fetch portfolio data');

                const result = await response.json();
                setPortfolios(result.portfolios || []);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Unknown error');
            } finally {
                setLoading(false);
            }
        }

        fetchData();
    }, [memberId, limit, apiBase, showDetails]);

    const formatValue = (val: number | undefined) => {
        if (!val) return '--';
        if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`;
        if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`;
        return `$${val.toFixed(0)}`;
    };

    const getConfidenceColor = (score: number) => {
        if (score >= 75) return 'text-green-600';
        if (score >= 50) return 'text-yellow-600';
        return 'text-orange-600';
    };

    const getConfidenceLevel = (score: number) => {
        if (score >= 75) return 'High';
        if (score >= 50) return 'Medium';
        return 'Low';
    };

    if (loading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Wallet className="h-5 w-5" />
                        Portfolio Reconstruction
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center justify-center py-8">
                        <div className="animate-pulse text-muted-foreground">Reconstructing portfolios...</div>
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (error) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Portfolio Reconstruction</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="text-destructive py-4">Error: {error}</div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Wallet className="h-5 w-5" />
                    Portfolio Reconstruction
                </CardTitle>
                <CardDescription>
                    Estimated holdings reconstructed from cumulative trading data
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="space-y-4">
                    {portfolios.length === 0 ? (
                        <div className="text-center text-muted-foreground py-8">
                            No portfolio data available
                        </div>
                    ) : (
                        portfolios.map((portfolio, idx) => (
                            <div
                                key={idx}
                                className="p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                            >
                                <div className="flex items-start justify-between">
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className="font-semibold">
                                                {portfolio.name || portfolio.member_key}
                                            </span>
                                            {portfolio.party && (
                                                <Badge variant="outline" className="text-xs">
                                                    {portfolio.party}
                                                </Badge>
                                            )}
                                        </div>

                                        <div className="flex items-center gap-4 mt-2 text-sm">
                                            <div className="flex items-center gap-1">
                                                <PieChart className="h-4 w-4 text-muted-foreground" />
                                                <span>{portfolio.position_count} positions</span>
                                            </div>
                                            {portfolio.top_sector && (
                                                <div className="flex items-center gap-1">
                                                    <TrendingUp className="h-4 w-4 text-muted-foreground" />
                                                    <span>{portfolio.top_sector} ({portfolio.top_sector_pct}%)</span>
                                                </div>
                                            )}
                                            {portfolio.last_trade_date && (
                                                <div className="flex items-center gap-1">
                                                    <Clock className="h-4 w-4 text-muted-foreground" />
                                                    <span>Last: {portfolio.last_trade_date}</span>
                                                </div>
                                            )}
                                        </div>

                                        {/* Top Holdings */}
                                        {portfolio.top_holdings && portfolio.top_holdings.length > 0 && (
                                            <div className="flex flex-wrap gap-1 mt-2">
                                                {portfolio.top_holdings.slice(0, 5).map((holding, hidx) => (
                                                    <Badge key={hidx} variant="secondary" className="text-xs">
                                                        {holding.ticker}: {formatValue(holding.value)}
                                                    </Badge>
                                                ))}
                                            </div>
                                        )}
                                    </div>

                                    <div className="text-right">
                                        <div className="text-lg font-bold">
                                            {formatValue(portfolio.estimated_portfolio_value)}
                                        </div>
                                        <div className="text-xs text-muted-foreground">
                                            Range: {formatValue(portfolio.portfolio_value_low)} - {formatValue(portfolio.portfolio_value_high)}
                                        </div>
                                        <div className={`text-xs mt-1 ${getConfidenceColor(portfolio.confidence_score)}`}>
                                            Confidence: {getConfidenceLevel(portfolio.confidence_score)} ({portfolio.confidence_score.toFixed(0)})
                                        </div>
                                    </div>
                                </div>

                                {/* Sector Allocation Bar */}
                                {portfolio.sector_allocation && Object.keys(portfolio.sector_allocation).length > 0 && (
                                    <div className="mt-3">
                                        <div className="text-xs text-muted-foreground mb-1">Sector Allocation</div>
                                        <div className="flex h-2 rounded overflow-hidden">
                                            {Object.entries(portfolio.sector_allocation).slice(0, 5).map(([sector, pct], sidx) => {
                                                const colors = [
                                                    'bg-blue-500', 'bg-green-500', 'bg-yellow-500',
                                                    'bg-purple-500', 'bg-pink-500'
                                                ];
                                                return (
                                                    <div
                                                        key={sidx}
                                                        className={`${colors[sidx % colors.length]}`}
                                                        style={{ width: `${pct}%` }}
                                                        title={`${sector}: ${pct}%`}
                                                    />
                                                );
                                            })}
                                        </div>
                                        <div className="flex flex-wrap gap-2 mt-1 text-xs">
                                            {Object.entries(portfolio.sector_allocation).slice(0, 5).map(([sector, pct], sidx) => (
                                                <span key={sidx} className="text-muted-foreground">
                                                    {sector}: {pct}%
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
