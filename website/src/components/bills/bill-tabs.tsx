"use client";

import { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Download, FileText } from 'lucide-react';
import { BillTimeline, TimelineEvent } from './bill-timeline';
import { BillTextComparison } from './bill-text-comparison';
import { AmendmentImpactAnalysis } from './amendment-impact-analysis';
import {
    fetchBillText,
    fetchBillCommittees,
    fetchBillCosponsors,
    fetchBillSubjects,
    fetchBillSummaries,
    fetchBillTitles,
    fetchBillAmendments,
    fetchBillRelated,
    fetchBillActions
} from '@/lib/api';

interface BillTabsProps {
    bill: any;
    textVersions?: any[];
    cosponsorsCount: number;
    actionsCount: number;
    billId: string;
}

export function BillTabs({ bill, textVersions, cosponsorsCount, actionsCount, billId }: BillTabsProps) {
    const [billTextData, setBillTextData] = useState<any>(null);
    const [selectedVersion, setSelectedVersion] = useState<number>(0);
    const [textContent, setTextContent] = useState<string | null>(null);
    const [loadingText, setLoadingText] = useState(false);

    const [committees, setCommittees] = useState<any[] | null>(null);
    const [loadingCommittees, setLoadingCommittees] = useState(false);

    const [cosponsors, setCosponsors] = useState<any[] | null>(null);
    const [loadingCosponsors, setLoadingCosponsors] = useState(false);

    const [subjects, setSubjects] = useState<any[] | null>(null);
    const [loadingSubjects, setLoadingSubjects] = useState(false);

    const [summaries, setSummaries] = useState<any[] | null>(null);
    const [loadingSummaries, setLoadingSummaries] = useState(false);

    const [titles, setTitles] = useState<any[] | null>(null);
    const [loadingTitles, setLoadingTitles] = useState(false);

    const [amendments, setAmendments] = useState<any[] | null>(null);
    const [loadingAmendments, setLoadingAmendments] = useState(false);

    const [relatedBills, setRelatedBills] = useState<any[] | null>(null);
    const [loadingRelated, setLoadingRelated] = useState(false);

    const [actions, setActions] = useState<any[] | null>(null);
    const [loadingActions, setLoadingActions] = useState(false);

    // Convert actions to timeline events
    const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);

    useEffect(() => {
        if (actions && actions.length > 0) {
            // Convert actions to timeline events
            const events: TimelineEvent[] = actions.map((action, index) => {
                const isLatest = index === 0;
                const isCompleted = !isLatest;

                return {
                    date: action.action_date || action.date,
                    title: action.action_text || action.text || 'Action taken',
                    description: action.description,
                    status: isLatest ? 'current' : 'completed',
                    chamber: action.chamber,
                    tradeAlert: false, // TODO: Connect with trade correlation data
                    tradeCount: 0,
                };
            });

            setTimelineEvents(events);
        }
    }, [actions]);

    // Fetch data when tabs are activated
    const handleTabChange = (val: string) => {
        if (val === 'text' && !billTextData && !loadingText) {
            setLoadingText(true);
            fetchBillText(billId).then(data => {
                // @ts-ignore - data can have various shapes from API
                setBillTextData(data);

                // Parse the content that was already fetched by the Lambda
                // @ts-ignore
                if (data?.content) {
                    const parser = new DOMParser();
                    // @ts-ignore
                    const doc = parser.parseFromString(data.content, 'text/html');
                    const pre = doc.querySelector('pre');
                    // @ts-ignore
                    setTextContent(pre?.textContent || data.content);
                } else {
                    setTextContent(null);
                }
            }).catch(() => {
                setBillTextData({ error: true });
                setTextContent("Failed to load text.");
            }).finally(() => setLoadingText(false));
        }

        if (val === 'committees' && !committees && !loadingCommittees) {
            setLoadingCommittees(true);
            // @ts-ignore
            fetchBillCommittees(billId).then(data => setCommittees(data?.committees || []))
                .finally(() => setLoadingCommittees(false));
        }

        if (val === 'cosponsors' && !cosponsors && !loadingCosponsors) {
            setLoadingCosponsors(true);
            // @ts-ignore
            fetchBillCosponsors(billId).then(data => setCosponsors(data?.cosponsors || []))
                .finally(() => setLoadingCosponsors(false));
        }

        if (val === 'subjects' && !subjects && !loadingSubjects) {
            setLoadingSubjects(true);
            // @ts-ignore
            fetchBillSubjects(billId).then(data => setSubjects(data?.subjects || []))
                .finally(() => setLoadingSubjects(false));
        }

        if (val === 'summaries' && !summaries && !loadingSummaries) {
            setLoadingSummaries(true);
            // @ts-ignore
            fetchBillSummaries(billId).then(data => setSummaries(data?.summaries || []))
                .finally(() => setLoadingSummaries(false));
        }

        if (val === 'titles' && !titles && !loadingTitles) {
            setLoadingTitles(true);
            // @ts-ignore
            fetchBillTitles(billId).then(data => setTitles(data?.titles || []))
                .finally(() => setLoadingTitles(false));
        }

        if (val === 'amendments' && !amendments && !loadingAmendments) {
            setLoadingAmendments(true);
            // @ts-ignore
            fetchBillAmendments(billId).then(data => setAmendments(data?.amendments || []))
                .finally(() => setLoadingAmendments(false));
        }

        if (val === 'related' && !relatedBills && !loadingRelated) {
            setLoadingRelated(true);
            // @ts-ignore
            fetchBillRelated(billId).then(data => setRelatedBills(data?.relatedBills || []))
                .finally(() => setLoadingRelated(false));
        }

        if (val === 'actions' && !actions && !loadingActions) {
            setLoadingActions(true);
            // @ts-ignore
            fetchBillActions(billId).then(data => setActions(data?.actions || []))
                .finally(() => setLoadingActions(false));
        }

        // Load actions for timeline tab
        if (val === 'timeline' && !actions && !loadingActions) {
            setLoadingActions(true);
            // @ts-ignore
            fetchBillActions(billId).then(data => setActions(data?.actions || []))
                .finally(() => setLoadingActions(false));
        }
    };

    return (
        <Tabs defaultValue="summary" className="w-full" onValueChange={handleTabChange}>
            <TabsList className="w-full justify-start overflow-x-auto h-auto flex-wrap gap-2 p-1 bg-background border-b rounded-none mb-4">
                <TabsTrigger value="summary">Summary</TabsTrigger>
                <TabsTrigger value="timeline">Timeline</TabsTrigger>
                <TabsTrigger value="text">Text</TabsTrigger>
                <TabsTrigger value="actions">
                    Actions <Badge variant="secondary" className="ml-1.5 text-[10px] h-5">{actionsCount}</Badge>
                </TabsTrigger>
                <TabsTrigger value="titles">Titles</TabsTrigger>
                <TabsTrigger value="cosponsors">
                    Cosponsors {cosponsorsCount > 0 && <Badge variant="secondary" className="ml-1.5 text-[10px] h-5">{cosponsorsCount}</Badge>}
                </TabsTrigger>
                <TabsTrigger value="committees">Committees</TabsTrigger>
                <TabsTrigger value="subjects">Subjects</TabsTrigger>
                <TabsTrigger value="amendments">Amendments</TabsTrigger>
                <TabsTrigger value="related">Related Bills</TabsTrigger>
                <TabsTrigger value="comparison">Text Comparison</TabsTrigger>
                <TabsTrigger value="impact">Amendment Impact</TabsTrigger>
            </TabsList>

            <div className="space-y-4">
                <TabsContent value="summary">
                    <Card>
                        <CardHeader>
                            <CardTitle>Bill Summary</CardTitle>
                            <CardDescription>Official summary from CRS</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="prose dark:prose-invert max-w-none text-sm text-muted-foreground whitespace-pre-wrap">
                                {bill.summary ? bill.summary : <i>No summary available.</i>}
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="timeline">
                    {loadingActions ? (
                        <Card>
                            <CardContent className="pt-6">
                                <div className="space-y-4">
                                    <div className="animate-pulse space-y-3">
                                        {[1, 2, 3, 4, 5].map(i => (
                                            <div key={i} className="flex gap-4">
                                                <div className="h-5 w-5 rounded-full bg-muted" />
                                                <div className="flex-1 space-y-2">
                                                    <div className="h-4 bg-muted rounded w-3/4" />
                                                    <div className="h-3 bg-muted rounded w-1/2" />
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    ) : timelineEvents.length > 0 ? (
                        <BillTimeline events={timelineEvents} billId={billId} />
                    ) : (
                        <Card>
                            <CardContent className="pt-6">
                                <p className="text-center text-muted-foreground">No timeline data available</p>
                            </CardContent>
                        </Card>
                    )}
                </TabsContent>

                <TabsContent value="text">
                    <Card>
                        <CardHeader>
                            <div className="flex items-start justify-between">
                                <div className="space-y-1">
                                    <CardTitle>Bill Text</CardTitle>
                                    <CardDescription>
                                        {billTextData?.text_versions?.[selectedVersion] && (
                                            <>
                                                {billTextData.text_versions[selectedVersion].type} — {
                                                    new Date(billTextData.text_versions[selectedVersion].date).toLocaleDateString()
                                                }
                                            </>
                                        )}
                                    </CardDescription>
                                </div>
                                {billTextData?.text_versions && billTextData.text_versions.length > 0 && (
                                    <div className="flex items-center gap-2">
                                        <Select
                                            value={selectedVersion.toString()}
                                            onValueChange={(v) => {
                                                const idx = parseInt(v);
                                                setSelectedVersion(idx);
                                                setLoadingText(true);
                                                setTextContent(null);

                                                // Fetch text content for selected version via API
                                                // @ts-ignore
                                                fetchBillText(billId + `?version=${idx}`).then(data => {
                                                    // @ts-ignore
                                                    if (data?.content) {
                                                        const parser = new DOMParser();
                                                        // @ts-ignore
                                                        const doc = parser.parseFromString(data.content, 'text/html');
                                                        const pre = doc.querySelector('pre');
                                                        // @ts-ignore
                                                        setTextContent(pre?.textContent || data.content);
                                                    } else {
                                                        setTextContent("Text not available for this version.");
                                                    }
                                                }).catch(() => {
                                                    setTextContent("Failed to load text content.");
                                                }).finally(() => {
                                                    setLoadingText(false);
                                                });
                                            }}
                                        >
                                            <SelectTrigger className="w-[240px]">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {billTextData.text_versions.map((v: any, i: number) => (
                                                    <SelectItem key={i} value={i.toString()}>
                                                        {v.type}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                )}
                            </div>
                            {billTextData?.text_versions?.[selectedVersion]?.formats && (
                                <div className="flex gap-2 mt-4">
                                    {billTextData.text_versions[selectedVersion].formats.map((format: any, i: number) => (
                                        <Button key={i} variant="outline" size="sm" asChild>
                                            <a href={format.url} target="_blank" rel="noreferrer" className="flex items-center gap-1">
                                                <Download className="h-3 w-3" />
                                                {format.type}
                                            </a>
                                        </Button>
                                    ))}
                                </div>
                            )}
                        </CardHeader>
                        <CardContent>
                            {loadingText ? (
                                <div className="flex items-center justify-center py-8 text-muted-foreground">Loading bill text...</div>
                            ) : textContent ? (
                                <ScrollArea className="h-[600px] w-full rounded-md border p-4 bg-muted/30">
                                    <pre className="text-xs font-mono whitespace-pre-wrap leading-relaxed">{textContent}</pre>
                                </ScrollArea>
                            ) : (
                                <div className="text-center py-8">
                                    <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                                    <p className="text-muted-foreground mb-4">Bill text not available yet.</p>
                                    <Button asChild>
                                        <a
                                            href={`https://www.congress.gov/bill/${bill.congress}th-congress/${bill.bill_type === 'hr' ? 'house-bill' : bill.bill_type === 's' ? 'senate-bill' : 'house-bill'}/${bill.bill_number}/text`}
                                            target="_blank"
                                            rel="noreferrer"
                                        >
                                            View on Congress.gov
                                        </a>
                                    </Button>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="actions">
                    <Card>
                        <CardHeader><CardTitle>Legislative Actions</CardTitle></CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {loadingActions ? (
                                    <div className="text-center py-4 text-muted-foreground">Loading actions...</div>
                                ) : actions && actions.length > 0 ? (
                                    actions.map((action: any, i: number) => (
                                        <div key={i} className="flex gap-4 border-b pb-4 last:border-0 last:pb-0">
                                            <div className="w-24 shrink-0 text-sm text-muted-foreground">{action.action_date}</div>
                                            <div className="text-sm">{action.action_text}</div>
                                        </div>
                                    ))
                                ) : (
                                    // Fallback to prop data if available and state is empty/loading check passed, or just show empty
                                    (!bill.actions_recent || bill.actions_recent.length === 0) ? <div className="text-muted-foreground">No recent actions found.</div> :
                                        // If we failed to fetch or haven't fetched yet, maybe show recent? But we are fetching on tab click.
                                        // Actually, if we are loading, we show loading. If done and empty, show empty.
                                        // But initially actions is null.
                                        <div className="text-muted-foreground">No actions found.</div>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="titles">
                    <Card>
                        <CardHeader><CardTitle>Titles</CardTitle></CardHeader>
                        <CardContent>
                            <ul className="list-disc pl-5 space-y-2 text-sm">
                                {loadingTitles ? (
                                    <div className="text-center py-4 text-muted-foreground">Loading titles...</div>
                                ) : titles && titles.length > 0 ? (
                                    titles.map((t: any, i: number) => (
                                        <li key={i}><span className="font-semibold">{t.type}:</span> {t.title}</li>
                                    ))
                                ) : <div className="text-center py-4 text-muted-foreground">No titles available</div>}
                            </ul>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="cosponsors">
                    <Card>
                        <CardHeader><CardTitle>Cosponsors</CardTitle></CardHeader>
                        <CardContent>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {loadingCosponsors ? (
                                    <div className="text-center py-4 text-muted-foreground col-span-full">Loading cosponsors...</div>
                                ) : cosponsors && cosponsors.length > 0 ? (
                                    cosponsors.map((c: any, i: number) => (
                                        <div key={i} className="flex items-center gap-2 border p-2 rounded text-sm">
                                            <div className="font-medium bg-muted w-8 h-8 flex items-center justify-center rounded-full">
                                                {c.party?.[0]}
                                            </div>
                                            <div>
                                                <div className="font-medium">{c.name}</div>
                                                <div className="text-xs text-muted-foreground">{c.state}-{c.party} • {c.sponsorshipDate}</div>
                                            </div>
                                        </div>
                                    ))
                                ) : <div className="text-center py-4 text-muted-foreground col-span-full">No cosponsors found</div>}
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="committees">
                    <Card>
                        <CardHeader><CardTitle>Committees</CardTitle></CardHeader>
                        <CardContent>
                            {loadingCommittees ? (
                                <div className="text-center py-4 text-muted-foreground">Loading committees...</div>
                            ) : committees && committees.length > 0 ? (
                                <ul className="space-y-2">
                                    {committees.map((c: any, i: number) => (
                                        <li key={i} className="flex justify-between border-b pb-2">
                                            <span className="font-medium">{c.name}</span>
                                            <span className="text-xs text-muted-foreground ml-2 capitalize">{c.chamber}</span>
                                        </li>
                                    ))}
                                </ul>
                            ) : <div className="text-center py-4 text-muted-foreground">No committees data available</div>}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="subjects">
                    <Card>
                        <CardHeader><CardTitle>Legislative Subjects</CardTitle></CardHeader>
                        <CardContent>
                            {loadingSubjects ? (
                                <div className="text-center py-4 text-muted-foreground">Loading subjects...</div>
                            ) : subjects && subjects.length > 0 ? (
                                <div className="flex flex-wrap gap-2">
                                    {subjects.map((s: any, i: number) => (
                                        <Badge key={i} variant="outline">{s.name || s}</Badge>
                                    ))}
                                </div>
                            ) : <div className="text-center py-4 text-muted-foreground">No subjects data available</div>}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="amendments">
                    <Card>
                        <CardHeader><CardTitle>Amendments</CardTitle></CardHeader>
                        <CardContent>
                            {loadingAmendments ? (
                                <div className="text-center py-4 text-muted-foreground">Loading amendments...</div>
                            ) : amendments && amendments.length > 0 ? (
                                <div className="space-y-3">
                                    {amendments.map((a: any, i: number) => (
                                        <div key={i} className="border p-3 rounded hover:bg-muted/50 transition-colors">
                                            <div className="font-mono text-xs font-bold">{a.number}</div>
                                            <div className="text-sm mt-1">{a.description || a.purpose}</div>
                                            <div className="text-xs text-muted-foreground mt-1">
                                                Sponsor: {a.sponsor?.firstName} {a.sponsor?.lastName}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : <div className="text-center py-4 text-muted-foreground">No amendments available</div>}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="related">
                    <Card>
                        <CardHeader><CardTitle>Related Bills</CardTitle></CardHeader>
                        <CardContent>
                            {loadingRelated ? (
                                <div className="text-center py-4 text-muted-foreground">Loading related bills...</div>
                            ) : relatedBills && relatedBills.length > 0 ? (
                                <div className="space-y-2">
                                    {relatedBills.map((r: any, i: number) => (
                                        <div key={i} className="border p-3 rounded hover:bg-muted/50 transition-colors">
                                            <div className="font-mono text-xs font-bold">{r.number || r.bill?.number}</div>
                                            <div className="text-sm truncate">{r.title || r.bill?.title}</div>
                                            <div className="text-xs text-muted-foreground mt-1">{r.type || r.relationshipType}</div>
                                        </div>
                                    ))}
                                </div>
                            ) : <div className="text-center py-4 text-muted-foreground">No related bills found</div>}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="comparison">
                    <BillTextComparison billId={billId} textVersions={textVersions || []} />
                </TabsContent>

                <TabsContent value="impact">
                    <AmendmentImpactAnalysis billId={billId} amendments={amendments || []} />
                </TabsContent>
            </div>
        </Tabs>
    );
}
