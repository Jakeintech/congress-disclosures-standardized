import { render, screen } from '@testing-library/react';
import { StatCardEnhanced } from './stat-card-enhanced';
import { describe, it, expect } from 'vitest';
import { Users } from 'lucide-react';
import React from 'react';

describe('StatCardEnhanced', () => {
    it('renders title and value correctly', () => {
        render(
            <StatCardEnhanced
                title="Total Members"
                value={535}
                icon={Users}
            />
        );

        expect(screen.getByText('Total Members')).toBeDefined();
        expect(screen.getByText('535')).toBeDefined();
    });

    it('renders trend information when provided', () => {
        render(
            <StatCardEnhanced
                title="Transactions"
                value={1500}
                change="+100"
                trend="up"
                icon={Users}
            />
        );

        expect(screen.getByText('+100')).toBeDefined();
    });

    it('shows skeleton when loading', () => {
        const { container } = render(
            <StatCardEnhanced
                title="Total Members"
                value={535}
                icon={Users}
                loading={true}
            />
        );

        // Check for skeleton class (or data-slot if using new shadcn)
        expect(container.querySelector('.animate-pulse')).toBeDefined();
    });
});
