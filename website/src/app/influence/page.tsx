'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Construction } from 'lucide-react';

export default function InfluencePage() {
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Influence Tracker</h1>
                <p className="text-muted-foreground">
                    Track correlations between congressional trades, bills, and lobbying activity
                </p>
            </div>

            <Alert>
                <Construction className="h-4 w-4" />
                <AlertTitle>Page Under Construction</AlertTitle>
                <AlertDescription>
                    The Influence Tracker is being updated with new data models and improved correlation algorithms.
                    Check back soon for comprehensive analysis of trade-bill-lobbying connections.
                </AlertDescription>
            </Alert>

            <Card>
                <CardHeader>
                    <CardTitle>What We're Building</CardTitle>
                    <CardDescription>
                        Advanced features coming soon
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <ul className="space-y-2 list-disc list-inside">
                        <li>Triple correlation analysis (trades + bills + lobbying)</li>
                        <li>Interactive timeline of related activities</li>
                        <li>Network visualization of connections</li>
                        <li>Automated pattern detection</li>
                        <li>Downloadable reports</li>
                    </ul>
                </CardContent>
            </Card>
        </div>
    );
}
