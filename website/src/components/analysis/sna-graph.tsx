'use client';

import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import * as d3 from 'd3';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
    ContextMenu,
    ContextMenuContent,
    ContextMenuItem,
    ContextMenuLabel,
    ContextMenuSeparator,
    ContextMenuTrigger,
} from '@/components/ui/context-menu';
import {
    ZoomIn, ZoomOut, RotateCcw, Eye, EyeOff,
    Expand, ExternalLink, Users, TrendingUp
} from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

export interface SNANode {
    id: string;
    name?: string;
    group: string; // 'member' | 'asset' | 'bill' | 'lobbyist' | 'client' | 'party_agg' etc.
    party?: string;
    chamber?: string;
    state?: string;
    bioguide_id?: string;
    value?: number;
    transaction_count?: number;
    degree?: number;
    // Computed by simulation
    x?: number;
    y?: number;
    fx?: number | null;
    fy?: number | null;
    calculatedRadius?: number;
}

export interface SNALink {
    source: string | SNANode;
    target: string | SNANode;
    type?: string;
    value?: number;
    count?: number;
}

export interface SNAGraphData {
    nodes: SNANode[];
    links: SNALink[];
}

export interface SNAGraphProps {
    data: SNAGraphData;
    height?: number;
    onNodeSelect?: (node: SNANode | null) => void;
    onNodeDrillDown?: (node: SNANode) => void;
    onNodeNavigate?: (node: SNANode) => void;
    nodeColorFn?: (node: SNANode) => string;
    nodeSizeFn?: (node: SNANode) => number;
    linkColorFn?: (link: SNALink) => string;
    showLabels?: boolean;
    className?: string;
}

// ============================================================================
// CONSTANTS
// ============================================================================

const DEFAULT_NODE_COLORS: Record<string, string> = {
    member: '#3b82f6',
    asset: '#10b981',
    bill: '#8b5cf6',
    lobbyist: '#f59e0b',
    client: '#ec4899',
    party_agg: '#6b7280',
    default: '#94a3b8',
};

const PARTY_COLORS: Record<string, string> = {
    Democrat: '#3b82f6',
    Republican: '#ef4444',
    Independent: '#10b981',
    D: '#3b82f6',
    R: '#ef4444',
    I: '#10b981',
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

const formatMoney = (val: number) =>
    new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        notation: 'compact',
        maximumFractionDigits: 1
    }).format(val);

function getDefaultNodeColor(node: SNANode): string {
    if (node.party && (node.group === 'member' || node.group?.includes('_agg'))) {
        return PARTY_COLORS[node.party] || DEFAULT_NODE_COLORS.member;
    }
    return DEFAULT_NODE_COLORS[node.group] || DEFAULT_NODE_COLORS.default;
}

