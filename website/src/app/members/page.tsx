'use client';

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { useMembers } from '@/hooks/use-api';
import { DataContainer } from '@/components/ui/data-container';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { MembersParams, CongressMember } from '@/types/api';

/**
 * Small member photo with fallback to initials
 */
function MemberPhotoSmall({ bioguideId, name, party }: { bioguideId: string, name?: string, party?: string }) {
    const [imageError, setImageError] = useState(false);
    const photoUrl = `https://bioguide.congress.gov/bioguide/photo/${bioguideId.charAt(0)}/${bioguideId}.jpg`;

    function getPartyColor(party?: string): string {
        switch (party) {
            case 'D': return 'bg-blue-500 text-white';
            case 'R': return 'bg-red-500 text-white';
            default: return 'bg-gray-500 text-white';
        }
    }

    if (imageError) {
        return (
            <div className={`w-12 h-12 rounded-full flex items-center justify-center text-xl font-bold ${getPartyColor(party)}`}>
                {name?.charAt(0) || '?'}
            </div>
        );
    }

    return (
        <div className="w-12 h-12 rounded-full overflow-hidden bg-gray-200 flex items-center justify-center flex-shrink-0">
            <Image
                src={photoUrl}
                alt={name || 'Member photo'}
                width={48}
                height={48}
                className="object-cover"
                onError={() => setImageError(true)}
                unoptimized
            />
        </div>
    );
}

const STATES = [
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
];

function MembersPage() {
    // Filters & Pagination
    const [search, setSearch] = useState('');
    const [party, setParty] = useState('');
    const [chamber, setChamber] = useState('');
    const [state, setState] = useState('');
    const [sortBy, setSortBy] = useState<'total_volume' | 'total_trades' | 'name'>('total_volume');
    const [page, setPage] = useState(1);
    const limit = 50;

    const params: MembersParams = {
        limit,
        offset: (page - 1) * limit,
        sortBy,
        sortOrder: 'desc'
    };
    if (party) params.party = party as 'D' | 'R' | 'I';
    if (chamber) params.chamber = chamber as 'house' | 'senate';
    if (state) params.state = state;

    const membersQuery = useMembers(params);
    const membersData = membersQuery.data || { data: [], pagination: { total: 0, count: 0, limit: 50, offset: 0 } };
    const members = membersData.data;
    const totalCount = membersData.pagination.total;

    // Client-side search for the current page
    const filteredMembers = members.filter(member => {
        if (!search) return true;
        const searchLower = search.toLowerCase();
        const fullName = `${member.first_name} ${member.last_name}`.toLowerCase();
        return (
            fullName.includes(searchLower) ||
            member.state?.toLowerCase().includes(searchLower)
        );
    });

    const totalPages = Math.ceil(totalCount / limit);

    function formatVolume(val?: number) {
        if (!val) return '$0';
        if (val >= 1000000) return `$${(val / 1000000).toFixed(1)}M`;
        if (val >= 1000) return `$${(val / 1000).toFixed(0)}K`;
        return `$${val.toFixed(0)}`;
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Members of Congress</h1>
                    <p className="text-muted-foreground">
                        Browse congressional members and their financial disclosure activity
                    </p>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Badge variant="outline">{totalCount} Members</Badge>
                </div>
            </div>

            {/* Filters */}
            <Card>
                <CardContent className="pt-6">
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                        <Input
                            placeholder="Search page..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />

                        <Select value={party || "all"} onValueChange={(val) => { setParty(val === "all" ? "" : val); setPage(1); }}>
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

                        <Select value={chamber || "all"} onValueChange={(val) => { setChamber(val === "all" ? "" : val); setPage(1); }}>
                            <SelectTrigger>
                                <SelectValue placeholder="Chamber" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">Both Chambers</SelectItem>
                                <SelectItem value="house">House</SelectItem>
                                <SelectItem value="senate">Senate</SelectItem>
                            </SelectContent>
                        </Select>

                        <Select value={state || "all"} onValueChange={(val) => { setState(val === "all" ? "" : val); setPage(1); }}>
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

                        <Select value={sortBy} onValueChange={(val: any) => { setSortBy(val); setPage(1); }}>
                            <SelectTrigger>
                                <SelectValue placeholder="Sort By" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="total_volume">Most Active (Volume)</SelectItem>
                                <SelectItem value="total_trades">Most Active (Trades)</SelectItem>
                                <SelectItem value="name">Name (A-Z)</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                </CardContent>
            </Card>

            <DataContainer
                isLoading={membersQuery.isLoading}
                isError={membersQuery.isError}
                error={membersQuery.error}
                data={members}
                emptyMessage="No members found matching your criteria"
                onRetry={() => membersQuery.refetch()}
                loadingSkeleton={<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {[...Array(12)].map((_, i) => (
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
                    ))}
                </div>}
            >
                {() => (
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                        {filteredMembers.map((member) => (
                            <Link key={member.bioguide_id || `${member.first_name}-${member.last_name}`} href={`/politician/${member.bioguide_id}`}>
                                <Card className="hover:bg-muted/50 transition-colors cursor-pointer h-full border-t-4 data-[party=D]:border-t-blue-500 data-[party=R]:border-t-red-500" data-party={member.party}>
                                    <CardContent className="pt-6">
                                        <div className="flex items-start gap-4">
                                            <MemberPhotoSmall
                                                bioguideId={member.bioguide_id || 'UNKNOWN'}
                                                name={`${member.first_name} ${member.last_name}`}
                                                party={member.party}
                                            />
                                            <div className="flex-1 min-w-0">
                                                <h3 className="font-semibold truncate">
                                                    {member.first_name} {member.last_name}
                                                </h3>
                                                <div className="flex items-center gap-2 mt-1">
                                                    <Badge variant="outline" className="text-[10px] px-1 h-4">
                                                        {member.party}-{member.state}
                                                    </Badge>
                                                    <span className="text-[10px] text-muted-foreground uppercase font-medium">
                                                        {member.chamber}
                                                    </span>
                                                </div>

                                                <div className="grid grid-cols-2 gap-2 mt-4 pt-4 border-t border-muted">
                                                    <div>
                                                        <p className="text-[10px] text-muted-foreground uppercase">Volume (Est)</p>
                                                        <p className="text-sm font-bold text-primary">
                                                            {formatVolume(member.total_volume)}
                                                        </p>
                                                    </div>
                                                    <div>
                                                        <p className="text-[10px] text-muted-foreground uppercase">Trades</p>
                                                        <p className="text-sm font-bold text-primary">
                                                            {member.total_trades || 0}
                                                        </p>
                                                    </div>
                                                </div>

                                                {member.last_trade_date && (
                                                    <p className="text-[10px] text-muted-foreground mt-2 italic">
                                                        Last trade: {member.last_trade_date}
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            </Link>
                        ))}
                    </div>
                )}
            </DataContainer>

            {/* Pagination */}
            {!membersQuery.isLoading && totalPages > 1 && (
                <div className="flex items-center justify-center gap-2 pt-8">
                    <button
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page === 1}
                        className="px-4 py-2 text-sm font-medium border rounded-md hover:bg-muted disabled:opacity-50"
                    >
                        Previous
                    </button>
                    <span className="text-sm text-muted-foreground">
                        Page {page} of {totalPages}
                    </span>
                    <button
                        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                        disabled={page === totalPages}
                        className="px-4 py-2 text-sm font-medium border rounded-md hover:bg-muted disabled:opacity-50"
                    >
                        Next
                    </button>
                </div>
            )}
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
