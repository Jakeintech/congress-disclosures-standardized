'use client';

import React, { useState } from 'react';
import { cn } from '@/lib/utils';

interface StockLogoProps {
    ticker: string;
    size?: 'sm' | 'md' | 'lg';
    className?: string;
}

const sizeClasses = {
    sm: 'w-8 h-8 text-xs',
    md: 'w-10 h-10 text-sm',
    lg: 'w-12 h-12 text-base',
};

export function StockLogo({ ticker, size = 'md', className }: StockLogoProps) {
    const [imageError, setImageError] = useState(false);

    const logoUrl = `https://financialmodelingprep.com/image-stock/${ticker}.png`;
    const fallbackLetter = ticker.charAt(0).toUpperCase();

    return (
        <div
            className={cn(
                'rounded-full bg-primary/10 flex items-center justify-center text-primary font-semibold overflow-hidden shrink-0',
                sizeClasses[size],
                className
            )}
        >
            {!imageError ? (
                <img
                    src={logoUrl}
                    alt={ticker}
                    className="w-full h-full object-cover"
                    onError={() => setImageError(true)}
                />
            ) : (
                <span>{fallbackLetter}</span>
            )}
        </div>
    );
}
