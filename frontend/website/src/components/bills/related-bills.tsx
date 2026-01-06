'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { DataContainer } from '@/components/ui/data-container';
import { useBillRelated } from '@/hooks/use-api';
import { RelatedBill as RelatedBillType } from '@/types/api';
import { Link as LinkIcon } from 'lucide-react';
import Link from 'next/link';

interface RelatedBillsProps {
    billId: string;
    initialData?: RelatedBillType[];
}

export function RelatedBills({ billId, initialData }: RelatedBillsProps) {
    const relatedQuery = useBillRelated(billId);

    return (
        <DataContainer
            isLoading={relatedQuery.isLoading}
            isError={relatedQuery.isError}
            data={relatedQuery.data?.relatedBills || initialData}
            emptyMessage="No related legislation found."
            onRetry={() => relatedQuery.refetch()}
        >
            {(related: RelatedBillType[]) => (
                <div className="grid gap-3">
                    {related.map((r, i) => (
                        <div key={i} className="p-4 bg-background rounded-xl border hover:border-primary/30 transition-all flex items-start justify-between gap-4 group">
                            <div className="min-w-0">
                                <div className="flex flex-wrap items-center gap-2 mb-1">
                                    <Badge variant="outline" className="font-mono text-[10px] uppercase">
                                        {r.congress}th-{r.type || (r as any).bill_type}-{r.number || (r as any).bill_number}
                                    </Badge>
                                    <Badge variant="secondary" className="text-[10px] text-primary font-bold uppercase tracking-wider h-4">
                                        {r.relationshipType || (r as any).relationship_type}
                                    </Badge>
                                </div>
                                <h4 className="text-sm font-semibold truncate group-hover:text-primary transition-colors">
                                    {r.title}
                                </h4>
                                {r.latestAction?.actionDate && (
                                    <p className="text-[10px] text-muted-foreground mt-1">
                                        Latest Action: {r.latestAction.text} ({new Date(r.latestAction.actionDate).toLocaleDateString()})
                                    </p>
                                )}
                            </div>
                            <Button variant="ghost" size="icon" className="shrink-0 h-8 w-8" asChild>
                                <Link href={`/bills/${r.congress}/${r.type || (r as any).bill_type}/${r.number || (r as any).bill_number}`}>
                                    <LinkIcon className="h-4 w-4" />
                                </Link>
                            </Button>
                        </div>
                    ))}
                </div>
            )}
        </DataContainer>
    );
}
