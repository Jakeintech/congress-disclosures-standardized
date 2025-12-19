'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { ExternalLink, TrendingUp, TrendingDown, Minus, Search, FilterX, ChevronRight } from 'lucide-react';
import { useTripleCorrelations } from '@/hooks/use-api';
import { DataContainer } from '@/components/ui/data-container';

interface Correlation {
    bill_id: string;
    raw_reference: string;
    member_bioguide?: string;
    ticker?: string;
    correlation_score: number;
    client_count: number;
    client_names: string;
    registrant_count: number;
    registrant_names: string;
    filing_count: number;
    lobbying_amount: number;
    top_issue_codes: string;
    trade_date?: string;
    bill_action_date?: string;
    contribution_amount?: number;
}

export function InfluenceTracker() {
    const [year, setYear] = useState('2025');
    const [minScore, setMinScore] = useState([50]);
    const [memberFilter, setMemberFilter] = useState('');
    const [tickerFilter, setTickerFilter] = useState('');
    const [billFilter, setBillFilter] = useState('');

    const { data: correlationsData, isLoading, isError, error, refetch } = useTripleCorrelations({
        year,
        min_score: minScore[0],
        member_bioguide: memberFilter,
        ticker: tickerFilter,
        bill_id: billFilter,
        limit: 100
    });

    const correlations = (correlationsData as any)?.correlations || [];

    const getScoreColor = (score: number) => {
        if (score === 100) return 'bg-purple-600';
        if (score >= 80) return 'bg-red-600';
        if (score >= 60) return 'bg-orange-600';
        if (score >= 40) return 'bg-amber-500';
        return 'bg-slate-400';
    };

    const formatCurrency = (amount: number) =>
        new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            notation: 'compact'
        }).format(amount);

    const getStockImpact = (issueCodes: string) => {
        const codes = issueCodes.split('|').filter(c => c);
        const impacts: { ticker: string; sentiment: string }[] = [];

        const stockMap: Record<string, { tickers: string[]; sentiment: string }> = {
            'DEF': { tickers: ['LMT', 'RTX', 'NOC'], sentiment: 'BULLISH' },
            'AER': { tickers: ['BA', 'LMT', 'RTX'], sentiment: 'BULLISH' },
            'HCR': { tickers: ['UNH', 'JNJ', 'PFE'], sentiment: 'MIXED' },
            'ENG': { tickers: ['XOM', 'CVX', 'COP'], sentiment: 'BULLISH' },
            'TEC': { tickers: ['AAPL', 'MSFT', 'GOOGL'], sentiment: 'MIXED' },
        };

        codes.forEach(code => {
            const mapping = stockMap[code];
            if (mapping) {
                mapping.tickers.slice(0, 3).forEach(ticker => {
                    impacts.push({ ticker, sentiment: mapping.sentiment });
                });
            }
        });

        return impacts.slice(0, 6);
    };

    return (
        <div className="space-y-6">
            <Card className="border-none shadow-none bg-accent/5">
                <CardHeader className="px-0 pt-0">
                    <CardTitle className="flex items-center gap-2">
                        <Search className="h-5 w-5" />
                        Analysis Filters
                    </CardTitle>
                    <CardDescription>Refine triple correlation results by member, asset, or legislation</CardDescription>
                </CardHeader>
                <CardContent className="px-0">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                        <div className="space-y-2">
                            <Label className="text-xs uppercase font-bold text-muted-foreground">Legislative Year</Label>
                            <Select value={year} onValueChange={setYear}>
                                <SelectTrigger className="bg-background">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="2025">2025</SelectItem>
                                    <SelectItem value="2024">2024</SelectItem>
                                    <SelectItem value="2023">2023</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label className="text-xs uppercase font-bold text-muted-foreground">Member ID</Label>
                            <Input
                                placeholder="e.g., P000197"
                                value={memberFilter}
                                onChange={(e) => setMemberFilter(e.target.value)}
                                className="bg-background"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label className="text-xs uppercase font-bold text-muted-foreground">Ticker</Label>
                            <Input
                                placeholder="e.g., NVDA"
                                value={tickerFilter}
                                onChange={(e) => setTickerFilter(e.target.value)}
                                className="bg-background font-mono uppercase"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label className="text-xs uppercase font-bold text-muted-foreground">Bill ID</Label>
                            <Input
                                placeholder="e.g., 119-hr-1234"
                                value={billFilter}
                                onChange={(e) => setBillFilter(e.target.value)}
                                className="bg-background font-mono"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label className="text-xs uppercase font-bold text-muted-foreground">Confidence: {minScore[0]}%</Label>
                            <div className="pt-2">
                                <Slider
                                    value={minScore}
                                    onValueChange={setMinScore}
                                    min={0}
                                    max={100}
                                    step={10}
                                />
                            </div>
                        </div>
                    </div>

                    <div className="mt-6 flex justify-between items-center bg-background/50 p-3 rounded-lg border border-dashed">
                        <div className="text-xs font-mono text-muted-foreground">
                            Found {correlations.length} potential correlations
                        </div>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                                setMemberFilter('');
                                setTickerFilter('');
                                setBillFilter('');
                                setMinScore([50]);
                            }}
                            className="h-8 text-[10px] uppercase font-bold"
                        >
                            <FilterX className="h-3 w-3 mr-2" />
                            Reset All
                        </Button>
                    </div>
                </CardContent>
            </Card>

            <DataContainer
                isLoading={isLoading}
                isError={isError}
                error={error}
                data={correlations}
                onRetry={() => refetch()}
                emptyMessage="No correlations match your current filters. Try lowering the confidence threshold."
            >
                {(correlations: any) => (
                    <div className="grid gap-4">
                        {correlations.map((corr: Correlation, idx: number) => {
                            const clients = corr.client_names.split('|').filter(c => c).slice(0, 3);
                            const issues = corr.top_issue_codes.split('|').filter(i => i);
                            const stockImpacts = getStockImpact(corr.top_issue_codes);

                            return (
                                <Card key={idx} className="group hover:border-primary/50 transition-all border shadow-sm">
                                    <CardContent className="p-0">
                                        <div className="flex flex-col md:flex-row">
                                            {/* Score Section */}
                                            <div className={`${getScoreColor(corr.correlation_score)} text-white p-6 md:w-32 flex flex-col items-center justify-center text-center gap-1 group-hover:brightness-110 transition-all`}>
                                                <div className="text-3xl font-black">{Math.round(corr.correlation_score)}</div>
                                                <div className="text-[10px] font-bold uppercase tracking-widest opacity-80">Score</div>
                                            </div>

                                            {/* Content Section */}
                                            <div className="flex-1 p-6 space-y-4">
                                                <div className="flex justify-between items-start">
                                                    <div className="space-y-1">
                                                        <h3 className="font-bold text-lg group-hover:text-primary transition-colors flex items-center gap-2">
                                                            {corr.raw_reference || corr.bill_id}
                                                            <ChevronRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-all -translate-x-2 group-hover:translate-x-0" />
                                                        </h3>
                                                        <div className="flex items-center gap-4 text-xs font-mono text-muted-foreground uppercase">
                                                            <span>{corr.filing_count} Filings</span>
                                                            <span>{corr.registrant_count} Firms</span>
                                                            <span className="text-primary font-bold">{formatCurrency(corr.lobbying_amount)} Vol</span>
                                                        </div>
                                                    </div>
                                                    {corr.ticker && (
                                                        <Badge className="font-mono text-base bg-primary/10 text-primary border-none px-3 py-1">
                                                            {corr.ticker}
                                                        </Badge>
                                                    )}
                                                </div>

                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                                    <div className="space-y-3">
                                                        <div>
                                                            <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Key Lobbing Clients</div>
                                                            <div className="flex flex-wrap gap-1.5">
                                                                {clients.map((client, i) => (
                                                                    <Badge key={i} variant="secondary" className="bg-emerald-500/10 text-emerald-700 border-none text-[10px]">
                                                                        {client}
                                                                    </Badge>
                                                                ))}
                                                            </div>
                                                        </div>
                                                        {issues.length > 0 && (
                                                            <div>
                                                                <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Lobbying Focus Areas</div>
                                                                <div className="flex flex-wrap gap-1.5">
                                                                    {issues.map((issue, i) => (
                                                                        <Badge key={i} variant="outline" className="text-[10px] border-orange-500/30 text-orange-700">
                                                                            {issue}
                                                                        </Badge>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>

                                                    <div className="bg-muted/30 p-4 rounded-xl space-y-3">
                                                        <div className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Impact Projection</div>
                                                        <div className="grid grid-cols-2 gap-2">
                                                            {stockImpacts.map((impact, i) => (
                                                                <div key={i} className="flex items-center justify-between p-2 bg-background rounded-lg border shadow-sm">
                                                                    <span className="font-mono text-xs font-bold">{impact.ticker}</span>
                                                                    <Badge variant="outline" className={`text-[9px] h-4 py-0 ${impact.sentiment === 'BULLISH' ? 'border-green-500 text-green-700' : 'border-slate-500 text-slate-700'}`}>
                                                                        {impact.sentiment}
                                                                    </Badge>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            );
                        })}
                    </div>
                )}
            </DataContainer>
        </div>
    );
}
