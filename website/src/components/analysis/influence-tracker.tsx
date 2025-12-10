'use client';

import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { ExternalLink, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

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
    const [correlations, setCorrelations] = useState<Correlation[]>([]);
    const [displayedCorrelations, setDisplayedCorrelations] = useState<Correlation[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Filters
    const [year, setYear] = useState('2025');
    const [minScore, setMinScore] = useState([50]);
    const [memberFilter, setMemberFilter] = useState('');
    const [tickerFilter, setTickerFilter] = useState('');
    const [billFilter, setBillFilter] = useState('');

    // Pagination
    const [displayCount, setDisplayCount] = useState(20);

    useEffect(() => {
        fetchCorrelations();
    }, [year, minScore, memberFilter, tickerFilter, billFilter]);

    const fetchCorrelations = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams({
                year,
                min_score: minScore[0].toString(),
                limit: '200',
            });

            if (memberFilter) params.append('member_bioguide', memberFilter);
            if (tickerFilter) params.append('ticker', tickerFilter.toUpperCase());
            if (billFilter) params.append('bill_id', billFilter.toLowerCase());

            const response = await fetch(`/api/correlations/triple?${params}`);
            if (!response.ok) throw new Error('Failed to fetch correlations');

            const data = await response.json();
            const correlationsData = data.data?.correlations || data.correlations || [];
            setCorrelations(correlationsData);
            setDisplayedCorrelations(correlationsData.slice(0, displayCount));
        } catch (err: any) {
            console.error('Error fetching correlations:', err);
            setError(err.message || 'Failed to load correlation data');
        } finally {
            setLoading(false);
        }
    };

    const loadMore = () => {
        const newCount = displayCount + 20;
        setDisplayCount(newCount);
        setDisplayedCorrelations(correlations.slice(0, newCount));
    };

    const getScoreColor = (score: number) => {
        if (score === 100) return 'bg-purple-500';
        if (score >= 80) return 'bg-red-500';
        if (score >= 60) return 'bg-orange-500';
        if (score >= 40) return 'bg-yellow-500';
        return 'bg-gray-400';
    };

    const getCongressUrl = (billId: string) => {
        const match = billId?.match(/(\d+)-(hr|s|hjres|sjres|hres|sres)-(\d+)/i);
        if (match) {
            const [, congress, type, number] = match;
            const typeMap: Record<string, string> = {
                'hr': 'house-bill',
                's': 'senate-bill',
                'hjres': 'house-joint-resolution',
                'sjres': 'senate-joint-resolution'
            };
            const urlType = typeMap[type.toLowerCase()] || type;
            return `https://www.congress.gov/bill/${congress}th-congress/${urlType}/${number}`;
        }
        return null;
    };

    const formatCurrency = (amount: number) =>
        new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
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

    const getSentimentIcon = (sentiment: string) => {
        if (sentiment === 'BULLISH') return <TrendingUp className="h-3 w-3" />;
        if (sentiment === 'BEARISH') return <TrendingDown className="h-3 w-3" />;
        return <Minus className="h-3 w-3" />;
    };

    const getSentimentColor = (sentiment: string) => {
        if (sentiment === 'BULLISH') return 'bg-green-100 text-green-700 border-green-200';
        if (sentiment === 'BEARISH') return 'bg-red-100 text-red-700 border-red-200';
        return 'bg-orange-100 text-orange-700 border-orange-200';
    };

    return (
        <div className="space-y-6">
            {/* Filters */}
            <Card>
                <CardHeader>
                    <CardTitle>Filter Correlations</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                        <div>
                            <Label>Year</Label>
                            <Select value={year} onValueChange={setYear}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="2025">2025</SelectItem>
                                    <SelectItem value="2024">2024</SelectItem>
                                    <SelectItem value="2023">2023</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div>
                            <Label>Member (Bioguide ID)</Label>
                            <Input
                                placeholder="e.g., P000197"
                                value={memberFilter}
                                onChange={(e) => setMemberFilter(e.target.value)}
                            />
                        </div>

                        <div>
                            <Label>Stock Ticker</Label>
                            <Input
                                placeholder="e.g., NVDA"
                                value={tickerFilter}
                                onChange={(e) => setTickerFilter(e.target.value)}
                            />
                        </div>

                        <div>
                            <Label>Bill ID</Label>
                            <Input
                                placeholder="e.g., 119-hr-1234"
                                value={billFilter}
                                onChange={(e) => setBillFilter(e.target.value)}
                            />
                        </div>

                        <div>
                            <Label>Min Score: {minScore[0]}</Label>
                            <Slider
                                value={minScore}
                                onValueChange={setMinScore}
                                min={0}
                                max={100}
                                step={10}
                            />
                        </div>
                    </div>

                    <div className="mt-4 flex gap-2">
                        <Button
                            variant="outline"
                            onClick={() => {
                                setMemberFilter('');
                                setTickerFilter('');
                                setBillFilter('');
                                setMinScore([50]);
                            }}
                        >
                            Clear Filters
                        </Button>
                        <div className="text-sm text-muted-foreground flex items-center">
                            Found {correlations.length} correlations
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Results */}
            {loading ? (
                <div className="space-y-4">
                    {[...Array(3)].map((_, i) => (
                        <Card key={i}>
                            <CardContent className="p-6">
                                <Skeleton className="h-24 w-full" />
                            </CardContent>
                        </Card>
                    ))}
                </div>
            ) : error ? (
                <Card>
                    <CardContent className="p-6 text-center text-muted-foreground">
                        {error}
                    </CardContent>
                </Card>
            ) : correlations.length === 0 ? (
                <Card>
                    <CardContent className="p-6 text-center text-muted-foreground">
                        No correlations found matching your filters. Try adjusting the criteria.
                    </CardContent>
                </Card>
            ) : (
                <>
                    <div className="space-y-4">
                        {displayedCorrelations.map((corr, idx) => {
                            const clients = corr.client_names.split('|').filter(c => c).slice(0, 3);
                            const registrants = corr.registrant_names.split('|').filter(r => r).slice(0, 2);
                            const issues = corr.top_issue_codes.split('|').filter(i => i);
                            const stockImpacts = getStockImpact(corr.top_issue_codes);
                            const congressUrl = getCongressUrl(corr.bill_id);

                            return (
                                <Card key={idx} className="hover:shadow-md transition-shadow">
                                    <CardContent className="p-6">
                                        <div className="flex gap-4">
                                            {/* Score Badge */}
                                            <div className="flex-shrink-0">
                                                <div
                                                    className={`${getScoreColor(corr.correlation_score)} text-white rounded-lg w-16 h-16 flex items-center justify-center font-bold text-2xl`}
                                                >
                                                    {Math.round(corr.correlation_score)}
                                                </div>
                                            </div>

                                            {/* Content */}
                                            <div className="flex-1 space-y-3">
                                                {/* Bill Info */}
                                                <div>
                                                    <div className="flex items-center gap-2">
                                                        <h3 className="font-semibold text-lg">
                                                            {corr.raw_reference || corr.bill_id}
                                                        </h3>
                                                        {congressUrl && (
                                                            <a
                                                                href={congressUrl}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="text-blue-600 hover:text-blue-800"
                                                            >
                                                                <ExternalLink className="h-4 w-4" />
                                                            </a>
                                                        )}
                                                    </div>
                                                </div>

                                                {/* Quick Stats */}
                                                <div className="flex flex-wrap gap-4 text-sm">
                                                    <div>
                                                        <span className="text-muted-foreground">Clients:</span>{' '}
                                                        <span className="font-semibold">{corr.client_count}</span>
                                                    </div>
                                                    <div>
                                                        <span className="text-muted-foreground">Lobbyists:</span>{' '}
                                                        <span className="font-semibold">{corr.registrant_count} firms</span>
                                                    </div>
                                                    <div>
                                                        <span className="text-muted-foreground">Filings:</span>{' '}
                                                        <span className="font-semibold">{corr.filing_count}</span>
                                                    </div>
                                                    <div>
                                                        <span className="text-muted-foreground">Lobbying:</span>{' '}
                                                        <span className="font-semibold">{formatCurrency(corr.lobbying_amount)}</span>
                                                    </div>
                                                </div>

                                                {/* Clients */}
                                                {clients.length > 0 && (
                                                    <div>
                                                        <div className="text-xs text-muted-foreground mb-1">Lobbying Clients</div>
                                                        <div className="flex flex-wrap gap-1">
                                                            {clients.map((client, i) => (
                                                                <Badge key={i} variant="outline" className="bg-green-50 text-green-700 border-green-200">
                                                                    {client.substring(0, 30)}
                                                                </Badge>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Issue Codes */}
                                                {issues.length > 0 && (
                                                    <div>
                                                        <div className="text-xs text-muted-foreground mb-1">Issue Codes</div>
                                                        <div className="flex flex-wrap gap-1">
                                                            {issues.map((issue, i) => (
                                                                <Badge key={i} variant="outline" className="bg-orange-50 text-orange-700 border-orange-200">
                                                                    {issue}
                                                                </Badge>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Stock Impact Predictions */}
                                                {stockImpacts.length > 0 && (
                                                    <div>
                                                        <div className="text-xs text-muted-foreground mb-1">📈 Potential Stock Impact</div>
                                                        <div className="flex flex-wrap gap-1">
                                                            {stockImpacts.map((impact, i) => (
                                                                <Badge
                                                                    key={i}
                                                                    variant="outline"
                                                                    className={`${getSentimentColor(impact.sentiment)} flex items-center gap-1`}
                                                                >
                                                                    {getSentimentIcon(impact.sentiment)}
                                                                    {impact.ticker}
                                                                </Badge>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            );
                        })}
                    </div>

                    {/* Load More */}
                    {displayCount < correlations.length && (
                        <div className="text-center">
                            <Button onClick={loadMore} variant="outline">
                                Load More ({correlations.length - displayCount} remaining)
                            </Button>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
