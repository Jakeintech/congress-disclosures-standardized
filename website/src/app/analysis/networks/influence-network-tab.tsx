"use client"

import { InfluenceTracker } from '@/components/analysis/influence-tracker';
import { Network, Zap, ShieldAlert, Cpu } from 'lucide-react';

export default function InfluenceNetworkContent() {
    return (
        <div className="space-y-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div className="space-y-2">
                    <h2 className="text-3xl font-black tracking-tight">Influence Graph Tracking</h2>
                    <p className="text-muted-foreground text-lg max-w-2xl leading-relaxed">
                        Cross-correlating congressional stock trades with active legislation and lobbying filings to detect potential information asymmetry and policy influence.
                    </p>
                </div>
                <div className="hidden lg:flex items-center gap-4">
                    <div className="h-16 w-0.5 bg-border" />
                    <div className="flex flex-col">
                        <span className="text-2xl font-black text-primary font-mono tracking-tighter">AI-POWERED</span>
                        <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Detection Engine v2.1</span>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-primary/5 p-6 rounded-2xl border border-primary/10 space-y-3">
                    <div className="h-10 w-10 bg-primary/10 rounded-xl flex items-center justify-center">
                        <Zap className="h-5 w-5 text-primary" />
                    </div>
                    <h3 className="font-bold">Trade Correlation</h3>
                    <p className="text-sm text-muted-foreground">Matching trades to specific bill sponsorship and committee membership dates.</p>
                </div>
                <div className="bg-orange-500/5 p-6 rounded-2xl border border-orange-500/10 space-y-3">
                    <div className="h-10 w-10 bg-orange-500/10 rounded-xl flex items-center justify-center">
                        <Network className="h-5 w-5 text-orange-600" />
                    </div>
                    <h3 className="font-bold">Lobbying Linkage</h3>
                    <p className="text-sm text-muted-foreground">Detecting coordination between lobbying firm clients and congressional portfolios.</p>
                </div>
                <div className="bg-purple-600/5 p-6 rounded-2xl border border-purple-600/10 space-y-3">
                    <div className="h-10 w-10 bg-purple-600/10 rounded-xl flex items-center justify-center">
                        <ShieldAlert className="h-5 w-5 text-purple-600" />
                    </div>
                    <h3 className="font-bold">Alpha Detection</h3>
                    <p className="text-sm text-muted-foreground">Identifying trades that occur within the 'window of influence' before major votes.</p>
                </div>
            </div>

            <InfluenceTracker />
        </div>
    );
}
