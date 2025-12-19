'use client';

import React from 'react';
import { TradingNetworkGraph } from '@/components/analysis/trading-network-graph';
import { useNetworkGraph } from '@/hooks/use-api';
import { DataContainer } from '@/components/ui/data-container';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

interface MemberAssociationGraphProps {
    bioguideId: string;
    memberName: string;
    congress?: number;
}

export function MemberAssociationGraph({ bioguideId, memberName, congress = 119 }: MemberAssociationGraphProps) {
    const { data: graphData, isLoading, isError, error, refetch } = useNetworkGraph({
        view_mode: 'member_detail',
        bioguide_id: bioguideId,
        congress: congress
    });

    return (
        <Card>
            <CardHeader>
                <CardTitle>Association Network</CardTitle>
                <CardDescription>
                    Visualizing household trading activity and legislative sponsorships for {memberName}.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <DataContainer
                    isLoading={isLoading}
                    isError={isError}
                    error={error}
                    data={graphData}
                    onRetry={() => refetch()}
                    emptyMessage={`No trading or legislative associations found for ${memberName} in the selected congress.`}
                >
                    {(data: any) => (
                        data.nodes.length > 1 ? (
                            <TradingNetworkGraph data={data} />
                        ) : (
                            <div className="flex flex-col items-center justify-center py-12 text-center border-2 border-dashed rounded-lg">
                                <p className="text-muted-foreground text-sm">
                                    No significant associations found for {memberName}.
                                </p>
                            </div>
                        )
                    )}
                </DataContainer>
            </CardContent>
        </Card>
    );
}
