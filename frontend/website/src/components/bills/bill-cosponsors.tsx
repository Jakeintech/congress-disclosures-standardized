'use client';

import { Badge } from '@/components/ui/badge';
import { DataContainer } from '@/components/ui/data-container';
import { useBillCosponsors } from '@/hooks/use-api';
import { Cosponsor as CosponsorType } from '@/types/api';
import Link from 'next/link';

interface BillCosponsorsProps {
    billId: string;
    initialData?: CosponsorType[];
}

export function BillCosponsors({ billId, initialData }: BillCosponsorsProps) {
    const cosponsorsQuery = useBillCosponsors(billId);

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
            isLoading={cosponsorsQuery.isLoading}
            isError={cosponsorsQuery.isError}
            data={cosponsorsQuery.data?.cosponsors || initialData}
            emptyMessage="No cosponsors found for this bill."
            onRetry={() => cosponsorsQuery.refetch()}
        >
            {(cosponsors: CosponsorType[]) => (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {cosponsors.map((c, i) => (
                        <div key={i} className="flex items-center gap-3 p-3 bg-background rounded-xl border hover:border-primary/30 transition-colors group">
                            <div className={`w-10 h-10 flex items-center justify-center rounded-full font-bold text-white shadow-sm shrink-0 ${c.party === 'R' ? 'bg-red-500' : c.party === 'D' ? 'bg-blue-500' : 'bg-gray-500'
                                }`}>
                                {c.party?.[0] || '?'}
                            </div>
                            <div className="min-w-0 flex-1">
                                <Link href={`/politician/${c.bioguideId}`} className="font-semibold truncate text-sm hover:text-primary transition-colors block">
                                    {c.name}
                                </Link>
                                <div className="text-[10px] text-muted-foreground uppercase tracking-tight flex items-center gap-1">
                                    <Badge variant="outline" className="h-3.5 px-1 text-[9px]">{c.state}-{c.party}</Badge>
                                    <span>Joined {formatDate(c.sponsorshipDate)}</span>
                                    {c.isOriginalCosponsor && (
                                        <Badge variant="secondary" className="h-3.5 px-1 text-[9px] bg-amber-500/10 text-amber-600 border-none">Original</Badge>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </DataContainer>
    );
}
