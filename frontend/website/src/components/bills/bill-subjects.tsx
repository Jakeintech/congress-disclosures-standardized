'use client';

import { Badge } from '@/components/ui/badge';
import { DataContainer } from '@/components/ui/data-container';
import { useBillSubjects } from '@/hooks/use-api';
import { Subject } from '@/types/api';

interface BillSubjectsProps {
    billId: string;
    initialData?: Subject[];
}

export function BillSubjects({ billId, initialData }: BillSubjectsProps) {
    const subjectsQuery = useBillSubjects(billId);

    return (
        <DataContainer
            isLoading={subjectsQuery.isLoading}
            isError={subjectsQuery.isError}
            data={subjectsQuery.data?.subjects || initialData}
            emptyMessage="No legislative subjects found."
            onRetry={() => subjectsQuery.refetch()}
        >
            {(subjects: Subject[]) => (
                <div className="flex flex-wrap gap-2 p-6 bg-background rounded-xl border">
                    {subjects.map((s, i) => (
                        <Badge key={i} variant="secondary" className="px-4 py-1.5 rounded-full font-normal shadow-sm hover:bg-secondary/80 transition-colors">
                            {typeof s === 'string' ? s : s.name}
                        </Badge>
                    ))}
                </div>
            )}
        </DataContainer>
    );
}
