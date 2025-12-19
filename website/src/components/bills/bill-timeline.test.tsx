import { render, screen } from '@testing-library/react';
import { BillTimeline, TimelineEvent } from './bill-timeline';
import { describe, it, expect } from 'vitest';
import React from 'react';

const mockEvents: TimelineEvent[] = [
    {
        date: '2025-01-20',
        title: 'Introduced',
        description: 'Bill was introduced in the House',
        status: 'completed',
        chamber: 'House'
    },
    {
        date: '2025-01-21',
        title: 'Committee Referral',
        status: 'current',
        chamber: 'House'
    }
];

describe('BillTimeline', () => {
    it('renders events correctly', () => {
        const { asFragment } = render(<BillTimeline events={mockEvents} />);

        expect(screen.getByText('Introduced')).toBeDefined();
        expect(asFragment()).toMatchSnapshot();
    });

    it('renders trade alerts if present', () => {
        const eventsWithTrade: TimelineEvent[] = [
            ...mockEvents,
            {
                date: '2025-01-22',
                title: 'Suspicious Activity',
                status: 'current',
                tradeAlert: true,
                tradeCount: 5
            }
        ];

        const { asFragment } = render(<BillTimeline events={eventsWithTrade} />);

        expect(screen.getByText(/5 trades/i)).toBeDefined();
        expect(asFragment()).toMatchSnapshot();
    });
});
