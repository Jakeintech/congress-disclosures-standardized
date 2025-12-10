'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { type NetworkGraphData, type NetworkGraphNode, type NetworkGraphLink } from '@/types/api';
//yes 
interface NetworkGraphProps {
    data: NetworkGraphData;
    width?: number;
    height?: number;
}

export function NetworkGraph({ data, width = 800, height = 600 }: NetworkGraphProps) {
    const svgRef = useRef<SVGSVGElement>(null);
    const [selectedNode, setSelectedNode] = useState<NetworkGraphNode | null>(null);
    const [tooltip, setTooltip] = useState<{ x: number; y: number; content: React.ReactNode } | null>(null);

    // Simulation state to keep it persistent across renders if needed
    const simulationRef = useRef<d3.Simulation<NetworkGraphNode, NetworkGraphLink> | null>(null);

    useEffect(() => {
        if (!data.nodes?.length || !svgRef.current) return;

        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove(); // Clear previous render

        const g = svg.append('g');

        // Zoom capability
        const zoom = d3.zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.1, 8])
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            });

        svg.call(zoom);

        // Process data copies to avoid mutating props
        const nodes = (data.nodes || []).map(d => ({ ...d })) as NetworkGraphNode[];
        const links = (data.links || []).map(d => ({ ...d })) as NetworkGraphLink[];

        // radius scale
        const radiusScale = d3.scaleLog()
            .domain([1000, 10000000])
            .range([4, 20])
            .clamp(true);

        const getNodeRadius = (d: NetworkGraphNode) => {
            if (d.type === 'member') return 8;
            if (d.type === 'bill') return 6;
            // Clients/Lobbyists sized by spend/revenue if available
            return Math.max(5, Math.min(20, Math.sqrt((d.spend || 0) / 10000) + 5));
        };

        const getNodeColor = (d: NetworkGraphNode) => {
            if (d.type === 'member') {
                if (d.party === 'Democrat') return '#3b82f6'; // blue-500
                if (d.party === 'Republican') return '#ef4444'; // red-500
                return '#8b5cf6'; // purple-500
            }
            if (d.type === 'bill') return '#10b981'; // emerald-500
            if (d.type === 'client') return '#f59e0b'; // amber-500
            if (d.type === 'lobbyist') return '#a855f7'; // purple-500 (distinct from member purple? maybe use pink)
            return '#94a3b8'; // slate-400
        };

        // Forces
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink<NetworkGraphNode, NetworkGraphLink>(links).id((d: NetworkGraphNode) => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-200))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collide', d3.forceCollide<NetworkGraphNode>().radius((d: NetworkGraphNode) => getNodeRadius(d) + 2));

        simulationRef.current = simulation;

        // Links
        const link = g.append('g')
            .selectAll<SVGLineElement, NetworkGraphLink>('line')
            .data(links)
            .join('line')
            .attr('stroke', '#cbd5e1')
            .attr('stroke-opacity', 0.6)
            .attr('stroke-width', (d) => Math.sqrt((d.value || 0) / 10000) + 1);

        // Nodes group (circle + text)
        const node = g.append('g')
            .selectAll('.node')
            .data(nodes)
            .join('g')
            .attr('class', 'node')
            .call(d3.drag<any, any>()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended) as any);

        // Node Circles
        node.append('circle')
            .attr('r', getNodeRadius)
            .attr('fill', getNodeColor)
            .attr('stroke', '#fff')
            .attr('stroke-width', 1.5)
            .style('cursor', 'pointer')
            .on('click', (event, d) => {
                event.stopPropagation();
                setSelectedNode(d);
            })
            .on('mouseover', (event, d) => {
                const label = d.name || d.id;
                setTooltip({
                    x: event.pageX,
                    y: event.pageY,
                    content: (
                        <div className="space-y-1">
                            <div className="font-bold">{label}</div>
                            <div className="text-xs capitalize">{d.type}</div>
                            {d.party && <div className="text-xs text-muted-foreground">{d.party} - {d.state}</div>}
                            {d.spend && <div className="text-xs font-mono">${d.spend.toLocaleString()}</div>}
                        </div>
                    )
                });
            })
            .on('mouseout', () => setTooltip(null));

        // Node Labels (only for larger nodes)
        node.append('text')
            .attr('dx', 12)
            .attr('dy', '.35em')
            .text(d => (d.spend && d.spend > 1000000) || d.type === 'member' ? (d.name || d.id) : '')
            .style('font-size', '10px')
            .style('fill', '#475569')
            .style('pointer-events', 'none');

        // Simulation tick
        simulation.on('tick', () => {
            link
                .attr('x1', (d: any) => d.source.x)
                .attr('y1', (d: any) => d.source.y)
                .attr('x2', (d: any) => d.target.x)
                .attr('y2', (d: any) => d.target.y);

            node.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
        });

        // Drag functions
        function dragstarted(event: any, d: any) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }

        function dragged(event: any, d: any) {
            d.fx = event.x;
            d.fy = event.y;
        }

        function dragended(event: any, d: any) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }

        return () => {
            simulation.stop();
        };
    }, [data, width, height]);

    return (
        <div className="relative border rounded-lg overflow-hidden bg-slate-50">
            <svg
                ref={svgRef}
                width={width}
                height={height}
                viewBox={`0 0 ${width} ${height}`}
                className="w-full h-full"
            />

            {/* Simple Tooltip */}
            {tooltip && (
                <div
                    className="absolute z-10 bg-white border border-slate-200 text-slate-800 text-xs px-2 py-2 rounded shadow-lg pointer-events-none transform -translate-x-1/2 -translate-y-full mt-[-8px] min-w-[120px]"
                    style={{ left: tooltip.x - (svgRef.current?.getBoundingClientRect().left || 0), top: tooltip.y - (svgRef.current?.getBoundingClientRect().top || 0) }}
                >
                    {tooltip.content}
                </div>
            )}

            {/* Legend Overlay */}
            <Card className="absolute top-4 right-4 p-4 w-48 bg-white/90 backdrop-blur-sm shadow-sm">
                <h4 className="font-semibold text-xs mb-2 text-muted-foreground uppercase tracking-wider">Legend</h4>
                <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-blue-500"></span>
                        <span>Democrat</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-red-500"></span>
                        <span>Republican</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-emerald-500"></span>
                        <span>Bill</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-amber-500"></span>
                        <span>Client</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-purple-500"></span>
                        <span>Lobbyist</span>
                    </div>
                </div>
            </Card>

            {/* Node Details Sheet */}
            <Sheet open={!!selectedNode} onOpenChange={(open) => !open && setSelectedNode(null)}>
                <SheetContent>
                    <SheetHeader>
                        <SheetTitle>{selectedNode?.name || selectedNode?.id}</SheetTitle>
                        <SheetDescription>
                            {selectedNode?.type === 'member' ? (
                                <span className="flex items-center gap-2 mt-2">
                                    <Badge variant={selectedNode.party === 'Democrat' ? 'default' : selectedNode.party === 'Republican' ? 'destructive' : 'secondary'}>
                                        {selectedNode.party}
                                    </Badge>
                                    <Badge variant="outline">{selectedNode.chamber || 'Unknown Chamber'}</Badge>
                                    {selectedNode.state && <Badge variant="outline">{selectedNode.state}</Badge>}
                                </span>
                            ) : (
                                <Badge variant="secondary" className="capitalize">{selectedNode?.type}</Badge>
                            )}
                        </SheetDescription>
                    </SheetHeader>

                    <div className="mt-6 space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            {(selectedNode?.spend !== undefined) && (
                                <div className="space-y-1">
                                    <p className="text-xs font-medium text-muted-foreground">Volume</p>
                                    <p className="text-lg font-mono font-bold">
                                        ${(selectedNode?.spend || 0).toLocaleString()}
                                    </p>
                                </div>
                            )}
                            <div className="space-y-1">
                                <p className="text-xs font-medium text-muted-foreground">Connections</p>
                                <p className="text-lg font-mono font-bold">
                                    {selectedNode?.connections || 0}
                                </p>
                            </div>
                        </div>

                        {selectedNode && (
                            <div className="pt-4 border-t">
                                <h4 className="font-semibold mb-2 text-sm">Description</h4>
                                <p className="text-sm text-muted-foreground">
                                    {selectedNode.type === 'member'
                                        ? `Member of Congress connected to bills and lobbying firms.`
                                        : selectedNode.type === 'bill'
                                            ? 'Legislative bill targeted by lobbying.'
                                            : 'Entity involved in lobbying activity.'}
                                </p>
                            </div>
                        )}

                        <div className="pt-4">
                            <Button className="w-full" onClick={() => setSelectedNode(null)}>Close</Button>
                        </div>
                    </div>
                </SheetContent>
            </Sheet>
        </div>
    );
}
