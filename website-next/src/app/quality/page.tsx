'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { fetchQualityStats, fetchQualityMembers, type QualityStats, type QualityMember } from '@/lib/api-quality';

export default function QualityPage() {
    const [stats, setStats] = useState<QualityStats | null>(null);
    const [members, setMembers] = useState<QualityMember[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Filters
    const [searchTerm, setSearchTerm] = useState('');
    const [partyFilter, setPartyFilter] = useState('');
    const [categoryFilter, setCategoryFilter] = useState('');
    const [statusFilter, setStatusFilter] = useState('all'); // all, flagged, ok

    // Sorting
    const [sortField, setSortField] = useState<keyof QualityMember>('quality_score');
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

    useEffect(() => {
        async function loadData() {
            setLoading(true);
            try {
                // Fetch stats and all members (we filter client-side to match legacy behavior or could move to server)
                // Legacy quality.js fetches /v1/analytics/compliance which returns everything.
                // Our new api fetchQualityMembers calls /quality/members properly if backend supports it.
                // Reverting to legacy endpoint pattern if needed, but let's assume our api-quality.ts logic works.
                // Actually, the legacy code fetched ONE endpoint for everything. 
                // Let's implement independent fetches.

                const [statsData, membersData] = await Promise.all([
                    fetchQualityStats(),
                    fetchQualityMembers({ limit: 1000 }) // Fetch all for client-side filtering
                ]);

                setStats(statsData);
                setMembers(membersData);
            } catch (err) {
                console.error(err);
                setError('Failed to load quality data');
            } finally {
                setLoading(false);
            }
        }

        loadData();
    }, []);

    // Filter Logic
    const filteredMembers = members.filter(member => {
        const searchLower = searchTerm.toLowerCase();
        const matchesSearch =
            member.full_name.toLowerCase().includes(searchLower) ||
            member.state.toLowerCase().includes(searchLower) ||
            (member.district && member.district.toLowerCase().includes(searchLower));

        const matchesParty = !partyFilter || partyFilter === 'all' || member.party === partyFilter;
        const matchesCategory = !categoryFilter || categoryFilter === 'all' || member.quality_category === categoryFilter;

        // Status filter: 'flagged' -> is_hard_to_process=true, 'ok' -> false
        let matchesStatus = true;
        if (statusFilter === 'flagged') matchesStatus = member.is_hard_to_process;
        if (statusFilter === 'ok') matchesStatus = !member.is_hard_to_process;

        return matchesSearch && matchesParty && matchesCategory && matchesStatus;
    });

    // Sort Logic
    const sortedMembers = [...filteredMembers].sort((a, b) => {
        const aVal = a[sortField];
        const bVal = b[sortField];

        if (typeof aVal === 'number' && typeof bVal === 'number') {
            return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
        }

        const aStr = String(aVal || '').toLowerCase();
        const bStr = String(bVal || '').toLowerCase();
        return sortDirection === 'asc' ? aStr.localeCompare(bStr) : bStr.localeCompare(aStr);
    });

    const handleSort = (field: keyof QualityMember) => {
        if (sortField === field) {
            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDirection('desc'); // Default to desc for new metrics
        }
    };

    function exportCSV() {
        const headers = ['Member', 'Party', 'State', 'Total Filings', 'Image PDF %', 'Avg Confidence', 'Quality Score', 'Category', 'Flagged'];
        const rows = sortedMembers.map(m => [
            m.full_name, m.party, `${m.state}-${m.district || ''}`, m.total_filings, m.image_pdf_pct, m.avg_confidence_score, m.quality_score, m.quality_category, m.is_hard_to_process ? 'Yes' : 'No'
        ]);

        const csvContent = [headers.join(','), ...rows.map(row => row.map(cell => `"${cell}"`).join(','))].join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.setAttribute('href', url);
        link.setAttribute('download', `quality_report_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    if (error) {
        return (
            <div className="p-8 text-center text-destructive">
                <h2 className="text-xl font-bold">Error</h2>
                <p>{error}</p>
                <Button className="mt-4" onClick={() => window.location.reload()}>Retry</Button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">🛡️ Document Quality Audit</h1>
                <p className="text-muted-foreground">
                    Tracking the machine-readability and OCR quality of financial disclosures.
                </p>
            </div>

            {/* Stats Overview */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card>
                    <CardHeader className="pb-2"><CardTitle className="text-sm font-medium">Total Members</CardTitle></CardHeader>
                    <CardContent>
                        {loading ? <Skeleton className="h-8 w-16" /> : <div className="text-2xl font-bold">{stats?.total_members || 0}</div>}
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="pb-2"><CardTitle className="text-sm font-medium">Flagged (Hard to Process)</CardTitle></CardHeader>
                    <CardContent>
                        {loading ? <Skeleton className="h-8 w-16" /> : (
                            <div className="text-2xl font-bold text-destructive">{stats?.flagged_members || 0}</div>
                        )}
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="pb-2"><CardTitle className="text-sm font-medium">Avg Quality Score</CardTitle></CardHeader>
                    <CardContent>
                        {loading ? <Skeleton className="h-8 w-16" /> : <div className="text-2xl font-bold">{stats?.avg_quality_score?.toFixed(1) || '-'}</div>}
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="pb-2"><CardTitle className="text-sm font-medium">Last Updated</CardTitle></CardHeader>
                    <CardContent>
                        {loading ? <Skeleton className="h-8 w-16" /> : (
                            <div className="text-sm">{stats?.last_updated ? new Date(stats.last_updated).toLocaleDateString() : 'N/A'}</div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Documentation Alert */}
            <Card className="bg-muted/50">
                <CardContent className="pt-6">
                    <h3 className="font-semibold mb-2">ℹ️ About Quality Scores</h3>
                    <div className="text-sm space-y-1 text-muted-foreground">
                        <p>Scores range from <strong>0-100</strong> based on PDF format and OCR confidence.</p>
                        <ul className="list-disc pl-5">
                            <li><strong>Excellent (90-100):</strong> Native digital PDFs.</li>
                            <li><strong>Good (70-89):</strong> Clean scans, high OCR confidence.</li>
                            <li><strong>Fair (50-69):</strong> Scanned images, mixed quality.</li>
                            <li><strong>Poor (&lt; 50):</strong> Low-quality scans, handwriting.</li>
                        </ul>
                    </div>
                </CardContent>
            </Card>

            {/* Controls */}
            <Card>
                <CardContent className="pt-6">
                    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                        <div className="flex-1 min-w-[200px]">
                            <Input
                                placeholder="Search member, state..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                        </div>
                        <div className="flex flex-wrap gap-2">
                            <Select value={partyFilter} onValueChange={setPartyFilter}>
                                <SelectTrigger className="w-[140px]"><SelectValue placeholder="Party" /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Parties</SelectItem>
                                    <SelectItem value="D">Democrat</SelectItem>
                                    <SelectItem value="R">Republican</SelectItem>
                                </SelectContent>
                            </Select>
                            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                                <SelectTrigger className="w-[140px]"><SelectValue placeholder="Category" /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Categories</SelectItem>
                                    <SelectItem value="Excellent">Excellent</SelectItem>
                                    <SelectItem value="Good">Good</SelectItem>
                                    <SelectItem value="Fair">Fair</SelectItem>
                                    <SelectItem value="Poor">Poor</SelectItem>
                                </SelectContent>
                            </Select>
                            <Select value={statusFilter} onValueChange={setStatusFilter}>
                                <SelectTrigger className="w-[140px]"><SelectValue placeholder="Status" /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Statuses</SelectItem>
                                    <SelectItem value="flagged">Flagged Only</SelectItem>
                                    <SelectItem value="ok">OK Only</SelectItem>
                                </SelectContent>
                            </Select>
                            <Button variant="outline" onClick={exportCSV}>Export CSV</Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Results Table */}
            <Card>
                <CardHeader>
                    <CardTitle>Member Data ({filteredMembers.length})</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="rounded-md border">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('full_name')}>Member</TableHead>
                                    <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('party')}>Party</TableHead>
                                    <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('state')}>State</TableHead>
                                    <TableHead className="cursor-pointer hover:bg-muted text-right" onClick={() => handleSort('total_filings')}>Filings</TableHead>
                                    <TableHead className="cursor-pointer hover:bg-muted text-right" onClick={() => handleSort('image_pdf_pct')}>Image %</TableHead>
                                    <TableHead className="cursor-pointer hover:bg-muted text-right" onClick={() => handleSort('quality_score')}>Score</TableHead>
                                    <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('quality_category')}>Category</TableHead>
                                    <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('is_hard_to_process')}>Status</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    [...Array(5)].map((_, i) => (
                                        <TableRow key={i}>
                                            <TableCell><Skeleton className="h-6 w-32" /></TableCell>
                                            <TableCell><Skeleton className="h-6 w-8" /></TableCell>
                                            <TableCell><Skeleton className="h-6 w-12" /></TableCell>
                                            <TableCell><Skeleton className="h-6 w-10 ml-auto" /></TableCell>
                                            <TableCell><Skeleton className="h-6 w-10 ml-auto" /></TableCell>
                                            <TableCell><Skeleton className="h-6 w-10 ml-auto" /></TableCell>
                                            <TableCell><Skeleton className="h-6 w-20" /></TableCell>
                                            <TableCell><Skeleton className="h-6 w-16" /></TableCell>
                                        </TableRow>
                                    ))
                                ) : sortedMembers.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                                            No members found matching filters.
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    sortedMembers.slice(0, 100).map((member) => (
                                        <TableRow key={member.bioguide_id}>
                                            <TableCell className="font-medium">
                                                <Link href={`/member?id=${member.bioguide_id}`} className="hover:underline">
                                                    {member.full_name}
                                                </Link>
                                            </TableCell>
                                            <TableCell>
                                                <Badge variant={member.party === 'D' ? 'default' : member.party === 'R' ? 'destructive' : 'secondary'} className="w-8 justify-center">
                                                    {member.party}
                                                </Badge>
                                            </TableCell>
                                            <TableCell>{member.state}{member.district ? `-${member.district}` : ''}</TableCell>
                                            <TableCell className="text-right">{member.total_filings}</TableCell>
                                            <TableCell className={`text-right font-bold ${member.image_pdf_pct > 30 ? 'text-destructive' : 'text-green-600'}`}>
                                                {member.image_pdf_pct}%
                                            </TableCell>
                                            <TableCell className="text-right font-bold">
                                                {member.quality_score}
                                            </TableCell>
                                            <TableCell>
                                                <Badge variant="outline" className={
                                                    member.quality_category === 'Excellent' ? 'border-green-500 text-green-700 bg-green-50' :
                                                        member.quality_category === 'Good' ? 'border-blue-500 text-blue-700 bg-blue-50' :
                                                            member.quality_category === 'Fair' ? 'border-yellow-500 text-yellow-700 bg-yellow-50' :
                                                                'border-red-500 text-red-700 bg-red-50'
                                                }>
                                                    {member.quality_category}
                                                </Badge>
                                            </TableCell>
                                            <TableCell>
                                                {member.is_hard_to_process ? (
                                                    <Badge variant="destructive">⚠️ Flagged</Badge>
                                                ) : (
                                                    <Badge variant="secondary" className="text-green-600">✓ OK</Badge>
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>
                    {sortedMembers.length > 100 && (
                        <p className="text-xs text-center text-muted-foreground mt-4">
                            Showing top 100 of {sortedMembers.length} results. Use filters to narrow down.
                        </p>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
