'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/lib/query-client';
import { Toaster } from '@/components/ui/sonner';

export function Providers({ children }: { children: React.ReactNode }) {
    return (
        <QueryClientProvider client={queryClient}>
            {children}
            <Toaster position="top-right" expand={false} richColors />
        </QueryClientProvider>
    );
}
