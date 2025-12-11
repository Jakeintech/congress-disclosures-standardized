'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Users, Building2, FileText, Info } from 'lucide-react';
import { fetchCommittees } from '@/lib/api';

interface Committee {
    systemCode: string;
    name: string;
    chamber: string;
    type: string;
    subcommittees?: any[];
}

export default function CommitteesPage() {
    const [committees, setCommittees] = useState<Committee[]>([]);
    const [loading, setLoading] = useState(true);
    const [chamberFilter, setChamberFilter] = useState('all');
    const [search, setSearch] = useState('');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadCommittees() {
            setLoading(true);
            try {
                const data = await fetchCommittees(119);

                // If API returns empty, display a message
                if (!data || (Array.isArray(data) && data.length === 0)) {
                    setCommittees([]);
                    setError('No committees found. Please check your connection or try again later.');
                } else {
                    setCommittees(Array.isArray(data) ? data : []);
                    setError(null);
                }
            } catch (err) {
                console.error('Failed to load committees:', err);
                setCommittees([]);
                setError('Failed to load committees from Congress.gov. Please try again later.');
            } finally {
                setLoading(false);
            }
        }
        loadCommittees();
    }, []);

    const filteredCommittees = committees.filter(committee => {
        const matchesChamber = chamberFilter === 'all' || committee.chamber === chamberFilter;
        const matchesSearch = !search || committee.name.toLowerCase().includes(search.toLowerCase());
        return matchesChamber && matchesSearch;
    });

    const houseCounts = committees.filter(c => c.chamber === 'House').length;
    const senateCounts = committees.filter(c => c.chamber === 'Senate').length;
    const jointCounts = committees.filter(c => c.chamber === 'Joint').length;

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Congressional Committees</h1>
                <p className="text-muted-foreground mt-2">
                    Explore House and Senate committees, subcommittees, and their legislative activities
                </p>
            </div>

            {error && (
                <Alert>
                    <Info className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            {/* Stats */}
            <div className="grid gap-4 md:grid-cols-3">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">House Committees</CardTitle>
                        <Building2 className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {loading ? <Skeleton className="h-8 w-16" /> : <div className="text-2xl font-bold">{houseCounts}</div>}
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Senate Committees</CardTitle>
                        <Building2 className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {loading ? <Skeleton className="h-8 w-16" /> : <div className="text-2xl font-bold">{senateCounts}</div>}
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Joint Committees</CardTitle>
                        <Building2 className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        {loading ? <Skeleton className="h-8 w-16" /> : <div className="text-2xl font-bold">{jointCounts}</div>}
                    </CardContent>
                </Card>
            </div>

            {/* Filters */}
            <Card>
                <CardHeader>
                    <CardTitle>Filter Committees</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-4 md:grid-cols-2">
                        <div>
                            <Input
                                placeholder="Search committees..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                            />
                        </div>
                        <div>
                            <Select value={chamberFilter} onValueChange={setChamberFilter}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Chambers</SelectItem>
                                    <SelectItem value="House">House</SelectItem>
                                    <SelectItem value="Senate">Senate</SelectItem>
                                    <SelectItem value="Joint">Joint</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Committees List */}
            {loading ? (
                <div className="grid gap-4 md:grid-cols-2">
                    {[...Array(6)].map((_, i) => (
                        <Card key={i}>
                            <CardContent className="p-6">
                                <Skeleton className="h-24 w-full" />
                            </CardContent>
                        </Card>
                    ))}
                </div>
            ) : (
                <div className="grid gap-4 md:grid-cols-2">
                    {filteredCommittees.map((committee) => (
                        <Link
                            key={committee.systemCode}
                            href={`/committees/${committee.chamber.toLowerCase()}/${committee.systemCode}`}
                        >
                            <Card className="h-full hover:shadow-lg transition-shadow cursor-pointer">
                                <CardHeader>
                                    <div className="flex items-start justify-between">
                                        <CardTitle className="text-lg line-clamp-2">{committee.name}</CardTitle>
                                        <Badge variant={
                                            committee.chamber === 'House' ? 'default' :
                                                committee.chamber === 'Senate' ? 'secondary' : 'outline'
                                        }>
                                            {committee.chamber}
                                        </Badge>
                                    </div>
                                    <CardDescription>{committee.type}</CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <div className="flex gap-4 text-sm text-muted-foreground">
                                        <div className="flex items-center gap-1">
                                            <Users className="h-4 w-4" />
                                            <span>{committee.subcommittees?.length || 0} subcommittees</span>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <FileText className="h-4 w-4" />
                                            <span>View bills</span>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </Link>
                    ))}
                </div>
            )}

            {!loading && filteredCommittees.length === 0 && (
                <Card>
                    <CardContent className="p-12 text-center text-muted-foreground">
                        No committees found matching your filters.
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
