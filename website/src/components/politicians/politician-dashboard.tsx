'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { useMemberProfile } from '@/hooks/use-api';
import { DataContainer } from '@/components/ui/data-container';
import { PoliticianHeader } from './politician-header';
import { TradeVolumeChart } from './trade-volume-chart';
import { SectorPieChart } from './sector-pie-chart';
import { RecentTradesTable } from './recent-trades-table';
import { MemberPortfolioTable } from './member-portfolio-table';
import { MemberAssociationGraph } from '../analysis/member-association-graph';

interface PoliticianDashboardProps {
    bioguideId: string;
}

export function PoliticianDashboard({ bioguideId }: PoliticianDashboardProps) {
    const { data: member, isLoading, isError, error, refetch } = useMemberProfile(bioguideId);

    const loadingSkeleton = (
        <div className="space-y-6 pt-6">
            <Skeleton className="h-48 w-full" />
            <div className="grid gap-6 md:grid-cols-2">
                <Skeleton className="h-64" />
                <Skeleton className="h-64" />
            </div>
        </div>
    );

    return (
        <DataContainer
            isLoading={isLoading}
            isError={isError}
            error={error}
            data={member}
            onRetry={() => refetch()}
            loadingSkeleton={loadingSkeleton}
        >
            {(member: any) => {
                const memberName = `${member.name || (member.first_name + ' ' + member.last_name)}`;
                return (
                    <div className="space-y-6 pb-12">
                        {/* Header Section */}
                        <PoliticianHeader member={member} />

                        <Tabs defaultValue="overview" className="w-full">
                            <TabsList className="grid w-full grid-cols-3 lg:w-[600px]">
                                <TabsTrigger value="overview">Overview</TabsTrigger>
                                <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
                                <TabsTrigger value="network">Network</TabsTrigger>
                            </TabsList>

                            <TabsContent value="overview" className="space-y-6 mt-6">
                                {/* Overview content */}
                                <div className="grid gap-6 lg:grid-cols-3">
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
                                                    <CardTitle>Recent Transactions</CardTitle>
                                                </div>
                                            </CardHeader>
                                            <CardContent>
                                                <RecentTradesTable bioguideId={bioguideId} />
                                            </CardContent>
                                        </Card>
                                    </div>

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

                            <TabsContent value="portfolio" className="mt-6">
                                <MemberPortfolioTable bioguideId={bioguideId} />
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
            }}
        </DataContainer>
    );
}
