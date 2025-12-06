'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';
import { fetchTransactions, type TransactionsParams } from '@/lib/api';

interface Transaction {
    transaction_date: string;
    ticker?: string;
    asset_name?: string;
    trade_type: string;
    amount_range?: string;
    member_name?: string;
    bioguide_id?: string;
    party?: string;
    state?: string;
}

export default function TransactionsPage() {
    const [allTransactions, setAllTransactions] = useState<Transaction[]>([]);
    const [filteredTransactions, setFilteredTransactions] = useState<Transaction[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Filters
    const [ticker, setTicker] = useState('');
    const [member, setMember] = useState('');
    const [tradeType, setTradeType] = useState('');

    useEffect(() => {
        async function loadTransactions() {
            setLoading(true);
            setError(null);

            try {
                // Fetch larger batch for client-side filtering, matching legacy behavior
                const data = await fetchTransactions({ limit: 1000 });
                const loaded = Array.isArray(data) ? (data as Transaction[]) : [];
                setAllTransactions(loaded);
                setFilteredTransactions(loaded);
            } catch (err) {
                setError('Failed to load transactions');
                console.error(err);
            } finally {
                setLoading(false);
            }
        }
        loadTransactions();
    }, []);

    // Client-side filtering
    useEffect(() => {
        const lowerTicker = ticker.toLowerCase();
        const lowerMember = member.toLowerCase();

        const filtered = allTransactions.filter(t => {
            const matchesTicker = !ticker || (t.ticker && t.ticker.toLowerCase().includes(lowerTicker)) || (t.asset_name && t.asset_name.toLowerCase().includes(lowerTicker));
            const matchesMember = !member || (t.member_name && t.member_name.toLowerCase().includes(lowerMember)) || (t.party && t.party.toLowerCase().includes(lowerMember));
            const matchesType = !tradeType || tradeType === 'all' || (t.trade_type && t.trade_type === tradeType);

            return matchesTicker && matchesMember && matchesType;
        });

        setFilteredTransactions(filtered);
    }, [ticker, member, tradeType, allTransactions]);

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

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Transactions</h1>
                <p className="text-muted-foreground">
                    Browse stock trades disclosed by members of Congress
                </p>
            </div>

            {error && (
                <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            {/* Filters */}
            <Card>
                <CardContent className="pt-6">
                    <div className="grid gap-4 sm:grid-cols-3">
                        <Input
                            placeholder="Filter by ticker (e.g., AAPL)..."
                            value={ticker}
                            onChange={(e) => setTicker(e.target.value.toUpperCase())}
                        />

                        <Input
                            placeholder="Filter by member name..."
                            value={member}
                            onChange={(e) => setMember(e.target.value)}
                        />

                        <Select value={tradeType || "all"} onValueChange={(val) => setTradeType(val === "all" ? "" : val)}>
                            <SelectTrigger>
                                <SelectValue placeholder="Trade Type" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All Types</SelectItem>
                                <SelectItem value="purchase">Purchase</SelectItem>
                                <SelectItem value="sale">Sale</SelectItem>
                            </SelectContent>
                        </Select>
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

            {/* Transactions Table */}
            <Card>
                <CardHeader>
                    <CardTitle>
                        {loading ? 'Loading...' : `${filteredTransactions.length} Transactions`}
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="rounded-md border">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Date</TableHead>
                                    <TableHead>Member</TableHead>
                                    <TableHead>Ticker</TableHead>
                                    <TableHead>Asset</TableHead>
                                    <TableHead>Type</TableHead>
                                    <TableHead>Amount</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    [...Array(10)].map((_, i) => (
                                        <TableRow key={i}>
                                            {[...Array(6)].map((_, j) => (
                                                <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                                            ))}
                                        </TableRow>
                                    ))
                                ) : filteredTransactions.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                                            No transactions found matching your filters.
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    filteredTransactions.map((tx, i) => (
                                        <TableRow key={i}>
                                            <TableCell>{formatDate(tx.transaction_date)}</TableCell>
                                            <TableCell>
                                                {tx.bioguide_id ? (
                                                    <Link
                                                        href={`/member?id=${tx.bioguide_id}`}
                                                        className="font-medium hover:underline"
                                                    >
                                                        {tx.member_name}
                                                    </Link>
                                                ) : tx.member_name || 'Unknown'}
                                                {tx.party && (
                                                    <span className="text-muted-foreground ml-1">
                                                        ({tx.party}-{tx.state})
                                                    </span>
                                                )}
                                            </TableCell>
                                            <TableCell className="font-mono font-bold">
                                                {tx.ticker || 'N/A'}
                                            </TableCell>
                                            <TableCell className="max-w-xs truncate">
                                                {tx.asset_name || 'N/A'}
                                            </TableCell>
                                            <TableCell>
                                                <Badge variant={tx.trade_type === 'purchase' ? 'default' : 'secondary'}>
                                                    {tx.trade_type}
                                                </Badge>
                                            </TableCell>
                                            <TableCell>{tx.amount_range || 'N/A'}</TableCell>
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
