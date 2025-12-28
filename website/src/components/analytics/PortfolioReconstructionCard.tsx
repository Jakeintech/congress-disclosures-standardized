"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Briefcase, TrendingUp, ShieldCheck, AlertCircle, PieChart } from "lucide-react";
import { usePortfolios } from "@/hooks/use-api";
import { DataContainer } from "@/components/ui/data-container";
import { PortfolioData } from "@/types/api";

interface PortfolioReconstructionCardProps {
    memberId?: string;
    limit?: number;
}

export function PortfolioReconstructionCard({
    memberId,
    limit = 10
}: PortfolioReconstructionCardProps) {
    const { data = [], isLoading, error, refetch } = usePortfolios({
        member_id: memberId,
        limit,
        include_holdings: false
    });

    const formatCurrency = (val: number | undefined) => {
        if (!val) return '--';
        if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`;
        if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`;
        return `$${val.toFixed(0)}`;
    };

    const getConfidenceColor = (score: number) => {
        if (score >= 0.8) return 'text-green-600';
        if (score >= 0.5) return 'text-yellow-600';
        return 'text-red-600';
    };

    return (
        <DataContainer
            isLoading={isLoading}
            isError={!!error}
            error={error}
            data={data}
            onRetry={() => refetch()}
            loadingSkeleton={
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Briefcase className="h-5 w-5" />
                            Portfolio Reconstruction
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center justify-center py-8">
                            <div className="animate-pulse text-muted-foreground">Reconstructing portfolios...</div>
                        </div>
                    </CardContent>
                </Card>
            }
        >
            {(data) => (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Briefcase className="h-5 w-5" />
                            Portfolio Reconstruction
                        </CardTitle>
                        <CardDescription>
                            Estimated current holdings based on disclosure history
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {(Array.isArray(data) ? data : []).map((port: PortfolioData, idx: number) => (
                                <div key={idx} className="p-4 rounded-lg border bg-card text-card-foreground shadow-sm">
                                    <div className="flex items-start justify-between mb-3">
                                        <div>
                                            <h4 className="font-semibold text-lg">{port.name || port.member_key}</h4>
                                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                                <span>{port.party}</span>
                                                <span>•</span>
                                                <Badge variant="outline" className="text-[10px] uppercase">
                                                    {port.position_count} positions
                                                </Badge>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <div className="text-sm text-muted-foreground mb-1 uppercase tracking-wider font-semibold">
                                                Est. Value
                                            </div>
                                            <div className="text-xl font-bold text-primary">
                                                {formatCurrency(port.estimated_portfolio_value)}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4 mt-4 py-3 border-t">
                                        <div>
                                            <div className="text-xs text-muted-foreground uppercase mb-1">Top Sector</div>
                                            <div className="flex items-center gap-2">
                                                <PieChart className="h-3 w-3 text-muted-foreground" />
                                                <span className="text-sm font-medium">{port.top_sector || '--'}</span>
                                            </div>
                                        </div>
                                        <div>
                                            <div className="text-xs text-muted-foreground uppercase mb-1">Confidence</div>
                                            <div className="flex items-center gap-2">
                                                {port.confidence_score >= 0.7 ? (
                                                    <ShieldCheck className={`h-3 w-3 ${getConfidenceColor(port.confidence_score)}`} />
                                                ) : (
                                                    <AlertCircle className={`h-3 w-3 ${getConfidenceColor(port.confidence_score)}`} />
                                                )}
                                                <span className={`text-sm font-bold ${getConfidenceColor(port.confidence_score)}`}>
                                                    {(port.confidence_score * 100).toFixed(0)}%
                                                </span>
                                            </div>
                                        </div>
                                    </div>

                                    {port.top_holdings && port.top_holdings.length > 0 && (
                                        <div className="mt-4 pt-3 border-t">
                                            <div className="text-xs text-muted-foreground uppercase mb-2">Top Holdings</div>
                                            <div className="flex flex-wrap gap-2">
                                                {port.top_holdings.map((h, i) => (
                                                    <Badge key={i} variant="secondary" className="font-mono text-[10px]">
                                                        {h.ticker}: {formatCurrency(h.value)}
                                                    </Badge>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {port.total_trades !== undefined && (
                                        <div className="mt-4 pt-3 flex items-center justify-between text-xs text-muted-foreground border-t border-dashed">
                                            <span>History: {port.total_trades} trades analyzed</span>
                                            {port.last_trade_date && (
                                                <span>Updated {new Date(port.last_trade_date).toLocaleDateString()}</span>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}
        </DataContainer>
    );
}
