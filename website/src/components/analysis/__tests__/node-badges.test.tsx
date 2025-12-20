import React from 'react';
import { render, screen } from '@testing-library/react';
import { TierBadge, RankBadge, TraderCountBadge } from '../node-badges';

describe('TierBadge', () => {
    it('renders platinum tier with Award icon', () => {
        const { container } = render(<TierBadge tier="platinum" />);
        const badge = container.querySelector('[class*="from-slate"]');
        expect(badge).toBeInTheDocument();
    });

    it('renders gold tier with Trophy icon', () => {
        const { container } = render(<TierBadge tier="gold" />);
        const badge = container.querySelector('[class*="from-amber"]');
        expect(badge).toBeInTheDocument();
    });

    it('renders silver tier with Medal icon', () => {
        const { container } = render(<TierBadge tier="silver" />);
        const badge = container.querySelector('[class*="from-gray"]');
        expect(badge).toBeInTheDocument();
    });

    it('renders bronze tier with Shield icon', () => {
        const { container } = render(<TierBadge tier="bronze" />);
        const badge = container.querySelector('[class*="from-orange"]');
        expect(badge).toBeInTheDocument();
    });

    it('has correct title attribute for accessibility', () => {
        const { getByTitle } = render(<TierBadge tier="gold" />);
        expect(getByTitle('Gold Tier')).toBeInTheDocument();
    });

    it('has hover scale animation class', () => {
        const { container } = render(<TierBadge tier="platinum" />);
        const badge = container.querySelector('[class*="hover:scale"]');
        expect(badge).toBeInTheDocument();
    });
});

describe('RankBadge', () => {
    it('renders rank number correctly', () => {
        const { container } = render(<RankBadge rank={5} />);
        expect(container.textContent).toContain('#5');
    });

    it('has amber gradient background', () => {
        const { container } = render(<RankBadge rank={1} />);
        const badge = container.querySelector('[class*="from-amber"]');
        expect(badge).toBeInTheDocument();
    });

    it('has centered positioning class', () => {
        const { container } = render(<RankBadge rank={10} />);
        const badge = container.querySelector('[class*="-translate-x-1/2"]');
        expect(badge).toBeInTheDocument();
    });

    it('displays title with rank number', () => {
        const { getByTitle } = render(<RankBadge rank={3} />);
        expect(getByTitle('Rank #3')).toBeInTheDocument();
    });
});

describe('TraderCountBadge', () => {
    it('renders trader count correctly', () => {
        const { container } = render(<TraderCountBadge count={45} />);
        expect(container.textContent).toContain('45');
    });

    it('has purple background', () => {
        const { container } = render(<TraderCountBadge count={20} />);
        const badge = container.querySelector('[class*="bg-purple"]');
        expect(badge).toBeInTheDocument();
    });

    it('includes Users icon', () => {
        const { container } = render(<TraderCountBadge count={10} />);
        const icon = container.querySelector('svg');
        expect(icon).toBeInTheDocument();
    });

    it('displays singular trader in title for count of 1', () => {
        const { getByTitle } = render(<TraderCountBadge count={1} />);
        expect(getByTitle('1 unique trader')).toBeInTheDocument();
    });

    it('displays plural traders in title for count > 1', () => {
        const { getByTitle } = render(<TraderCountBadge count={5} />);
        expect(getByTitle('5 unique traders')).toBeInTheDocument();
    });
});
