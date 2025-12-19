import { useMemberTrades } from '@/hooks/use-api';
import { DataContainer } from '@/components/ui/data-container';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';

interface RecentTradesTableProps {
    bioguideId: string;
}

export function RecentTradesTable({ bioguideId }: RecentTradesTableProps) {
    const { data: trades, isLoading, isError, error, refetch } = useMemberTrades(bioguideId, 10);

    const loadingSkeleton = (
        <div className="space-y-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
        </div>
    );

    return (
        <DataContainer
            isLoading={isLoading}
            isError={isError}
            error={error}
            data={trades}
            onRetry={() => refetch()}
            loadingSkeleton={loadingSkeleton}
            emptyMessage="No recent trades found for this member."
        >
            {(trades: any[]) => (
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
                                    <TableCell>{trade.filing_date ? new Date(trade.filing_date).toLocaleDateString() : 'N/A'}</TableCell>
                                    <TableCell>{trade.transaction_date ? new Date(trade.transaction_date).toLocaleDateString() : 'N/A'}</TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>
            )}
        </DataContainer>
    );
}
