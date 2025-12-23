import { fetchTransactions, type Transaction } from '@/lib/api';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { TransactionsClient } from './TransactionsClient';

// Server Component
export default async function TransactionsPageWrapper() {
    let transactions: Transaction[] = [];
    let error: string | null = null;

    try {
        // Fetch larger batch for client-side filtering, matching legacy behavior
        // On the server, this enables prerendering
        transactions = await fetchTransactions({ limit: 1000 });
    } catch (err) {
        console.error('Failed to pre-fetch transactions:', err);
        error = 'Failed to load transactions';
    }

    return (
        <ErrorBoundary>
            <div className="space-y-6">
                {/* Header */}
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Transactions</h1>
                    <p className="text-muted-foreground">
                        Browse stock trades disclosed by members of Congress
                    </p>
                </div>

                {error ? (
                    <div className="p-4 border border-red-200 rounded-md bg-red-50 text-red-800">
                        {error}
                    </div>
                ) : (
                    <TransactionsClient initialTransactions={transactions} />
                )}
            </div>
        </ErrorBoundary>
    );
}
