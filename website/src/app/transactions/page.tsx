import { fetchTransactions, type Transaction } from '@/lib/api';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { TransactionsClient } from './TransactionsClient';

// Server Component
export default async function TransactionsPageWrapper() {
    let transactions: Transaction[] = [];
    let error: string | null = null;
    let debugInfo: any = null;

    try {
        console.log('[Transactions Page] Fetching transactions from server...');
        transactions = await fetchTransactions({ limit: 1000 });
        console.log(`[Transactions Page] Successfully fetched ${transactions?.length || 0} transactions`);

        // Debug: log first transaction shape
        if (transactions && transactions.length > 0) {
            console.log('[Transactions Page] First transaction sample:', JSON.stringify(transactions[0]));
        }

        // Validate data
        if (!Array.isArray(transactions)) {
            console.error('[Transactions Page] ERROR: transactions is not an array!', typeof transactions, transactions);
            debugInfo = {
                type: typeof transactions,
                isArray: Array.isArray(transactions),
                value: transactions
            };
            throw new Error('Invalid data format: expected array');
        }
    } catch (err) {
        const errorMessage = err instanceof Error ? err.message : String(err);
        console.error('[Transactions Page] Failed to pre-fetch transactions:', errorMessage, err);
        error = `Failed to load transactions: ${errorMessage}`;
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
                    <div className="p-4 border border-red-200 rounded-md bg-red-50 dark:bg-red-950 dark:border-red-800 dark:text-red-200 text-red-800">
                        <div className="font-semibold mb-2">{error}</div>
                        {debugInfo && (
                            <details className="text-xs mt-2">
                                <summary className="cursor-pointer font-mono">Debug Info</summary>
                                <pre className="mt-2 overflow-auto">{JSON.stringify(debugInfo, null, 2)}</pre>
                            </details>
                        )}
                        <div className="mt-4 text-sm">
                            <a
                                href="/api/health"
                                className="underline hover:no-underline"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                Check API Status
                            </a>
                        </div>
                    </div>
                ) : (
                    <TransactionsClient initialTransactions={transactions} />
                )}
            </div>
        </ErrorBoundary>
    );
}
