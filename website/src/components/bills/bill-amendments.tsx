'use client';

import { Badge } from '@/components/ui/badge';
import { DataContainer } from '@/components/ui/data-container';
import { useBillAmendments } from '@/hooks/use-api';
import { Amendment } from '@/types/api';
import { Users } from 'lucide-react';

interface BillAmendmentsProps {
    billId: string;
    initialData?: Amendment[];
}

export function BillAmendments({ billId, initialData }: BillAmendmentsProps) {
    const amendmentsQuery = useBillAmendments(billId);

    function formatDate(dateStr?: string): string {
        if (!dateStr) return '';
        try {
            return new Date(dateStr).toLocaleDateString('en-US', {
                year: 'numeric', month: 'short', day: 'numeric'
            });
        } catch {
            return dateStr;
        }
    }

    return (
        <DataContainer
            isLoading={amendmentsQuery.isLoading}
            isError={amendmentsQuery.isError}
            data={amendmentsQuery.data?.amendments || initialData}
            emptyMessage="No amendments proposed for this bill."
            onRetry={() => amendmentsQuery.refetch()}
        >
            {(amendments: Amendment[]) => (
                <div className="space-y-4">
                    {amendments.map((a, i) => (
                        <div key={i} className="p-5 bg-background rounded-xl border hover:border-primary/30 transition-all shadow-sm">
                            <div className="flex items-center justify-between mb-3">
                                <Badge className="font-mono text-[10px] uppercase">{a.type} {a.number}</Badge>
                                {a.latestAction?.actionDate && (
                                    <span className="text-[10px] text-muted-foreground uppercase font-semibold">
                                        Last action: {formatDate(a.latestAction.actionDate)}
                                    </span>
                                )}
                            </div>
                            <h4 className="font-semibold text-sm mb-2">{a.purpose}</h4>
                            <p className="text-sm text-muted-foreground leading-relaxed mb-4">{a.description}</p>

                            <div className="flex items-center justify-between pt-3 border-t">
                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                    <Users className="h-3.5 w-3.5" />
                                    <span>
                                        Sponsor: {a.sponsor?.name || `${a.sponsor?.firstName} ${a.sponsor?.lastName}`}
                                        {a.sponsor?.party && ` (${a.sponsor.party}-${a.sponsor.state})`}
                                    </span>
                                </div>
                                {a.latestAction?.text && (
                                    <Badge variant="outline" className="text-[9px] uppercase h-4">
                                        {a.latestAction.text.split(' ')[0]}
                                    </Badge>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </DataContainer>
    );
}
