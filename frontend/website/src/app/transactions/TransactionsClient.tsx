'use client';

import { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Transaction } from '@/lib/api';

interface TransactionsClientProps {
    initialTransactions: Transaction[];
}

export function TransactionsClient({ initialTransactions }: TransactionsClientProps) {
    // Filters
    const [ticker, setTicker] = useState('');
    const [member, setMember] = useState('');
    const [tradeType, setTradeType] = useState('');

    const filteredTransactions = useMemo(() => {
        const lowerTicker = ticker.toLowerCase();
        const lowerMember = member.toLowerCase();

        return initialTransactions.filter(t => {
            const matchesTicker = !ticker ||
                (t.ticker && t.ticker.toLowerCase().includes(lowerTicker)) ||
                (t.asset_description && t.asset_description.toLowerCase().includes(lowerTicker));

            const matchesMember = !member ||
                (t.filer_name && t.filer_name.toLowerCase().includes(lowerMember)) ||
                (t.member_name && t.member_name.toLowerCase().includes(lowerMember)) ||
                (t.party && t.party.toLowerCase().includes(lowerMember));

            const matchesType = !tradeType || tradeType === 'all' ||
                (t.transaction_type && t.transaction_type.toLowerCase() === tradeType.toLowerCase());

            return matchesTicker && matchesMember && matchesType;
        });
    }, [ticker, member, tradeType, initialTransactions]);

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

    function formatAmount(tx: Transaction): string {
        if (tx.amount) return tx.amount;
        if (tx.amount_low === 0 && tx.amount_high === 0) return 'N/A';

        const low = tx.amount_low !== undefined ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(tx.amount_low) : null;
        const high = tx.amount_high !== undefined ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(tx.amount_high) : null;

        if (low && high && low !== high) {
            return `${low} - ${high}`;
        } else if (low) {
            return `${low}+`;
        }
        return 'N/A';
    }

    return (
        <div className="space-y-6">
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
                                <SelectItem value="exchange">Exchange</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                </CardContent>
            </Card>

            {/* Transactions Table */}
            <Card>
                <CardHeader>
                    <CardTitle>
                        {`${filteredTransactions.length} Transactions`}
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="rounded-md border overflow-x-auto">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead className="w-[120px]">Date</TableHead>
                                    <TableHead>Member</TableHead>
                                    <TableHead className="w-[100px]">Ticker</TableHead>
                                    <TableHead>Asset</TableHead>
                                    <TableHead className="w-[120px]">Type</TableHead>
                                    <TableHead className="w-[180px]">Amount</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {filteredTransactions.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                                            No transactions found matching your filters.
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    filteredTransactions.map((tx, i) => (
                                        <TableRow key={tx.transaction_key || tx.doc_id || i}>
                                            <TableCell>{formatDate(tx.transaction_date)}</TableCell>
                                            <TableCell>
                                                <div className="flex flex-col">
                                                    {tx.bioguide_id ? (
                                                        <Link
                                                            href={`/politician/${tx.bioguide_id}`}
                                                            className="font-medium hover:underline"
                                                        >
                                                            {tx.filer_name || tx.member_name || 'Unknown'}
                                                        </Link>
                                                    ) : (tx.filer_name || tx.member_name || 'Unknown')}
                                                    {tx.party && (
                                                        <span className="text-xs text-muted-foreground">
                                                            ({tx.party.substring(0, 1)}-{tx.state})
                                                        </span>
                                                    )}
                                                </div>
                                            </TableCell>
                                            <TableCell className="font-mono font-bold">
                                                {tx.ticker || 'N/A'}
                                            </TableCell>
                                            <TableCell className="max-w-[200px] truncate">
                                                {tx.asset_description || 'N/A'}
                                            </TableCell>
                                            <TableCell>
                                                <Badge variant={tx.transaction_type?.toLowerCase() === 'purchase' ? 'default' : 'secondary'}>
                                                    {tx.transaction_type}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="whitespace-nowrap font-medium">
                                                {formatAmount(tx)}
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
