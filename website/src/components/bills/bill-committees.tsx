'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useBillCommittees } from '@/hooks/use-api';
import { DataContainer } from '@/components/ui/data-container';
import { Badge } from '@/components/ui/badge';
import { Users, Building2, Calendar, FileText } from 'lucide-react';

interface BillCommitteesProps {
    billId: string;
}

export function BillCommittees({ billId }: BillCommitteesProps) {
    const { data, isLoading, isError, error, refetch } = useBillCommittees(billId);

    return (
        <DataContainer
            isLoading={isLoading}
            isError={isError}
            error={error}
            data={data}
            onRetry={() => refetch()}
            emptyMessage="No committee information available for this bill."
        >
            {(committees: any) => (
                <div className="grid gap-6">
                    {committees.map((committee: any, idx: number) => (
                        <Card key={idx} className="overflow-hidden">
                            <CardHeader className="bg-muted/30 pb-4">
                                <div className="flex items-start justify-between">
                                    <div className="space-y-1">
                                        <CardTitle className="text-xl flex items-center gap-2">
                                            <Building2 className="h-5 w-5 text-primary" />
                                            {committee.name}
                                        </CardTitle>
                                        <CardDescription className="flex items-center gap-2">
                                            <Badge variant="outline" className="uppercase">{committee.chamber}</Badge>
                                            {committee.systemCode && <span className="text-xs font-mono">Code: {committee.systemCode}</span>}
                                        </CardDescription>
                                    </div>
                                    {committee.type && <Badge variant="secondary">{committee.type}</Badge>}
                                </div>
                            </CardHeader>
                            <CardContent className="pt-6">
                                <div className="grid gap-6 md:grid-cols-2">
                                    <div className="space-y-4">
                                        <div className="flex items-center gap-3 text-sm">
                                            <Calendar className="h-4 w-4 text-muted-foreground" />
                                            <div>
                                                <span className="font-semibold block">Referred Date</span>
                                                <span className="text-muted-foreground">{committee.referredDate || 'N/A'}</span>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-3 text-sm">
                                            <Users className="h-4 w-4 text-muted-foreground" />
                                            <div>
                                                <span className="font-semibold block">Role</span>
                                                <span className="text-muted-foreground">Primary jurisdiction over this bill</span>
                                            </div>
                                        </div>
                                    </div>

                                    {committee.subcommittees && committee.subcommittees.length > 0 && (
                                        <div className="space-y-3">
                                            <h4 className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                                                <Users className="h-3 w-3" />
                                                Subcommittees
                                            </h4>
                                            <div className="space-y-2">
                                                {committee.subcommittees.map((sub: any, sIdx: number) => (
                                                    <div key={sIdx} className="flex items-center justify-between p-2 rounded-lg bg-accent/30 border border-accent/50 text-sm">
                                                        <span>{sub.name}</span>
                                                        <Badge variant="outline" className="text-[10px] h-4">{sub.systemCode}</Badge>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>

                                {committee.activities && committee.activities.length > 0 && (
                                    <div className="mt-6 pt-6 border-t">
                                        <h4 className="text-sm font-bold uppercase tracking-wider text-muted-foreground mb-4 flex items-center gap-2">
                                            <FileText className="h-3 w-3" />
                                            Committee Activities
                                        </h4>
                                        <div className="flex flex-wrap gap-2">
                                            {committee.activities.map((activity: any, aIdx: number) => (
                                                <Badge key={aIdx} variant="secondary" className="px-3 py-1">
                                                    {activity.name}
                                                </Badge>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}
        </DataContainer>
    );
}
