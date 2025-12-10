'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import {
    fetchBillDetail,
    fetchBillAmendments,
    fetchBillCommittees,
    fetchBillRelated,
    fetchBillSubjects,
    fetchBillTitles,
    fetchBillActions
} from '@/lib/api';

interface Cosponsor {
    bioguide_id: string;
    name: string;
    party?: string;
    state?: string;
    sponsored_date?: string;
}

interface Action {
    action_date: string;
    action_text: string;
    chamber?: string;
}

interface IndustryTag {
    industry: string;
    confidence: number;
    tickers?: string[];
    keywords?: string[];
}

interface TradeCorrelation {
    member: {
        bioguide_id: string;
        name: string;
        party?: string;
        state?: string;
    };
    ticker: string;
    trade_date: string;
    trade_type: string;
    amount_range?: string;
    days_offset: number;
    correlation_score: number;
    role?: string;
    committee_overlap?: boolean;
}

interface BillDetail {
    bill: {
        congress: number;
        bill_type: string;
        bill_number: number;
        title: string;
        policy_area?: string;
        latest_action_date?: string;
        latest_action_text?: string;
    };
    sponsor: {
        bioguide_id: string;
        name: string;
        party?: string;
        state?: string;
    };
    cosponsors: Cosponsor[];
    cosponsors_count: number;
    actions_recent: Action[];
    actions?: Action[];
    actions_count_total: number;
    industry_tags: IndustryTag[];
    trade_correlations: TradeCorrelation[];
    trade_correlations_count: number;
    congress_gov_url: string;
    summary?: string;
    text_versions?: { format: string; url: string }[];
    subjects?: string[];
    titles?: { title: string; type: string }[];
}

const INDUSTRY_ICONS: Record<string, string> = {
    'Defense': '🛡️',
    'Healthcare': '🏥',
    'Finance': '💰',
    'Energy': '⚡',
    'Technology': '💻',
    'Agriculture': '🌾',
    'Transportation': '🚗',
    'Real Estate': '🏠',
};

interface BillDetailClientProps {
    billId: string;
}

