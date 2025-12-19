'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { fetchMemberProfile } from '@/lib/api';
import { PoliticianHeader } from './politician-header';
import { TradeVolumeChart } from './trade-volume-chart';
import { SectorPieChart } from './sector-pie-chart';
import { RecentTradesTable } from './recent-trades-table';
import { MemberAssociationGraph } from '../analysis/member-association-graph';

interface PoliticianDashboardProps {
    bioguideId: string;
}

export function PoliticianDashboard({ bioguideId }: PoliticianDashboardProps) {
    const [member, setMember] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadData() {
            setLoading(true);
            try {
                const data = await fetchMemberProfile(bioguideId);
                setMember(data);
            } catch (err) {
                console.error(err);
                setError('Failed to load politician profile');
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, [bioguideId]);

    if (loading) {
        return <div className="space-y-6 pt-6">
            <Skeleton className="h-48 w-full" />
            <div className="grid gap-6 md:grid-cols-2">
                <Skeleton className="h-64" />
                <Skeleton className="h-64" />
            </div>
        </div>;
    }

    if (error || !member) {
        return <div className="pt-6 text-center text-red-500">{error || 'Member not found'}</div>;
    }

    const memberName = `${member.name || (member.first_name + ' ' + member.last_name)}`;

    return (
        <div className="space-y-6 pb-12">
            {/* Header Section */}
            <PoliticianHeader member={member} />

            <Tabs defaultValue="overview" className="w-full">
                <TabsList className="grid w-full grid-cols-2 lg:w-[400px]">
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="network">Association Network</TabsTrigger>
                </TabsList>

                <TabsContent value="overview" className="space-y-6 mt-6">
                    {/* Main Content Grid */}
                    <div className="grid gap-6 lg:grid-cols-3">
                        {/* Left Column: Charts */}
                        <div className="lg:col-span-2 space-y-6">
                            <Card>
                                <CardHeader>
                                    <div className="flex items-center justify-between">
                                        <CardTitle>Trade Volume by Year</CardTitle>
                                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                            <span className="flex items-center gap-1"><div className="w-3 h-3 bg-emerald-500 rounded-sm" /> Buy</span>
                                            <span className="flex items-center gap-1"><div className="w-3 h-3 bg-orange-500 rounded-sm" /> Sell</span>
                                        </div>
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    <TradeVolumeChart bioguideId={bioguideId} />
                                </CardContent>
                            </Card>

                            <Card>
                                <CardHeader>
                                    <div className="flex items-center justify-between">
                                        <CardTitle>Transactions</CardTitle>
                                        <span className="text-sm text-muted-foreground">Recent trading activity</span>
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    <RecentTradesTable bioguideId={bioguideId} />
                                </CardContent>
                            </Card>
                        </div>

                        {/* Right Column: Stats & Actions */}
                        <div className="space-y-6">
                            <Card>
                                <CardHeader>
                                    <CardTitle>Top Traded Sectors</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <SectorPieChart bioguideId={bioguideId} />
                                </CardContent>
                            </Card>
                        </div>
                    </div>
                </TabsContent>

                <TabsContent value="network" className="mt-6">
                    <MemberAssociationGraph
                        bioguideId={bioguideId}
                        memberName={memberName}
                        congress={119}
                    />
                </TabsContent>
            </Tabs>
        </div>
    );
}
