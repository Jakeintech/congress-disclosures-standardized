'use client';

import { useEffect, useState } from 'react';
import { use } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ArrowLeft, Users, FileText, Calendar, Info } from 'lucide-react';
import { fetchCommitteeDetail, fetchCommitteeBills, fetchCommitteeReports } from '@/lib/api';

interface PageProps {
    params: Promise<{
        chamber: string;
        code: string;
    }>;
}

export default function CommitteeDetailPage(props: PageProps) {
    const params = use(props.params);
    const { chamber, code } = params;

    const [committee, setCommittee] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [bills, setBills] = useState<any[]>([]);
    const [reports, setReports] = useState<any[]>([]);

    useEffect(() => {
        async function loadCommitteeData() {
            setLoading(true);
            try {
                // Fetch detail, bills, and reports in parallel
                const [detailData, billsData, reportsData] = await Promise.all([
                    fetchCommitteeDetail(chamber, code),
                    fetchCommitteeBills(chamber, code, 20),
                    fetchCommitteeReports(chamber, code, 20)
                ]);

                if (!detailData) {
                    setError('Committee metadata not found');
                } else {
                    setCommittee(detailData);
                }

                setBills(billsData || []);
                setReports(reportsData || []);
            } catch (err) {
                console.error('Failed to load committee data:', err);
                setError('Failed to load committee data');
            } finally {
                setLoading(false);
            }
        }
        loadCommitteeData();
    }, [chamber, code]);

    if (loading) {
        return (
            <div className="space-y-6">
                <Skeleton className="h-12 w-2/3" />
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-96 w-full" />
            </div>
        );
    }

    if (!committee) {
        return (
            <div className="text-center py-12">
                <h2 className="text-xl font-bold text-red-500">Committee not found</h2>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Back button */}
            <Link href="/committees" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Committees
            </Link>

            {error && (
                <Alert>
                    <Info className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            {/* Header */}
            <div>
                <div className="flex items-start justify-between">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">{committee.name}</h1>
                        <p className="text-muted-foreground mt-2">{committee.systemCode}</p>
                    </div>
                    <Badge variant={chamber === 'house' ? 'default' : 'secondary'} className="text-sm">
                        {chamber.charAt(0).toUpperCase() + chamber.slice(1)}
                    </Badge>
                </div>
            </div>

            {/* Stats */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Members</CardTitle>
                        <Users className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{committee.members?.length || 0}</div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Subcommittees</CardTitle>
                        <FileText className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{committee.subcommittees?.length || 0}</div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Bills Referred</CardTitle>
                        <FileText className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{committee.billCount || bills.length || 0}</div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Reports</CardTitle>
                        <Calendar className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{reports.length || 0}</div>
                    </CardContent>
                </Card>
            </div>

            {/* Tabs */}
            <Tabs defaultValue="members" className="w-full">
                <TabsList>
                    <TabsTrigger value="members">Members</TabsTrigger>
                    <TabsTrigger value="bills">Bills</TabsTrigger>
                    <TabsTrigger value="subcommittees">Subcommittees</TabsTrigger>
                    <TabsTrigger value="reports">Reports</TabsTrigger>
                </TabsList>

                <TabsContent value="members" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Committee Members</CardTitle>
                            <CardDescription>
                                Current members of the {committee.name}
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {committee.members && committee.members.length > 0 ? (
                                <div className="grid gap-4 md:grid-cols-2">
                                    {committee.members.map((member: any, idx: number) => (
                                        <Link
                                            key={idx}
                                            href={`/politician/${member.bioguideId}`}
                                            className="flex items-center gap-4 p-4 border rounded-lg hover:bg-muted transition-colors"
                                        >
                                            <Avatar>
                                                <AvatarImage
                                                    src={`https://bioguide.congress.gov/bioguide/photo/${member.bioguideId[0]}/${member.bioguideId}.jpg`}
                                                />
                                                <AvatarFallback>
                                                    {member.name.split(' ').map((n: string) => n[0]).join('')}
                                                </AvatarFallback>
                                            </Avatar>
                                            <div className="flex-1">
                                                <div className="font-semibold">{member.name}</div>
                                                <div className="text-sm text-muted-foreground">
                                                    {member.party} - {member.state}
                                                </div>
                                            </div>
                                            {member.role && (
                                                <Badge variant="outline">{member.role}</Badge>
                                            )}
                                        </Link>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-8 text-muted-foreground">
                                    Member roster not yet available
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="bills">
                    <Card>
                        <CardHeader>
                            <CardTitle>Bills Referred to Committee</CardTitle>
                            <CardDescription>Recent legislation referred to this committee</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {bills.length > 0 ? (
                                <div className="space-y-4">
                                    {bills.map((bill: any, idx: number) => (
                                        <div key={idx} className="p-4 border rounded-lg hover:bg-muted transition-colors">
                                            <div className="flex justify-between items-start">
                                                <div>
                                                    <Link href={`/bills/${bill.congress}/${bill.type.toLowerCase()}/${bill.number}`} className="font-bold text-blue-500 hover:underline">
                                                        {bill.type.toUpperCase()} {bill.number}
                                                    </Link>
                                                    <h3 className="text-sm font-medium mt-1">{bill.title}</h3>
                                                </div>
                                                <Badge variant="outline">{bill.introducedDate}</Badge>
                                            </div>
                                            {bill.latestAction && (
                                                <p className="text-xs text-muted-foreground mt-2">
                                                    <span className="font-semibold">Latest Action:</span> {bill.latestAction.text}
                                                </p>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-8 text-muted-foreground">
                                    No recent bills found for this committee
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="subcommittees">
                    <Card>
                        <CardHeader>
                            <CardTitle>Subcommittees</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {committee.subcommittees && committee.subcommittees.length > 0 ? (
                                <div className="space-y-2">
                                    {committee.subcommittees.map((sub: any, idx: number) => (
                                        <div key={idx} className="p-4 border rounded-lg">
                                            <div className="font-semibold">{sub.name}</div>
                                            <div className="text-sm text-muted-foreground mt-1">
                                                {sub.systemCode}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-8 text-muted-foreground">
                                    No subcommittees
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="reports">
                    <Card>
                        <CardHeader>
                            <CardTitle>Committee Reports</CardTitle>
                            <CardDescription>Recent reports issued by this committee</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {reports.length > 0 ? (
                                <div className="space-y-4">
                                    {reports.map((report: any, idx: number) => (
                                        <div key={idx} className="p-4 border rounded-lg">
                                            <div className="flex justify-between">
                                                <span className="font-bold">{report.citation}</span>
                                                <span className="text-xs text-muted-foreground">{report.issueDate}</span>
                                            </div>
                                            <p className="text-sm mt-1">{report.title}</p>
                                            <div className="flex gap-2 mt-2">
                                                <Badge variant="outline" className="text-[10px]">{report.type}</Badge>
                                                {report.number && <Badge variant="outline" className="text-[10px]">Report #{report.number}</Badge>}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-8 text-muted-foreground">
                                    No recent reports found
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
