"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, AlertCircle, Info, ShieldAlert } from "lucide-react";
import { useState, useEffect } from "react";

interface ConflictData {
    member_bioguide_id: string;
    member_name?: string;
    bill_id: string;
    bill_title?: string;
    ticker: string;
    transaction_type: string;
    trade_date: string;
    conflict_score: number;
    severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
    days_offset: number;
    trade_industry?: string;
    amount_display?: string;
}

interface ConflictSummary {
    critical_count: number;
    high_count: number;
    medium_count: number;
    low_count: number;
}

interface ConflictDetectionCardProps {
    severity?: 'all' | 'critical' | 'high' | 'medium' | 'low';
    limit?: number;
    apiBase?: string;
    showSummary?: boolean;
}

export function ConflictDetectionCard({
    severity = 'all',
    limit = 10,
    apiBase = process.env.NEXT_PUBLIC_API_URL || '',
    showSummary = true
}: ConflictDetectionCardProps) {
    const [conflicts, setConflicts] = useState<ConflictData[]>([]);
    const [summary, setSummary] = useState<ConflictSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function fetchData() {
            try {
                setLoading(true);
                const response = await fetch(
                    `${apiBase}/v1/analytics/conflicts?severity=${severity}&limit=${limit}`
                );

                if (!response.ok) throw new Error('Failed to fetch conflict data');

                const result = await response.json();
                setConflicts(result.conflicts || []);
                setSummary(result.summary || null);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Unknown error');
            } finally {
                setLoading(false);
            }
        }

        fetchData();
    }, [severity, limit, apiBase]);

    const getSeverityIcon = (sev: string) => {
        switch (sev) {
            case 'CRITICAL':
                return <ShieldAlert className="h-5 w-5 text-red-600" />;
            case 'HIGH':
                return <AlertTriangle className="h-5 w-5 text-orange-500" />;
            case 'MEDIUM':
                return <AlertCircle className="h-5 w-5 text-yellow-500" />;
            default:
                return <Info className="h-5 w-5 text-blue-500" />;
        }
    };

    const getSeverityBadge = (sev: string) => {
        const variants: Record<string, string> = {
            'CRITICAL': 'bg-red-600 text-white',
            'HIGH': 'bg-orange-500 text-white',
            'MEDIUM': 'bg-yellow-500 text-black',
            'LOW': 'bg-blue-500 text-white'
        };
        return (
            <Badge className={variants[sev] || 'bg-gray-500'}>
                {sev}
            </Badge>
        );
    };

    const formatScore = (score: number) => {
        return `${score}/100`;
    };

    if (loading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <ShieldAlert className="h-5 w-5" />
                        Conflict Detection
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center justify-center py-8">
                        <div className="animate-pulse text-muted-foreground">Analyzing conflicts...</div>
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (error) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Conflict Detection</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="text-destructive py-4">Error: {error}</div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <ShieldAlert className="h-5 w-5" />
                    Conflict of Interest Detection
                </CardTitle>
                <CardDescription>
                    Potential conflicts between trading and legislative activity
                </CardDescription>
            </CardHeader>
            <CardContent>
                {/* Summary Stats */}
                {showSummary && summary && (
                    <div className="grid grid-cols-4 gap-2 mb-4">
                        <div className="text-center p-2 rounded bg-red-50 dark:bg-red-950">
                            <div className="text-2xl font-bold text-red-600">{summary.critical_count}</div>
                            <div className="text-xs text-muted-foreground">Critical</div>
                        </div>
                        <div className="text-center p-2 rounded bg-orange-50 dark:bg-orange-950">
                            <div className="text-2xl font-bold text-orange-500">{summary.high_count}</div>
                            <div className="text-xs text-muted-foreground">High</div>
                        </div>
                        <div className="text-center p-2 rounded bg-yellow-50 dark:bg-yellow-950">
                            <div className="text-2xl font-bold text-yellow-600">{summary.medium_count}</div>
                            <div className="text-xs text-muted-foreground">Medium</div>
                        </div>
                        <div className="text-center p-2 rounded bg-blue-50 dark:bg-blue-950">
                            <div className="text-2xl font-bold text-blue-500">{summary.low_count}</div>
                            <div className="text-xs text-muted-foreground">Low</div>
                        </div>
                    </div>
                )}

                {/* Conflict List */}
                <div className="space-y-3">
                    {conflicts.length === 0 ? (
                        <div className="text-center text-muted-foreground py-8">
                            No conflicts detected
                        </div>
                    ) : (
                        conflicts.map((conflict, idx) => (
                            <div
                                key={idx}
                                className="p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                            >
                                <div className="flex items-start justify-between gap-3">
                                    <div className="flex items-start gap-3">
                                        {getSeverityIcon(conflict.severity)}
                                        <div>
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <span className="font-medium">
                                                    {conflict.member_name || conflict.member_bioguide_id}
                                                </span>
                                                {getSeverityBadge(conflict.severity)}
                                                <span className="text-sm text-muted-foreground">
                                                    Score: {formatScore(conflict.conflict_score)}
                                                </span>
                                            </div>
                                            <div className="text-sm mt-1">
                                                <span className="font-mono bg-muted px-1 rounded">{conflict.ticker}</span>
                                                <span className="mx-2">•</span>
                                                <span>{conflict.transaction_type}</span>
                                                {conflict.amount_display && (
                                                    <>
                                                        <span className="mx-2">•</span>
                                                        <span>{conflict.amount_display}</span>
                                                    </>
                                                )}
                                            </div>
                                            <div className="text-xs text-muted-foreground mt-1">
                                                {conflict.bill_id}
                                                {conflict.bill_title && `: ${conflict.bill_title.substring(0, 60)}...`}
                                            </div>
                                            <div className="text-xs text-muted-foreground">
                                                Trade: {conflict.trade_date} •
                                                {Math.abs(conflict.days_offset)} days {conflict.days_offset > 0 ? 'before' : 'after'} bill action
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
