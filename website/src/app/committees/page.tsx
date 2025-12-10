'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Construction } from 'lucide-react';

export default function CommitteesPage() {
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Congressional Committees</h1>
                <p className="text-muted-foreground mt-2">
                    Explore House and Senate committees, subcommittees, and their legislative activities
                </p>
            </div>

            <Alert>
                <Construction className="h-4 w-4" />
                <AlertTitle>Page Under Construction</AlertTitle>
                <AlertDescription>
                    The committees explorer is being built with Congress.gov integration.
                    Check back soon for committee rosters, bills referred, hearings, and reports.
                </AlertDescription>
            </Alert>

            <Card>
                <CardHeader>
                    <CardTitle>Planned Features</CardTitle>
                    <CardDescription>
                        Committee data integration in progress
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <ul className="space-y-2 list-disc list-inside">
                        <li>House and Senate committee directory</li>
                        <li>Committee membership with member photos</li>
                        <li>Bills referred to each committee</li>
                        <li>Committee reports and publications</li>
                        <li>Hearing schedules and transcripts</li>
                        <li>Subcommittee structure</li>
                        <li>Committee voting records</li>
                        <li>Trading activity by committee members</li>
                    </ul>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle>API Integration Required</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                    <p>This page requires the following API endpoints to be implemented:</p>
                    <ul className="mt-2 space-y-1 list-disc list-inside">
                        <li><code>/v1/congress/committees</code> - List all committees</li>
                        <li><code>/v1/congress/committees/[code]</code> - Committee details</li>
                        <li><code>/v1/congress/committees/[code]/bills</code> - Bills referred</li>
                        <li><code>/v1/congress/committees/[code]/members</code> - Committee roster</li>
                    </ul>
                    <p className="mt-4">These endpoints will proxy to Congress.gov API and cache results.</p>
                </CardContent>
            </Card>
        </div>
    );
}
