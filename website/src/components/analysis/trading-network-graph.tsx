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
import { RotateCcw, Tag, Download } from 'lucide-react';

interface TradingNetworkGraphProps {
    data: any;
}

export function TradingNetworkGraph({ data: originalData }: TradingNetworkGraphProps) {
    const svgRef = useRef<SVGSVGElement>(null);
    const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
    const [labelsVisible, setLabelsVisible] = useState(true);
    const [selectedNode, setSelectedNode] = useState<any>(null);

    // Filters
    const [partyFilter, setPartyFilter] = useState('all');
    const [chamberFilter, setChamberFilter] = useState('all');
    const [txTypeFilter, setTxTypeFilter] = useState('all');
    const [volumeThreshold, setVolumeThreshold] = useState([0]);
    const [searchQuery, setSearchQuery] = useState('');
    const [aggregationMode, setAggregationMode] = useState('party');

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

    useEffect(() => {
        if (!originalData || !svgRef.current) return;

        renderGraph();
    }, [
        originalData,
        expandedGroups,
        labelsVisible,
        partyFilter,
        chamberFilter,
        txTypeFilter,
        volumeThreshold,
        searchQuery,
        aggregationMode,
        linkDistance,
        chargeStrength,
        nodeSizeBy
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

        const g = svg.append('g');

        // Zoom
        const zoom = d3.zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.1, 8])
            .on('zoom', (event) => {
                g.attr('transform', event.transform.toString());
            });

        svg.call(zoom);

        // Double click to reset
        svg.on('dblclick', () => {
            setExpandedGroups(new Set());
            setSelectedNode(null);
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
            .selectAll('line')
            .data(links)
            .join('line')
            .attr('stroke-width', (d: any) => d.is_aggregated ? Math.max(2, Math.sqrt((d.value || 0) / 100000)) : Math.max(1, Math.sqrt((d.value || 0) / 50000)))
            .attr('stroke', (d: any) => {
                if (d.is_aggregated) return '#6b7280';
                const type = (d.type || '').toLowerCase();
                if (type.includes('purchase') || type.includes('buy')) return '#22c55e';
                if (type.includes('sale') || type.includes('sell')) return '#ef4444';
                return '#9ca3af';
            })
            .attr('stroke-opacity', (d: any) => d.is_aggregated ? 0.6 : 0.4);

        // Draw nodes
        const node = g.append('g')
            .selectAll('g')
            .data(nodes)
            .join('g')
            .call(drag(simulation) as any);

        // Node circles
        node.append('circle')
            .attr('r', (d: any) => d.calculatedRadius)
            .attr('fill', getNodeColor)
            .attr('stroke', getNodeStroke)
            .attr('stroke-width', (d: any) => d.group?.includes('_agg') ? 3 : 1.5)
            .attr('stroke-dasharray', (d: any) => d.group?.includes('_agg') ? '5,5' : 'none')
            .style('cursor', 'pointer')
            .on('click', (event: any, d: any) => {
                event.stopPropagation();
                if (d.group?.includes('_agg')) {
                    const newExpanded = new Set(expandedGroups);
                    newExpanded.add(d.id);
                    setExpandedGroups(newExpanded);
                } else {
                    setSelectedNode(d);
                }
            });

        // Labels
        node.append('text')
            .text((d: any) => d.group?.includes('_agg') || d.calculatedRadius > 5 ? d.id : '')
            .attr('dx', (d: any) => d.group?.includes('_agg') ? 0 : 12)
            .attr('dy', (d: any) => d.group?.includes('_agg') ? 5 : '.35em')
            .attr('text-anchor', (d: any) => d.group?.includes('_agg') ? 'middle' : 'start')
            .style('font-size', (d: any) => d.group?.includes('_agg') ? '14px' : '10px')
            .style('font-weight', (d: any) => d.group?.includes('_agg') ? 'bold' : 'normal')
            .style('pointer-events', 'none')
            .style('fill', '#374151')
            .style('opacity', labelsVisible ? 1 : 0);

        // Tooltip
        const tooltip = d3.select('body').append('div')
            .attr('class', 'absolute hidden bg-gray-900 text-white text-sm p-2 rounded shadow-lg z-50')
            .style('pointer-events', 'none');

        node.on('mouseover', (event: any, d: any) => {
            tooltip
                .style('display', 'block')
                .html(`<strong>${d.id}</strong><br>Volume: ${formatMoney(d.value || 0)}<br>Connections: ${d.degree || 0}`)
                .style('left', (event.pageX + 10) + 'px')
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

            node.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
        });

        return () => {
            tooltip.remove();
            simulation.stop();
        };
    };

    const applyFilters = () => {
        // Complex filtering logic from network.js adapted for React
        // This is a simplified version - full implementation would match network.js logic
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
                    // Create chamber agg node if not in data (client-side backup)
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
                    // Group links by chamber
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
        const baseSize = d.group === 'member' ? 8 : d.group === 'asset' ? 10 : 12;
        if (d.group?.includes('_agg')) {
            // Aggregated nodes should be quite large, representing the total volume
            return Math.max(40, Math.min(80, 40 + Math.sqrt(d.value || 0) / 1000));
        }

        let scale = 0;
        if (nodeSizeBy === 'volume') {
            // More dramatic scale for volume
            scale = Math.sqrt(d.value || 0) / 200;
        } else if (nodeSizeBy === 'count') {
            scale = (d.transaction_count || 0) * 1.5;
        } else {
            scale = (d.degree || 0) * 2;
        }

        return Math.max(5, Math.min(60, baseSize + scale));
    };

    const getNodeColor = (d: any) => {
        if (d.group === 'party_agg') {
            return d.id === 'Democrat' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(239, 68, 68, 0.2)';
        }
        if (d.group === 'asset') return '#10b981';
        if (d.party === 'Republican') return '#ef4444';
        if (d.party === 'Democrat') return '#3b82f6';
        return '#9ca3af';
    };

    const getNodeStroke = (d: any) => {
        if (d.group === 'party_agg') {
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
        setPartyFilter('all');
        setChamberFilter('all');
        setTxTypeFilter('all');
        setVolumeThreshold([0]);
        setSearchQuery('');
    };

    return (
        <div className="space-y-4">
            {/* Controls */}
            <Card className="p-4">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div>
                        <Label>Aggregation Mode</Label>
                        <Select value={aggregationMode} onValueChange={setAggregationMode}>
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="party">By Party</SelectItem>
                                <SelectItem value="chamber">By Chamber</SelectItem>
                                <SelectItem value="state">By State</SelectItem>
                                <SelectItem value="volume">By Volume</SelectItem>
                                <SelectItem value="none">No Aggregation</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div>
                        <Label>Party Filter</Label>
                        <Select value={partyFilter} onValueChange={setPartyFilter}>
                            <SelectTrigger>
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
                        <Label>Chamber Filter</Label>
                        <Select value={chamberFilter} onValueChange={setChamberFilter}>
                            <SelectTrigger>
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
                        <Label>Search Members</Label>
                        <Input
                            placeholder="Search..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                </div>

                <div className="mt-4 flex gap-2">
                    <Button variant="outline" size="sm" onClick={resetView}>
                        <RotateCcw className="h-4 w-4 mr-2" />
                        Reset View
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => setLabelsVisible(!labelsVisible)}>
                        <Tag className="h-4 w-4 mr-2" />
                        {labelsVisible ? 'Hide' : 'Show'} Labels
                    </Button>
                </div>
            </Card>

            {/* Graph */}
            <div className="relative border rounded-lg bg-gray-50 overflow-hidden" style={{ height: '700px' }}>
                <svg ref={svgRef} className="w-full h-full" />

                {/* Legend */}
                <div className="absolute top-4 right-4 bg-white/95 p-3 rounded-lg border shadow-sm text-xs">
                    <div className="font-semibold mb-2">Legend</div>
                    <div className="space-y-1">
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full bg-red-500" />
                            <span>Republican</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full bg-blue-500" />
                            <span>Democrat</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full bg-green-500" />
                            <span>Asset</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 rounded-full border-2 border-blue-500 bg-blue-100" />
                            <span>Aggregated</span>
                        </div>
                    </div>
                </div>

                {/* Instructions */}
                <div className="absolute bottom-4 left-4 bg-white/80 p-2 rounded text-xs text-gray-600 max-w-xs">
                    Click aggregate nodes to expand. Drag to rearrange. Scroll to zoom. Double-click to reset.
                </div>
            </div>

            {/* Selected Node Details */}
            {selectedNode && (
                <Card className="p-4">
                    <div className="flex justify-between items-start mb-4">
                        <div>
                            <h3 className="font-semibold text-lg">{selectedNode.id}</h3>
                            <p className="text-sm text-muted-foreground capitalize">{selectedNode.group}</p>
                        </div>
                        <Button variant="ghost" size="sm" onClick={() => setSelectedNode(null)}>
                            ×
                        </Button>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {selectedNode.party && (
                            <div>
                                <div className="text-sm text-muted-foreground">Party</div>
                                <div className="font-semibold">{selectedNode.party}</div>
                            </div>
                        )}
                        {selectedNode.chamber && (
                            <div>
                                <div className="text-sm text-muted-foreground">Chamber</div>
                                <div className="font-semibold">{selectedNode.chamber}</div>
                            </div>
                        )}
                        <div>
                            <div className="text-sm text-muted-foreground">Total Volume</div>
                            <div className="font-semibold">{formatMoney(selectedNode.value || 0)}</div>
                        </div>
                        <div>
                            <div className="text-sm text-muted-foreground">Transactions</div>
                            <div className="font-semibold">{selectedNode.transaction_count || 0}</div>
                        </div>
                    </div>
                </Card>
            )}
        </div>
    );
}
