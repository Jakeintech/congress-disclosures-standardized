import type { NodeData } from '../NodeComponent';

// Mock graph data for testing
export const mockMemberNode: NodeData = {
    id: 'P000197',
    name: 'Nancy Pelosi',
    initials: 'NP',
    group: 'member',
    party: 'Democrat',
    photo_url: 'https://www.congress.gov/img/member/P000197_200.jpg',
    tier: 'platinum',
    rank: 1,
    value: 25000000,
    transaction_count: 225,
    buy_sell_ratio: 2.0,
};

export const mockStockNode: NodeData = {
    id: 'NVDA',
    name: 'NVDA',
    group: 'asset',
    logo_url: 'https://assets.polygon.io/logos/nvda/logo.png',
    value: 12000000,
    transaction_count: 150,
    buy_sell_ratio: 1.8,
    unique_traders: 45,
};

export const mockRepublicanMember: NodeData = {
    id: 'M000355',
    name: 'Mitch McConnell',
    initials: 'MM',
    group: 'member',
    party: 'Republican',
    photo_url: 'https://www.congress.gov/img/member/M000355_200.jpg',
    tier: 'gold',
    rank: 5,
    value: 800000,
    transaction_count: 50,
    buy_sell_ratio: 0.5,
};

// Graph data for integration tests
export const mockGraphData = {
    nodes: [
        mockMemberNode,
        mockStockNode,
        mockRepublicanMember,
        {
            id: 'AAPL',
            name: 'AAPL',
            group: 'asset',
            value: 500000,
            unique_traders: 25,
        },
    ],
    links: [
        {
            source: 'P000197',
            target: 'NVDA',
            value: 1000000,
            count: 50,
            type: 'purchase',
        },
        {
            source: 'M000355',
            target: 'AAPL',
            value: 500000,
            count: 25,
            type: 'sale',
        },
    ],
};

// Dense label data - multiple edges between same nodes
export const denseLabelData = {
    nodes: [
        mockMemberNode,
        ...Array.from({ length: 10 }, (_, i) => ({
            id: `S00${i}`,
            name: `Stock ${i}`,
            group: 'asset',
            value: 100000 * (i + 1),
        })),
    ],
    links: Array.from({ length: 10 }, (_, i) => ({
        source: 'P000197',
        target: `S00${i}`,
        value: 50000 + i * 10000,
        count: 5,
        type: i % 2 === 0 ? 'purchase' : 'sale',
    })),
};

// Data that triggers overlapping labels bug (multiple edges, same source/target)
export const overlappingLabelData = {
    nodes: [
        { id: 'M001', name: 'Member 1', group: 'member' },
        { id: 'S001', name: 'Stock 1', group: 'asset' },
    ],
    links: [
        { source: 'M001', target: 'S001', value: 100000, type: 'purchase', count: 10 },
        { source: 'M001', target: 'S001', value: 75000, type: 'sale', count: 5 },
        { source: 'M001', target: 'S001', value: 50000, type: 'mixed', count: 15 },
    ],
};
