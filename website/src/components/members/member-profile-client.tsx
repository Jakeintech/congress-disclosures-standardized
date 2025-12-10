'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { fetchMemberProfile, fetchMemberTrades } from '@/lib/api';
import type { MemberProfile as APIMemberProfile, Transaction } from '@/types/api';

// Local type extending API type with computed fields
type MemberProfile = APIMemberProfile & {
    name?: string; // Computed from first_name + last_name
    trade_count?: number;
    total_volume?: string;
    most_traded_tickers?: string[];
    terms_served?: number;
};

type Trade = Transaction;

interface MemberProfileClientProps {
    bioguideId: string;
}

export function MemberProfileClient({ bioguideId }: MemberProfileClientProps) {
    const [member, setMember] = useState<MemberProfile | null>(null);
    const [trades, setTrades] = useState<Trade[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadData() {
            if (!bioguideId) return;

            setLoading(true);
            setError(null);

            try {
                const [memberData, tradesData] = await Promise.allSettled([
                    fetchMemberProfile(bioguideId),
                    fetchMemberTrades(bioguideId)
                ]);

                if (memberData.status === 'fulfilled') {
                    setMember(memberData.value as MemberProfile);
                }
                if (tradesData.status === 'fulfilled') {
                    setTrades(Array.isArray(tradesData.value) ? (tradesData.value as Trade[]) : []);
                }
            } catch (err) {
                setError('Failed to load member profile');
                console.error(err);
            } finally {
                setLoading(false);
            }
        }

        loadData();
    }, [bioguideId]);

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

    function getPartyColor(party?: string): string {
        switch (party) {
            case 'D': return 'bg-blue-500';
            case 'R': return 'bg-red-500';
            default: return 'bg-gray-500';
        }
    }

    if (loading) {
        return (
            <div className="space-y-6">
                <Skeleton className="h-10 w-64" />
                <div className="grid gap-4 md:grid-cols-4">
                    {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-24" />)}
                </div>
            </div>
        );
    }

    if (error || !member) {
        return (
            <Card className="border-destructive">
                <CardContent className="pt-6">
                    <p className="text-destructive">{error || 'Member not found'}</p>
                    <Button asChild className="mt-4">
                        <Link href="/members">← Back to Members</Link>
                    </Button>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            {/* Breadcrumb */}
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Link href="/members" className="hover:underline">Members</Link>
                <span>/</span>
                <span>{member.name}</span>
            </div>

            {/* Header */}
            <div className="flex items-start gap-6">
                <div className={`w-20 h-20 rounded-full flex items-center justify-center text-3xl font-bold text-white ${getPartyColor(member.party)}`}>
                    {member.name?.charAt(0) || '?'}
                </div>
                <div>
                    <h1 className="text-3xl font-bold">{member.name}</h1>
                    <div className="flex items-center gap-2 mt-2">
                        <Badge variant={member.party === 'D' ? 'default' : 'secondary'}>
                            {member.party === 'D' ? 'Democrat' : member.party === 'R' ? 'Republican' : 'Independent'}
                        </Badge>
                        <span className="text-muted-foreground">
                            {member.state}{member.district ? `-${member.district}` : ''}
                        </span>
                        <span className="text-muted-foreground capitalize">
                            • {member.chamber}
                        </span>
                    </div>
                </div>
            </div>

            {/* Stats */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card>
                    <CardHeader className="pb-2">
                        <CardDescription>Total Trades</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <p className="text-2xl font-bold">{member.trade_count || 0}</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardDescription>Total Volume</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <p className="text-2xl font-bold">{member.total_volume || 'N/A'}</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardDescription>Terms Served</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <p className="text-2xl font-bold">{member.terms_served || 'N/A'}</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardDescription>Most Traded</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-wrap gap-1">
                            {member.most_traded_tickers?.slice(0, 3).map(ticker => (
                                <Badge key={ticker} variant="outline">{ticker}</Badge>
                            )) || <span className="text-muted-foreground">N/A</span>}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Tabs */}
            <Tabs defaultValue="trades" className="space-y-4">
                <TabsList>
                    <TabsTrigger value="trades">Trades ({trades.length})</TabsTrigger>
                    <TabsTrigger value="bills">Sponsored Bills</TabsTrigger>
                    <TabsTrigger value="lobbying">Lobbying Connections</TabsTrigger>
                </TabsList>

                {/* Trades Tab */}
                <TabsContent value="trades">
                    <Card>
                        <CardHeader>
                            <CardTitle>Recent Trades</CardTitle>
                            <CardDescription>
                                Financial disclosure transactions
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {trades.length === 0 ? (
                                <p className="text-muted-foreground py-4 text-center">
                                    No trades found
                                </p>
                            ) : (
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>Date</TableHead>
                                            <TableHead>Ticker</TableHead>
                                            <TableHead>Asset</TableHead>
                                            <TableHead>Type</TableHead>
                                            <TableHead>Amount</TableHead>
                                            <TableHead>Owner</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {trades.map((trade, i) => (
                                            <TableRow key={i}>
                                                <TableCell>{formatDate(trade.transaction_date)}</TableCell>
                                                <TableCell className="font-mono font-bold">
                                                    {trade.ticker || 'N/A'}
                                                </TableCell>
                                                <TableCell className="max-w-xs truncate">
                                                    {trade.asset_description || 'N/A'}
                                                </TableCell>
                                                <TableCell>
                                                    <Badge variant={trade.transaction_type === 'Purchase' ? 'default' : 'secondary'}>
                                                        {trade.transaction_type}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell>{trade.amount || 'N/A'}</TableCell>
                                                <TableCell>{trade.owner || 'Self'}</TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Bills Tab */}
                <TabsContent value="bills">
                    <Card>
                        <CardHeader>
                            <CardTitle>Sponsored Bills</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <p className="text-muted-foreground py-4 text-center">
                                Coming soon - bills sponsored by this member
                            </p>
                            <Button asChild variant="outline" className="w-full">
                                <Link href={`/bills?sponsor=${bioguideId}`}>
                                    View Bills Sponsored by {member.name}
                                </Link>
                            </Button>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Lobbying Tab */}
                <TabsContent value="lobbying">
                    <Card>
                        <CardHeader>
                            <CardTitle>Lobbying Connections</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <p className="text-muted-foreground py-4 text-center">
                                Coming soon - lobbying activity related to this member
                            </p>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
