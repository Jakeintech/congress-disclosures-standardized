'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Checkbox } from '@/components/ui/checkbox';
import { RotateCcw, Tag, Download, Filter, ChevronDown, ChevronUp } from 'lucide-react';

interface TradingNetworkGraphProps {
    data: any;
}

// Relationship type mapping for edge labels
const RELATIONSHIP_LABELS: Record<string, string> = {
    'trade': 'Traded',
    'purchase': 'Bought',
    'sale': 'Sold',
    'mixed': 'Bought & Sold',
    'sponsorship': 'Sponsored',
    'relationship': 'Family'
};

// Vibrant color gradients
const EDGE_COLORS = {
    purchase: { from: '#10b981', to: '#34d399', stroke: '#10b981' },
    sale: { from: '#ef4444', to: '#fb923c', stroke: '#ef4444' },
    mixed: { from: '#8b5cf6', to: '#a78bfa', stroke: '#8b5cf6' },
    sponsorship: { from: '#a855f7', to: '#c084fc', stroke: '#a855f7' },
    relationship: { from: '#f97316', to: '#fb923c', stroke: '#f97316' },
    trade: { from: '#6366f1', to: '#818cf8', stroke: '#6366f1' },
    default: { from: '#9ca3af', to: '#d1d5db', stroke: '#9ca3af' }
};

