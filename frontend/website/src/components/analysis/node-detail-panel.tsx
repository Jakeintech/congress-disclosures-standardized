'use client';

import React from 'react';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { StockLogo } from '@/components/ui/stock-logo';
import {
    X, TrendingUp, TrendingDown, BarChart3, Users,
    Building2, MapPin, Calendar, DollarSign, ArrowUpRight,
    ArrowDownRight, Minus, ExternalLink, Briefcase
} from 'lucide-react';

interface NodeData {
    id: string;
    group: string;
    name?: string;
    party?: string;
    chamber?: string;
    state?: string;
    bioguide_id?: string;
    photo_url?: string;
    logo_url?: string;
    value?: number;
    transaction_count?: number;
    buy_count?: number;
    sell_count?: number;
    buy_volume?: number;
    sell_volume?: number;
    unique_traders?: number;
    latest_trade_date?: string;
    sector?: string;
    company_name?: string;
    title?: string;
    bill_id?: string;
    // Aggregated node data
    member_count?: number;
    top_stocks?: Array<{ ticker: string; volume: number }>;
    recent_transactions?: Array<{
        ticker: string;
        type: string;
        amount: string;
        date: string;
    }>;
}

interface NodeDetailPanelProps {
    node: NodeData | null;
    onClose: () => void;
    onDrillDown?: (nodeId: string) => void;
    onNavigate?: (path: string) => void;
}

const formatMoney = (val: number) =>
    new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        notation: 'compact',
        maximumFractionDigits: 1
    }).format(val);

const formatDate = (dateStr: string) => {
    try {
        return new Date(dateStr).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    } catch {
        return dateStr;
    }
};

