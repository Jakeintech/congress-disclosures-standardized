import { Suspense } from 'react';
import { notFound } from 'next/navigation';
import { fetchBillDetail, fetchBills } from '@/lib/api';
import { BillHeader } from '@/components/bills/bill-header';
import { BillTabs } from '@/components/bills/bill-tabs';
import { Skeleton } from '@/components/ui/skeleton';

interface PageProps {
    params: Promise<{
        congress: string;
        type: string;
        number: string;
    }>;
}

// Generate static params for recent bills (subset for static build)
export async function generateStaticParams() {
    try {
        const bills = await fetchBills({ limit: 100, congress: 119 }); // Build for current congress
        return bills.map((bill: any) => ({
            congress: bill.congress.toString(),
            type: bill.bill_type.toLowerCase(),
            number: bill.bill_number.toString(),
        }));
    } catch (e) {
        console.error("Failed to generate static params for bills", e);
        // Fallback for build robustness
        return [
            { congress: "119", type: "sconres", number: "23" },
            { congress: "119", type: "hr", number: "1" }
        ];
    }
}

async function BillContent({ params }: { params: { congress: string; type: string; number: string } }) {
    const { congress, type, number } = params;
    const billId = `${congress}-${type}-${number}`;

    try {
        const data = await fetchBillDetail(billId);

        if (!data || !data.bill) {
            return notFound();
        }

        return (
            <div className="space-y-8 pb-12">
                <BillHeader
                    bill={data.bill}
                    sponsor={data.sponsor}
                />

                <BillTabs
                    bill={data.bill}
                    textVersions={data.text_versions}
                    cosponsorsCount={data.cosponsors_count}
                    actionsCount={data.actions_count_total}
                    billId={billId}
                    actions={data.actions}
                    cosponsors={data.cosponsors}
                    industryTags={data.industry_tags}
                    tradeCorrelations={data.trade_correlations}
                    summary={data.summary}
                    committees={data.committees}
                    relatedBills={data.related_bills}
                    subjects={data.subjects}
                    titles={data.titles}
                />
            </div>
        );
    } catch (e) {
        console.error("Failed to load bill", e); // Logic to handle error or 404
        return (
            <div className="pt-12 text-center">
                <h2 className="text-xl font-bold text-red-500">Failed to load bill</h2>
                <p className="text-muted-foreground">Could not fetch details for {billId}</p>
            </div>
        );
    }
}

export default async function BillPage(props: PageProps) {
    const params = await props.params;

    return (
        <Suspense fallback={<div className="space-y-6">
            <Skeleton className="h-12 w-2/3" />
            <Skeleton className="h-8 w-1/3" />
            <Skeleton className="h-64 w-full" />
        </div>}>
            <BillContent params={params} />
        </Suspense>
    );
}
