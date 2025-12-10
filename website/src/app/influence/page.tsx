'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';

export default function InfluencePage() {
    const router = useRouter();

    useEffect(() => {
        // Redirect to new location
        router.replace('/analysis/influence');
    }, [router]);

    return (
        <div className="flex items-center justify-center min-h-[60vh]">
            <Card>
                <CardContent className="p-8 text-center">
                    <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
                    <p className="text-muted-foreground">Redirecting to Influence Tracker...</p>
                </CardContent>
            </Card>
        </div>
    );
}