function getDefaultNodeSize(node: SNANode): number {
    if (node.group?.includes('_agg')) {
        return Math.min(40, 15 + Math.sqrt((node.value || 0) / 1000000) * 2);
    }
    if (node.group === 'member') {
        return Math.min(25, 8 + Math.sqrt((node.value || 0) / 500000) * 2);
    }
    if (node.group === 'asset') {
        return Math.min(20, 6 + Math.sqrt((node.value || 0) / 1000000) * 1.5);
    }
    return 8;
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function SNAGraph({
    data,
    height = 700,
    onNodeSelect,
    onNodeDrillDown,
    onNodeNavigate,
    nodeColorFn = getDefaultNodeColor,
    nodeSizeFn = getDefaultNodeSize,
    linkColorFn,
    showLabels = true,
    className = '',
}: SNAGraphProps) {
    const svgRef = useRef<SVGSVGElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [selectedNode, setSelectedNode] = useState<SNANode | null>(null);
    const [hoveredNode, setHoveredNode] = useState<SNANode | null>(null);
    const [currentZoom, setCurrentZoom] = useState(1);
    const [labelsVisible, setLabelsVisible] = useState(showLabels);
    const [contextMenuNode, setContextMenuNode] = useState<SNANode | null>(null);

    // Memoize processed data to avoid re-computation
    const processedData = useMemo(() => {
        if (!data?.nodes?.length) return { nodes: [], links: [] };

        const nodeCount = data.nodes.length;
        const nodes = data.nodes.map((n, i) => {
            const calculatedRadius = nodeSizeFn(n);
            // Initialize with circular distribution around center
            const angle = (i / nodeCount) * 2 * Math.PI;
            const radius = 150 + Math.random() * 200;
            return {
                ...n,
                calculatedRadius,
                x: 500 + Math.cos(angle) * radius + (Math.random() - 0.5) * 100,
                y: height / 2 + Math.sin(angle) * radius + (Math.random() - 0.5) * 100,
            };
        });

        const links = data.links.map(l => ({ ...l }));

        return { nodes, links };
    }, [data, height, nodeSizeFn]);

    // Handle node selection
    const handleNodeSelect = useCallback((node: SNANode | null) => {
        setSelectedNode(node);
        onNodeSelect?.(node);
    }, [onNodeSelect]);

    // Render the D3 graph
    useEffect(() => {
        if (!svgRef.current || !containerRef.current || !processedData.nodes.length) return;

        const container = containerRef.current;
        const width = container.clientWidth || 1000;
        const svg = d3.select(svgRef.current);

        // Clear previous render
        svg.selectAll('*').remove();
        svg.attr('width', width).attr('height', height);

        const g = svg.append('g');

        // Setup zoom
        const zoom = d3.zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.1, 8])
            .on('zoom', (event) => {
                g.attr('transform', event.transform.toString());
                setCurrentZoom(event.transform.k);
            });

        svg.call(zoom);

        // Double-click to reset
        svg.on('dblclick.zoom', null);
        svg.on('dblclick', () => {
            handleNodeSelect(null);
            svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
        });

        // Create copies of data for D3
        const nodes = processedData.nodes.map(n => ({ ...n }));
        const links = processedData.links.map(l => ({ ...l }));

        // Dynamic force parameters
        const nodeCount = nodes.length;
        const dynamicCharge = Math.min(-50, -100 - nodeCount * 2);
        const dynamicLinkDistance = Math.max(80, 100 + nodeCount * 0.3);

        // Force simulation
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links)
                .id((d: any) => d.id)
                .distance(dynamicLinkDistance)
                .strength(0.15))
            .force('charge', d3.forceManyBody()
                .strength((d: any) => d.group?.includes('_agg') ? dynamicCharge * 5 : dynamicCharge)
                .distanceMin(30)
                .distanceMax(500))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collide', d3.forceCollide()
                .radius((d: any) => (d.calculatedRadius || 10) + 15)
                .strength(1)
                .iterations(3))
            .force('x', d3.forceX(width / 2).strength(0.03))
            .force('y', d3.forceY(height / 2).strength(0.03))
            .alpha(1)
            .alphaDecay(0.02)
            .velocityDecay(0.4);

        // Pre-run simulation for stability
        simulation.tick(80);

        // Draw links
        const link = g.append('g')
            .attr('class', 'links')
            .selectAll('line')
            .data(links)
            .join('line')
            .attr('stroke', (d: any) => linkColorFn ? linkColorFn(d) : '#94a3b8')
            .attr('stroke-opacity', 0.5)
            .attr('stroke-width', (d: any) => Math.max(1, Math.sqrt((d.value || 0) / 100000)));

        // Draw nodes
        const node = g.append('g')
            .attr('class', 'nodes')
            .selectAll('g')
            .data(nodes)
            .join('g')
            .call(d3.drag<any, any>()
                .on('start', (event, d) => {
                    if (!event.active) simulation.alphaTarget(0.3).restart();
                    d.fx = d.x;
                    d.fy = d.y;
                })
                .on('drag', (event, d) => {
                    d.fx = event.x;
                    d.fy = event.y;
                })
                .on('end', (event, d) => {
                    if (!event.active) simulation.alphaTarget(0);
                    d.fx = null;
                    d.fy = null;
                }) as any);

        // Fade in animation
        node.style('opacity', 0)
            .transition()
            .duration(300)
            .delay((d: any, i: number) => Math.min(i * 3, 300))
            .style('opacity', 1);

        // Node circles
        node.append('circle')
            .attr('r', (d: any) => d.calculatedRadius || 10)
            .attr('fill', (d: any) => nodeColorFn(d))
            .attr('stroke', '#fff')
            .attr('stroke-width', 2)
            .style('cursor', 'pointer')
            .style('filter', 'drop-shadow(0 2px 3px rgba(0,0,0,0.15))')
            .on('click', (event: any, d: any) => {
                event.stopPropagation();
                handleNodeSelect(d);
            })
            .on('contextmenu', (event: any, d: any) => {
                event.preventDefault();
                setContextMenuNode(d);
            })
            .on('mouseenter', (event: any, d: any) => {
                setHoveredNode(d);
                d3.select(event.target)
                    .transition()
                    .duration(150)
                    .attr('r', (d.calculatedRadius || 10) * 1.15);
            })
            .on('mouseleave', (event: any, d: any) => {
                setHoveredNode(null);
                d3.select(event.target)
                    .transition()
                    .duration(150)
                    .attr('r', d.calculatedRadius || 10);
            });

        // Node labels
        if (labelsVisible) {
            // Background halo
            node.append('text')
                .attr('dx', (d: any) => d.group?.includes('_agg') ? 0 : (d.calculatedRadius || 10) + 4)
                .attr('dy', (d: any) => d.group?.includes('_agg') ? 4 : '.35em')
                .attr('text-anchor', (d: any) => d.group?.includes('_agg') ? 'middle' : 'start')
                .style('font-size', '10px')
                .style('font-weight', '600')
                .style('fill', 'var(--background)')
                .style('stroke', 'var(--background)')
                .style('stroke-width', '3px')
                .style('stroke-linejoin', 'round')
                .style('pointer-events', 'none')
                .text((d: any) => d.name || d.id);

            // Foreground text
            node.append('text')
                .attr('dx', (d: any) => d.group?.includes('_agg') ? 0 : (d.calculatedRadius || 10) + 4)
                .attr('dy', (d: any) => d.group?.includes('_agg') ? 4 : '.35em')
                .attr('text-anchor', (d: any) => d.group?.includes('_agg') ? 'middle' : 'start')
                .style('font-size', '10px')
                .style('font-weight', '600')
                .style('fill', 'currentColor')
                .style('pointer-events', 'none')
                .text((d: any) => d.name || d.id);
        }

        // Tooltip
        const tooltip = d3.select('body').append('div')
            .attr('class', 'sna-tooltip fixed z-50 bg-card border border-border text-card-foreground text-xs p-2 rounded-lg shadow-lg pointer-events-none hidden')
            .style('max-width', '200px');

        node.on('mouseover.tooltip', (event: any, d: any) => {
            let html = `<strong>${d.name || d.id}</strong><br/>`;
            html += `<span class="text-muted-foreground capitalize">${d.group}</span>`;
            if (d.value) html += `<br/><span class="text-green-500">${formatMoney(d.value)}</span>`;
            if (d.transaction_count) html += `<br/><span class="text-muted-foreground">${d.transaction_count} transactions</span>`;

            tooltip
                .html(html)
                .style('display', 'block')
                .style('left', `${event.pageX + 12}px`)
                .style('top', `${event.pageY - 10}px`);
        })
            .on('mouseout.tooltip', () => {
                tooltip.style('display', 'none');
            });

        // Simulation tick
        simulation.on('tick', () => {
            link
                .attr('x1', (d: any) => d.source.x)
                .attr('y1', (d: any) => d.source.y)
                .attr('x2', (d: any) => d.target.x)
                .attr('y2', (d: any) => d.target.y);

            node.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
        });

        // Cleanup
        return () => {
            tooltip.remove();
            simulation.stop();
        };
    }, [processedData, height, nodeColorFn, linkColorFn, labelsVisible, handleNodeSelect]);

    // Handle context menu actions
    const handleContextAction = useCallback((action: string) => {
        if (!contextMenuNode) return;

        switch (action) {
            case 'select':
                handleNodeSelect(contextMenuNode);
                break;
            case 'drilldown':
                onNodeDrillDown?.(contextMenuNode);
                break;
            case 'navigate':
                onNodeNavigate?.(contextMenuNode);
                break;
        }
        setContextMenuNode(null);
    }, [contextMenuNode, handleNodeSelect, onNodeDrillDown, onNodeNavigate]);

    if (!data?.nodes?.length) {
        return (
            <Card className={`flex items-center justify-center bg-muted/20 ${className}`} style={{ height }}>
                <div className="text-center text-muted-foreground">
                    <Users className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p className="font-medium">No network data available</p>
                    <p className="text-sm">Try adjusting your filters or check back later</p>
                </div>
            </Card>
        );
    }

    return (
        <div ref={containerRef} className={`relative ${className}`}>
            <ContextMenu>
                <ContextMenuTrigger asChild>
                    <svg
                        ref={svgRef}
                        className="w-full bg-card rounded-lg border"
                        style={{ height }}
                    />
                </ContextMenuTrigger>
                <ContextMenuContent>
                    <ContextMenuLabel>
                        {contextMenuNode?.name || contextMenuNode?.id || 'Node Actions'}
                    </ContextMenuLabel>
                    <ContextMenuSeparator />
                    <ContextMenuItem onClick={() => handleContextAction('select')}>
                        <Eye className="mr-2 h-4 w-4" />
                        View Details
                    </ContextMenuItem>
                    {contextMenuNode?.group?.includes('_agg') && (
                        <ContextMenuItem onClick={() => handleContextAction('drilldown')}>
                            <Expand className="mr-2 h-4 w-4" />
                            Expand Group
                        </ContextMenuItem>
                    )}
                    {(contextMenuNode?.group === 'member' || contextMenuNode?.group === 'asset') && (
                        <ContextMenuItem onClick={() => handleContextAction('navigate')}>
                            <ExternalLink className="mr-2 h-4 w-4" />
                            Go to Profile
                        </ContextMenuItem>
                    )}
                </ContextMenuContent>
            </ContextMenu>

            {/* Controls overlay */}
            <div className="absolute top-4 left-4 flex flex-col gap-2">
                <Badge variant="secondary" className="text-xs">
                    Zoom: {currentZoom.toFixed(1)}x
                </Badge>
                <Button
                    variant="secondary"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => setLabelsVisible(!labelsVisible)}
                    title={labelsVisible ? 'Hide labels' : 'Show labels'}
                >
                    {labelsVisible ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                </Button>
            </div>

            {/* Legend */}
            <Card className="absolute top-4 right-4 p-3 bg-card/90 backdrop-blur-sm text-xs space-y-1.5 shadow-md">
                <div className="font-semibold text-muted-foreground uppercase tracking-wider mb-2">Legend</div>
                {Object.entries(DEFAULT_NODE_COLORS).slice(0, -1).map(([key, color]) => (
                    <div key={key} className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                        <span className="capitalize">{key.replace('_', ' ')}</span>
                    </div>
                ))}
            </Card>

            {/* Selected node indicator */}
            {selectedNode && (
                <div className="absolute bottom-4 left-4 right-4">
                    <Card className="p-3 bg-card/95 backdrop-blur-sm border-primary shadow-lg">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div
                                    className="w-4 h-4 rounded-full"
                                    style={{ backgroundColor: nodeColorFn(selectedNode) }}
                                />
                                <div>
                                    <div className="font-semibold">{selectedNode.name || selectedNode.id}</div>
                                    <div className="text-xs text-muted-foreground capitalize">
                                        {selectedNode.group} {selectedNode.party && `• ${selectedNode.party}`}
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                {selectedNode.value && (
                                    <Badge variant="secondary" className="text-green-500">
                                        {formatMoney(selectedNode.value)}
                                    </Badge>
                                )}
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleNodeSelect(null)}
                                >
                                    ✕
                                </Button>
                            </div>
                        </div>
                    </Card>
                </div>
            )}

            {/* Hover tooltip is handled by D3 */}
        </div>
    );
}
