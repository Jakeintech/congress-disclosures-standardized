/**
 * Enhanced Network Graph with Hierarchical Drill-Down
 */

let originalData = null;
let filteredData = null;
let currentSimulation = null;
let currentSvg = null;
let labelsVisible = true;
let currentViewMode = 'detailed';
let selectedNode = null;

// State for hierarchical view
let expandedGroups = new Set(); // Stores IDs of expanded aggregated nodes (e.g., 'Democrat', 'Republican')

document.addEventListener('DOMContentLoaded', () => {
    loadNetworkGraph();
    setupEventListeners();
});

async function loadNetworkGraph() {
    try {
        const response = await fetch('https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/website/data/network_graph.json');
        if (response.ok) {
            originalData = await response.json();
            // Initialize with no groups expanded
            expandedGroups.clear();

            // Initial filter application
            applyFilters();
        }
    } catch (err) {
        console.log('Network graph not yet available:', err);
        document.getElementById('network-graph-container').innerHTML = `<div class="error-state"><p>Error loading graph data. Please try again later.</p></div>`;
    }
}

function setupEventListeners() {
    // Filter controls
    document.getElementById('party-filter')?.addEventListener('change', applyFilters);
    document.getElementById('chamber-filter')?.addEventListener('change', applyFilters);
    document.getElementById('transaction-type-filter')?.addEventListener('change', applyFilters);
    document.getElementById('volume-threshold')?.addEventListener('input', (e) => {
        document.getElementById('volume-display').textContent = `$${parseInt(e.target.value).toLocaleString()}`;
        debounce(applyFilters, 300)();
    });
    document.getElementById('member-search')?.addEventListener('input', debounce(applyFilters, 300));

    // View mode buttons
    document.querySelectorAll('.view-mode-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.view-mode-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentViewMode = e.target.dataset.mode;

            if (currentViewMode === 'overview') {
                expandedGroups.clear();
            } else if (currentViewMode === 'detailed') {
                expandedGroups.add('Democrat');
                expandedGroups.add('Republican');
            }
            applyFilters();
        });
    });

    // Node sizing
    document.getElementById('node-size-by')?.addEventListener('change', () => {
        if (filteredData) renderGraph(filteredData);
    });

    // Graph controls
    document.getElementById('reset-view')?.addEventListener('click', resetView);
    document.getElementById('toggle-labels')?.addEventListener('click', toggleLabels);
    document.getElementById('export-filtered')?.addEventListener('click', exportFiltered);
}

