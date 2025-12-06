'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { MemberProfileClient } from '@/components/members/member-profile-client';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

function MemberProfileContent() {
    const searchParams = useSearchParams();
    const bioguideId = searchParams.get('id');

    if (!bioguideId) {
        return (
            <Card>
                <CardContent className="pt-6 text-center">
                    <p className="text-muted-foreground">No member ID specified</p>
                    <Button asChild className="mt-4">
                        <Link href="/members">Browse Members</Link>
                    </Button>
                </CardContent>
            </Card>
        );
    }

    return <MemberProfileClient bioguideId={bioguideId} />;
}

export default function MemberProfilePage() {
    return (
        <Suspense fallback={<div>Loading...</div>}>
            <MemberProfileContent />
        </Suspense>
    );
}
