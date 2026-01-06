'use client';

import { Badge } from '@/components/ui/badge';
import { DataContainer } from '@/components/ui/data-container';
import { usePortfolios } from '@/hooks/use-api';
import { PortfolioHolding } from '@/types/api';
import { Briefcase, Calendar } from 'lucide-react';

interface MemberPortfolioTableProps {
    bioguideId: string;
}

export function MemberPortfolioTable({ bioguideId }: MemberPortfolioTableProps) {
    const portfolioQuery = usePortfolios({ member_id: bioguideId, include_holdings: true });

    return (
        <DataContainer
            isLoading={portfolioQuery.isLoading}
            isError={portfolioQuery.isError}
            data={portfolioQuery.data}
            emptyMessage="No portfolio holdings found for this member."
            onRetry={() => portfolioQuery.refetch()}
        >
            {(data: any) => {
                // The hook might return an array or a single object depending on the API
                const portfolio = Array.isArray(data) ? data[0] : data;
                const holdings = portfolio?.holdings || [];

                return (
                    <div className="space-y-4">
                        <div className="flex items-center justify-between px-1">
                            <div>
                                <h3 className="text-lg font-bold flex items-center gap-2">
                                    <Briefcase className="h-5 w-5 text-primary" />
                                    Current Holdings
                                </h3>
                                <p className="text-sm text-muted-foreground">Estimated positions based on latest disclosures</p>
                            </div>
                            {portfolio?.last_updated && (
                                <Badge variant="outline" className="text-[10px] uppercase font-mono">
                                    Last Updated: {new Date(portfolio.last_updated).toLocaleDateString()}
                                </Badge>
                            )}
                        </div>

                        <div className="bg-background rounded-xl border shadow-sm overflow-hidden">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b bg-muted/30">
                                        <th className="text-left py-3 px-4 font-semibold text-muted-foreground uppercase tracking-wider text-[10px]">Asset</th>
                                        <th className="text-left py-3 px-4 font-semibold text-muted-foreground uppercase tracking-wider text-[10px]">Ticker</th>
                                        <th className="text-left py-3 px-4 font-semibold text-muted-foreground uppercase tracking-wider text-[10px]">Value Range</th>
                                        <th className="text-left py-3 px-4 font-semibold text-muted-foreground uppercase tracking-wider text-[10px]">Type</th>
                                        <th className="text-right py-3 px-4 font-semibold text-muted-foreground uppercase tracking-wider text-[10px]">Last Seen</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y">
                                    {holdings.map((holding: PortfolioHolding, i: number) => (
                                        <tr key={i} className="hover:bg-accent/5 transition-colors group">
                                            <td className="py-3 px-4">
                                                <div className="font-semibold text-sm group-hover:text-primary transition-colors truncate max-w-[200px]" title={holding.asset_description}>
                                                    {holding.asset_description}
                                                </div>
                                            </td>
                                            <td className="py-3 px-4">
                                                {holding.ticker ? (
                                                    <Badge className="font-mono text-[11px] bg-primary/10 text-primary border-none">
                                                        {holding.ticker}
                                                    </Badge>
                                                ) : (
                                                    <span className="text-muted-foreground text-xs italic">N/A</span>
                                                )}
                                            </td>
                                            <td className="py-3 px-4">
                                                <span className="font-mono text-xs font-medium text-emerald-600">
                                                    {holding.value_range}
                                                </span>
                                            </td>
                                            <td className="py-3 px-4">
                                                <Badge variant="outline" className="text-[10px] uppercase h-4">
                                                    {holding.asset_type}
                                                </Badge>
                                            </td>
                                            <td className="py-3 px-4 text-right">
                                                <div className="flex items-center justify-end gap-1.5 text-xs text-muted-foreground font-mono">
                                                    <Calendar className="h-3 w-3" />
                                                    {new Date(holding.filing_date).toLocaleDateString()}
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            {holdings.length === 0 && (
                                <div className="p-8 text-center text-muted-foreground italic">
                                    No detailed holdings available.
                                </div>
                            )}
                        </div>
                    </div>
                );
            }}
        </DataContainer>
    );
}
