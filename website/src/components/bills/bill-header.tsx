import { Badge } from '@/components/ui/badge';
import Link from 'next/link';

interface BillHeaderProps {
    bill: {
        congress: number;
        bill_type: string;
        bill_number: string;
        title: string;
        latest_action_date?: string;
        latest_action_text?: string;
    };
    sponsor?: {
        bioguide_id?: string;
        name?: string;
        party?: string;
        state?: string;
    };
}

export function BillHeader({ bill, sponsor }: BillHeaderProps) {
    const typeLabel = bill.bill_type.toUpperCase();
    const numberLabel = bill.bill_number;

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span>{bill.congress}th Congress</span>
                <span>•</span>
                <span className="uppercase">{bill.bill_type}</span>
            </div>

            <h1 className="text-3xl font-bold tracking-tight">
                {typeLabel} {numberLabel}: {bill.title}
            </h1>

            <div className="flex flex-wrap items-center gap-6 text-sm">
                {/* Sponsor */}
                <div className="flex items-center gap-2">
                    <span className="font-semibold text-muted-foreground">Sponsor:</span>
                    {sponsor?.bioguide_id ? (
                        <Link href={`/politician/${sponsor.name}-${sponsor.bioguide_id}`} className="flex items-center gap-1 hover:underline text-primary">
                            {sponsor.name}
                            <span className="text-muted-foreground">
                                ({sponsor.party}-{sponsor.state})
                            </span>
                        </Link>
                    ) : (
                        <span>{sponsor?.name || 'Unknown'}</span>
                    )}
                </div>

                {/* Latest Action */}
                <div className="flex items-center gap-2">
                    <span className="font-semibold text-muted-foreground">Latest Action:</span>
                    <span>{bill.latest_action_text || 'No recent action'}</span>
                    {bill.latest_action_date && (
                        <span className="text-muted-foreground">
                            ({new Date(bill.latest_action_date).toLocaleDateString()})
                        </span>
                    )}
                </div>

                {/* Status Badge (Placeholder logic) */}
                <Badge variant="outline">Introduced</Badge>
            </div>
        </div>
    );
}
