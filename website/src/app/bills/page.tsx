'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { useBills } from '@/hooks/use-api';
import { type BillsParams, type Bill } from '@/types/api';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { DataContainer } from '@/components/ui/data-container';
import { Search, RotateCcw, AlertTriangle } from 'lucide-react';

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
    // Filters - using default values
    const [congress, setCongress] = useState<string>('119');
    const [billType, setBillType] = useState<string>('');
    const [industry, setIndustry] = useState<string>('');
    const [search, setSearch] = useState<string>('');
    const [hasCorrelations, setHasCorrelations] = useState<boolean>(false);

    const params: BillsParams = {
        limit: 50,
        congress: parseInt(congress, 10),
        billType: billType || undefined,
        industry: industry || undefined,
        hasTradeCorrelations: hasCorrelations || undefined,
        sortBy: 'latest_action_date',
        sortOrder: 'desc',
    };

    const { data: bills = [], isLoading, error, refetch } = useBills(params);

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
        <div className="container mx-auto py-6 space-y-6">
            {/* Header */}
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight">Congressional Bills</h1>
                <p className="text-muted-foreground max-w-2xl">
                    Search and analyze legislation with integrated trade correlation insights,
                    identifying potential conflicts of interest and market-moving bills.
                </p>
            </div>

            {/* Filters */}
            <Card className="border-none shadow-sm bg-muted/30">
                <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium flex items-center gap-2 text-muted-foreground">
                        <Search className="h-4 w-4" /> Filter Legislation
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                        {/* Search */}
                        <div className="lg:col-span-2">
                            <Input
                                placeholder="Search bills by title, number or sponsor..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="bg-background shadow-none"
                            />
                        </div>

                        {/* Congress */}
                        <Select value={congress} onValueChange={setCongress}>
                            <SelectTrigger className="bg-background shadow-none">
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
                            <SelectTrigger className="bg-background shadow-none">
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
                            <SelectTrigger className="bg-background shadow-none">
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

                    <div className="flex flex-wrap items-center gap-2 mt-4">
                        <Button
                            variant={hasCorrelations ? 'default' : 'outline'}
                            size="sm"
                            className={hasCorrelations ? 'bg-amber-600 hover:bg-amber-700' : ''}
                            onClick={() => setHasCorrelations(!hasCorrelations)}
                        >
                            <AlertTriangle className="h-4 w-4 mr-2" />
                            Has Trade Correlations
                        </Button>

                        <Button
                            variant="ghost"
                            size="sm"
                            className="text-muted-foreground ml-auto"
                            onClick={() => {
                                setCongress('119');
                                setBillType('');
                                setIndustry('');
                                setSearch('');
                                setHasCorrelations(false);
                            }}
                        >
                            <RotateCcw className="h-4 w-4 mr-2" />
                            Reset Filters
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* Bills Table */}
            <DataContainer
                isLoading={isLoading}
                isError={!!error}
                error={error}
                data={filteredBills}
                onRetry={() => refetch()}
                emptyMessage="No bills found matching your updated criteria."
                loadingSkeleton={
                    <div className="space-y-4">
                        <Skeleton className="h-10 w-full" />
                        <Skeleton className="h-[400px] w-full" />
                    </div>
                }
            >
                {(data) => (
                    <Card className="border-none shadow-sm overflow-hidden">
                        <div className="relative w-full overflow-auto">
                            <Table>
                                <TableHeader className="bg-muted/50">
                                    <TableRow>
                                        <TableHead className="w-[120px]">Bill ID</TableHead>
                                        <TableHead>Legislation Title</TableHead>
                                        <TableHead className="w-[160px]">Sponsor</TableHead>
                                        <TableHead className="w-[100px] text-center">Cosponsors</TableHead>
                                        <TableHead className="w-[100px] text-center">Trade Analysis</TableHead>
                                        <TableHead className="w-[140px]">Last Action</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {data.map((bill) => (
                                        <TableRow key={getBillId(bill)} className="hover:bg-muted/30 transition-colors">
                                            <TableCell>
                                                <Link
                                                    href={`/bills/${bill.congress}/${bill.bill_type}/${bill.bill_number}`}
                                                    className="font-mono font-medium text-primary hover:underline decoration-primary/30 underline-offset-4"
                                                >
                                                    {bill.bill_type.toUpperCase()} {bill.bill_number}
                                                </Link>
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex flex-col gap-1">
                                                    <span className="font-medium line-clamp-2 leading-tight" title={bill.title}>
                                                        {bill.title}
                                                    </span>
                                                    {bill.top_industry_tags && bill.top_industry_tags.length > 0 && (
                                                        <div className="flex flex-wrap gap-1">
                                                            {bill.top_industry_tags.slice(0, 3).map(tag => (
                                                                <Badge key={tag} variant="secondary" className="text-[10px] py-0 px-1 font-normal bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 border-none">
                                                                    {tag}
                                                                </Badge>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                {bill.sponsor_bioguide_id ? (
                                                    <Link
                                                        href={`/politician/${bill.sponsor_bioguide_id}`}
                                                        className="text-sm hover:text-primary transition-colors flex flex-col"
                                                    >
                                                        <span className="font-medium">{bill.sponsor_name || bill.sponsor_bioguide_id}</span>
                                                        <span className="text-xs text-muted-foreground">{bill.sponsor_party} - {bill.sponsor_state}</span>
                                                    </Link>
                                                ) : (
                                                    <span className="text-sm text-muted-foreground">
                                                        {bill.sponsor_name || 'Multiple/Unknown'}
                                                    </span>
                                                )}
                                            </TableCell>
                                            <TableCell className="text-center font-medium">
                                                {bill.cosponsors_count || 0}
                                            </TableCell>
                                            <TableCell className="text-center">
                                                {(bill.trade_correlations_count || 0) > 0 ? (
                                                    <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-200 border-amber-200 dark:bg-amber-900/40 dark:text-amber-300 dark:border-amber-800 transition-colors">
                                                        {bill.trade_correlations_count} Correlated
                                                    </Badge>
                                                ) : (
                                                    <span className="inline-block w-4 h-[1px] bg-muted mx-auto" aria-label="No data"></span>
                                                )}
                                            </TableCell>
                                            <TableCell className="text-sm text-muted-foreground">
                                                <div className="flex flex-col">
                                                    <span>{formatDate(bill.latest_action_date)}</span>
                                                    <span className="text-[10px] truncate max-w-[120px]" title={bill.latest_action_text}>
                                                        {bill.latest_action_text}
                                                    </span>
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </div>
                    </Card>
                )}
            </DataContainer>
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