export function BillDetailClient({ billId }: BillDetailClientProps) {
    const [bill, setBill] = useState<BillDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showAllActions, setShowAllActions] = useState(false);

    // Additional Congress.gov data
    const [amendments, setAmendments] = useState<any>(null);
    const [committees, setCommittees] = useState<any>(null);
    const [relatedBills, setRelatedBills] = useState<any>(null);
    const [subjects, setSubjects] = useState<any>(null);
    const [titles, setTitles] = useState<any>(null);
    const [fullActions, setFullActions] = useState<any>(null);

    useEffect(() => {
        async function loadBill() {
            if (!billId) return;

            setLoading(true);
            setError(null);

            try {
                const data = await fetchBillDetail(billId);
                setBill(data as BillDetail);

                // Load additional Congress.gov data in parallel (non-blocking)
                Promise.allSettled([
                    fetchBillAmendments(billId),
                    fetchBillCommittees(billId),
                    fetchBillRelated(billId),
                    fetchBillSubjects(billId),
                    fetchBillTitles(billId),
                    fetchBillActions(billId)
                ]).then(([amendmentsRes, committeesRes, relatedRes, subjectsRes, titlesRes, actionsRes]) => {
                    if (amendmentsRes.status === 'fulfilled') setAmendments(amendmentsRes.value);
                    if (committeesRes.status === 'fulfilled') setCommittees(committeesRes.value);
                    if (relatedRes.status === 'fulfilled') setRelatedBills(relatedRes.value);
                    if (subjectsRes.status === 'fulfilled') setSubjects(subjectsRes.value);
                    if (titlesRes.status === 'fulfilled') setTitles(titlesRes.value);
                    if (actionsRes.status === 'fulfilled') setFullActions(actionsRes.value);
                });
            } catch (err) {
                setError('Failed to load bill details');
                console.error(err);
            } finally {
                setLoading(false);
            }
        }

        loadBill();
    }, [billId]);

    function formatDate(dateStr?: string): string {
        if (!dateStr) return 'N/A';
        try {
            const date = new Date(dateStr);
            // Check for invalid date
            if (isNaN(date.getTime())) return dateStr || 'N/A';
            return date.toLocaleDateString('en-US', {
                year: 'numeric', month: 'short', day: 'numeric'
            });
        } catch {
            return dateStr || 'N/A';
        }
    }

    function getScoreColor(score: number): string {
        if (score >= 70) return 'bg-red-500 text-white';
        if (score >= 40) return 'bg-yellow-500 text-black';
        return 'bg-gray-300 text-black';
    }

    if (loading) {
        return (
            <div className="space-y-6">
                <Skeleton className="h-10 w-64" />
                <Skeleton className="h-6 w-full max-w-2xl" />
                <div className="grid gap-4 md:grid-cols-4">
                    {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-24" />)}
                </div>
            </div>
        );
    }

    if (error || !bill || !bill.bill) {
        return (
            <Card className="border-destructive">
                <CardContent className="pt-6">
                    <p className="text-destructive">{error || 'Bill not found'}</p>
                    <Button asChild className="mt-4">
                        <Link href="/bills">← Back to Bills</Link>
                    </Button>
                </CardContent>
            </Card>
        );
    }

    const recentActions = bill.actions_recent || [];
    const allActions = bill.actions || recentActions;
    const actions = showAllActions ? allActions : recentActions.slice(0, 10);

    return (
        <div className="space-y-6">
            {/* Breadcrumb */}
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Link href="/bills" className="hover:underline">Bills</Link>
                <span>/</span>
                <span>{(bill.bill.bill_type || '').toUpperCase()} {bill.bill.bill_number}</span>
            </div>

            {/* Header */}
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div className="space-y-2">
                    <div className="flex items-center gap-3">
                        <h1 className="text-3xl font-bold tracking-tight">
                            {bill.bill.congress}-{(bill.bill.bill_type || '').toUpperCase()}-{bill.bill.bill_number}
                        </h1>
                        <Badge variant="outline" className="text-base">
                            {bill.bill.congress}th Congress
                        </Badge>
                        {bill.bill.policy_area && (
                            <Badge variant="secondary" className="text-base">
                                {bill.bill.policy_area}
                            </Badge>
                        )}
                    </div>
                    <h2 className="text-xl font-medium text-muted-foreground max-w-4xl leading-relaxed">
                        {bill.bill.title}
                    </h2>
                </div>
                <Button asChild variant="outline" className="shrink-0">
                    <a href={bill.congress_gov_url} target="_blank" rel="noopener noreferrer">
                        View on Congress.gov ↗
                    </a>
                </Button>
            </div>

            {/* Alerts */}
            {bill.trade_correlations_count > 0 && (
                <Card className="border-l-4 border-l-yellow-500 bg-yellow-50/50 dark:bg-yellow-950/20">
                    <CardContent className="py-4 flex items-center gap-3">
                        <span className="text-2xl">⚠️</span>
                        <div>
                            <p className="font-semibold text-yellow-800 dark:text-yellow-200">
                                Trade Activity Detected
                            </p>
                            <p className="text-yellow-700 dark:text-yellow-300 text-sm">
                                {bill.trade_correlations_count} legislator{bill.trade_correlations_count > 1 ? 's' : ''} traded related stocks within 90 days of this bill's activity.
                            </p>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Main Content Tabs */}
            <Tabs defaultValue="overview" className="mt-8">
                <TabsList className="w-full justify-start h-auto flex-wrap p-1 bg-muted/50">
                    <TabsTrigger value="overview" className="px-6 py-2">Overview</TabsTrigger>
                    {bill.summary && <TabsTrigger value="summary" className="px-6 py-2">Summary</TabsTrigger>}
                    <TabsTrigger value="text" className="px-6 py-2">Text</TabsTrigger>
                    <TabsTrigger value="actions" className="px-6 py-2">Actions <span className="ml-2 text-muted-foreground text-xs">{fullActions?.count || bill.actions_count_total}</span></TabsTrigger>
                    <TabsTrigger value="cosponsors" className="px-6 py-2">Cosponsors <span className="ml-2 text-muted-foreground text-xs">{bill.cosponsors_count}</span></TabsTrigger>
                    {committees && committees.count > 0 && (
                        <TabsTrigger value="committees" className="px-6 py-2">Committees <span className="ml-2 text-muted-foreground text-xs">{committees.count}</span></TabsTrigger>
                    )}
                    {amendments && amendments.count > 0 && (
                        <TabsTrigger value="amendments" className="px-6 py-2">Amendments <span className="ml-2 text-muted-foreground text-xs">{amendments.count}</span></TabsTrigger>
                    )}
                    {relatedBills && relatedBills.count > 0 && (
                        <TabsTrigger value="related" className="px-6 py-2">Related Bills <span className="ml-2 text-muted-foreground text-xs">{relatedBills.count}</span></TabsTrigger>
                    )}
                    {subjects && subjects.count > 0 && (
                        <TabsTrigger value="subjects" className="px-6 py-2">Subjects <span className="ml-2 text-muted-foreground text-xs">{subjects.count}</span></TabsTrigger>
                    )}
                    {titles && titles.count > 0 && (
                        <TabsTrigger value="titles" className="px-6 py-2">Titles <span className="ml-2 text-muted-foreground text-xs">{titles.count}</span></TabsTrigger>
                    )}
                    <TabsTrigger value="trades" className="px-6 py-2">Analysis <span className="ml-2 text-muted-foreground text-xs">{bill.trade_correlations_count}</span></TabsTrigger>
                </TabsList>

                <div className="mt-6">
                    {/* OVERVIEW TAB */}
                    <TabsContent value="overview" className="space-y-6">
                        <div className="grid gap-6 md:grid-cols-2">
                            <Card>
                                <CardHeader>
                                    <CardTitle>Bill Information</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="grid grid-cols-[120px_1fr] items-baseline gap-4">
                                        <span className="text-sm font-medium text-muted-foreground">Sponsor</span>
                                        <div>
                                            <Link href={`/member?id=${bill.sponsor.bioguide_id}`} className="font-medium hover:underline text-primary">
                                                {bill.sponsor.name}
                                            </Link>
                                            <p className="text-sm text-muted-foreground">
                                                {bill.sponsor.party} - {bill.sponsor.state}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-[120px_1fr] items-baseline gap-4">
                                        <span className="text-sm font-medium text-muted-foreground">Introduced</span>
                                        <span>{formatDate(bill.actions_recent[bill.actions_recent.length - 1]?.action_date)}</span>
                                    </div>
                                    <div className="grid grid-cols-[120px_1fr] items-baseline gap-4">
                                        <span className="text-sm font-medium text-muted-foreground">Latest Action</span>
                                        <span>{formatDate(bill.bill.latest_action_date)}</span>
                                    </div>
                                    <div className="grid grid-cols-[120px_1fr] items-baseline gap-4">
                                        <span className="text-sm font-medium text-muted-foreground">Cosponsors</span>
                                        <span>{bill.cosponsors_count}</span>
                                    </div>
                                </CardContent>
                            </Card>

                            <Card>
                                <CardHeader>
                                    <CardTitle>Industry Classification</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    {bill.industry_tags.length > 0 ? (
                                        <div className="flex flex-wrap gap-2">
                                            {bill.industry_tags.map(tag => (
                                                <Badge key={tag.industry} variant="secondary" className="text-sm py-1.5 px-3">
                                                    {INDUSTRY_ICONS[tag.industry] || '🏭'} {tag.industry}
                                                    <span className="ml-1.5 text-muted-foreground text-xs">
                                                        {Math.round(tag.confidence * 100)}%
                                                    </span>
                                                </Badge>
                                            ))}
                                        </div>
                                    ) : (
                                        <p className="text-muted-foreground">No industry classification available.</p>
                                    )}
                                </CardContent>
                            </Card>
                        </div>

                        {bill.summary && (
                            <Card>
                                <CardHeader>
                                    <CardTitle>Summary Preview</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <p className="text-muted-foreground line-clamp-3">{bill.summary}</p>
                                    <Button variant="link" className="p-0 h-auto mt-2" onClick={() => document.querySelector<HTMLElement>('[value="summary"]')?.click()}>
                                        Read full summary
                                    </Button>
                                </CardContent>
                            </Card>
                        )}
                    </TabsContent>

                    {/* SUMMARY TAB */}
                    <TabsContent value="summary">
                        <Card>
                            <CardHeader>
                                <CardTitle>Bill Summary</CardTitle>
                                <CardDescription>Provided by Congressional Research Service</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {bill.summary ? (
                                    <div className="prose dark:prose-invert max-w-none">
                                        <p className="leading-relaxed whitespace-pre-wrap">{bill.summary}</p>
                                    </div>
                                ) : (
                                    <p className="text-muted-foreground italic">No summary available.</p>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* TEXT TAB */}
                    <TabsContent value="text">
                        <Card>
                            <CardHeader>
                                <CardTitle>Bill Text</CardTitle>
                            </CardHeader>
                            <CardContent>
                                {bill.text_versions && bill.text_versions.length > 0 ? (
                                    <div className="space-y-4">
                                        <p className="text-muted-foreground mb-4">Available versions:</p>
                                        <div className="flex gap-4">
                                            {bill.text_versions.map((ver, i) => (
                                                <Button key={i} asChild variant="outline">
                                                    <a href={ver.url} target="_blank" rel="noopener noreferrer" className="uppercase">
                                                        {ver.format} ↗
                                                    </a>
                                                </Button>
                                            ))}
                                        </div>
                                    </div>
                                ) : (
                                    <div className="text-center py-12">
                                        <p className="text-muted-foreground mb-4">Text versions are fetched from Congress.gov</p>
                                        <Button asChild>
                                            <a href={`${bill.congress_gov_url}/text`} target="_blank" rel="noopener noreferrer">
                                                View Text on Congress.gov ↗
                                            </a>
                                        </Button>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* ACTIONS TAB */}
                    <TabsContent value="actions">
                        <Card>
                            <CardHeader>
                                <CardTitle>Legislative History</CardTitle>
                            </CardHeader>
                            <CardContent className="p-0">
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead className="w-[120px]">Date</TableHead>
                                            <TableHead className="w-[100px]">Chamber</TableHead>
                                            <TableHead>Action</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {actions.map((action, i) => (
                                            <TableRow key={i}>
                                                <TableCell className="font-medium whitespace-nowrap">
                                                    {formatDate(action.action_date)}
                                                </TableCell>
                                                <TableCell>
                                                    {action.chamber ? (
                                                        <Badge variant="outline" className="capitalize">
                                                            {action.chamber.toLowerCase()}
                                                        </Badge>
                                                    ) : '-'}
                                                </TableCell>
                                                <TableCell className="text-muted-foreground">
                                                    {action.action_text}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                                {bill.actions_count_total > 10 && !showAllActions && (
                                    <div className="p-4 border-t">
                                        <Button
                                            variant="ghost"
                                            className="w-full"
                                            onClick={() => setShowAllActions(true)}
                                        >
                                            Show all {bill.actions_count_total} actions
                                        </Button>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* COSPONSORS TAB */}
                    <TabsContent value="cosponsors">
                        <Card>
                            <CardHeader>
                                <CardTitle>Cosponsors ({bill.cosponsors_count})</CardTitle>
                            </CardHeader>
                            <CardContent>
                                {bill.cosponsors.length === 0 ? (
                                    <p className="text-muted-foreground py-4 text-center">No cosponsors.</p>
                                ) : (
                                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                                        {bill.cosponsors.map((cosponsor, i) => (
                                            <div key={i} className="flex items-center gap-3 p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
                                                <div className="h-10 w-10 shrink-0 bg-muted rounded-full flex items-center justify-center font-bold text-muted-foreground">
                                                    {cosponsor.name.charAt(0)}
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <Link href={`/member?id=${cosponsor.bioguide_id}`} className="font-medium hover:underline truncate block">
                                                        {cosponsor.name}
                                                    </Link>
                                                    <p className="text-xs text-muted-foreground">
                                                        {cosponsor.party} - {cosponsor.state}
                                                    </p>
                                                </div>
                                                <div className="text-xs text-muted-foreground whitespace-nowrap">
                                                    {formatDate(cosponsor.sponsored_date)}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* COMMITTEES TAB */}
                    <TabsContent value="committees">
                        <Card>
                            <CardHeader>
                                <CardTitle>Committee Referrals</CardTitle>
                                <CardDescription>Committees that have jurisdiction over this bill</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {!committees ? (
                                    <div className="flex items-center justify-center py-8">
                                        <Skeleton className="h-32 w-full" />
                                    </div>
                                ) : committees.committees && committees.committees.length > 0 ? (
                                    <div className="space-y-4">
                                        {committees.committees.map((committee: any, i: number) => (
                                            <div key={i} className="border rounded-lg p-4 hover:bg-muted/50 transition-colors">
                                                <h4 className="font-semibold text-lg">{committee.name}</h4>
                                                {committee.system_code && (
                                                    <p className="text-sm text-muted-foreground font-mono mt-1">{committee.system_code}</p>
                                                )}
                                                {committee.activities && committee.activities.length > 0 && (
                                                    <div className="mt-3 space-y-1">
                                                        {committee.activities.map((activity: any, j: number) => (
                                                            <div key={j} className="flex items-center gap-2 text-sm">
                                                                <Badge variant="outline">{activity.name}</Badge>
                                                                <span className="text-muted-foreground">{formatDate(activity.date)}</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-muted-foreground text-center py-8">No committee referrals found.</p>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* AMENDMENTS TAB */}
                    <TabsContent value="amendments">
                        <Card>
                            <CardHeader>
                                <CardTitle>Amendments</CardTitle>
                                <CardDescription>Proposed changes to this bill</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {!amendments ? (
                                    <div className="flex items-center justify-center py-8">
                                        <Skeleton className="h-32 w-full" />
                                    </div>
                                ) : amendments.amendments && amendments.amendments.length > 0 ? (
                                    <Table>
                                        <TableHeader>
                                            <TableRow>
                                                <TableHead>Amendment</TableHead>
                                                <TableHead>Sponsor</TableHead>
                                                <TableHead>Description</TableHead>
                                                <TableHead>Date</TableHead>
                                                <TableHead>Status</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {amendments.amendments.map((amendment: any, i: number) => (
                                                <TableRow key={i}>
                                                    <TableCell className="font-mono">{amendment.number}</TableCell>
                                                    <TableCell>{amendment.sponsor?.name || 'N/A'}</TableCell>
                                                    <TableCell className="max-w-md truncate">{amendment.description || amendment.purpose || 'N/A'}</TableCell>
                                                    <TableCell>{formatDate(amendment.submit_date)}</TableCell>
                                                    <TableCell>
                                                        <Badge variant={amendment.latest_action?.action_code === 'APPROVED' ? 'default' : 'secondary'}>
                                                            {amendment.latest_action?.text || 'Pending'}
                                                        </Badge>
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                ) : (
                                    <p className="text-muted-foreground text-center py-8">No amendments found.</p>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* RELATED BILLS TAB */}
                    <TabsContent value="related">
                        <Card>
                            <CardHeader>
                                <CardTitle>Related Bills</CardTitle>
                                <CardDescription>Bills with similar provisions or related subject matter</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {!relatedBills ? (
                                    <div className="flex items-center justify-center py-8">
                                        <Skeleton className="h-32 w-full" />
                                    </div>
                                ) : relatedBills.relatedBills && relatedBills.relatedBills.length > 0 ? (
                                    <div className="space-y-3">
                                        {relatedBills.relatedBills.map((related: any, i: number) => (
                                            <div key={i} className="border rounded-lg p-4 hover:bg-muted/50 transition-colors">
                                                <div className="flex items-start justify-between gap-4">
                                                    <div className="flex-1">
                                                        <div className="flex items-center gap-2">
                                                            <h4 className="font-semibold">
                                                                {related.congress}-{related.type?.toUpperCase()}-{related.number}
                                                            </h4>
                                                            <Badge variant="outline">{related.relationship_type || related.type}</Badge>
                                                        </div>
                                                        <p className="text-sm text-muted-foreground mt-1">{related.title}</p>
                                                        {related.latest_action && (
                                                            <p className="text-xs text-muted-foreground mt-2">
                                                                Latest: {related.latest_action.text} ({formatDate(related.latest_action.action_date)})
                                                            </p>
                                                        )}
                                                    </div>
                                                    <Button variant="ghost" size="sm" asChild>
                                                        <Link href={`/bills/${related.congress}/${related.type}/${related.number}`}>
                                                            View →
                                                        </Link>
                                                    </Button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-muted-foreground text-center py-8">No related bills found.</p>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* SUBJECTS TAB */}
                    <TabsContent value="subjects">
                        <Card>
                            <CardHeader>
                                <CardTitle>Policy Subjects</CardTitle>
                                <CardDescription>Legislative subjects assigned by the Library of Congress</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {!subjects ? (
                                    <div className="flex items-center justify-center py-8">
                                        <Skeleton className="h-32 w-full" />
                                    </div>
                                ) : subjects.subjects && subjects.subjects.length > 0 ? (
                                    <div className="flex flex-wrap gap-2">
                                        {subjects.subjects.map((subject: any, i: number) => (
                                            <Badge key={i} variant="secondary" className="text-sm py-2 px-3">
                                                {typeof subject === 'string' ? subject : subject.name}
                                            </Badge>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-muted-foreground text-center py-8">No subjects assigned.</p>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* TITLES TAB */}
                    <TabsContent value="titles">
                        <Card>
                            <CardHeader>
                                <CardTitle>Bill Titles</CardTitle>
                                <CardDescription>All official and short titles for this bill</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {!titles ? (
                                    <div className="flex items-center justify-center py-8">
                                        <Skeleton className="h-32 w-full" />
                                    </div>
                                ) : titles.titles && titles.titles.length > 0 ? (
                                    <div className="space-y-4">
                                        {titles.titles.map((title: any, i: number) => (
                                            <div key={i} className="border-b pb-4 last:border-b-0">
                                                <div className="flex items-start gap-2 mb-1">
                                                    <Badge variant="outline" className="shrink-0">{title.title_type || title.type}</Badge>
                                                    {title.chamber && <Badge variant="secondary" className="shrink-0 capitalize">{title.chamber}</Badge>}
                                                </div>
                                                <p className="mt-2">{title.title}</p>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-muted-foreground text-center py-8">No titles found.</p>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* TRADES / ANALYSIS TAB */}
                    <TabsContent value="trades">
                        <Card>
                            <CardHeader>
                                <div className="flex items-center justify-between">
                                    <div>
                                        <CardTitle>Trade Correlation Analysis</CardTitle>
                                        <CardDescription>
                                            Legislative activity correlated with stock trading patterns
                                        </CardDescription>
                                    </div>
                                    <Badge variant={bill.trade_correlations_count > 0 ? "destructive" : "secondary"}>
                                        {bill.trade_correlations_count} Correlated Trades
                                    </Badge>
                                </div>
                            </CardHeader>
                            <CardContent>
                                {bill.trade_correlations.length === 0 ? (
                                    <div className="text-center py-12">
                                        <div className="text-4xl mb-4">📊</div>
                                        <h3 className="text-lg font-medium">No correlations detected</h3>
                                        <p className="text-muted-foreground max-w-md mx-auto mt-2">
                                            We haven't found any stock trades by legislators that strongly correlate with the timeline of this bill's activity.
                                        </p>
                                    </div>
                                ) : (
                                    <Table>
                                        <TableHeader>
                                            <TableRow>
                                                <TableHead>Member</TableHead>
                                                <TableHead>Ticker</TableHead>
                                                <TableHead>Trade Date</TableHead>
                                                <TableHead>Type</TableHead>
                                                <TableHead>Amount</TableHead>
                                                <TableHead className="text-center">Exposure</TableHead>
                                                <TableHead className="text-right">Correlation</TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {bill.trade_correlations.map((trade, i) => (
                                                <TableRow key={i} className="group hover:bg-muted/50">
                                                    <TableCell>
                                                        <div className="flex flex-col">
                                                            <Link href={`/member?id=${trade.member.bioguide_id}`} className="font-medium hover:underline">
                                                                {trade.member.name}
                                                            </Link>
                                                            <span className="text-xs text-muted-foreground">
                                                                {trade.member.party}-{trade.member.state}
                                                            </span>
                                                        </div>
                                                    </TableCell>
                                                    <TableCell>
                                                        <Badge variant="outline" className="font-mono">
                                                            {trade.ticker}
                                                        </Badge>
                                                    </TableCell>
                                                    <TableCell>{formatDate(trade.trade_date)}</TableCell>
                                                    <TableCell>
                                                        <span className={trade.trade_type === 'purchase' ? 'text-green-600 font-medium' : 'text-red-500 font-medium'}>
                                                            {trade.trade_type.toUpperCase()}
                                                        </span>
                                                    </TableCell>
                                                    <TableCell>{trade.amount_range}</TableCell>
                                                    <TableCell className="text-center">
                                                        <div className="flex flex-col items-center">
                                                            <span className="font-bold">{trade.days_offset} days</span>
                                                            <span className="text-xs text-muted-foreground">from action</span>
                                                        </div>
                                                    </TableCell>
                                                    <TableCell className="text-right">
                                                        <Badge className={getScoreColor(trade.correlation_score)}>
                                                            {trade.correlation_score}%
                                                        </Badge>
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>
                </div>
            </Tabs>
        </div>
    );
}
