'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { fetchMembers, type MembersParams, type CongressMember } from '@/lib/api';
import { ErrorBoundary, ApiError } from '@/components/ErrorBoundary';

type Member = CongressMember & {
    name?: string; // Computed from first_name + last_name
    trade_count?: number; // Optional trade count from API
};

const STATES = [
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
];

function MembersPage() {
    const [members, setMembers] = useState<Member[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Filters
    const [search, setSearch] = useState('');
    const [party, setParty] = useState('');
    const [chamber, setChamber] = useState('');
    const [state, setState] = useState('');

    useEffect(() => {
        async function loadMembers() {
            setLoading(true);
            setError(null);

            try {
                const params: MembersParams = { limit: 100 };
                if (party) params.party = party as 'D' | 'R' | 'I';
                if (chamber) params.chamber = chamber as 'house' | 'senate';
                if (state) params.state = state;

                const data = await fetchMembers(params);
                // Add computed name field
                const membersWithName = data.map(m => ({
                    ...m,
                    name: m.direct_order_name || `${m.first_name} ${m.last_name}`
                }));
                setMembers(Array.isArray(membersWithName) ? membersWithName : []);
            } catch (err) {
                setError('Failed to load members');
                console.error(err);
            } finally {
                setLoading(false);
            }
        }

        loadMembers();
    }, [party, chamber, state]);

    const filteredMembers = members.filter(member => {
        if (!search) return true;
        const searchLower = search.toLowerCase();
        return (
            member.name?.toLowerCase().includes(searchLower) ||
            member.state?.toLowerCase().includes(searchLower)
        );
    });

    function getPartyColor(party?: string): string {
        switch (party) {
            case 'D': return 'bg-blue-500 text-white';
            case 'R': return 'bg-red-500 text-white';
            default: return 'bg-gray-500 text-white';
        }
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Members of Congress</h1>
                <p className="text-muted-foreground">
                    Browse congressional members and their financial disclosure activity
                </p>
            </div>

            {/* Filters */}
            <Card>
                <CardContent className="pt-6">
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                        <Input
                            placeholder="Search by name..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />

                        <Select value={party || "all"} onValueChange={(val) => setParty(val === "all" ? "" : val)}>
                            <SelectTrigger>
                                <SelectValue placeholder="Party" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All Parties</SelectItem>
                                <SelectItem value="D">Democrat</SelectItem>
                                <SelectItem value="R">Republican</SelectItem>
                                <SelectItem value="I">Independent</SelectItem>
                            </SelectContent>
                        </Select>

                        <Select value={chamber || "all"} onValueChange={(val) => setChamber(val === "all" ? "" : val)}>
                            <SelectTrigger>
                                <SelectValue placeholder="Chamber" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">Both Chambers</SelectItem>
                                <SelectItem value="house">House</SelectItem>
                                <SelectItem value="senate">Senate</SelectItem>
                            </SelectContent>
                        </Select>

                        <Select value={state || "all"} onValueChange={(val) => setState(val === "all" ? "" : val)}>
                            <SelectTrigger>
                                <SelectValue placeholder="State" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All States</SelectItem>
                                {STATES.map(s => (
                                    <SelectItem key={s} value={s}>{s}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                </CardContent>
            </Card>

            {/* Error */}
            {error && <ApiError error={error} onRetry={() => window.location.reload()} />}

            {/* Members Grid */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {loading ? (
                    [...Array(12)].map((_, i) => (
                        <Card key={i}>
                            <CardContent className="pt-6">
                                <div className="flex items-center gap-4">
                                    <Skeleton className="h-12 w-12 rounded-full" />
                                    <div className="space-y-2">
                                        <Skeleton className="h-4 w-32" />
                                        <Skeleton className="h-3 w-20" />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    ))
                ) : filteredMembers.length === 0 ? (
                    <Card className="col-span-full">
                        <CardContent className="py-8 text-center text-muted-foreground">
                            No members found matching your criteria
                        </CardContent>
                    </Card>
                ) : (
                    filteredMembers.filter(m => m.bioguide_id && m.name).map((member) => (
                        <Link key={member.bioguide_id} href={`/politician/${member.bioguide_id}`}>
                            <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full">
                                <CardContent className="pt-6">
                                    <div className="flex items-start gap-4">
                                        <div className={`w-12 h-12 rounded-full flex items-center justify-center text-xl font-bold ${getPartyColor(member.party)}`}>
                                            {member.name?.charAt(0) || '?'}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <h3 className="font-semibold truncate">{member.name}</h3>
                                            <div className="flex items-center gap-2 mt-1">
                                                <Badge variant="outline" className="text-xs">
                                                    {member.party}-{member.state}
                                                </Badge>
                                                {member.chamber && (
                                                    <span className="text-xs text-muted-foreground capitalize">
                                                        {member.chamber}
                                                    </span>
                                                )}
                                            </div>
                                            {member.trade_count !== undefined && member.trade_count > 0 && (
                                                <p className="text-sm text-muted-foreground mt-2">
                                                    {member.trade_count} trades
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </Link>
                    ))
                )}
            </div>
        </div>
    );
}

// Export wrapped in ErrorBoundary
export default function MembersWithErrorBoundary() {
    return (
        <ErrorBoundary>
            <MembersPage />
        </ErrorBoundary>
    );
}
