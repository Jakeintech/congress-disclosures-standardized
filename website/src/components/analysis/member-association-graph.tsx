'use client';

import React, { useEffect, useState } from 'react';
import { TradingNetworkGraph } from '@/components/analysis/trading-network-graph';
import { fetchNetworkGraph } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Loader2, Info } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

interface MemberAssociationGraphProps {
    bioguideId: string;
    memberName: string;
    congress?: number;
}

export function MemberAssociationGraph({ bioguideId, memberName, congress = 119 }: MemberAssociationGraphProps) {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadGraph() {
            setLoading(true);
            try {
                const graphData = await fetchNetworkGraph({
                    view_mode: 'member_detail',
                    bioguide_id: bioguideId,
                    congress: congress
                });
                setData(graphData);
            } catch (err) {
                console.error('Failed to load member association graph:', err);
                setError('Failed to load association graph. Please try again later.');
            } finally {
                setLoading(false);
            }
        }

        if (bioguideId) {
            loadGraph();
        }
    }, [bioguideId, congress]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (error) {
        return (
            <Alert variant="destructive">
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
            </Alert>
        );
    }

    if (!data || data.nodes.length <= 1) {
        return (
            <Alert>
                <Info className="h-4 w-4" />
                <AlertTitle>No Associations Found</AlertTitle>
                <AlertDescription>
                    No trading or legislative associations found for {memberName} in the selected congress.
                </AlertDescription>
            </Alert>
        );
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle>Association Network</CardTitle>
                <CardDescription>
                    Visualizing household trading activity and legislative sponsorships for {memberName}.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <TradingNetworkGraph data={data} />
            </CardContent>
        </Card>
    );
}