function applyFilters() {
    if (!originalData) return;

    const partyFilter = document.getElementById('party-filter')?.value || 'all';
    const chamberFilter = document.getElementById('chamber-filter')?.value || 'all';
    const txTypeFilter = document.getElementById('transaction-type-filter')?.value || 'all';
    const volumeThreshold = parseInt(document.getElementById('volume-threshold')?.value || 0);
    const searchQuery = document.getElementById('member-search')?.value.toLowerCase() || '';

    // 1. Filter Base Nodes (Members and Assets)
    let nodes = JSON.parse(JSON.stringify(originalData.nodes));
    let links = JSON.parse(JSON.stringify(originalData.links));
    let aggNodes = JSON.parse(JSON.stringify(originalData.aggregated_nodes || []));
    let aggLinks = JSON.parse(JSON.stringify(originalData.aggregated_links || []));

    // Apply party filter (affects members)
    if (partyFilter !== 'all') {
        nodes = nodes.filter(n => n.group === 'asset' || n.party === partyFilter);
        // Also filter agg nodes if they match the party
        aggNodes = aggNodes.filter(n => n.party === partyFilter);
    }

    // Apply chamber filter
    if (chamberFilter !== 'all') {
        nodes = nodes.filter(n => n.group === 'asset' || n.chamber === chamberFilter);
    }

    // Apply search filter
    if (searchQuery) {
        nodes = nodes.filter(n => n.id.toLowerCase().includes(searchQuery));
        // If searching, we might want to auto-expand relevant groups, but for now let's just filter
    }

    // 2. Determine Visible Nodes based on Expansion State
    let visibleNodes = [];
    let visibleNodeIds = new Set();

    // Add Asset Nodes (always visible if they pass filters)
    const assetNodes = nodes.filter(n => n.group === 'asset');
    visibleNodes.push(...assetNodes);
    assetNodes.forEach(n => visibleNodeIds.add(n.id));

    // Add Member Nodes OR Aggregated Nodes
    const parties = ['Democrat', 'Republican'];

    parties.forEach(party => {
        // If party is filtered out, skip
        if (partyFilter !== 'all' && partyFilter !== party) return;

        if (expandedGroups.has(party)) {
            // Show individual members
            const partyMembers = nodes.filter(n => n.party === party && n.group === 'member');
            visibleNodes.push(...partyMembers);
            partyMembers.forEach(n => visibleNodeIds.add(n.id));
        } else {
            // Show aggregated node
            const aggNode = aggNodes.find(n => n.id === party);
            if (aggNode) {
                visibleNodes.push(aggNode);
                visibleNodeIds.add(aggNode.id);
            }
        }
    });

    // Add 'Unknown' or other parties members directly for now (or group them if we had an 'Other' agg node)
    const otherMembers = nodes.filter(n => !parties.includes(n.party) && n.group === 'member');
    visibleNodes.push(...otherMembers);
    otherMembers.forEach(n => visibleNodeIds.add(n.id));


    // 3. Determine Visible Links
    let visibleLinks = [];

    // Case A: Member <-> Asset (when group is expanded)
    const memberLinks = links.filter(l => {
        const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
        const targetId = typeof l.target === 'object' ? l.target.id : l.target;
        return visibleNodeIds.has(sourceId) && visibleNodeIds.has(targetId);
    });
    visibleLinks.push(...memberLinks);

    // Case B: Aggregated Node <-> Asset (when group is collapsed)
    const activeAggNodes = parties.filter(p => !expandedGroups.has(p) && visibleNodeIds.has(p));

    activeAggNodes.forEach(party => {
        // Find aggregated links for this party
        const partyAggLinks = aggLinks.filter(l => l.source === party);
        partyAggLinks.forEach(l => {
            if (visibleNodeIds.has(l.target)) {
                visibleLinks.push(l);
            }
        });
    });

    // Apply transaction type filter to links
    if (txTypeFilter !== 'all') {
        visibleLinks = visibleLinks.filter(l => l.type?.toLowerCase().includes(txTypeFilter) || l.type === 'mixed');
    }

    // Apply volume threshold
    if (volumeThreshold > 0) {
        visibleLinks = visibleLinks.filter(l => l.value >= volumeThreshold);
    }

    // Remove orphan nodes (optional, but keeps graph clean)
    const connectedNodeIds = new Set();
    visibleLinks.forEach(l => {
        const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
        const targetId = typeof l.target === 'object' ? l.target.id : l.target;
        connectedNodeIds.add(sourceId);
        connectedNodeIds.add(targetId);
    });

    // Always keep aggregated nodes visible even if no links (they act as anchors)
    activeAggNodes.forEach(id => connectedNodeIds.add(id));

    visibleNodes = visibleNodes.filter(n => connectedNodeIds.has(n.id));

    filteredData = {
        ...originalData,
        nodes: visibleNodes,
        links: visibleLinks
    };

    updateStats(filteredData);
    renderGraph(filteredData);
}

function updateStats(data) {
    document.getElementById('stat-nodes').textContent = data.nodes?.length || 0;
    document.getElementById('stat-links').textContent = data.links?.length || 0;
    document.getElementById('stat-transactions').textContent = originalData?.summary_stats?.total_transactions?.toLocaleString() || '-';
}

function renderGraph(data) {
    const container = document.getElementById('network-graph-container');
    if (!container) return;

    // Only create container structure once
    if (!document.getElementById('network-svg')) {
        container.innerHTML = `
            <div style="height: 700px; border: 1px solid #e5e7eb; border-radius: 8px; position: relative; overflow: hidden; background: #f8f9fa;">
                <div id="network-svg" style="width: 100%; height: 100%;"></div>
                
                <!-- Legend -->
                <div style="position: absolute; top: 10px; right: 10px; background: rgba(255,255,255,0.95); padding: 12px; border-radius: 8px; border: 1px solid #e5e7eb; font-size: 0.8rem; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                    <div style="font-weight: 600; margin-bottom: 8px;">Legend</div>
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                        <div style="width: 12px; height: 12px; border-radius: 50%; background: #ef4444;"></div>
                        <span>Republican</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                        <div style="width: 12px; height: 12px; border-radius: 50%; background: #3b82f6;"></div>
                        <span>Democrat</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                        <div style="width: 14px; height: 14px; border-radius: 50%; border: 2px solid #3b82f6; background: rgba(59, 130, 246, 0.2);"></div>
                        <span>Aggregated Group</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 12px; height: 12px; border-radius: 50%; background: #10b981;"></div>
                        <span>Asset</span>
                    </div>
                </div>

                <!-- Tooltip -->
                <div id="tooltip" style="position: absolute; display: none; background: rgba(0,0,0,0.85); color: white; padding: 10px; border-radius: 6px; font-size: 0.85rem; pointer-events: none; z-index: 100; max-width: 300px;"></div>
                
                <!-- Instructions -->
                <div style="position: absolute; bottom: 10px; left: 10px; background: rgba(255,255,255,0.8); padding: 8px; border-radius: 4px; font-size: 0.75rem; color: #666;">
                    Click group nodes to expand/collapse.<br>
                    Drag nodes to rearrange.<br>
                    Scroll to zoom.
                </div>
            </div>
        `;
    }

    renderD3(data);
}

