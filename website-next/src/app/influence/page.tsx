'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { fetchTripleCorrelations, type TripleCorrelationsParams } from '@/lib/api';

interface TripleCorrelation {
    member_name: string;
    member_bioguide_id: string;
    member_party?: string;
    member_state?: string;
    bill_id: string;
    bill_title?: string;
    ticker: string;
    company_name?: string;
    trade_date: string;
    trade_type: string;
    trade_amount?: string;
    bill_action_date?: string;
    client_name?: string;
    lobbying_spend?: number;
    contribution_amount?: number;
    correlation_score: number;
    explanation_text?: string;
}

export default function InfluencePage() {
    const [correlations, setCorrelations] = useState<TripleCorrelation[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [minScore, setMinScore] = useState(40);

    useEffect(() => {
        async function loadCorrelations() {
            setLoading(true);
            setError(null);

            try {
                const params: TripleCorrelationsParams = {
                    minScore,
                    limit: 50
                };

                const data = await fetchTripleCorrelations(params);
                setCorrelations(Array.isArray(data) ? (data as TripleCorrelation[]) : []);
            } catch (err) {
                setError('Failed to load correlations');
                console.error(err);
            } finally {
                setLoading(false);
            }
        }

        loadCorrelations();
    }, [minScore]);

    function formatDate(dateStr?: string): string {
        if (!dateStr) return 'N/A';
        try {
            return new Date(dateStr).toLocaleDateString('en-US', {
                year: 'numeric', month: 'short', day: 'numeric'
            });
        } catch {
            return dateStr;
        }
    }

    function formatMoney(amount?: number): string {
        if (!amount) return 'N/A';
        return `$${amount.toLocaleString()}`;
    }

    function getScoreColor(score: number): string {
        if (score >= 70) return 'bg-red-500 text-white';
        if (score >= 40) return 'bg-yellow-500 text-black';
        return 'bg-gray-300 text-black';
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                    <span>⚡</span>
                    Influence Tracker
                </h1>
                <p className="text-muted-foreground">
                    Trade-Bill-Lobbying triple correlation analysis
                </p>
            </div>

            {/* Score Explanation */}
            <Card className="bg-muted/50">
                <CardHeader className="pb-2">
                    <CardTitle className="text-lg">Correlation Score</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-2 text-sm sm:grid-cols-4">
                        <div><strong>Stock Trade:</strong> 40 pts</div>
                        <div><strong>Bill Sponsorship:</strong> 30 pts</div>
                        <div><strong>Lobbying Activity:</strong> 20 pts</div>
                        <div><strong>Contributions:</strong> 10 pts</div>
                    </div>
                    <div className="flex gap-2 mt-3">
                        <Badge className="bg-red-500">70-100 High</Badge>
                        <Badge className="bg-yellow-500 text-black">40-69 Moderate</Badge>
                        <Badge variant="secondary">0-39 Low</Badge>
                    </div>
                </CardContent>
            </Card>

            {/* Filters */}
            <Card>
                <CardContent className="pt-6">
                    <div className="flex items-center gap-4">
                        <span className="text-sm font-medium">Min Score:</span>
                        <div className="flex gap-2">
                            {[0, 20, 40, 60, 80].map(score => (
                                <Button
                                    key={score}
                                    variant={minScore === score ? 'default' : 'outline'}
                                    size="sm"
                                    onClick={() => setMinScore(score)}
                                >
                                    {score}+
                                </Button>
                            ))}
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Error */}
            {error && (
                <Card className="border-destructive">
                    <CardContent className="pt-6">
                        <p className="text-destructive">{error}</p>
                    </CardContent>
                </Card>
            )}

            {/* Results Table */}
            <Card>
                <CardHeader>
                    <CardTitle>
                        {loading ? 'Loading...' : `${correlations.length} Correlations Found`}
                    </CardTitle>
                    <CardDescription>
                        Connections between stock trades, legislation, and lobbying activity
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="rounded-md border">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead className="text-center">Score</TableHead>
                                    <TableHead>Member</TableHead>
                                    <TableHead>Trade</TableHead>
                                    <TableHead>Bill</TableHead>
                                    <TableHead>Lobbying</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    [...Array(5)].map((_, i) => (
                                        <TableRow key={i}>
                                            {[...Array(5)].map((_, j) => (
                                                <TableCell key={j}><Skeleton className="h-6 w-full" /></TableCell>
                                            ))}
                                        </TableRow>
                                    ))
                                ) : correlations.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                                            No correlations found with score ≥ {minScore}
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    correlations.map((corr, i) => (
                                        <TableRow key={i}>
                                            <TableCell className="text-center">
                                                <Badge className={getScoreColor(corr.correlation_score)}>
                                                    {corr.correlation_score}
                                                </Badge>
                                            </TableCell>
                                            <TableCell>
                                                <Link
                                                    href={`/member?id=${corr.member_bioguide_id}`}
                                                    className="font-medium hover:underline"
                                                >
                                                    {corr.member_name}
                                                </Link>
                                                <span className="text-muted-foreground ml-1">
                                                    ({corr.member_party}-{corr.member_state})
                                                </span>
                                            </TableCell>
                                            <TableCell>
                                                <div className="font-mono font-bold">{corr.ticker}</div>
                                                <div className="text-sm text-muted-foreground">
                                                    {formatDate(corr.trade_date)} • {corr.trade_type}
                                                </div>
                                                {corr.trade_amount && (
                                                    <div className="text-sm">{corr.trade_amount}</div>
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                <Link
                                                    href={`/bill?id=${corr.bill_id}`}
                                                    className="font-medium hover:underline"
                                                >
                                                    {corr.bill_id}
                                                </Link>
                                                {corr.bill_title && (
                                                    <p className="text-sm text-muted-foreground truncate max-w-xs">
                                                        {corr.bill_title}
                                                    </p>
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                {corr.client_name ? (
                                                    <div>
                                                        <p className="font-medium">{corr.client_name}</p>
                                                        {corr.lobbying_spend && (
                                                            <p className="text-sm text-muted-foreground">
                                                                {formatMoney(corr.lobbying_spend)} spent
                                                            </p>
                                                        )}
                                                        {corr.contribution_amount && (
                                                            <p className="text-sm text-green-600">
                                                                +{formatMoney(corr.contribution_amount)} contributed
                                                            </p>
                                                        )}
                                                    </div>
                                                ) : (
                                                    <span className="text-muted-foreground">N/A</span>
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
