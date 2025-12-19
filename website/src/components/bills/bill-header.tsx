import { Badge } from '@/components/ui/badge';
import Link from 'next/link';
import { type Bill, type Sponsor } from '@/types/api';
import { Calendar, User, FileText, ExternalLink, BarChart3 } from 'lucide-react';

interface BillHeaderProps {
    bill: Bill;
    sponsor?: Sponsor;
}

export function BillHeader({ bill, sponsor }: BillHeaderProps) {
    const typeLabel = bill.bill_type.toUpperCase();
    const numberLabel = bill.bill_number;

    return (
        <div className="space-y-6">
            <div className="flex flex-wrap items-center gap-2 text-sm font-medium text-muted-foreground">
                <Badge variant="secondary" className="font-mono">
                    {bill.congress}th Congress
                </Badge>
                <span className="text-muted-foreground/30">•</span>
                <span className="uppercase flex items-center gap-1">
                    <FileText className="h-3.5 w-3.5" />
                    {bill.bill_type}
                </span>
            </div>

            <div className="space-y-2">
                <h1 className="text-3xl font-bold tracking-tight leading-tight">
                    {typeLabel} {numberLabel}: {bill.title}
                </h1>
                {bill.congress_gov_url && (
                    <a
                        href={bill.congress_gov_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-primary flex items-center gap-1 hover:underline w-fit"
                    >
                        View on Congress.gov <ExternalLink className="h-3 w-3" />
                    </a>
                )}
            </div>

            <div className="flex flex-wrap items-center gap-y-4 gap-x-8 text-sm">
                {/* Sponsor */}
                <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                        <User className="h-4 w-4" />
                    </div>
                    <div className="flex flex-col">
                        <span className="text-[10px] uppercase font-bold text-muted-foreground leading-none mb-1">Sponsor</span>
                        {sponsor?.bioguide_id ? (
                            <Link href={`/politician/${sponsor.bioguide_id}`} className="font-medium hover:text-primary transition-colors">
                                {sponsor.name}
                                <span className="ml-1 text-muted-foreground font-normal">({sponsor.party}-{sponsor.state})</span>
                            </Link>
                        ) : (
                            <span className="font-medium">{sponsor?.name || 'Multiple/Unknown'}</span>
                        )}
                    </div>
                </div>

                {/* Latest Action */}
                <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded-full bg-amber-500/10 flex items-center justify-center text-amber-600">
                        <Calendar className="h-4 w-4" />
                    </div>
                    <div className="flex flex-col">
                        <span className="text-[10px] uppercase font-bold text-muted-foreground leading-none mb-1">Latest Action</span>
                        <div className="flex items-baseline gap-2">
                            <span className="font-medium line-clamp-1 max-w-[300px]" title={bill.latest_action_text}>
                                {bill.latest_action_text || 'Introduced'}
                            </span>
                            {bill.latest_action_date && (
                                <span className="text-xs text-muted-foreground whitespace-nowrap">
                                    {new Date(bill.latest_action_date).toLocaleDateString('en-US', {
                                        month: 'short', day: 'numeric', year: 'numeric'
                                    })}
                                </span>
                            )}
                        </div>
                    </div>
                </div>

                {/* Status Badge */}
                <Badge className="ml-auto bg-green-500/10 text-green-600 hover:bg-green-500/20 border-green-200 shadow-none">
                    Active
                </Badge>
            </div>

            {/* Trade Alerts */}
            {(bill.trade_correlations_count ?? 0) > 0 && (
                <div className="rounded-lg border-l-4 border-l-amber-500 bg-amber-500/5 p-4 flex items-start gap-3">
                    <div className="mt-1 h-5 w-5 rounded-full bg-amber-500/20 flex items-center justify-center text-amber-600 shrink-0">
                        <BarChart3 className="h-3 w-3" />
                    </div>
                    <div>
                        <h4 className="text-sm font-semibold text-amber-900 dark:text-amber-200">Trade Activity Detected</h4>
                        <p className="text-xs text-amber-800/80 dark:text-amber-300/80 mt-1">
                            {bill.trade_correlations_count} legislator{bill.trade_correlations_count !== 1 ? 's' : ''} traded related stocks within 90 days of this bill's activity.
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}
