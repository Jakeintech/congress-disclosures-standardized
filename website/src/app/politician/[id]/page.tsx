import { Suspense } from 'react';
import { PoliticianDashboard } from '@/components/politicians/politician-dashboard';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { fetchMembers } from '@/lib/api';

// Generate static params for all members at build time
export async function generateStaticParams() {
    try {
        const members = await fetchMembers({ limit: 1000 }); // Fetch all members
        return members.map((member: { bioguide_id: string; name: string }) => ({
            id: member.bioguide_id,
        }));
    } catch (error) {
        console.error("Failed to generate static params for politicians:", error);
        return [];
    }
}

interface PageProps {
    params: {
        id: string;
    };
}

function PoliticianContent({ id }: { id: string }) {
    const bioguideId = id; // The ID from the URL is the bioguideId

    if (!bioguideId) {
        return (
            <Card>
                <CardContent className="pt-6 text-center">
                    <p className="text-muted-foreground">Invalid politician ID</p>
                    <Button asChild className="mt-4">
                        <Link href="/members">Browse Members</Link>
                    </Button>
                </CardContent>
            </Card>
        );
    }

    return <PoliticianDashboard bioguideId={bioguideId} />;
}

export default function PoliticianPage({ params }: PageProps) {
    return (
        <Suspense fallback={<div>Loading...</div>}>
            <PoliticianContent id={params.id} />
        </Suspense>
    );
}