export function NodeDetailPanel({ node, onClose, onDrillDown, onNavigate }: NodeDetailPanelProps) {
    if (!node) return null;

    const isMember = node.group === 'member';
    const isAsset = node.group === 'asset';
    const isBill = node.group === 'bill';
    const isAggregate = node.group?.includes('_agg');

    const partyColor = node.party === 'Democrat' || node.party === 'D'
        ? 'bg-blue-500'
        : node.party === 'Republican' || node.party === 'R'
            ? 'bg-red-500'
            : 'bg-gray-500';

    const buyPercent = node.transaction_count
        ? ((node.buy_count || 0) / node.transaction_count * 100).toFixed(0)
        : '0';
    const sellPercent = node.transaction_count
        ? ((node.sell_count || 0) / node.transaction_count * 100).toFixed(0)
        : '0';

    return (
        <Card className="border-2 border-primary shadow-xl overflow-hidden">
            {/* Header with gradient based on type */}
            <CardHeader className={`pb-3 ${isMember ? (node.party === 'Democrat' ? 'bg-gradient-to-r from-blue-500/10 to-blue-600/5' : 'bg-gradient-to-r from-red-500/10 to-red-600/5')
                : isAsset ? 'bg-gradient-to-r from-green-500/10 to-emerald-600/5'
                    : isBill ? 'bg-gradient-to-r from-purple-500/10 to-violet-600/5'
                        : 'bg-gradient-to-r from-gray-500/10 to-gray-600/5'
                }`}>
                <div className="flex items-start gap-4">
                    {/* Avatar/Logo */}
                    {isMember && (
                        <Avatar className="h-16 w-16 border-2 border-background shadow-md">
                            <AvatarImage
                                src={node.photo_url || `https://bioguide.congress.gov/bioguide/photo/${node.bioguide_id?.charAt(0)}/${node.bioguide_id}.jpg`}
                                alt={node.name || node.id}
                            />
                            <AvatarFallback className={`${partyColor} text-white font-bold`}>
                                {(node.name || node.id).split(' ').map(n => n[0]).join('').substring(0, 2)}
                            </AvatarFallback>
                        </Avatar>
                    )}
                    {isAsset && (
                        <div className="h-16 w-16 rounded-lg bg-card border-2 border-border flex items-center justify-center shadow-md">
                            <StockLogo ticker={node.id} size="lg" />
                        </div>
                    )}
                    {isAggregate && (
                        <div className={`h-16 w-16 rounded-full ${partyColor} flex items-center justify-center shadow-md`}>
                            <Users className="h-8 w-8 text-white" />
                        </div>
                    )}

                    {/* Title & Subtitle */}
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                            <CardTitle className="text-xl truncate">{node.name || node.id}</CardTitle>
                            {node.party && (
                                <Badge variant={node.party === 'Democrat' ? 'default' : 'destructive'} className="shrink-0">
                                    {node.party}
                                </Badge>
                            )}
                        </div>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                            {node.chamber && (
                                <span className="flex items-center gap-1">
                                    <Building2 className="h-3 w-3" />
                                    {node.chamber}
                                </span>
                            )}
                            {node.state && (
                                <span className="flex items-center gap-1">
                                    <MapPin className="h-3 w-3" />
                                    {node.state}
                                </span>
                            )}
                            {node.sector && (
                                <span className="flex items-center gap-1">
                                    <Briefcase className="h-3 w-3" />
                                    {node.sector}
                                </span>
                            )}
                            {isAggregate && (
                                <span className="flex items-center gap-1">
                                    <Users className="h-3 w-3" />
                                    {node.member_count || 0} members
                                </span>
                            )}
                        </div>
                        {node.company_name && (
                            <p className="text-sm text-muted-foreground mt-1 truncate">{node.company_name}</p>
                        )}
                    </div>

                    {/* Close button */}
                    <Button variant="ghost" size="icon" onClick={onClose} className="shrink-0">
                        <X className="h-4 w-4" />
                    </Button>
                </div>
            </CardHeader>

            <CardContent className="pt-4 space-y-4">
                {/* Key Stats Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="bg-muted/50 rounded-lg p-3 text-center">
                        <div className="text-2xl font-bold text-green-500">
                            {formatMoney(node.value || 0)}
                        </div>
                        <div className="text-xs text-muted-foreground font-medium">Total Volume</div>
                    </div>
                    <div className="bg-muted/50 rounded-lg p-3 text-center">
                        <div className="text-2xl font-bold">
                            {node.transaction_count || 0}
                        </div>
                        <div className="text-xs text-muted-foreground font-medium">Transactions</div>
                    </div>
                    {isAsset && (
                        <div className="bg-muted/50 rounded-lg p-3 text-center">
                            <div className="text-2xl font-bold text-blue-500">
                                {node.unique_traders || 0}
                            </div>
                            <div className="text-xs text-muted-foreground font-medium">Unique Traders</div>
                        </div>
                    )}
                    {node.latest_trade_date && (
                        <div className="bg-muted/50 rounded-lg p-3 text-center">
                            <div className="text-sm font-bold flex items-center justify-center gap-1">
                                <Calendar className="h-3 w-3" />
                                {formatDate(node.latest_trade_date)}
                            </div>
                            <div className="text-xs text-muted-foreground font-medium">Latest Trade</div>
                        </div>
                    )}
                </div>

                {/* Buy/Sell Breakdown */}
                {(node.buy_count !== undefined || node.sell_count !== undefined) && (
                    <>
                        <Separator />
                        <div>
                            <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                                <BarChart3 className="h-4 w-4" />
                                Trading Activity Breakdown
                            </h4>

                            {/* Visual bar */}
                            <div className="h-3 rounded-full overflow-hidden bg-muted flex mb-2">
                                <div
                                    className="bg-green-500 transition-all"
                                    style={{ width: `${buyPercent}%` }}
                                />
                                <div
                                    className="bg-red-500 transition-all"
                                    style={{ width: `${sellPercent}%` }}
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="flex items-center gap-2">
                                    <ArrowUpRight className="h-4 w-4 text-green-500" />
                                    <div>
                                        <div className="font-semibold text-green-500">
                                            {node.buy_count || 0} Buys
                                        </div>
                                        <div className="text-xs text-muted-foreground">
                                            {formatMoney(node.buy_volume || 0)}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <ArrowDownRight className="h-4 w-4 text-red-500" />
                                    <div>
                                        <div className="font-semibold text-red-500">
                                            {node.sell_count || 0} Sells
                                        </div>
                                        <div className="text-xs text-muted-foreground">
                                            {formatMoney(node.sell_volume || 0)}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </>
                )}

                {/* Recent Transactions */}
                {node.recent_transactions && node.recent_transactions.length > 0 && (
                    <>
                        <Separator />
                        <div>
                            <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                                <TrendingUp className="h-4 w-4" />
                                Recent Transactions
                            </h4>
                            <ScrollArea className="h-32">
                                <div className="space-y-2">
                                    {node.recent_transactions.slice(0, 5).map((tx, i) => (
                                        <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
                                            <div className="flex items-center gap-2">
                                                {tx.type === 'purchase' ? (
                                                    <ArrowUpRight className="h-4 w-4 text-green-500" />
                                                ) : (
                                                    <ArrowDownRight className="h-4 w-4 text-red-500" />
                                                )}
                                                <span className="font-medium">{tx.ticker}</span>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-sm font-medium">{tx.amount}</div>
                                                <div className="text-xs text-muted-foreground">{formatDate(tx.date)}</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </ScrollArea>
                        </div>
                    </>
                )}

                {/* Top Stocks (for aggregates/members) */}
                {node.top_stocks && node.top_stocks.length > 0 && (
                    <>
                        <Separator />
                        <div>
                            <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                                <DollarSign className="h-4 w-4" />
                                Top Traded Stocks
                            </h4>
                            <div className="flex flex-wrap gap-2">
                                {node.top_stocks.slice(0, 8).map((stock, i) => (
                                    <Badge key={i} variant="secondary" className="flex items-center gap-1">
                                        <StockLogo ticker={stock.ticker} size="sm" />
                                        {stock.ticker}
                                        <span className="text-muted-foreground ml-1">{formatMoney(stock.volume)}</span>
                                    </Badge>
                                ))}
                            </div>
                        </div>
                    </>
                )}

                {/* Action Buttons */}
                <Separator />
                <div className="flex flex-wrap gap-2">
                    {isMember && node.bioguide_id && (
                        <Button size="sm" asChild>
                            <Link href={`/politician/${node.bioguide_id}`}>
                                <ExternalLink className="h-3 w-3 mr-1" />
                                View Full Profile
                            </Link>
                        </Button>
                    )}
                    {isAsset && (
                        <Button size="sm" asChild>
                            <Link href={`/stocks/${node.id}`}>
                                <ExternalLink className="h-3 w-3 mr-1" />
                                View Stock Details
                            </Link>
                        </Button>
                    )}
                    {isBill && node.bill_id && (
                        <Button size="sm" asChild>
                            <Link href={`/bills/${node.bill_id.replace('-', '/')}`}>
                                <ExternalLink className="h-3 w-3 mr-1" />
                                View Bill Details
                            </Link>
                        </Button>
                    )}
                    {isAggregate && onDrillDown && (
                        <Button size="sm" onClick={() => onDrillDown(node.id)}>
                            <Users className="h-3 w-3 mr-1" />
                            Expand to Members
                        </Button>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
