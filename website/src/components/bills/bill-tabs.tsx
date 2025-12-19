"use client";

import { useState, useMemo } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Download, FileText, Users, Landmark, Tag, Layers, Link as LinkIcon, History, FileSearch, BarChart3 } from 'lucide-react';
import { BillActions } from './bill-actions';
import { BillCosponsors } from './bill-cosponsors';
import { BillSubjects } from './bill-subjects';
import { BillAmendments } from './bill-amendments';
import { RelatedBills } from './related-bills';
import { BillSummary } from './bill-summary-tab';
import { BillTimeline, type TimelineEvent } from './bill-timeline';
import { AmendmentImpactAnalysis } from './amendment-impact-analysis';
import { DataContainer } from '@/components/ui/data-container';
import { useBillText, useBillTitles, useBillActions } from '@/hooks/use-api';
import { type Bill } from '@/types/api';

interface BillTabsProps {
    bill: Bill;
    textVersions?: any[];
    cosponsorsCount: number;
    actionsCount: number;
    billId: string;
}

export function BillTabs({ bill, textVersions, cosponsorsCount, actionsCount, billId }: BillTabsProps) {
    const [selectedVersion, setSelectedVersion] = useState<number>(0);
    const [activeTab, setActiveTab] = useState<string>("summary");

    // We still need actions for the timeline and summaries for some basic info
    const actionsQuery = useBillActions(billId);
    const titlesQuery = useBillTitles(billId);
    const textQuery = useBillText(billId);

    // Convert actions to timeline events
    const timelineEvents = useMemo(() => {
        const actions = (actionsQuery.data as any)?.actions || [];
        return actions.map((action: any, index: number): TimelineEvent => {
            const isLatest = index === 0;
            return {
                date: action.action_date || action.date,
                title: action.action_text || action.text || 'Action taken',
                description: action.description,
                status: isLatest ? 'current' : 'completed',
                chamber: action.chamber,
                tradeAlert: false,
                tradeCount: 0,
            };
        });
    }, [actionsQuery.data]);

    // Format text content from HTML if needed
    const textContent = useMemo(() => {
        const data = textQuery.data as any;
        if (!data?.content) return null;

        try {
            const parser = new DOMParser();
            const doc = parser.parseFromString(data.content, 'text/html');
            const pre = doc.querySelector('pre');
            return pre?.textContent || data.content;
        } catch (e) {
            return data.content;
        }
    }, [textQuery.data]);

    return (
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="w-full justify-start overflow-x-auto h-auto flex-wrap gap-1 p-1 bg-background border-b rounded-none mb-6">
                <TabsTrigger value="summary" className="gap-2">
                    <FileSearch className="h-4 w-4" /> Summary
                </TabsTrigger>
                <TabsTrigger value="timeline" className="gap-2">
                    <History className="h-4 w-4" /> Timeline
                </TabsTrigger>
                <TabsTrigger value="text" className="gap-2">
                    <FileText className="h-4 w-4" /> Text
                </TabsTrigger>
                <TabsTrigger value="actions" className="gap-2">
                    <Layers className="h-4 w-4" /> Actions
                    <Badge variant="secondary" className="ml-1 text-[10px] h-4 min-w-4 flex items-center justify-center">
                        {actionsCount}
                    </Badge>
                </TabsTrigger>
                <TabsTrigger value="titles" className="gap-2">
                    <Tag className="h-4 w-4" /> Titles
                </TabsTrigger>
                <TabsTrigger value="cosponsors" className="gap-2">
                    <Users className="h-4 w-4" /> Cosponsors
                    {cosponsorsCount > 0 && (
                        <Badge variant="secondary" className="ml-1 text-[10px] h-4 min-w-4 flex items-center justify-center">
                            {cosponsorsCount}
                        </Badge>
                    )}
                </TabsTrigger>
                <TabsTrigger value="committees" className="gap-2">
                    <Landmark className="h-4 w-4" /> Committees
                </TabsTrigger>
                <TabsTrigger value="subjects" className="gap-2">
                    <Tag className="h-4 w-4" /> Subjects
                </TabsTrigger>
                <TabsTrigger value="amendments" className="gap-2">
                    <Layers className="h-4 w-4" /> Amendments
                </TabsTrigger>
                <TabsTrigger value="related" className="gap-2">
                    <LinkIcon className="h-4 w-4" /> Related
                </TabsTrigger>
                <TabsTrigger value="impact" className="gap-2">
                    <BarChart3 className="h-4 w-4" /> AI Impact
                </TabsTrigger>
            </TabsList>

            <div className="space-y-4">
                <TabsContent value="summary">
                    <BillSummary billId={billId} initialData={bill.summary ? { text: bill.summary } as any : undefined} />
                </TabsContent>

                <TabsContent value="timeline">
                    <DataContainer
                        isLoading={actionsQuery.isLoading}
                        isError={actionsQuery.isError}
                        data={timelineEvents}
                        emptyMessage="No legislative timeline data available."
                        onRetry={() => actionsQuery.refetch()}
                    >
                        <BillTimeline events={timelineEvents} billId={billId} />
                    </DataContainer>
                </TabsContent>

                <TabsContent value="text">
                    <Card className="border-none shadow-none bg-accent/5">
                        <CardHeader className="px-0 pt-0">
                            <div className="flex flex-wrap items-center justify-between gap-4">
                                <div className="space-y-1">
                                    <CardTitle className="text-lg">Bill Text</CardTitle>
                                    <CardDescription>
                                        Full legislative text of the measure
                                    </CardDescription>
                                </div>
                                {textVersions && textVersions.length > 0 && (
                                    <div className="flex items-center gap-2">
                                        <Select
                                            value={selectedVersion.toString()}
                                            onValueChange={(v) => setSelectedVersion(parseInt(v))}
                                        >
                                            <SelectTrigger className="w-[200px] h-9">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {textVersions.map((v: any, i: number) => (
                                                    <SelectItem key={i} value={i.toString()}>
                                                        {v.type} ({new Date(v.date).toLocaleDateString()})
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        <Button variant="outline" size="sm" asChild>
                                            <a href={textVersions[selectedVersion]?.formats?.[0]?.url} target="_blank" rel="noopener noreferrer">
                                                <Download className="h-4 w-4 mr-2" /> PDF
                                            </a>
                                        </Button>
                                    </div>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent className="px-0">
                            <DataContainer
                                isLoading={textQuery.isLoading}
                                isError={textQuery.isError}
                                data={textContent}
                                emptyMessage="Text not yet available for this version."
                                onRetry={() => textQuery.refetch()}
                            >
                                <ScrollArea className="h-[600px] w-full rounded-xl border bg-background p-6">
                                    <pre className="text-xs font-mono whitespace-pre-wrap leading-relaxed text-foreground/90">{textContent}</pre>
                                </ScrollArea>
                            </DataContainer>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="actions">
                    <BillActions billId={billId} />
                </TabsContent>

                <TabsContent value="titles">
                    <Card className="border-none shadow-none bg-accent/5">
                        <CardHeader className="px-0 pt-0">
                            <CardTitle className="text-lg">Official Titles</CardTitle>
                        </CardHeader>
                        <CardContent className="px-0">
                            <DataContainer
                                isLoading={titlesQuery.isLoading}
                                isError={titlesQuery.isError}
                                data={(titlesQuery.data as any)?.titles}
                                onRetry={() => titlesQuery.refetch()}
                            >
                                <div className="grid gap-3">
                                    {(titlesQuery.data as any)?.titles?.map((t: any, i: number) => (
                                        <div key={i} className="p-4 bg-background rounded-xl border">
                                            <Badge variant="secondary" className="mb-2 text-[10px] uppercase">{t.type}</Badge>
                                            <p className="text-sm font-medium leading-relaxed">{t.title}</p>
                                        </div>
                                    ))}
                                </div>
                            </DataContainer>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="cosponsors">
                    <BillCosponsors billId={billId} />
                </TabsContent>

                <TabsContent value="committees">
                    <Card className="border-none shadow-none bg-accent/5">
                        <CardHeader className="px-0 pt-0">
                            <CardTitle className="text-lg">Assigned Committees</CardTitle>
                        </CardHeader>
                        <CardContent className="px-0">
                            <div className="bg-background rounded-xl border divide-y">
                                <p className="p-4 text-sm text-muted-foreground italic">Committee data integrated with actions and legislative timeline.</p>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="subjects">
                    <BillSubjects billId={billId} />
                </TabsContent>

                <TabsContent value="amendments">
                    <BillAmendments billId={billId} />
                </TabsContent>

                <TabsContent value="related">
                    <RelatedBills billId={billId} />
                </TabsContent>

                <TabsContent value="impact">
                    <AmendmentImpactAnalysis billId={billId} amendments={[]} />
                </TabsContent>
            </div>
        </Tabs>
    );
}
