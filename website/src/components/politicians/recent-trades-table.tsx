'use client';

import { useEffect, useState } from 'react';
import { fetchMemberTrades } from '@/lib/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';

interface RecentTradesTableProps {
    bioguideId: string;
}

export function RecentTradesTable({ bioguideId }: RecentTradesTableProps) {
    const [trades, setTrades] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function load() {
            try {
                const data = await fetchMemberTrades(bioguideId, 10);
                setTrades(data);
            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        }
        load();
    }, [bioguideId]);

    if (loading) return <div className="space-y-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
    </div>;

    if (trades.length === 0) return <div className="text-center py-4 text-muted-foreground">No recent trades found</div>;

    return (
        <div className="rounded-md border">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead>Stock</TableHead>
                        <TableHead>Transaction</TableHead>
                        <TableHead>Filed</TableHead>
                        <TableHead>Traded</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {trades.map((trade, i) => (
                        <TableRow key={i}>
                            <TableCell className="font-medium">
                                <div className="flex items-center gap-2">
                                    {trade.ticker && <div className="w-8 h-8 rounded bg-muted flex items-center justify-center font-bold text-xs">{trade.ticker}</div>}
                                    <div>
                                        <div>{trade.ticker || 'N/A'}</div>
                                        <div className="text-xs text-muted-foreground truncate max-w-[120px]">{trade.asset_description}</div>
                                    </div>
                                </div>
                            </TableCell>
                            <TableCell>
                                <div className="flex flex-col">
                                    <span className={trade.transaction_type?.toLowerCase().includes('purchase') ? 'text-emerald-500 font-medium' : 'text-orange-500 font-medium'}>
                                        {trade.transaction_type}
                                    </span>
                                    <span className="text-xs text-muted-foreground">{trade.amount}</span>
                                </div>
                            </TableCell>
                            <TableCell>{new Date(trade.filing_date).toLocaleDateString()}</TableCell>
                            <TableCell>{new Date(trade.transaction_date).toLocaleDateString()}</TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </div>
    );
}
