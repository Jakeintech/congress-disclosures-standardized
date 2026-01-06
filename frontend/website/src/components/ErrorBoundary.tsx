'use client';

import React, { Component, ReactNode } from 'react';
import { AlertCircle } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

/**
 * Error Boundary Component
 *
 * Catches React errors in child components and displays a user-friendly error message
 * with the option to retry. Prevents the entire app from crashing.
 */
export class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        // Log error to console for debugging
        console.error('ErrorBoundary caught an error:', error, errorInfo);

        // TODO: Send to error tracking service (e.g., Sentry)
        // Example: logErrorToService(error, errorInfo);
    }

    handleReset = () => {
        this.setState({ hasError: false, error: null });
    };

    render() {
        if (this.state.hasError) {
            // Custom fallback UI if provided
            if (this.props.fallback) {
                return this.props.fallback;
            }

            // Default error UI
            return (
                <div className="container mx-auto px-4 py-8">
                    <Alert variant="destructive" className="max-w-2xl mx-auto">
                        <AlertCircle className="h-4 w-4" />
                        <AlertTitle>Something went wrong</AlertTitle>
                        <AlertDescription className="mt-2 space-y-4">
                            <p>
                                We encountered an error while loading this page. This could be due to:
                            </p>
                            <ul className="list-disc list-inside space-y-1 text-sm">
                                <li>A temporary network issue</li>
                                <li>An API service disruption</li>
                                <li>Invalid or missing data</li>
                            </ul>

                            {/* Show error details in development mode */}
                            {process.env.NODE_ENV === 'development' && this.state.error && (
                                <details className="mt-4">
                                    <summary className="cursor-pointer font-medium">
                                        Error details (development only)
                                    </summary>
                                    <pre className="mt-2 p-4 bg-muted rounded text-xs overflow-auto">
                                        {this.state.error.toString()}
                                        {'\n\n'}
                                        {this.state.error.stack}
                                    </pre>
                                </details>
                            )}

                            <div className="flex gap-2 mt-4">
                                <Button onClick={this.handleReset}>
                                    Try Again
                                </Button>
                                <Button variant="outline" onClick={() => window.location.href = '/'}>
                                    Go to Dashboard
                                </Button>
                            </div>
                        </AlertDescription>
                    </Alert>
                </div>
            );
        }

        return this.props.children;
    }
}

/**
 * Simple error display component for API errors
 * Use this for displaying API fetch errors without full error boundary
 */
export function ApiError({
    error,
    onRetry
}: {
    error: string | Error;
    onRetry?: () => void;
}) {
    const errorMessage = typeof error === 'string' ? error : error.message;

    return (
        <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Failed to load data</AlertTitle>
            <AlertDescription className="mt-2">
                <p className="mb-3">{errorMessage}</p>
                {onRetry && (
                    <Button onClick={onRetry} size="sm">
                        Retry
                    </Button>
                )}
            </AlertDescription>
        </Alert>
    );
}
