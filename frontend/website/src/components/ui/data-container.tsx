'use client';

import React from 'react';
import { Loader2, AlertCircle, RefreshCcw } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

interface DataContainerProps {
    isLoading: boolean;
    isError: boolean;
    error?: any;
    data: any;
    emptyMessage?: string;
    onRetry?: () => void;
    loadingSkeleton?: React.ReactNode;
    children: (data: any) => React.ReactNode;
}

/**
 * A standardized wrapper for data-fetching components.
 * Automatically handles:
 * 1. Loading state (with custom skeleton or default spinner)
 * 2. Error state (with retry button)
 * 3. Empty state
 * 4. Data passing to children
 */
export function DataContainer({
    isLoading,
    isError,
    error,
    data,
    emptyMessage = "No data found.",
    onRetry,
    loadingSkeleton,
    children
}: DataContainerProps) {
    if (isLoading) {
        return loadingSkeleton || (
            <div className="flex flex-col items-center justify-center min-h-[200px] gap-2">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Loading data...</p>
            </div>
        );
    }

    if (isError) {
        return (
            <div className="py-6">
                <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>Error Loading Data</AlertTitle>
                    <AlertDescription className="mt-2 flex flex-col gap-4">
                        <p>{error?.message || "Something went wrong while fetching data. Please check your connection and try again."}</p>
                        {onRetry && (
                            <Button onClick={onRetry} variant="outline" size="sm" className="w-fit gap-2">
                                <RefreshCcw className="h-4 w-4" />
                                Try Again
                            </Button>
                        )}
                    </AlertDescription>
                </Alert>
            </div>
        );
    }

    const isEmpty = !data || (Array.isArray(data) && data.length === 0) || (typeof data === 'object' && Object.keys(data).length === 0);

    if (isEmpty && emptyMessage !== "none") {
        return (
            <div className="flex flex-col items-center justify-center min-h-[200px] border-2 border-dashed rounded-lg p-6 text-center">
                <p className="text-muted-foreground">{emptyMessage}</p>
            </div>
        );
    }

    return <>{children(data)}</>;
}
