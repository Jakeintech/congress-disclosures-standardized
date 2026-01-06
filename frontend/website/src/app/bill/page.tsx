'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { BillDetailClient } from '@/components/bills/bill-detail-client';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

function BillDetailContent() {
    const searchParams = useSearchParams();
    const billId = searchParams.get('id');

    if (!billId) {
        return (
            <Card>
                <CardContent className="pt-6 text-center">
                    <p className="text-muted-foreground">No bill ID specified</p>
                    <Button asChild className="mt-4">
                        <Link href="/bills">Browse Bills</Link>
                    </Button>
                </CardContent>
            </Card>
        );
    }

    return <BillDetailClient billId={billId} />;
}

export default function BillDetailPage() {
    return (
        <Suspense fallback={<div>Loading...</div>}>
            <BillDetailContent />
        </Suspense>
    );
}
