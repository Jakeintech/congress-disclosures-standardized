'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import Link from 'next/link';
import { fetchMemberTrades, fetchMemberAssets } from '@/lib/api';

// Helper to format large numbers
const formatCurrency = (val: number) => {
    if (val === 0) return 'N/A';
    if (val >= 1000000) return `$${(val / 1000000).toFixed(2)}M`;
    if (val >= 1000) return `$${(val / 1000).toFixed(2)}K`;
    return `$${val.toFixed(2)}`;
};

interface PoliticianHeaderProps {
    member: {
        bioguide_id: string;
        name: string;
        party: string;
        state: string;
        district?: string;
        chamber?: string;
    };
}

export function PoliticianHeader({ member }: PoliticianHeaderProps) {
    const [netWorth, setNetWorth] = useState<number | null>(null);
    const [volume, setVolume] = useState<number | null>(null);
    const [totalTrades, setTotalTrades] = useState<number>(0);
    const [lastTraded, setLastTraded] = useState<string>('N/A');

    useEffect(() => {
        async function loadStats() {
            if (!member?.bioguide_id) return;

            try {
                // 1. Calculate Volume & Trades
                const trades = await fetchMemberTrades(member.bioguide_id, 1000);
                setTotalTrades(trades.length);
                if (trades.length > 0) {
                    setLastTraded(new Date(trades[0].transaction_date).toLocaleDateString());

                    let vol = 0;
                    trades.forEach((t: any) => {
                        if (t.amount) {
                            const clean = t.amount.replace(/[$,]/g, '');
                            const parts = clean.split('-');
                            if (parts.length > 1) {
                                vol += (parseFloat(parts[0]) + parseFloat(parts[1])) / 2;
                            } else {
                                vol += parseFloat(parts[0]);
                            }
                        }
                    });
                    setVolume(vol);
                } else {
                    setVolume(0);
                }

                // 2. Calculate Net Worth from Assets
                const assets = await fetchMemberAssets(member.bioguide_id);
                let nw = 0;
                let hasAssets = false;

                if (Array.isArray(assets)) {
                    assets.forEach((a: any) => {
                        let val = 0;
                        if (a.asset_value) {
                            val = parseFloat(a.asset_value);
                        } else if (a.asset_value_range) {
                            const clean = a.asset_value_range.replace(/[$,]/g, '');
                            const parts = clean.split('-');
                            if (parts.length > 1) {
                                val = (parseFloat(parts[0]) + parseFloat(parts[1])) / 2;
                            } else {
                                val = parseFloat(parts[0]);
                            }
                        }
                        if (!isNaN(val)) {
                            nw += val;
                            hasAssets = true;
                        }
                    });
                }

                setNetWorth(hasAssets ? nw : 0);

            } catch (e) {
                console.error("Stats error", e);
            }
        }
        loadStats();
    }, [member]);

    return (
        <Card className="overflow-hidden">
            <CardContent className="p-0">
                <div className="flex flex-col md:flex-row items-stretch">
                    {/* Left: Profile Info */}
                    <div className="p-8 flex flex-col items-center justify-center border-b md:border-b-0 md:border-r md:w-1/3 bg-muted/10">
                        <div className="w-32 h-32 rounded-full bg-gray-200 mb-4 overflow-hidden border-4 border-background shadow-sm flex items-center justify-center text-4xl font-bold text-gray-400">
                            {member.name.charAt(0)}
                        </div>
                        <h1 className="text-2xl font-bold text-center">{member.name}</h1>
                        <p className="text-muted-foreground text-center mb-6">
                            {member.party === 'D' ? 'Democrat' : member.party === 'R' ? 'Republican' : member.party} / {member.state} {member.district ? `/ District ${member.district}` : ''}
                        </p>

                        <div className="grid grid-cols-2 gap-8 w-full max-w-xs text-center">
                            <div>
                                <p className="text-2xl font-bold">{netWorth !== null ? formatCurrency(netWorth) : 'N/A'}</p>
                                <p className="text-xs text-muted-foreground uppercase tracking-wide">Net Worth Est.</p>
                            </div>
                            <div>
                                <p className="text-2xl font-bold">{volume !== null ? formatCurrency(volume) : 'N/A'}</p>
                                <p className="text-xs text-muted-foreground uppercase tracking-wide">Trade Volume</p>
                            </div>
                            <div>
                                <p className="text-xl font-bold">{totalTrades}</p>
                                <p className="text-xs text-muted-foreground uppercase tracking-wide">Total Trades</p>
                            </div>
                            <div>
                                <p className="text-xl font-bold">{lastTraded}</p>
                                <p className="text-xs text-muted-foreground uppercase tracking-wide">Last Traded</p>
                            </div>
                        </div>

                        <div className="w-full mt-8 space-y-2">
                            <div className="flex justify-between text-sm border-b pb-2">
                                <span className="text-muted-foreground">Current Member</span>
                                <span className="text-emerald-500 font-medium">Yes</span>
                            </div>
                            <div className="flex justify-between text-sm border-b pb-2">
                                <span className="text-muted-foreground">Years Active</span>
                                <span>-</span>
                            </div>
                        </div>
                    </div>

                    {/* Right: Navigation */}
                    <div className="flex-1 p-6">
                        <div className="grid grid-cols-3 gap-4 mb-4">
                            <Link href="#" className="flex items-center justify-center py-3 bg-muted/20 hover:bg-muted/40 rounded-md text-sm font-medium border border-border">Trades</Link>
                            <Link href="#" className="flex items-center justify-center py-3 bg-muted/10 hover:bg-muted/30 rounded-md text-sm font-medium text-muted-foreground">Live Stock Portfolio</Link>
                            <Link href="#" className="flex items-center justify-center py-3 bg-muted/10 hover:bg-muted/30 rounded-md text-sm font-medium text-muted-foreground">Net Worth</Link>
                        </div>
                        <div className="flex items-center justify-center h-48 bg-muted/5 rounded-lg border border-dashed text-muted-foreground">
                            Politician Analytics Dashboard
                        </div>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
