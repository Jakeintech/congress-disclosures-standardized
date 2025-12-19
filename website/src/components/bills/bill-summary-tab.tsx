'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { DataContainer } from '@/components/ui/data-container';
import { useBillSummaries } from '@/hooks/use-api';
import { BillSummary as BillSummaryType } from '@/types/api';

interface BillSummaryProps {
    billId: string;
    initialData?: BillSummaryType;
}

export function BillSummary({ billId, initialData }: BillSummaryProps) {
    const summaryQuery = useBillSummaries(billId);

    return (
        <DataContainer
            isLoading={summaryQuery.isLoading}
            isError={summaryQuery.isError}
            data={summaryQuery.data?.summary || initialData}
            emptyMessage="No official summary available for this bill yet."
            onRetry={() => summaryQuery.refetch()}
        >
            {(summary: BillSummaryType) => (
                <Card className="border-none shadow-none bg-accent/5">
                    <CardHeader className="px-0 pt-0">
                        <CardTitle className="text-lg">Official Summary</CardTitle>
                        <CardDescription>
                            Provided by the Congressional Research Service (CRS)
                            {summary.actionDate && ` as of ${new Date(summary.actionDate).toLocaleDateString()}`}
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="px-0">
                        <div className="prose prose-sm dark:prose-invert max-w-none text-foreground/80 leading-relaxed whitespace-pre-wrap bg-background p-6 rounded-xl border shadow-sm">
                            {summary.text || (summary as any).summary || <span className="italic text-muted-foreground">Summary text empty.</span>}
                        </div>
                    </CardContent>
                </Card>
            )}
        </DataContainer>
    );
}