export function TradingNetworkGraph({ data: originalData }: TradingNetworkGraphProps) {
    const svgRef = useRef<SVGSVGElement>(null);
    const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
    const [labelsVisible, setLabelsVisible] = useState(true);
    const [edgeLabelsVisible, setEdgeLabelsVisible] = useState(true);
    const [selectedNode, setSelectedNode] = useState<any>(null);
    const [selectedEdge, setSelectedEdge] = useState<any>(null);
    const [hoveredEdge, setHoveredEdge] = useState<any>(null);
    const [currentZoom, setCurrentZoom] = useState(1);
    const [advancedOpen, setAdvancedOpen] = useState(false);

    // Filters
    const [partyFilter, setPartyFilter] = useState('all');
    const [chamberFilter, setChamberFilter] = useState('all');
    const [txTypeFilter, setTxTypeFilter] = useState('all');
    const [volumeThreshold, setVolumeThreshold] = useState([0]);
    const [searchQuery, setSearchQuery] = useState('');
    const [aggregationMode, setAggregationMode] = useState('party');

    // Relationship type filters
    const [relationshipFilters, setRelationshipFilters] = useState({
        trade: true,
        purchase: true,
        sale: true,
        mixed: true,
        sponsorship: true,
        relationship: true
    });

    // Advanced settings
    const [linkDistance, setLinkDistance] = useState([150]);
    const [chargeStrength, setChargeStrength] = useState([-200]);
    const [nodeSizeBy, setNodeSizeBy] = useState('volume');

    const formatMoney = (val: number) =>
        new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            notation: "compact"
        }).format(val);

    const getRelationshipLabel = (type: string): string => {
        return RELATIONSHIP_LABELS[type?.toLowerCase()] || type || 'Connected';
    };

    const getEdgeColor = (type: string): string => {
        const edgeType = type?.toLowerCase() || 'default';
        return EDGE_COLORS[edgeType as keyof typeof EDGE_COLORS]?.stroke || EDGE_COLORS.default.stroke;
    };

    const getEdgeGradientId = (type: string): string => {
        return `gradient-${type?.toLowerCase() || 'default'}`;
    };

    useEffect(() => {
        if (!originalData || !svgRef.current) return;

        renderGraph();
    }, [
        originalData,
        expandedGroups,
        labelsVisible,
        edgeLabelsVisible,
        partyFilter,
        chamberFilter,
        txTypeFilter,
        volumeThreshold,
        searchQuery,
        aggregationMode,
        linkDistance,
        chargeStrength,
        nodeSizeBy,
        relationshipFilters,
        hoveredEdge
    ]);

    const renderGraph = () => {
        if (!svgRef.current || !originalData) return;

        const container = svgRef.current.parentElement;
        if (!container) return;

        const width = container.clientWidth;
        const height = 700;

        // Clear previous
        d3.select(svgRef.current).selectAll('*').remove();

        // Apply filters
        const filteredData = applyFilters();

        // Setup SVG
        const svg = d3.select(svgRef.current)
            .attr('width', width)
            .attr('height', height);

        // Add gradient definitions
        const defs = svg.append('defs');

        Object.entries(EDGE_COLORS).forEach(([type, colors]) => {
            const gradient = defs.append('linearGradient')
                .attr('id', `gradient-${type}`)
                .attr('gradientUnits', 'userSpaceOnUse');

            gradient.append('stop')
                .attr('offset', '0%')
                .attr('stop-color', colors.from);

            gradient.append('stop')
                .attr('offset', '100%')
                .attr('stop-color', colors.to);
        });

        // Add glow filter for edges
        const glowFilter = defs.append('filter')
            .attr('id', 'edge-glow')
            .attr('x', '-50%')
            .attr('y', '-50%')
            .attr('width', '200%')
            .attr('height', '200%');

        glowFilter.append('feGaussianBlur')
            .attr('stdDeviation', '3')
            .attr('result', 'coloredBlur');

        const feMerge = glowFilter.append('feMerge');
        feMerge.append('feMergeNode').attr('in', 'coloredBlur');
        feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

        const g = svg.append('g');

        // Zoom
        const zoom = d3.zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.1, 8])
            .on('zoom', (event) => {
                g.attr('transform', event.transform.toString());
                setCurrentZoom(event.transform.k);
            });

        svg.call(zoom);

        // Double click to reset
        svg.on('dblclick.zoom', null);
        svg.on('dblclick', () => {
            setExpandedGroups(new Set());
            setSelectedNode(null);
            setSelectedEdge(null);
            setHoveredEdge(null);
        });

        // Process nodes
        const nodes = filteredData.nodes.map((n: any) => {
            const calculatedRadius = calculateNodeSize(n);
            return { ...n, calculatedRadius };
        });

        const links = filteredData.links.map((l: any) => ({ ...l }));

        // Simulation
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links)
                .id((d: any) => d.id)
                .distance((d: any) => d.is_aggregated ? linkDistance[0] * 0.67 : linkDistance[0])
                .strength((d: any) => d.is_aggregated ? 0.8 : 0.3))
            .force('charge', d3.forceManyBody()
                .strength((d: any) => d.group?.includes('_agg') ? chargeStrength[0] * 5 : chargeStrength[0]))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collide', d3.forceCollide()
                .radius((d: any) => d.calculatedRadius + 5)
                .strength(0.8))
            .force('x', d3.forceX(width / 2).strength(0.05))
            .force('y', d3.forceY(height / 2).strength(0.05));

        // Draw links
        const link = g.append('g')
            .attr('class', 'links')
            .selectAll('line')
            .data(links)
            .join('line')
            .attr('stroke-width', (d: any) => {
                const baseWidth = d.is_aggregated ? Math.max(2, Math.sqrt((d.value || 0) / 100000)) : Math.max(1, Math.sqrt((d.value || 0) / 50000));
                return hoveredEdge === d ? baseWidth * 1.5 : baseWidth;
            })
            .attr('stroke', (d: any) => {
                if (d.is_aggregated) return '#6b7280';
                const type = (d.type || 'default').toLowerCase();
                return `url(#${getEdgeGradientId(type)})`;
            })
            .attr('stroke-opacity', (d: any) => {
                if (hoveredEdge && hoveredEdge !== d) return 0.15;
                if (selectedNode) {
                    const sourceMatch = typeof d.source === 'object' ? d.source.id === selectedNode.id : d.source === selectedNode.id;
                    const targetMatch = typeof d.target === 'object' ? d.target.id === selectedNode.id : d.target === selectedNode.id;
                    return (sourceMatch || targetMatch) ? 0.8 : 0.15;
                }
                return d.is_aggregated ? 0.6 : 0.5;
            })
            .attr('stroke-dasharray', (d: any) => d.is_aggregated ? '5,5' : 'none')
            .style('cursor', 'pointer')
            .style('filter', (d: any) => (hoveredEdge === d || (d.value > 100000 && !d.is_aggregated)) ? 'url(#edge-glow)' : 'none')
            .style('transition', 'all 0.3s ease')
            .on('mouseenter', function (event: any, d: any) {
                setHoveredEdge(d);
            })
            .on('mouseleave', function (event: any, d: any) {
                setHoveredEdge(null);
            })
            .on('click', function (event: any, d: any) {
                event.stopPropagation();
                setSelectedEdge(d);
            });


        // Draw edge labels with deduplication
        // Group edges by source-target pair to prevent overlapping labels
        const edgeGroupMap = new Map<string, any[]>();
        links.forEach((link: any) => {
            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
            const targetId = typeof link.target === 'object' ? link.target.id : link.target;
            const key = `${sourceId}-${targetId}`;

            if (!edgeGroupMap.has(key)) {
                edgeGroupMap.set(key, []);
            }
            edgeGroupMap.get(key)!.push(link);
        });

        // For each group, keep only the highest-value edge for labeling
        const representativeEdges = Array.from(edgeGroupMap.values()).map(group => {
            return group.reduce((max, edge) =>
                (edge.value || 0) > (max.value || 0) ? edge : max
            );
        });

        const edgeLabels = g.append('g')
            .attr('class', 'edge-labels')
            .selectAll('g')
            .data(representativeEdges)
            .join('g')
            .attr('class', 'edge-label-group')
            .style('pointer-events', 'none');

        edgeLabels.append('rect')
            .attr('class', 'edge-label-bg')
            .attr('rx', 8)
            .attr('ry', 8)
            .attr('fill', 'rgba(17, 24, 39, 0.9)')
            .attr('stroke', (d: any) => getEdgeColor(d.type))
            .attr('stroke-width', 1.5)
            .style('opacity', (d: any) => {
                // Show label only if:
                // 1. It's the hovered edge, OR
                // 2. Edge labels are toggled on AND zoom >= 2.0 AND value >= $100K
                if (hoveredEdge === d) return 1;
                if (!edgeLabelsVisible) return 0;
                if (currentZoom < 2.0) return 0;
                if ((d.value || 0) < 100000) return 0;
                return 0.95;
            })
            .style('transition', 'opacity 0.3s ease');

        edgeLabels.append('text')
            .attr('class', 'edge-label-text')
            .attr('text-anchor', 'middle')
            .attr('dy', '0.35em')
            .style('font-size', '10px')
            .style('font-weight', '600')
            .style('fill', '#fff')
            .style('opacity', (d: any) => {
                if (hoveredEdge === d) return 1;
                if (!edgeLabelsVisible) return 0;
                if (currentZoom < 2.0) return 0;
                if ((d.value || 0) < 100000) return 0;
                return 1;
            })
            .style('transition', 'opacity 0.3s ease')
            .text((d: any) => getRelationshipLabel(d.type));

        // Measure text for background sizing
        edgeLabels.each(function (d: any) {
            const text = d3.select(this).select('text').node() as SVGTextElement;
            if (text) {
                const bbox = text.getBBox();
                d3.select(this).select('rect')
                    .attr('width', bbox.width + 12)
                    .attr('height', bbox.height + 6)
                    .attr('x', -bbox.width / 2 - 6)
                    .attr('y', -bbox.height / 2 - 3);
            }
        });

        // Draw nodes
        const node = g.append('g')
            .attr('class', 'nodes')
            .selectAll('g')
            .data(nodes)
            .join('g')
            .call(drag(simulation) as any);

        // Apply entry animation
        node.style('opacity', 0)
            .style('transform', 'scale(0)')
            .transition()
            .duration(500)
            .delay((d: any, i: number) => i * 10)
            .style('opacity', 1)
            .style('transform', 'scale(1)');

        // Node rendering with images using foreignObject
        node.each(function (d: any) {
            const nodeGroup = d3.select(this);

            // Use image-based rendering for non-aggregated nodes
            if (!d.group?.includes('_agg')) {
                const size = d.calculatedRadius * 2;

                // Import dynamically to avoid SSR issues
                import('@/components/analysis/NodeComponent').then(({ renderNodeToHTML }) => {
                    nodeGroup.append('foreignObject')
                        .attr('width', size)
                        .attr('height', size)
                        .attr('x', -size / 2)
                        .attr('y', -size / 2)
                        .style('overflow', 'visible')
                        .style('cursor', 'pointer')
                        .html(renderNodeToHTML(d, size))
                        .on('click', (event: any) => {
                            event.stopPropagation();
                            setSelectedNode(d);
                        });
                }).catch(() => {
                    // Fallback to circle if import fails
                    nodeGroup.append('circle')
                        .attr('r', d.calculatedRadius)
                        .attr('fill', getNodeColor(d))
                        .attr('stroke', getNodeStroke(d))
                        .attr('stroke-width', 2)
                        .style('cursor', 'pointer')
                        .on('click', (event: any) => {
                            event.stopPropagation();
                            setSelectedNode(d);
                        });
                });
            } else {
                // Aggregated nodes use circles with enhanced styling
                nodeGroup.append('circle')
                    .attr('r', d.calculatedRadius)
                    .attr('fill', getNodeColor(d))
                    .attr('stroke', getNodeStroke(d))
                    .attr('stroke-width', 3)
                    .attr('stroke-dasharray', '5,5')
                    .style('cursor', 'pointer')
                    .style('filter', 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1))')
                    .style('transition', 'all 0.3s ease')
                    .on('mouseenter', function (this: any) {
                        d3.select(this)
                            .transition()
                            .duration(200)
                            .attr('r', d.calculatedRadius * 1.15)
                            .style('filter', 'drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2))');
                    })
                    .on('mouseleave', function (this: any) {
                        d3.select(this)
                            .transition()
                            .duration(200)
                            .attr('r', d.calculatedRadius)
                            .style('filter', 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1))');
                    })
                    .on('click', (event: any) => {
                        event.stopPropagation();
                        const newExpanded = new Set(expandedGroups);
                        newExpanded.add(d.id);
                        setExpandedGroups(newExpanded);
                    });
            }
        });

        // Node labels
        node.append('text')
            .text((d: any) => d.group?.includes('_agg') || d.calculatedRadius > 5 ? d.id : '')
            .attr('dx', (d: any) => d.group?.includes('_agg') ? 0 : 12)
            .attr('dy', (d: any) => d.group?.includes('_agg') ? 5 : '.35em')
            .attr('text-anchor', (d: any) => d.group?.includes('_agg') ? 'middle' : 'start')
            .style('font-size', (d: any) => d.group?.includes('_agg') ? '14px' : '11px')
            .style('font-weight', (d: any) => d.group?.includes('_agg') ? 'bold' : '600')
            .style('pointer-events', 'none')
            .style('fill', 'currentColor')
            .attr('class', 'text-slate-900 dark:text-slate-100')
            .style('text-shadow', (d: any) => d.group?.includes('_agg') ? 'none' : '0 1px 4px var(--background)')
            .style('opacity', labelsVisible ? 1 : 0)
            .style('transition', 'opacity 0.3s ease');

        // Tooltip - use singleton pattern to prevent multiple instances
        // Check if tooltip already exists
        const existingTooltip = document.querySelector('.network-graph-tooltip');
        if (existingTooltip) {
            existingTooltip.remove();
        }

        const tooltip = d3.select('body').append('div')
            .attr('class', 'network-graph-tooltip absolute hidden bg-gray-900/95 backdrop-blur-sm text-white text-sm p-3 rounded-lg shadow-xl z-50 border border-gray-700')
            .style('pointer-events', 'none')
            .style('max-width', '300px');

        node.on('mouseover', (event: any, d: any) => {
            let html = `<strong class="text-base">${d.name || d.id}</strong><br>`;
            if (d.group === 'bill') {
                html += `<div class="max-w-xs text-xs mt-1 text-gray-300 italic">${d.title || ''}</div>`;
            } else if (d.group === 'person' && d.subgroup === 'family') {
                html += `<div class="text-xs mt-1 text-orange-300">Relationship: ${d.owner_code === 'SP' ? 'Spouse' : 'Dependent'}</div>`;
            } else {
                html += `<div class="text-sm mt-1">Volume: ${formatMoney(d.value || 0)}</div>`;
            }
            html += `<div class="text-xs text-gray-400 mt-1">Connections: ${d.degree || 0}</div>`;

            tooltip
                .style('display', 'block')
                .html(html)
                .style('left', (event.pageX + 15) + 'px')
                .style('top', (event.pageY - 10) + 'px');
        })
            .on('mouseout', () => {
                tooltip.style('display', 'none');
            });

        // Edge tooltip
        link.on('mouseover', (event: any, d: any) => {
            let html = `<strong class="text-base">${getRelationshipLabel(d.type)}</strong><br>`;
            if (d.count) {
                html += `<div class="text-sm mt-1">Transactions: ${d.count}</div>`;
            }
            if (d.value) {
                html += `<div class="text-sm">Total Value: ${formatMoney(d.value)}</div>`;
            }

            tooltip
                .style('display', 'block')
                .html(html)
                .style('left', (event.pageX + 15) + 'px')
                .style('top', (event.pageY - 10) + 'px');
        })
            .on('mouseout', () => {
                tooltip.style('display', 'none');
            });

        simulation.on('tick', () => {
            link
                .attr('x1', (d: any) => d.source.x)
                .attr('y1', (d: any) => d.source.y)
                .attr('x2', (d: any) => d.target.x)
                .attr('y2', (d: any) => d.target.y);

            edgeLabels.attr('transform', (d: any) => {
                const x = (d.source.x + d.target.x) / 2;
                const y = (d.source.y + d.target.y) / 2;
                const angle = Math.atan2(d.target.y - d.source.y, d.target.x - d.source.x) * 180 / Math.PI;
                const rotation = angle > 90 || angle < -90 ? angle + 180 : angle;
                return `translate(${x},${y}) rotate(${rotation})`;
            });

            node.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
        });

        return () => {
            tooltip.remove();
            simulation.stop();
        };
    };

    const applyFilters = () => {
        // Complex filtering logic from network.js adapted for React
        let nodes = JSON.parse(JSON.stringify(originalData.nodes || []));
        let links = JSON.parse(JSON.stringify(originalData.links || []));
        let aggNodes = JSON.parse(JSON.stringify(originalData.aggregated_nodes || []));
        let aggLinks = JSON.parse(JSON.stringify(originalData.aggregated_links || []));

        // Apply party filter
        if (partyFilter !== 'all') {
            nodes = nodes.filter((n: any) => n.group === 'asset' || n.party === partyFilter);
            aggNodes = aggNodes.filter((n: any) => n.party === partyFilter);
        }

        // Apply chamber filter
        if (chamberFilter !== 'all') {
            nodes = nodes.filter((n: any) => n.group === 'asset' || n.chamber === chamberFilter);
        }

        // Apply search
        if (searchQuery) {
            nodes = nodes.filter((n: any) => n.id.toLowerCase().includes(searchQuery.toLowerCase()));
        }

        // Determine visible nodes based on aggregation mode and expansion
        let visibleNodes: any[] = [];
        const visibleNodeIds = new Set<string>();

        // Add asset nodes (always visible)
        const assetNodes = nodes.filter((n: any) => n.group === 'asset');
        visibleNodes.push(...assetNodes);
        assetNodes.forEach((n: any) => visibleNodeIds.add(n.id));

        // Handle aggregation modes
        if (aggregationMode === 'none') {
            const memberNodes = nodes.filter((n: any) => n.group === 'member');
            visibleNodes.push(...memberNodes);
            memberNodes.forEach((n: any) => visibleNodeIds.add(n.id));
        } else if (aggregationMode === 'party') {
            ['Democrat', 'Republican'].forEach(party => {
                if (partyFilter !== 'all' && partyFilter !== party) return;
                if (expandedGroups.has(party)) {
                    const partyMembers = nodes.filter((n: any) => n.party === party && n.group === 'member');
                    visibleNodes.push(...partyMembers);
                    partyMembers.forEach((n: any) => visibleNodeIds.add(n.id));
                } else {
                    const aggNode = aggNodes.find((n: any) => n.id === party);
                    if (aggNode) {
                        visibleNodes.push(aggNode);
                        visibleNodeIds.add(aggNode.id);
                    }
                }
            });
        } else if (aggregationMode === 'chamber') {
            ['House', 'Senate'].forEach(chamber => {
                if (chamberFilter !== 'all' && chamberFilter !== chamber) return;
                if (expandedGroups.has(chamber)) {
                    const chamberMembers = nodes.filter((n: any) => n.chamber === chamber && n.group === 'member');
                    visibleNodes.push(...chamberMembers);
                    chamberMembers.forEach((n: any) => visibleNodeIds.add(n.id));
                } else {
                    let aggNode = aggNodes.find((n: any) => n.id === chamber);
                    if (!aggNode) {
                        const chamberNodes = nodes.filter((n: any) => n.chamber === chamber && n.group === 'member');
                        if (chamberNodes.length > 0) {
                            aggNode = {
                                id: chamber,
                                group: 'chamber_agg',
                                chamber: chamber,
                                value: chamberNodes.reduce((acc: number, curr: any) => acc + (curr.value || 0), 0),
                                transaction_count: chamberNodes.reduce((acc: number, curr: any) => acc + (curr.transaction_count || 0), 0)
                            };
                        }
                    }
                    if (aggNode) {
                        visibleNodes.push(aggNode);
                        visibleNodeIds.add(aggNode.id);
                    }
                }
            });
        } else if (aggregationMode === 'state') {
            const states = Array.from(new Set(nodes.map((n: any) => n.state))).filter(s => s && s !== 'N/A') as string[];
            states.forEach(state => {
                if (expandedGroups.has(state)) {
                    const stateMembers = nodes.filter((n: any) => n.state === state && n.group === 'member');
                    visibleNodes.push(...stateMembers);
                    stateMembers.forEach((n: any) => visibleNodeIds.add(n.id));
                } else {
                    const stateNodes = nodes.filter((n: any) => n.state === state && n.group === 'member');
                    const aggNode = {
                        id: state,
                        group: 'state_agg',
                        state: state,
                        value: stateNodes.reduce((acc: number, curr: any) => acc + (curr.value || 0), 0),
                        transaction_count: stateNodes.reduce((acc: number, curr: any) => acc + (curr.transaction_count || 0), 0)
                    };
                    visibleNodes.push(aggNode);
                    visibleNodeIds.add(aggNode.id);
                }
            });
        } else if (aggregationMode === 'household') {
            const memberIds = new Set<string>(nodes.filter((n: any) => n.group === 'member').map((n: any) => n.id as string));
            memberIds.forEach((mId: string) => {
                if (expandedGroups.has(mId)) {
                    const familyNodes = nodes.filter((n: any) =>
                        (n.id === mId && n.group === 'member') ||
                        (n.parent_id === mId && n.group === 'person' && n.subgroup === 'family')
                    );
                    visibleNodes.push(...familyNodes);
                    familyNodes.forEach((n: any) => visibleNodeIds.add(n.id));
                } else {
                    const householdNodes = nodes.filter((n: any) =>
                        n.id === mId || (n.parent_id === mId && n.subgroup === 'family')
                    );
                    const memberNode = nodes.find((n: any) => n.id === mId);
                    const aggNode = {
                        id: mId,
                        name: `${memberNode?.name || mId} Household`,
                        group: 'household_agg',
                        value: householdNodes.reduce((acc: number, curr: any) => acc + (curr.value || 0), 0),
                        transaction_count: householdNodes.reduce((acc: number, curr: any) => acc + (curr.transaction_count || 0), 0),
                        is_primary: memberNode?.is_primary
                    };
                    visibleNodes.push(aggNode);
                    visibleNodeIds.add(aggNode.id);
                }
            });
        }

        // Filter links
        let visibleLinks = links.filter((l: any) => {
            const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
            const targetId = typeof l.target === 'object' ? l.target.id : l.target;
            return visibleNodeIds.has(sourceId) && visibleNodeIds.has(targetId);
        });

        // Add aggregated links for modes
        if (aggregationMode === 'party') {
            ['Democrat', 'Republican'].forEach(party => {
                if (!expandedGroups.has(party) && visibleNodeIds.has(party)) {
                    const partyAggLinks = aggLinks.filter((l: any) => l.source === party);
                    partyAggLinks.forEach((l: any) => {
                        if (visibleNodeIds.has(l.target)) visibleLinks.push(l);
                    });
                }
            });
        } else if (aggregationMode === 'chamber') {
            ['House', 'Senate'].forEach(chamber => {
                if (!expandedGroups.has(chamber) && visibleNodeIds.has(chamber)) {
                    const chamberMembers = new Set(nodes.filter((n: any) => n.chamber === chamber).map((n: any) => n.id));
                    const chamberLinks = links.filter((l: any) => chamberMembers.has(l.source));

                    const stockMap = new Map();
                    chamberLinks.forEach((l: any) => {
                        if (!stockMap.has(l.target)) stockMap.set(l.target, { value: 0, count: 0 });
                        stockMap.get(l.target).value += (l.value || 0);
                        stockMap.get(l.target).count += (l.count || 1);
                    });

                    stockMap.forEach((stats, stockId) => {
                        if (visibleNodeIds.has(stockId)) {
                            visibleLinks.push({
                                source: chamber,
                                target: stockId,
                                value: stats.value,
                                count: stats.count,
                                is_aggregated: true
                            });
                        }
                    });
                }
            });
        }

        // Apply relationship type filters
        visibleLinks = visibleLinks.filter((l: any) => {
            const type = (l.type || 'trade').toLowerCase();
            return relationshipFilters[type as keyof typeof relationshipFilters] !== false;
        });

        // Apply volume threshold
        if (volumeThreshold[0] > 0) {
            visibleLinks = visibleLinks.filter((l: any) => l.value >= volumeThreshold[0]);
        }

        // Remove orphan nodes
        const connectedNodeIds = new Set<string>();
        visibleLinks.forEach((l: any) => {
            const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
            const targetId = typeof l.target === 'object' ? l.target.id : l.target;
            connectedNodeIds.add(sourceId);
            connectedNodeIds.add(targetId);
        });

        visibleNodes = visibleNodes.filter((n: any) => connectedNodeIds.has(n.id));

        return { nodes: visibleNodes, links: visibleLinks };
    };

    const calculateNodeSize = (d: any) => {
        const baseSize = d.group === 'member' ? 12 : d.group === 'asset' ? 10 : d.group === 'bill' ? 8 : 10;

        if (d.is_primary) return 24;

        if (d.group?.includes('_agg')) {
            return Math.max(40, Math.min(80, 40 + Math.sqrt(d.value || 0) / 1000));
        }

        let scale = 0;
        if (nodeSizeBy === 'volume') {
            scale = Math.sqrt(d.value || 0) / 200;
        } else if (nodeSizeBy === 'count') {
            scale = (d.transaction_count || d.count || 0) * 1.5;
        } else {
            scale = (d.degree || 0) * 2;
        }

        return Math.max(8, Math.min(60, baseSize + scale));
    };

    const getNodeColor = (d: any) => {
        if (d.group === 'party_agg') {
            return d.id === 'Democrat' ? 'rgba(59, 130, 246, 0.5)' : 'rgba(239, 68, 68, 0.5)';
        }
        if (d.group === 'asset') return '#10b981';
        if (d.group === 'bill') return '#a855f7';
        if (d.group === 'person' && d.subgroup === 'family') return '#f97316';

        if (d.party === 'Republican' || d.party === 'R') return '#ef4444';
        if (d.party === 'Democrat' || d.party === 'D') return '#3b82f6';
        return '#9ca3af';
    };

    const getNodeStroke = (d: any) => {
        if (d.is_primary) return '#000';
        if (d.group?.includes('_agg')) {
            return d.id === 'Democrat' ? '#3b82f6' : '#ef4444';
        }
        return '#fff';
    };

    const drag = (simulation: any): any => {
        function dragstarted(event: any) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }

        function dragged(event: any) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }

        function dragended(event: any) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }

        return d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended);
    };

    const resetView = () => {
        setExpandedGroups(new Set());
        setSelectedNode(null);
        setSelectedEdge(null);
        setPartyFilter('all');
        setChamberFilter('all');
        setTxTypeFilter('all');
        setVolumeThreshold([0]);
        setSearchQuery('');
        setRelationshipFilters({
            trade: true,
            purchase: true,
            sale: true,
            mixed: true,
            sponsorship: true,
            relationship: true
        });
    };

    const toggleRelationshipFilter = (type: keyof typeof relationshipFilters) => {
        setRelationshipFilters(prev => ({
            ...prev,
            [type]: !prev[type]
        }));
    };

    return (
        <div className="space-y-4">
            {/* Modern Glassmorphism Controls */}
            <Card className="p-5 bg-white/80 backdrop-blur-md border border-gray-200/50 shadow-lg">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div>
                        <Label className="text-sm font-semibold text-gray-700">Aggregation Mode</Label>
                        <Select value={aggregationMode} onValueChange={setAggregationMode}>
                            <SelectTrigger className="mt-1.5 border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="party">By Party</SelectItem>
                                <SelectItem value="chamber">By Chamber</SelectItem>
                                <SelectItem value="state">By State</SelectItem>
                                <SelectItem value="volume">By Volume</SelectItem>
                                <SelectItem value="household">By Household</SelectItem>
                                <SelectItem value="none">No Aggregation</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div>
                        <Label className="text-sm font-semibold text-gray-700">Party Filter</Label>
                        <Select value={partyFilter} onValueChange={setPartyFilter}>
                            <SelectTrigger className="mt-1.5 border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All Parties</SelectItem>
                                <SelectItem value="Democrat">Democrat</SelectItem>
                                <SelectItem value="Republican">Republican</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div>
                        <Label className="text-sm font-semibold text-gray-700">Chamber Filter</Label>
                        <Select value={chamberFilter} onValueChange={setChamberFilter}>
                            <SelectTrigger className="mt-1.5 border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All Chambers</SelectItem>
                                <SelectItem value="House">House</SelectItem>
                                <SelectItem value="Senate">Senate</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div>
                        <Label className="text-sm font-semibold text-gray-700">Search Members</Label>
                        <Input
                            placeholder="Search..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="mt-1.5 border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
                        />
                    </div>
                </div>

                {/* Relationship Type Filters */}
                <div className="mt-4 pt-4 border-t border-gray-200">
                    <Label className="text-sm font-semibold text-gray-700 mb-3 block">Relationship Types</Label>
                    <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
                        {Object.entries(relationshipFilters).map(([type, enabled]) => (
                            <div key={type} className="flex items-center space-x-2">
                                <Checkbox
                                    id={`filter-${type}`}
                                    checked={enabled}
                                    onCheckedChange={() => toggleRelationshipFilter(type as keyof typeof relationshipFilters)}
                                    className="border-2 data-[state=checked]:bg-gradient-to-br data-[state=checked]:from-blue-500 data-[state=checked]:to-blue-600"
                                />
                                <label
                                    htmlFor={`filter-${type}`}
                                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer flex items-center gap-1.5"
                                >
                                    <div
                                        className="w-3 h-3 rounded-full"
                                        style={{ backgroundColor: getEdgeColor(type) }}
                                    />
                                    {RELATIONSHIP_LABELS[type] || type}
                                </label>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={resetView}
                        className="border-gray-300 hover:bg-gradient-to-r hover:from-blue-50 hover:to-purple-50 transition-all"
                    >
                        <RotateCcw className="h-4 w-4 mr-2" />
                        Reset View
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setLabelsVisible(!labelsVisible)}
                        className="border-gray-300 hover:bg-gradient-to-r hover:from-blue-50 hover:to-purple-50 transition-all"
                    >
                        <Tag className="h-4 w-4 mr-2" />
                        {labelsVisible ? 'Hide' : 'Show'} Node Labels
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setEdgeLabelsVisible(!edgeLabelsVisible)}
                        className="border-gray-300 hover:bg-gradient-to-r hover:from-blue-50 hover:to-purple-50 transition-all"
                    >
                        <Tag className="h-4 w-4 mr-2" />
                        {edgeLabelsVisible ? 'Hide' : 'Show'} Edge Labels
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setAdvancedOpen(!advancedOpen)}
                        className="border-gray-300 hover:bg-gradient-to-r hover:from-blue-50 hover:to-purple-50 transition-all"
                    >
                        <Filter className="h-4 w-4 mr-2" />
                        Advanced
                        {advancedOpen ? <ChevronUp className="h-4 w-4 ml-1" /> : <ChevronDown className="h-4 w-4 ml-1" />}
                    </Button>
                </div>

                {/* Advanced Settings - Collapsible */}
                {advancedOpen && (
                    <div className="mt-4 pt-4 border-t border-gray-200 space-y-4 animate-in slide-in-from-top-2 duration-300">
                        <div>
                            <Label className="text-sm font-semibold text-gray-700">Node Size By</Label>
                            <Select value={nodeSizeBy} onValueChange={setNodeSizeBy}>
                                <SelectTrigger className="mt-1.5">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="volume">Transaction Volume</SelectItem>
                                    <SelectItem value="count">Transaction Count</SelectItem>
                                    <SelectItem value="degree">Number of Connections</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <Label className="text-sm font-semibold text-gray-700">Link Distance: {linkDistance[0]}</Label>
                            <Slider
                                value={linkDistance}
                                onValueChange={setLinkDistance}
                                min={50}
                                max={300}
                                step={10}
                                className="mt-2"
                            />
                        </div>
                        <div>
                            <Label className="text-sm font-semibold text-gray-700">Charge Strength: {chargeStrength[0]}</Label>
                            <Slider
                                value={chargeStrength}
                                onValueChange={setChargeStrength}
                                min={-500}
                                max={-50}
                                step={10}
                                className="mt-2"
                            />
                        </div>
                    </div>
                )}
            </Card>

            {/* Graph with Modern Styling */}
            <div className="relative border-2 border-gray-200 rounded-xl bg-gradient-to-br from-gray-50 to-gray-100 overflow-hidden shadow-xl" style={{ height: '700px' }}>
                <svg ref={svgRef} className="w-full h-full" />

                {/* Enhanced Legend with Glassmorphism */}
                <div className="absolute top-4 right-4 bg-white/90 backdrop-blur-md p-4 rounded-xl border border-gray-200/50 shadow-lg text-xs">
                    <div className="font-bold mb-3 text-sm text-gray-800">Legend</div>
                    <div className="space-y-2">
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 rounded-full bg-blue-500 shadow-sm" />
                            <span className="font-medium">Democrat</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 rounded-full bg-red-500 shadow-sm" />
                            <span className="font-medium">Republican</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 rounded-full bg-green-500 shadow-sm" />
                            <span className="font-medium">Stock / Asset</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 rounded-full bg-purple-500 shadow-sm" />
                            <span className="font-medium">Sponsored Bill</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 rounded-full bg-orange-500 shadow-sm" />
                            <span className="font-medium">Family Member</span>
                        </div>
                        <div className="h-px bg-gray-300 my-2" />
                        <div className="text-xs font-semibold text-gray-700 mb-1.5">Edge Types:</div>
                        {Object.entries(RELATIONSHIP_LABELS).map(([type, label]) => (
                            <div key={type} className="flex items-center gap-2">
                                <div
                                    className="w-8 h-0.5 rounded-full"
                                    style={{
                                        background: `linear-gradient(to right, ${EDGE_COLORS[type as keyof typeof EDGE_COLORS]?.from}, ${EDGE_COLORS[type as keyof typeof EDGE_COLORS]?.to})`
                                    }}
                                />
                                <span className="font-medium text-xs">{label}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Instructions */}
                <div className="absolute bottom-4 left-4 bg-white/85 backdrop-blur-sm p-3 rounded-lg text-xs text-gray-700 max-w-md shadow-md border border-gray-200/50">
                    <p className="font-semibold mb-1">💡 Interaction Guide:</p>
                    <p>• <strong>Click</strong> aggregate nodes to expand • <strong>Drag</strong> to rearrange • <strong>Scroll</strong> to zoom</p>
                    <p>• <strong>Hover</strong> edges for details • <strong>Double-click</strong> to reset view</p>
                </div>

                {/* Zoom indicator */}
                <div className="absolute top-4 left-4 bg-white/85 backdrop-blur-sm px-3 py-1.5 rounded-lg text-xs font-semibold text-gray-700 shadow-md border border-gray-200/50">
                    Zoom: {currentZoom.toFixed(1)}x
                </div>
            </div>

            {/* Selected Node Details */}
            {selectedNode && (
                <Card className="p-5 bg-gradient-to-br from-white to-blue-50/30 border-2 border-blue-200 shadow-lg">
                    <div className="flex justify-between items-start mb-4">
                        <div>
                            <h3 className="font-bold text-xl text-gray-900">{selectedNode.id}</h3>
                            <p className="text-sm text-gray-600 capitalize font-medium">{selectedNode.group}</p>
                        </div>
                        <Button variant="ghost" size="sm" onClick={() => setSelectedNode(null)} className="hover:bg-red-100">
                            ×
                        </Button>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {selectedNode.party && (
                            <div>
                                <div className="text-xs text-gray-500 font-semibold">Party</div>
                                <div className="font-bold text-lg">{selectedNode.party}</div>
                            </div>
                        )}
                        {selectedNode.chamber && (
                            <div>
                                <div className="text-xs text-gray-500 font-semibold">Chamber</div>
                                <div className="font-bold text-lg">{selectedNode.chamber}</div>
                            </div>
                        )}
                        {selectedNode.group === 'bill' ? (
                            <div className="col-span-2">
                                <div className="text-xs text-gray-500 font-semibold">Title</div>
                                <div className="text-sm line-clamp-2">{selectedNode.title}</div>
                            </div>
                        ) : (
                            <>
                                <div>
                                    <div className="text-xs text-gray-500 font-semibold">Total Volume</div>
                                    <div className="font-bold text-lg text-green-600">{formatMoney(selectedNode.value || 0)}</div>
                                </div>
                                <div>
                                    <div className="text-xs text-gray-500 font-semibold">Transactions</div>
                                    <div className="font-bold text-lg">{selectedNode.transaction_count || 0}</div>
                                </div>
                            </>
                        )}
                    </div>
                </Card>
            )}

            {/* Selected Edge Details */}
            {selectedEdge && (
                <Card className="p-5 bg-gradient-to-br from-white to-purple-50/30 border-2 border-purple-200 shadow-lg">
                    <div className="flex justify-between items-start mb-4">
                        <div>
                            <h3 className="font-bold text-xl text-gray-900">
                                {getRelationshipLabel(selectedEdge.type)} Connection
                            </h3>
                            <p className="text-sm text-gray-600 font-medium">
                                {typeof selectedEdge.source === 'object' ? selectedEdge.source.id : selectedEdge.source} → {typeof selectedEdge.target === 'object' ? selectedEdge.target.id : selectedEdge.target}
                            </p>
                        </div>
                        <Button variant="ghost" size="sm" onClick={() => setSelectedEdge(null)} className="hover:bg-red-100">
                            ×
                        </Button>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                        <div>
                            <div className="text-xs text-gray-500 font-semibold">Relationship Type</div>
                            <div className="font-bold text-lg flex items-center gap-2">
                                <div
                                    className="w-4 h-4 rounded-full"
                                    style={{ backgroundColor: getEdgeColor(selectedEdge.type) }}
                                />
                                {getRelationshipLabel(selectedEdge.type)}
                            </div>
                        </div>
                        {selectedEdge.count && (
                            <div>
                                <div className="text-xs text-gray-500 font-semibold">Transaction Count</div>
                                <div className="font-bold text-lg">{selectedEdge.count}</div>
                            </div>
                        )}
                        {selectedEdge.value && (
                            <div>
                                <div className="text-xs text-gray-500 font-semibold">Total Value</div>
                                <div className="font-bold text-lg text-green-600">{formatMoney(selectedEdge.value)}</div>
                            </div>
                        )}
                    </div>
                </Card>
            )}
        </div>
    );
}
