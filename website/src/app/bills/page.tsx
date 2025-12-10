'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { fetchBills, type BillsParams } from '@/lib/api';
import { ErrorBoundary, ApiError } from '@/components/ErrorBoundary';

interface Bill {
    bill_id?: string;
    congress: number;
    bill_type: string;
    bill_number: number;
    title: string;
    sponsor_name?: string;
    sponsor_bioguide_id?: string;
    cosponsors_count?: number;
    latest_action_date?: string;
    latest_action_text?: string;
    top_industry_tags?: string[];
    trade_correlations_count?: number;
}

const INDUSTRIES = [
    'Defense', 'Healthcare', 'Finance', 'Energy',
    'Technology', 'Agriculture', 'Transportation', 'Real Estate'
];

const BILL_TYPES = [
    { value: 'hr', label: 'House Bills (H.R.)' },
    { value: 's', label: 'Senate Bills (S.)' },
    { value: 'hjres', label: 'House Joint Resolutions' },
    { value: 'sjres', label: 'Senate Joint Resolutions' },
];

function BillsPage() {
    const [bills, setBills] = useState<Bill[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Filters - using default values
    const [congress, setCongress] = useState<string>('119');
    const [billType, setBillType] = useState<string>('');
    const [industry, setIndustry] = useState<string>('');
    const [search, setSearch] = useState<string>('');
    const [hasCorrelations, setHasCorrelations] = useState<boolean>(false);

    useEffect(() => {
        async function loadBills() {
            setLoading(true);
            setError(null);

            try {
                const params: BillsParams = {
                    limit: 50,
                    sortBy: 'latest_action_date',
                    sortOrder: 'desc',
                };

                if (congress) params.congress = parseInt(congress, 10);
                if (billType) params.billType = billType;
                if (industry) params.industry = industry;
                if (hasCorrelations) params.hasTradeCorrelations = true;

                const data = await fetchBills(params);
                setBills(Array.isArray(data) ? (data as Bill[]) : []);
            } catch (err) {
                setError('Failed to load bills');
                console.error(err);
            } finally {
                setLoading(false);
            }
        }

        loadBills();
    }, [congress, billType, industry, hasCorrelations]);

    const filteredBills = bills.filter(bill => {
        if (!search) return true;
        const searchLower = search.toLowerCase();
        return (
            bill.title?.toLowerCase().includes(searchLower) ||
            bill.sponsor_name?.toLowerCase().includes(searchLower) ||
            `${bill.bill_type}-${bill.bill_number}`.toLowerCase().includes(searchLower)
        );
    });

    function getBillId(bill: Bill): string {
        return bill.bill_id || `${bill.congress}-${bill.bill_type}-${bill.bill_number}`;
    }

    function formatDate(dateStr?: string): string {
        if (!dateStr) return 'N/A';
        try {
            return new Date(dateStr).toLocaleDateString('en-US', {
                year: 'numeric', month: 'short', day: 'numeric'
            });
        } catch {
            return dateStr;
        }
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Bills</h1>
                <p className="text-muted-foreground">
                    Browse congressional legislation with trade correlation analysis
                </p>
            </div>

            {/* Filters */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-lg">Filters</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                        {/* Search */}
                        <div className="lg:col-span-2">
                            <Input
                                placeholder="Search bills by title or sponsor..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                            />
                        </div>

                        {/* Congress */}
                        <Select value={congress} onValueChange={setCongress}>
                            <SelectTrigger>
                                <SelectValue placeholder="Congress" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="119">119th Congress (Current)</SelectItem>
                                <SelectItem value="118">118th Congress</SelectItem>
                                <SelectItem value="117">117th Congress</SelectItem>
                                <SelectItem value="116">116th Congress</SelectItem>
                            </SelectContent>
                        </Select>

                        {/* Bill Type */}
                        <Select value={billType || "all"} onValueChange={(val) => setBillType(val === "all" ? "" : val)}>
                            <SelectTrigger>
                                <SelectValue placeholder="Bill Type" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All Types</SelectItem>
                                {BILL_TYPES.map(type => (
                                    <SelectItem key={type.value} value={type.value}>
                                        {type.label}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>

                        {/* Industry */}
                        <Select value={industry || "all"} onValueChange={(val) => setIndustry(val === "all" ? "" : val)}>
                            <SelectTrigger>
                                <SelectValue placeholder="Industry" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All Industries</SelectItem>
                                {INDUSTRIES.map(ind => (
                                    <SelectItem key={ind} value={ind}>{ind}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="flex items-center gap-4 mt-4">
                        <Button
                            variant={hasCorrelations ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setHasCorrelations(!hasCorrelations)}
                        >
                            ⚠️ Has Trade Correlations
                        </Button>

                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                                setCongress('119');
                                setBillType('');
                                setIndustry('');
                                setSearch('');
                                setHasCorrelations(false);
                            }}
                        >
                            Clear Filters
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Error */}
            {error && (
                <Card className="border-destructive">
                    <CardContent className="pt-6">
                        <p className="text-destructive">{error}</p>
                    </CardContent>
                </Card>
            )}

            {/* Bills Table */}
            <Card>
                <CardHeader>
                    <CardTitle>
                        {loading ? 'Loading...' : `${filteredBills.length} Bills`}
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="rounded-md border">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead className="w-[120px]">Bill</TableHead>
                                    <TableHead>Title</TableHead>
                                    <TableHead className="w-[140px]">Sponsor</TableHead>
                                    <TableHead className="w-[100px] text-center">Cosponsors</TableHead>
                                    <TableHead className="w-[100px] text-center">Trades</TableHead>
                                    <TableHead className="w-[120px]">Last Action</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    [...Array(10)].map((_, i) => (
                                        <TableRow key={i}>
                                            <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                                            <TableCell><Skeleton className="h-4 w-full" /></TableCell>
                                            <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                                            <TableCell><Skeleton className="h-4 w-8 mx-auto" /></TableCell>
                                            <TableCell><Skeleton className="h-4 w-8 mx-auto" /></TableCell>
                                            <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                                        </TableRow>
                                    ))
                                ) : filteredBills.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                                            No bills found matching your criteria
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    filteredBills.map((bill) => (
                                        <TableRow key={getBillId(bill)}>
                                            <TableCell>
                                                <Link
                                                    href={`/bills/${bill.congress}/${bill.bill_type}/${bill.bill_number}`}
                                                    className="font-medium text-primary hover:underline"
                                                >
                                                    {bill.bill_type.toUpperCase()} {bill.bill_number}
                                                </Link>
                                            </TableCell>
                                            <TableCell>
                                                <div className="max-w-xs truncate" title={bill.title}>
                                                    {bill.title}
                                                </div>
                                                {bill.top_industry_tags && bill.top_industry_tags.length > 0 && (
                                                    <div className="flex gap-1 mt-1">
                                                        {bill.top_industry_tags.slice(0, 2).map(tag => (
                                                            <Badge key={tag} variant="outline" className="text-xs">
                                                                {tag}
                                                            </Badge>
                                                        ))}
                                                    </div>
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                {bill.sponsor_bioguide_id && bill.sponsor_name ? (
                                                    <Link
                                                        href={`/politician/${bill.sponsor_name.toLowerCase().replace(/\s+/g, '-')}-${bill.sponsor_bioguide_id}`}
                                                        className="hover:underline"
                                                    >
                                                        {bill.sponsor_name}
                                                    </Link>
                                                ) : (
                                                    bill.sponsor_name || 'Unknown'
                                                )}
                                            </TableCell>
                                            <TableCell className="text-center">
                                                {bill.cosponsors_count || 0}
                                            </TableCell>
                                            <TableCell className="text-center">
                                                {(bill.trade_correlations_count || 0) > 0 ? (
                                                    <Badge variant="destructive">
                                                        {bill.trade_correlations_count}
                                                    </Badge>
                                                ) : (
                                                    <span className="text-muted-foreground">-</span>
                                                )}
                                            </TableCell>
                                            <TableCell className="text-sm text-muted-foreground">
                                                {formatDate(bill.latest_action_date)}
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

// Export wrapped in ErrorBoundary
export default function BillsWithErrorBoundary() {
    return (
        <ErrorBoundary>
            <BillsPage />
        </ErrorBoundary>
    );
}
