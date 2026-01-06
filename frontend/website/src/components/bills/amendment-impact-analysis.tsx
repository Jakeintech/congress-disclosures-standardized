'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Info, TrendingUp, TrendingDown, AlertTriangle, Check } from 'lucide-react';

interface AmendmentImpactAnalysisProps {
    billId: string;
    amendments: any[];
}

export function AmendmentImpactAnalysis({ billId, amendments }: AmendmentImpactAnalysisProps) {
    const [analysis, setAnalysis] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Simulate analysis - in production this would call backend
        setTimeout(() => {
            if (amendments && amendments.length > 0) {
                setAnalysis(generateMockAnalysis(amendments));
            } else {
                setAnalysis(generateMockAnalysis([
                    { number: 'SA 001', sponsor: { firstName: 'John', lastName: 'Doe' }, purpose: 'Increase funding for healthcare' },
                    { number: 'SA 002', sponsor: { firstName: 'Jane', lastName: 'Smith' }, purpose: 'Modify eligibility requirements' },
                ]));
            }
            setLoading(false);
        }, 500);
    }, [amendments]);

    if (loading) {
        return (
            <Card>
                <CardContent className="p-12 text-center text-muted-foreground">
                    Analyzing amendments...
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-4">
            <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                    Amendment Impact Analysis uses AI to assess how proposed amendments would affect the bill's scope, cost, and effectiveness.
                    This is a prototype feature that requires backend ML integration.
                </AlertDescription>
            </Alert>

            {/* Summary Cards */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-medium">Total Amendments</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{analysis.totalAmendments}</div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-medium">Cost Impact</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center gap-2">
                            {analysis.costImpact > 0 ? (
                                <TrendingUp className="h-5 w-5 text-red-500" />
                            ) : analysis.costImpact < 0 ? (
                                <TrendingDown className="h-5 w-5 text-green-500" />
                            ) : (
                                <Check className="h-5 w-5 text-muted-foreground" />
                            )}
                            <div className="text-2xl font-bold">
                                {analysis.costImpact > 0 ? '+' : ''}{analysis.costImpact}%
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-medium">Scope Change</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <Badge variant={analysis.scopeChange === 'major' ? 'destructive' : analysis.scopeChange === 'minor' ? 'default' : 'outline'}>
                            {analysis.scopeChange}
                        </Badge>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-medium">Risk Level</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center gap-2">
                            <AlertTriangle className={`h-5 w-5 ${
                                analysis.riskLevel === 'high' ? 'text-red-500' :
                                analysis.riskLevel === 'medium' ? 'text-yellow-500' :
                                'text-green-500'
                            }`} />
                            <div className="text-2xl font-bold capitalize">{analysis.riskLevel}</div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Detailed Analysis */}
            <Tabs defaultValue="summary" className="w-full">
                <TabsList>
                    <TabsTrigger value="summary">Summary</TabsTrigger>
                    <TabsTrigger value="byAmendment">By Amendment</TabsTrigger>
                    <TabsTrigger value="sectors">Affected Sectors</TabsTrigger>
                    <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
                </TabsList>

                <TabsContent value="summary">
                    <Card>
                        <CardHeader>
                            <CardTitle>Overall Impact Summary</CardTitle>
                            <CardDescription>
                                How amendments collectively affect the bill
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ScrollArea className="h-[400px]">
                                <div className="space-y-4">
                                    <div>
                                        <h4 className="font-semibold mb-2">Key Changes</h4>
                                        <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                                            {analysis.keyChanges.map((change: string, i: number) => (
                                                <li key={i}>{change}</li>
                                            ))}
                                        </ul>
                                    </div>

                                    <div>
                                        <h4 className="font-semibold mb-2">Financial Impact</h4>
                                        <p className="text-sm text-muted-foreground">
                                            {analysis.financialImpact}
                                        </p>
                                    </div>

                                    <div>
                                        <h4 className="font-semibold mb-2">Policy Implications</h4>
                                        <p className="text-sm text-muted-foreground">
                                            {analysis.policyImplications}
                                        </p>
                                    </div>
                                </div>
                            </ScrollArea>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="byAmendment">
                    <Card>
                        <CardHeader>
                            <CardTitle>Amendment-by-Amendment Analysis</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <ScrollArea className="h-[400px]">
                                <div className="space-y-3">
                                    {analysis.amendmentDetails.map((amendment: any, i: number) => (
                                        <div key={i} className="border rounded-lg p-4 space-y-2">
                                            <div className="flex items-start justify-between">
                                                <div>
                                                    <div className="font-semibold">{amendment.number}</div>
                                                    <div className="text-sm text-muted-foreground">
                                                        {amendment.purpose}
                                                    </div>
                                                </div>
                                                <Badge variant={amendment.impact === 'positive' ? 'default' : amendment.impact === 'negative' ? 'destructive' : 'outline'}>
                                                    {amendment.impact}
                                                </Badge>
                                            </div>
                                            <div className="text-sm">
                                                <strong>Estimated Cost:</strong> {amendment.estimatedCost}
                                            </div>
                                            <div className="text-sm text-muted-foreground">
                                                {amendment.analysis}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </ScrollArea>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="sectors">
                    <Card>
                        <CardHeader>
                            <CardTitle>Affected Sectors & Industries</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-3">
                                {analysis.affectedSectors.map((sector: any, i: number) => (
                                    <div key={i} className="flex items-center justify-between p-3 border rounded">
                                        <div>
                                            <div className="font-semibold">{sector.name}</div>
                                            <div className="text-sm text-muted-foreground">{sector.description}</div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            {sector.impact === 'positive' ? (
                                                <TrendingUp className="h-5 w-5 text-green-500" />
                                            ) : sector.impact === 'negative' ? (
                                                <TrendingDown className="h-5 w-5 text-red-500" />
                                            ) : (
                                                <div className="h-5 w-5" />
                                            )}
                                            <Badge variant="outline">{sector.magnitude}</Badge>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="recommendations">
                    <Card>
                        <CardHeader>
                            <CardTitle>Analysis Recommendations</CardTitle>
                            <CardDescription>
                                Suggested considerations for stakeholders
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {analysis.recommendations.map((rec: any, i: number) => (
                                    <div key={i} className="border-l-4 border-blue-500 pl-4">
                                        <div className="font-semibold">{rec.title}</div>
                                        <div className="text-sm text-muted-foreground mt-1">{rec.description}</div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}

function generateMockAnalysis(amendments: any[]) {
    return {
        totalAmendments: amendments.length,
        costImpact: 15.5, // percentage
        scopeChange: 'minor',
        riskLevel: 'medium',
        keyChanges: [
            'Expands eligibility criteria for program benefits',
            'Increases funding allocation by $2.5 billion over 5 years',
            'Modifies reporting requirements for participating entities',
            'Adds new enforcement mechanisms for compliance'
        ],
        financialImpact: 'The proposed amendments would increase program costs by an estimated $2.5B over five years, primarily through expanded eligibility and enhanced benefits. However, improved efficiency measures are expected to offset 30% of these costs.',
        policyImplications: 'These amendments significantly broaden the program scope while maintaining core objectives. The expansion may improve outcomes for underserved populations but will require additional administrative capacity.',
        amendmentDetails: amendments.map((a, i) => ({
            number: a.number,
            purpose: a.purpose || a.description,
            impact: i % 2 === 0 ? 'positive' : 'neutral',
            estimatedCost: `$${(Math.random() * 500 + 50).toFixed(1)}M`,
            analysis: `This amendment ${i % 2 === 0 ? 'strengthens' : 'clarifies'} key provisions of the bill by ${i % 3 === 0 ? 'expanding coverage' : i % 3 === 1 ? 'improving efficiency' : 'reducing administrative burden'}. Expected to ${i % 2 === 0 ? 'positively' : 'minimally'} affect implementation timeline.`
        })),
        affectedSectors: [
            { name: 'Healthcare', description: 'Hospitals, insurers, medical device manufacturers', impact: 'positive', magnitude: 'High' },
            { name: 'Technology', description: 'Health IT companies, data analytics firms', impact: 'positive', magnitude: 'Medium' },
            { name: 'Pharmaceuticals', description: 'Drug manufacturers, biotech companies', impact: 'neutral', magnitude: 'Low' },
            { name: 'Insurance', description: 'Health insurance providers, TPAs', impact: 'negative', magnitude: 'Medium' },
        ],
        recommendations: [
            {
                title: 'Monitor Cost Projections',
                description: 'CBO scoring may vary significantly based on participation rates. Request updated estimates after final amendments.'
            },
            {
                title: 'Stakeholder Engagement',
                description: 'Consult affected industry groups, particularly healthcare providers, about implementation feasibility.'
            },
            {
                title: 'Implementation Timeline',
                description: 'Consider phased rollout to manage administrative burden and allow for mid-course corrections.'
            }
        ]
    };
}
