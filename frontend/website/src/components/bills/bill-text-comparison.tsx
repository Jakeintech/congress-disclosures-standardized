'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ArrowLeftRight, Download, Info } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';

interface BillTextComparisonProps {
    billId: string;
    textVersions: any[];
}

export function BillTextComparison({ billId, textVersions }: BillTextComparisonProps) {
    const [leftVersion, setLeftVersion] = useState<string>('');
    const [rightVersion, setRightVersion] = useState<string>('');
    const [leftText, setLeftText] = useState<string>('');
    const [rightText, setRightText] = useState<string>('');
    const [loading, setLoading] = useState(false);

    const handleCompare = async () => {
        if (!leftVersion || !rightVersion) return;

        setLoading(true);
        try {
            // Fetch both versions
            // TODO: Implement actual API calls
            setLeftText(`[Text for ${leftVersion}]\n\nThis feature requires bill text to be fetched from the backend.\n\nSection 1. Short Title\nThis Act may be cited as the "Example Act".\n\nSection 2. Definitions\nFor purposes of this Act...\n\nSection 3. Amendments\nThe following amendments are made...`);
            setRightText(`[Text for ${rightVersion}]\n\nThis feature requires bill text to be fetched from the backend.\n\nSection 1. Short Title\nThis Act may be cited as the "Example Act of 2025".\n\nSection 2. Definitions\nFor purposes of this Act, the term "qualified entity" means...\n\nSection 3. Amendments\nThe following amendments are made to existing law...`);
        } catch (err) {
            console.error('Failed to load text versions:', err);
        } finally {
            setLoading(false);
        }
    };

    const availableVersions = textVersions && textVersions.length > 0 ? textVersions : [
        { type: 'ih', date: '2025-01-15', name: 'Introduced in House' },
        { type: 'rh', date: '2025-03-20', name: 'Reported in House' },
        { type: 'eh', date: '2025-04-10', name: 'Engrossed in House' },
        { type: 'es', date: '2025-05-01', name: 'Engrossed in Senate' },
    ];

    return (
        <div className="space-y-4">
            <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                    Compare different versions of bill text side-by-side to see what changed between revisions.
                    This feature requires backend implementation to fetch full bill text.
                </AlertDescription>
            </Alert>

            <Card>
                <CardHeader>
                    <CardTitle>Select Versions to Compare</CardTitle>
                    <CardDescription>
                        Choose two versions of the bill to view side-by-side
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-4 md:grid-cols-3">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Left Version</label>
                            <Select value={leftVersion} onValueChange={setLeftVersion}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select version" />
                                </SelectTrigger>
                                <SelectContent>
                                    {availableVersions.map((version: any) => (
                                        <SelectItem key={version.type} value={version.type}>
                                            {version.name} ({version.type.toUpperCase()})
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="flex items-end justify-center">
                            <Button
                                onClick={handleCompare}
                                disabled={!leftVersion || !rightVersion || loading}
                                variant="outline"
                            >
                                <ArrowLeftRight className="h-4 w-4 mr-2" />
                                {loading ? 'Loading...' : 'Compare'}
                            </Button>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium">Right Version</label>
                            <Select value={rightVersion} onValueChange={setRightVersion}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select version" />
                                </SelectTrigger>
                                <SelectContent>
                                    {availableVersions.map((version: any) => (
                                        <SelectItem key={version.type} value={version.type}>
                                            {version.name} ({version.type.toUpperCase()})
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {leftText && rightText && (
                <div className="grid gap-4 md:grid-cols-2">
                    <Card>
                        <CardHeader className="pb-3">
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-base">
                                    {availableVersions.find(v => v.type === leftVersion)?.name}
                                </CardTitle>
                                <Badge variant="outline">
                                    {leftVersion.toUpperCase()}
                                </Badge>
                            </div>
                            <CardDescription className="text-xs">
                                {availableVersions.find(v => v.type === leftVersion)?.date}
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ScrollArea className="h-[600px] w-full rounded border p-4">
                                <pre className="text-sm whitespace-pre-wrap font-mono">
                                    {leftText}
                                </pre>
                            </ScrollArea>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader className="pb-3">
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-base">
                                    {availableVersions.find(v => v.type === rightVersion)?.name}
                                </CardTitle>
                                <Badge variant="outline">
                                    {rightVersion.toUpperCase()}
                                </Badge>
                            </div>
                            <CardDescription className="text-xs">
                                {availableVersions.find(v => v.type === rightVersion)?.date}
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ScrollArea className="h-[600px] w-full rounded border p-4">
                                <pre className="text-sm whitespace-pre-wrap font-mono">
                                    {rightText}
                                </pre>
                            </ScrollArea>
                        </CardContent>
                    </Card>
                </div>
            )}

            {leftText && rightText && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">Analysis Tools</CardTitle>
                    </CardHeader>
                    <CardContent className="flex gap-2">
                        <Button variant="outline" size="sm">
                            <Download className="h-4 w-4 mr-2" />
                            Export Comparison
                        </Button>
                        <Button variant="outline" size="sm">
                            Highlight Differences
                        </Button>
                        <Button variant="outline" size="sm">
                            Show Line Numbers
                        </Button>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
