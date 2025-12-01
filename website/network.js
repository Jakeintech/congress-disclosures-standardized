/**
 * Enhanced Network Graph with SNA Filtering and Interactive Features
 */

let originalData = null;
let filteredData = null;
let currentSimulation = null;
let currentSvg = null;
let labelsVisible = true;
let currentViewMode = 'detailed';
let selectedNode = null;

document.addEventListener('DOMContentLoaded', () => {
    loadNetworkGraph();
    setupEventListeners();
});

async function loadNetworkGraph() {
    try {
        const response = await fetch('https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/website/data/network_graph.json');
        if (response.ok) {
            originalData = await response.json();
            filteredData = JSON.parse(JSON.stringify(originalData)); // Deep copy
            updateStats(originalData);
            applyFilters();
        }
    } catch (err) {
        console.log('Network graph not yet available:', err);
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

    let nodes = JSON.parse(JSON.stringify(originalData.nodes));
    let links = JSON.parse(JSON.stringify(originalData.links));

    // Apply party filter
    if (partyFilter !== 'all') {
        nodes = nodes.filter(n => n.group === 'asset' || n.party === partyFilter);
    }

    // Apply chamber filter
    if (chamberFilter !== 'all') {
        nodes = nodes.filter(n => n.group === 'asset' || n.chamber === chamberFilter);
    }

    // Apply search filter
    if (searchQuery) {
        nodes = nodes.filter(n => n.id.toLowerCase().includes(searchQuery));
    }

    // Get valid node IDs after filtering
    const validNodeIds = new Set(nodes.map(n => n.id));

    // Filter links based on remaining nodes
    links = links.filter(l => {
        const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
        const targetId = typeof l.target === 'object' ? l.target.id : l.target;
        return validNodeIds.has(sourceId) && validNodeIds.has(targetId);
    });

    // Apply transaction type filter
    if (txTypeFilter !== 'all') {
        links = links.filter(l => l.type?.toLowerCase().includes(txTypeFilter));
    }

    // Apply volume threshold
    if (volumeThreshold > 0) {
        links = links.filter(l => l.value >= volumeThreshold);
    }

    // Recalculate connected nodes (remove orphans)
    const connectedNodeIds = new Set();
    links.forEach(l => {
        const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
        const targetId = typeof l.target === 'object' ? l.target.id : l.target;
        connectedNodeIds.add(sourceId);
        connectedNodeIds.add(targetId);
    });
    nodes = nodes.filter(n => connectedNodeIds.has(n.id));

    // Apply view mode transformations
    if (currentViewMode === 'ego' && selectedNode) {
        const egoNodeIds = new Set([selectedNode]);
        links.forEach(l => {
            const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
            const targetId = typeof l.target === 'object' ? l.target.id : l.target;
            if (sourceId === selectedNode || targetId === selectedNode) {
                egoNodeIds.add(sourceId);
                egoNodeIds.add(targetId);
            }
        });
        nodes = nodes.filter(n => egoNodeIds.has(n.id));
        links = links.filter(l => {
            const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
            const targetId = typeof l.target === 'object' ? l.target.id : l.target;
            return egoNodeIds.has(sourceId) && egoNodeIds.has(targetId);
        });
    }

    filteredData = {
        ...originalData,
        nodes,
        links
    };

    updateStats(filteredData);
    renderGraph(filteredData);
}

function updateStats(data) {
    document.getElementById('stat-nodes').textContent = data.nodes?.length || 0;
    document.getElementById('stat-links').textContent = data.links?.length || 0;
    document.getElementById('stat-transactions').textContent = data.summary_stats?.total_transactions?.toLocaleString() || '-';
}

function renderGraph(data) {
    const container = document.getElementById('network-graph-container');
    if (!container) return;

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
                    <div style="width: 12px; height: 12px; border-radius: 50%; background: #9ca3af;"></div>
                    <span>Other/Unknown</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 12px; height: 12px; border-radius: 50%; background: #10b981;"></div>
                    <span>Asset</span>
                </div>
            </div>

            <!-- Tooltip -->
            <div id="tooltip" style="position: absolute; display: none; background: rgba(0,0,0,0.85); color: white; padding: 10px; border-radius: 6px; font-size: 0.85rem; pointer-events: none; z-index: 100; max-width: 300px;"></div>
        </div>
    `;

    renderD3(data);
}

function renderD3(data) {
    const selector = '#network-svg';
    const element = document.querySelector(selector);
    const width = element.clientWidth;
    const height = element.clientHeight;

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

    // Get node sizing metric
    const sizeBy = document.getElementById('node-size-by')?.value || 'volume';
    const nodes = data.nodes.map(n => {
        let newRadius;
        if (sizeBy === 'count') {
            newRadius = Math.log((n.transaction_count || 0) + 1) * 2;
        } else if (sizeBy === 'degree') {
            newRadius = Math.log((n.degree || 0) + 1) * 2;
        } else {
            newRadius = Math.log((n.value || 0) + 1000) / 2;
        }
        return {
            ...n,
            calculatedRadius: Math.max(3, Math.min(20, newRadius))
        };
    });

    const links = data.links.map(l => ({ ...l }));

    // Calculate community cluster positions for better layout
    const communities = {};
    const memberNodes = nodes.filter(n => n.group === 'member');

    memberNodes.forEach(n => {
        const communityId = n.community_id || 'Unknown';
        if (!communities[communityId]) {
            communities[communityId] = [];
        }
        communities[communityId].push(n);
    });

    // Assign radial positions for communities (arrange around circle)
    const communityIds = Object.keys(communities);
    const angleStep = (2 * Math.PI) / communityIds.length;
    const clusterRadius = Math.min(width, height) * 0.3;

    communityIds.forEach((id, i) => {
        const angle = i * angleStep;
        const cx = width / 2 + Math.cos(angle) * clusterRadius;
        const cy = height / 2 + Math.sin(angle) * clusterRadius;
        communities[id].forEach(node => {
            node.clusterX = cx;
            node.clusterY = cy;
        });
    });

    // Enhanced simulation with clustering forces
    const simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(d => d.id).distance(d => {
            // Shorter links within same community, longer between different communities
            if (d.source.community_id && d.target.community_id &&
                d.source.community_id === d.target.community_id) {
                return 80;
            }
            return 150;
        }).strength(0.5))
        .force("charge", d3.forceManyBody()
            .strength(d => {
                // Stronger repulsion for member nodes to spread them out
                return d.group === 'member' ? -300 : -150;
            })
        )
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collide", d3.forceCollide()
            .radius(d => d.calculatedRadius + 5)  // Add padding between nodes
            .strength(0.8)
        )
        // Add clustering force - pull members towards their community centers
        .force("cluster", alpha => {
            memberNodes.forEach(n => {
                if (n.clusterX !== undefined) {
                    const k = alpha * 0.1;  // Clustering strength
                    n.vx -= (n.x - n.clusterX) * k;
                    n.vy -= (n.y - n.clusterY) * k;
                }
            });
        })
        // Add party-based grouping - pull same-party members closer
        .force("party", alpha => {
            const parties = {};
            memberNodes.forEach(n => {
                const party = n.party || 'Unknown';
                if (!parties[party]) parties[party] = [];
                parties[party].push(n);
            });

            Object.values(parties).forEach(partyNodes => {
                if (partyNodes.length < 2) return;

                // Calculate centroid for this party
                let cx = 0, cy = 0;
                partyNodes.forEach(n => {
                    cx += n.x || 0;
                    cy += n.y || 0;
                });
                cx /= partyNodes.length;
                cy /= partyNodes.length;

                // Pull nodes towards party centroid
                partyNodes.forEach(n => {
                    const k = alpha * 0.05;  // Party clustering strength
                    n.vx -= (n.x - cx) * k;
                    n.vy -= (n.y - cy) * k;
                });
            });
        });

    currentSimulation = simulation;

    // Links
    const link = g.append("g")
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke-width", d => Math.max(1, Math.sqrt((d.value || 0) / 50000)))
        .attr("stroke", d => {
            const type = (d.type || '').toLowerCase();
            if (type.includes('purchase') || type.includes('buy')) return '#22c55e';
            if (type.includes('sale') || type.includes('sell')) return '#ef4444';
            return '#9ca3af';
        })
        .attr("stroke-opacity", 0.4);

    // Nodes
    const node = g.append("g")
        .selectAll("circle")
        .data(nodes)
        .join("circle")
        .attr("r", d => d.calculatedRadius)
        .attr("fill", d => {
            if (d.group === 'asset') return '#10b981';
            if (d.party === 'Republican') return '#ef4444';
            if (d.party === 'Democrat') return '#3b82f6';
            return '#9ca3af';
        })
        .attr("stroke", "#fff")
        .attr("stroke-width", 1.5)
        .style("cursor", "pointer")
        .call(drag(simulation))
        .on("click", (event, d) => {
            selectedNode = d.id;
            if (currentViewMode === 'ego') {
                applyFilters();
            }
        });

    // Labels
    const label = g.append("g")
        .selectAll("text")
        .data(nodes)
        .join("text")
        .attr("dx", 12)
        .attr("dy", ".35em")
        .text(d => d.calculatedRadius > 5 ? d.id : '')
        .style("font-size", "10px")
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
        label.style("opacity", 0.1);

        const connectedIds = new Set([d.id]);
        link.filter(l => l.source.id === d.id || l.target.id === d.id)
            .style("opacity", 1)
            .each(l => {
                connectedIds.add(l.source.id);
                connectedIds.add(l.target.id);
            });

        node.filter(n => connectedIds.has(n.id)).style("opacity", 1);
        label.filter(n => connectedIds.has(n.id)).style("opacity", labelsVisible ? 1 : 0).text(n => n.id);

        // Tooltip content
        const formatMoney = (val) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: "compact" }).format(val);
        let content = `<strong>${d.id}</strong><br>`;
        if (d.group === 'member') {
            content += `Party: ${d.party || 'Unknown'}<br>`;
            content += `Chamber: ${d.chamber || 'Unknown'}<br>`;
            if (d.state) content += `State: ${d.state}<br>`;
            if (d.community_id) content += `Community: ${d.community_id}<br>`;
        }
        content += `Volume: ${formatMoney(d.value || 0)}<br>`;
        content += `Transactions: ${d.transaction_count || 0}<br>`;
        content += `Connections: ${d.degree || 0}`;

        tooltip.style("display", "block")
            .html(content)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 10) + "px");
    })
        .on("mouseout", () => {
            node.style("opacity", 1);
            link.style("opacity", 0.4);
            label.style("opacity", labelsVisible ? 1 : 0).text(d => d.calculatedRadius > 5 ? d.id : '');
            tooltip.style("display", "none");
        });

    simulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        node
            .attr("cx", d => d.x)
            .attr("cy", d => d.y);

        label
            .attr("x", d => d.x)
            .attr("y", d => d.y);
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

    const headers = ['Source', 'Target', 'Type', 'Value', 'Count'];
    const rows = filteredData.links.map(l => [
        typeof l.source === 'object' ? l.source.id : l.source,
        typeof l.target === 'object' ? l.target.id : l.target,
        l.type || '',
        l.value || 0,
        l.count || 0
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
