'use client';

import { Badge } from '@/components/ui/badge';
import { DataContainer } from '@/components/ui/data-container';
import { useBillActions } from '@/hooks/use-api';
import { BillAction as BillActionType } from '@/types/api';

interface BillActionsProps {
    billId: string;
    initialData?: BillActionType[];
}

export function BillActions({ billId, initialData }: BillActionsProps) {
    const actionsQuery = useBillActions(billId);

    function formatDate(dateStr: string): string {
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
            isLoading={actionsQuery.isLoading}
            isError={actionsQuery.isError}
            data={(actionsQuery.data as any)?.actions || initialData}
            emptyMessage="No legislative actions found for this bill."
            onRetry={() => actionsQuery.refetch()}
        >
            {(actions: BillActionType[]) => (
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <h3 className="text-lg font-semibold flex items-center gap-2">
                            Legislative History
                            <Badge variant="secondary" className="text-xs">{actions.length}</Badge>
                        </h3>
                    </div>
                    <div className="bg-background rounded-xl border overflow-hidden">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b bg-muted/50">
                                    <th className="text-left py-3 px-4 font-semibold w-32 text-muted-foreground">Date</th>
                                    <th className="text-left py-3 px-4 font-semibold text-muted-foreground">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y">
                                {actions.map((action, i) => (
                                    <tr key={i} className="hover:bg-accent/5 transition-colors">
                                        <td className="py-3 px-4 text-muted-foreground font-mono text-xs">
                                            {formatDate(action.action_date)}
                                        </td>
                                        <td className="py-3 px-4 leading-relaxed">
                                            <div className="flex flex-col gap-1">
                                                {action.action_text}
                                                {action.action_code && (
                                                    <Badge variant="outline" className="w-fit text-[10px] h-4 uppercase">
                                                        {action.action_code.replace(/_/g, ' ')}
                                                    </Badge>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </DataContainer>
    );
}