function renderD3(data) {
    const selector = '#network-svg';
    const element = document.querySelector(selector);
    const width = element.clientWidth;
    const height = element.clientHeight;

    // Clear previous SVG if it exists to prevent duplicates during hot reloads, 
    // but ideally we want to update existing simulation. 
    // For simplicity in this refactor, we'll re-render but try to preserve positions if possible.
    d3.select(selector).selectAll("*").remove();

    const svg = d3.select(selector)
        .append("svg")
        .attr("width", width)
        .attr("height", height);

    const g = svg.append("g");

    // Zoom
    const zoom = d3.zoom()
        .scaleExtent([0.1, 8])
        .on("zoom", (event) => {
            g.attr("transform", event.transform);
        });

    svg.call(zoom);

    // Double click background to reset/collapse all
    svg.on("dblclick.zoom", null); // Disable default zoom double click
    svg.on("dblclick", () => {
        expandedGroups.clear();
        applyFilters();
    });

    // Process Nodes for Sizing
    const sizeBy = document.getElementById('node-size-by')?.value || 'volume';
    const nodes = data.nodes.map(n => {
        let newRadius;
        if (n.group === 'party_agg') {
            newRadius = 40; // Fixed size for aggregators
        } else if (sizeBy === 'count') {
            newRadius = Math.log((n.transaction_count || 0) + 1) * 2;
        } else if (sizeBy === 'degree') {
            newRadius = Math.log((n.degree || 0) + 1) * 2;
        } else {
            newRadius = Math.log((n.value || 0) + 1000) / 2;
        }
        return {
            ...n,
            calculatedRadius: Math.max(3, Math.min(50, newRadius))
        };
    });

    const links = data.links.map(l => ({ ...l }));

    // Simulation Setup
    const simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(d => d.id).distance(d => {
            // Aggregated links are stronger/shorter
            if (d.is_aggregated) return 100;
            return 150;
        }).strength(d => d.is_aggregated ? 0.8 : 0.3))
        .force("charge", d3.forceManyBody()
            .strength(d => {
                if (d.group === 'party_agg') return -1000;
                return -200;
            })
        )
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collide", d3.forceCollide()
            .radius(d => d.calculatedRadius + 5)
            .strength(0.8)
        )
        .force("x", d3.forceX(width / 2).strength(0.05))
        .force("y", d3.forceY(height / 2).strength(0.05));

    // Custom Clustering Force
    // Pull members towards their party center (if expanded) or just generally group them
    simulation.force("cluster", alpha => {
        const partyCenters = {
            'Democrat': { x: width * 0.3, y: height * 0.5 },
            'Republican': { x: width * 0.7, y: height * 0.5 }
        };

        nodes.forEach(d => {
            if (d.group === 'party_agg') {
                // Pull agg nodes to their designated sides
                const target = partyCenters[d.id];
                if (target) {
                    d.vx -= (d.x - target.x) * alpha * 0.1;
                    d.vy -= (d.y - target.y) * alpha * 0.1;
                }
            } else if (d.group === 'member') {
                // Pull members towards their party side
                const target = partyCenters[d.party];
                if (target) {
                    d.vx -= (d.x - target.x) * alpha * 0.05;
                    d.vy -= (d.y - target.y) * alpha * 0.05;
                }
            }
        });
    });

    currentSimulation = simulation;

    // Draw Links
    const link = g.append("g")
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke-width", d => {
            if (d.is_aggregated) return Math.max(2, Math.sqrt((d.value || 0) / 100000));
            return Math.max(1, Math.sqrt((d.value || 0) / 50000));
        })
        .attr("stroke", d => {
            if (d.is_aggregated) return '#6b7280'; // Neutral for aggregated
            const type = (d.type || '').toLowerCase();
            if (type.includes('purchase') || type.includes('buy')) return '#22c55e';
            if (type.includes('sale') || type.includes('sell')) return '#ef4444';
            return '#9ca3af';
        })
        .attr("stroke-opacity", d => d.is_aggregated ? 0.6 : 0.4);

    // Draw Nodes
    const node = g.append("g")
        .selectAll("g") // Group for circle + label
        .data(nodes)
        .join("g")
        .call(drag(simulation));

    // Node Circles
    node.append("circle")
        .attr("r", d => d.calculatedRadius)
        .attr("fill", d => {
            if (d.group === 'party_agg') {
                return d.id === 'Democrat' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(239, 68, 68, 0.2)';
            }
            if (d.group === 'asset') return '#10b981';
            if (d.party === 'Republican') return '#ef4444';
            if (d.party === 'Democrat') return '#3b82f6';
            return '#9ca3af';
        })
        .attr("stroke", d => {
            if (d.group === 'party_agg') {
                return d.id === 'Democrat' ? '#3b82f6' : '#ef4444';
            }
            return "#fff";
        })
        .attr("stroke-width", d => d.group === 'party_agg' ? 3 : 1.5)
        .attr("stroke-dasharray", d => d.group === 'party_agg' ? "5,5" : "none")
        .style("cursor", "pointer")
        .on("click", (event, d) => {
            if (d.group === 'party_agg') {
                // Expand group
                expandedGroups.add(d.id);
                applyFilters();
            } else if (d.group === 'member') {
                // Maybe highlight ego network?
                selectedNode = d.id;
                // Optional: trigger ego view
            }
        });

    // Node Labels (Inside for Agg, Outside for others)
    node.append("text")
        .text(d => {
            if (d.group === 'party_agg') return d.id;
            return d.calculatedRadius > 5 ? d.id : '';
        })
        .attr("dx", d => d.group === 'party_agg' ? 0 : 12)
        .attr("dy", d => d.group === 'party_agg' ? 5 : ".35em")
        .attr("text-anchor", d => d.group === 'party_agg' ? "middle" : "start")
        .style("font-size", d => d.group === 'party_agg' ? "14px" : "10px")
        .style("font-weight", d => d.group === 'party_agg' ? "bold" : "normal")
        .style("pointer-events", "none")
        .style("fill", "#374151")
        .style("text-shadow", "1px 1px 0 #fff, -1px -1px 0 #fff, 1px -1px 0 #fff, -1px 1px 0 #fff")
        .style("opacity", labelsVisible ? 1 : 0);

    // Tooltip
    const tooltip = d3.select("#tooltip");

    node.on("mouseover", (event, d) => {
        // Highlight
        node.style("opacity", 0.1);
        link.style("opacity", 0.05);

        const connectedIds = new Set([d.id]);
        link.filter(l => l.source.id === d.id || l.target.id === d.id)
            .style("opacity", 1)
            .each(l => {
                connectedIds.add(l.source.id);
                connectedIds.add(l.target.id);
            });

        node.filter(n => connectedIds.has(n.id)).style("opacity", 1);

        // Tooltip content
        const formatMoney = (val) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: "compact" }).format(val);
        let content = `<strong>${d.id}</strong><br>`;

        if (d.group === 'party_agg') {
            content += `<em>Click to expand</em><br>`;
            content += `Total Volume: ${formatMoney(d.value || 0)}<br>`;
            content += `Transactions: ${d.transaction_count || 0}`;
        } else {
            if (d.group === 'member') {
                content += `Party: ${d.party || 'Unknown'}<br>`;
                content += `Chamber: ${d.chamber || 'Unknown'}<br>`;
            }
            content += `Volume: ${formatMoney(d.value || 0)}<br>`;
            content += `Transactions: ${d.transaction_count || 0}<br>`;
            content += `Connections: ${d.degree || 0}`;
        }

        tooltip.style("display", "block")
            .html(content)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 10) + "px");
    })
        .on("mouseout", () => {
            node.style("opacity", 1);
            link.style("opacity", d => d.is_aggregated ? 0.6 : 0.4);
            tooltip.style("display", "none");
        });

    simulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        node.attr("transform", d => `translate(${d.x},${d.y})`);
    });

    currentSvg = svg;
}

function drag(simulation) {
    function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
    }

    function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
    }

    function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
    }

    return d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended);
}

function resetView() {
    selectedNode = null;
    expandedGroups.clear();
    document.getElementById('party-filter').value = 'all';
    document.getElementById('chamber-filter').value = 'all';
    document.getElementById('transaction-type-filter').value = 'all';
    document.getElementById('volume-threshold').value = '0';
    document.getElementById('volume-display').textContent = '$0';
    document.getElementById('member-search').value = '';
    applyFilters();
}

function toggleLabels() {
    labelsVisible = !labelsVisible;
    if (filteredData) renderGraph(filteredData);
}

function exportFiltered() {
    if (!filteredData || !filteredData.links) return;

    const headers = ['Source', 'Target', 'Type', 'Value', 'Count', 'IsAggregated'];
    const rows = filteredData.links.map(l => [
        typeof l.source === 'object' ? l.source.id : l.source,
        typeof l.target === 'object' ? l.target.id : l.target,
        l.type || '',
        l.value || 0,
        l.count || 0,
        l.is_aggregated || false
    ]);

    const csv = [headers.join(','), ...rows.map(row => row.map(c => `"${c}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'filtered_network_graph.csv';
    a.click();
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
