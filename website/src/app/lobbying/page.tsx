'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

export default function LobbyingPage() {
    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Lobbying Explorer</h1>
                <p className="text-muted-foreground">
                    Explore lobbying activity, clients, and their connections to legislation
                </p>
            </div>

            {/* Feature Cards */}
            <div className="grid gap-6 md:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <span className="text-2xl">🕸️</span>
                            Network Visualization
                        </CardTitle>
                        <CardDescription>
                            Interactive graph showing connections between members, clients, and bills
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Button asChild className="w-full">
                            <Link href="/lobbying/network">Open Network Graph</Link>
                        </Button>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <span className="text-2xl">⚡</span>
                            Influence Tracker
                        </CardTitle>
                        <CardDescription>
                            Trade-Bill-Lobbying correlation analysis with scoring
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Button asChild className="w-full">
                            <Link href="/influence">Open Influence Tracker</Link>
                        </Button>
                    </CardContent>
                </Card>
            </div>

            {/* Coming Soon */}
            <Card className="border-dashed">
                <CardHeader>
                    <CardTitle>Coming Soon</CardTitle>
                    <CardDescription>
                        Additional lobbying features in development
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <ul className="space-y-2 text-muted-foreground">
                        <li>📊 Top lobbying clients by spend</li>
                        <li>📋 Searchable filings database</li>
                        <li>🔍 Issue code analytics</li>
                        <li>👤 Lobbyist profiles with revolving door tracking</li>
                    </ul>
                </CardContent>
            </Card>
        </div>
    );
}
