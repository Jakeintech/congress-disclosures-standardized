import React from 'react';
import { render } from '@testing-library/react';
import { NodeComponent } from '../NodeComponent';
import { mockMemberNode, mockStockNode, mockRepublicanMember } from './fixtures/graph-data';

describe('NodeComponent', () => {
    describe('Member Nodes', () => {
        it('renders Democrat member with blue border', () => {
            const { container } = render(<NodeComponent data={mockMemberNode} />);
            const avatar = container.querySelector('[class*="border-blue"]');
            expect(avatar).toBeInTheDocument();
        });

        it('renders Republican member with red border', () => {
            const { container } = render(<NodeComponent data={mockRepublicanMember} />);
            const avatar = container.querySelector('[class*="border-red"]');
            expect(avatar).toBeInTheDocument();
        });

        it('renders tier badge for member with tier', () => {
            const { container } = render(<NodeComponent data={mockMemberNode} />);
            const tierBadge = container.querySelector('[class*="absolute"][class*="-top-1"][class*="-right-1"]');
            expect(tierBadge).toBeInTheDocument();
        });

        it('renders rank badge for top 10 member', () => {
            const { container } = render(<NodeComponent data={mockMemberNode} />);
            expect(container.textContent).toContain('#1');
        });

        it('uses thicker border for high-value traders', () => {
            const { container } = render(<NodeComponent data={mockMemberNode} size={48} />);
            const avatar = container.querySelector('[style*="border-width: 4px"]');
            expect(avatar).toBeInTheDocument();
        });

        it('renders initials as fallback when photo fails', () => {
            const nodeWithoutPhoto = { ...mockMemberNode, photo_url: undefined };
            const { container } = render(<NodeComponent data={nodeWithoutPhoto} />);
            expect(container.textContent).toContain('NP');
        });
    });

    describe('Stock Nodes', () => {
        it('renders stock node with logo URL', () => {
            const { container } = render(<NodeComponent data={mockStockNode} />);
            const img = container.querySelector('img');
            expect(img).toHaveAttribute('src', mockStockNode.logo_url);
        });

        it('renders trader count badge for stocks', () => {
            const { container } = render(<NodeComponent data={mockStockNode} />);
            expect(container.textContent).toContain('45');
        });

        it('renders green border for net buying stocks', () => {
            const { container } = render(<NodeComponent data={mockStockNode} />);
            const avatar = container.querySelector('[class*="border-green"]');
            expect(avatar).toBeInTheDocument();
        });

        it('does not render tier badge for stocks', () => {
            const { container } = render(<NodeComponent data={mockStockNode} />);
            const tierBadge = container.querySelector('[title*="Tier"]');
            expect(tierBadge).not.toBeInTheDocument();
        });
    });

    describe('Size Prop', () => {
        it('respects custom size prop', () => {
            const { container } = render(<NodeComponent data={mockMemberNode} size={64} />);
            const wrapper = container.firstChild as HTMLElement;
            expect(wrapper.style.width).toBe('64px');
            expect(wrapper.style.height).toBe('64px');
        });

        it('defaults to 48px when size not provided', () => {
            const { container } = render(<NodeComponent data={mockMemberNode} />);
            const wrapper = container.firstChild as HTMLElement;
            expect(wrapper.style.width).toBe('48px');
        });
    });

    describe('Accessibility', () => {
        it('includes alt text for member photo', () => {
            const { container } = render(<NodeComponent data={mockMemberNode} />);
            const img = container.querySelector('img');
            expect(img).toHaveAttribute('alt', mockMemberNode.name);
        });

        it('renders fallback content with proper contrast', () => {
            const nodeWithoutPhoto = { ...mockMemberNode, photo_url: undefined };
            const { container } = render(<NodeComponent data={nodeWithoutPhoto} />);
            const fallback = container.querySelector('[class*="bg-gradient-to-br"]');
            expect(fallback).toBeInTheDocument();
        });
    });
});
