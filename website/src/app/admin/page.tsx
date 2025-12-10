'use client';

import { useEffect, useState, useMemo } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';

// Since we know the bucket URL pattern from legacy
const S3_BUCKET = "congress-disclosures-standardized";
const S3_REGION = "us-east-1";
const API_BASE = `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com`;

interface DocumentMsg {
    doc_id: string;
    filing_type?: string;
    year?: string;
    member_name?: string;
    first_name?: string;
    last_name?: string;
    extraction_status?: string;
}

interface Manifest {
    filings?: DocumentMsg[];
    documents?: DocumentMsg[]; // Silver manifest structure
}

export default function AdminPage() {
    const [allDocs, setAllDocs] = useState<DocumentMsg[]>([]);
    const [filteredDocs, setFilteredDocs] = useState<DocumentMsg[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedDoc, setSelectedDoc] = useState<DocumentMsg | null>(null);
    const [search, setSearch] = useState('');
    const [filingType, setFilingType] = useState('all');

    // Load Manifests
    useEffect(() => {
        async function loadManifests() {
            try {
                // Fetch Bronze and Silver manifests
                const [bronzeRes, silverRes] = await Promise.allSettled([
                    fetch(`${API_BASE}/website/api/v1/documents/manifest.json`),
                    fetch(`${API_BASE}/website/api/v1/documents/silver/manifest.json`)
                ]);

                let bronzeDocs: DocumentMsg[] = [];
                let silverMap = new Map<string, DocumentMsg>();

                if (bronzeRes.status === 'fulfilled') {
                    const data = await bronzeRes.value.json();
                    bronzeDocs = data.filings || [];
                }

                if (silverRes.status === 'fulfilled') {
                    try {
                        const data = await silverRes.value.json();
                        (data.documents || []).forEach((d: DocumentMsg) => {
                            if (d.doc_id) silverMap.set(String(d.doc_id), d);
                        });
                    } catch (e) {
                        console.warn('Silver manifest parse error', e);
                    }
                }

                // Merge: Use Bronze as base, enrich with Silver status
                const merged = bronzeDocs.map(doc => {
                    const silver = silverMap.get(String(doc.doc_id));
                    return {
                        ...doc,
                        extraction_status: silver?.extraction_status || 'none',
                        member_name: silver?.member_name || doc.member_name || `${doc.first_name || ''} ${doc.last_name || ''}`.trim()
                    };
                });

                setAllDocs(merged);
                setFilteredDocs(merged);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        }
        loadManifests();
    }, []);

    // Filter Logic
    useEffect(() => {
        const lowerSearch = search.toLowerCase();
        const filtered = allDocs.filter(doc => {
            const matchesSearch = !search ||
                String(doc.doc_id).includes(lowerSearch) ||
                (doc.member_name && doc.member_name.toLowerCase().includes(lowerSearch)) ||
                (doc.year && String(doc.year).includes(lowerSearch));

            const matchesType = filingType === 'all' || doc.filing_type === filingType;

            return matchesSearch && matchesType;
        });
        setFilteredDocs(filtered);
    }, [search, filingType, allDocs]);

    return (
        <div className="flex h-[calc(100vh-4rem)] flex-col">
            <header className="border-b bg-background px-4 py-3 flex items-center justify-between">
                <h1 className="text-xl font-bold">Admin Document Viewer</h1>
                <div className="flex items-center gap-2">
                    <Badge variant="outline">{filteredDocs.length} Docs</Badge>
                </div>
            </header>

            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar List */}
                <div className="w-80 border-r bg-muted/10 flex flex-col">
                    <div className="p-3 space-y-3 border-b">
                        <Input
                            placeholder="Search ID, Name, Year..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                        <Select value={filingType} onValueChange={setFilingType}>
                            <SelectTrigger>
                                <SelectValue placeholder="Filter Type" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All Types</SelectItem>
                                <SelectItem value="P">PTR</SelectItem>
                                <SelectItem value="A">Annual</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <ScrollArea className="flex-1">
                        <div className="p-2 space-y-1">
                            {loading ? (
                                <p className="text-sm text-muted-foreground p-4 text-center">Loading manifests...</p>
                            ) : filteredDocs.slice(0, 100).map(doc => (
                                <div
                                    key={doc.doc_id}
                                    onClick={() => setSelectedDoc(doc)}
                                    className={`p-2 rounded-md cursor-pointer text-sm hover:bg-muted ${selectedDoc?.doc_id === doc.doc_id ? 'bg-primary/10 border border-primary/20' : ''}`}
                                >
                                    <div className="flex justify-between font-mono font-semibold">
                                        <span>{doc.doc_id}</span>
                                        <StatusIcon status={doc.extraction_status} />
                                    </div>
                                    <div className="truncate text-muted-foreground">{doc.member_name || 'Unknown'}</div>
                                    <div className="flex gap-2 text-xs mt-1">
                                        <Badge variant="secondary" className="h-5 px-1">{doc.filing_type}</Badge>
                                        <span>{doc.year}</span>
                                    </div>
                                </div>
                            ))}
                            {filteredDocs.length > 100 && (
                                <p className="text-xs text-center text-muted-foreground py-2">
                                    + {filteredDocs.length - 100} more
                                </p>
                            )}
                        </div>
                    </ScrollArea>
                </div>

                {/* Main Content (Split View Shim) */}
                <div className="flex-1 flex overflow-hidden">
                    {selectedDoc ? (
                        <div className="flex-1 flex flex-col md:flex-row h-full">
                            {/* PDF View - Using simple iframe for V1 */}
                            <div className="flex-1 border-r bg-slate-100 flex flex-col relative group">
                                <div className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <Button size="sm" variant="secondary" asChild>
                                        <a href={getPdfUrl(selectedDoc)} target="_blank" rel="noopener noreferrer">Open Ext ↗</a>
                                    </Button>
                                </div>
                                <iframe
                                    src={getPdfUrl(selectedDoc)}
                                    className="w-full h-full border-0"
                                    title="PDF Viewer"
                                />
                            </div>

                            {/* Data View */}
                            <div className="w-full md:w-[400px] bg-background border-l overflow-y-auto p-4 space-y-6">
                                <div>
                                    <h2 className="text-lg font-bold mb-2">Metadata</h2>
                                    <dl className="grid grid-cols-2 gap-2 text-sm">
                                        <dt className="text-muted-foreground">Doc ID</dt>
                                        <dd className="font-mono">{selectedDoc.doc_id}</dd>
                                        <dt className="text-muted-foreground">Member</dt>
                                        <dd>{selectedDoc.member_name}</dd>
                                        <dt className="text-muted-foreground">Year</dt>
                                        <dd>{selectedDoc.year}</dd>
                                        <dt className="text-muted-foreground">Type</dt>
                                        <dd>{selectedDoc.filing_type}</dd>
                                        <dt className="text-muted-foreground">Status</dt>
                                        <dd>{selectedDoc.extraction_status}</dd>
                                    </dl>
                                </div>
                                <Separator />
                                <div>
                                    <h2 className="text-lg font-bold mb-2">Raw Data</h2>
                                    <div className="bg-muted p-2 rounded-md overflow-x-auto">
                                        <pre className="text-xs font-mono">
                                            {JSON.stringify(selectedDoc, null, 2)}
                                        </pre>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="flex-1 flex items-center justify-center text-muted-foreground">
                            Select a document to view
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function StatusIcon({ status }: { status?: string }) {
    if (status === 'success') return <span className="text-green-500">✓</span>;
    if (status === 'pending') return <span className="text-yellow-500">⏳</span>;
    if (status === 'failed') return <span className="text-red-500">✗</span>;
    return <span className="text-slate-300">•</span>;
}

function getPdfUrl(doc: DocumentMsg) {
    // Construct PDF URL similar to legacy admin.js logic
    const year = doc.year || '2025';
    // Use Bronze URL pattern, or fallback to Congress.gov
    // https://disclosures-clerk.house.gov/public_disc/financial-pdfs/2024/10061234.pdf
    return `https://disclosures-clerk.house.gov/public_disc/financial-pdfs/${year}/${doc.doc_id}.pdf`;
}
