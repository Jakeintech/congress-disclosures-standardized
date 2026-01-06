// Lobbying Network Graph Visualization
const API_BASE = window.CONFIG?.API_BASE || 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com';

// State
let networkData = null;
let filteredData = null;
let simulation = null;
let svg, g, zoom;
let labelsVisible = true;
let selectedNode = null;

// Colors for node types
const COLORS = {
    member: '#3b82f6',      // Blue circles
    bill: '#10b981',        // Green circles
    client: '#f59e0b',      // Orange squares
    lobbyist: '#a855f7',    // Purple diamonds
    link: {
        sponsored: '#10b981',
        lobbied: '#f59e0b',
        traded: '#3b82f6',
        contributed: '#a855f7',
        default: '#6b7280'
    }
};

// Node shapes
const SHAPES = {
    member: 'circle',
    bill: 'circle',
    client: 'rect',
    lobbyist: 'diamond'
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeSVG();
    fetchNetworkData();
    setupEventListeners();
});

function initializeSVG() {
    const container = document.getElementById('graph-container');
    const width = container.clientWidth;
    const height = container.clientHeight;

    svg = d3.select('#graph-svg')
        .attr('width', width)
        .attr('height', height);

    g = svg.append('g');

    // Zoom behavior
    zoom = d3.zoom()
        .scaleExtent([0.1, 8])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
        });

    svg.call(zoom);

    // Click background to deselect
    svg.on('click', function (event) {
        if (event.target.tagName === 'svg') {
            deselectNode();
        }
    });
}

async function fetchNetworkData() {
    try {
        const year = document.getElementById('filter-year').value;

        // Add timeout for Lambda cold start (can take 3-5 seconds)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000);

        console.log('Fetching network data for year:', year);
        const response = await fetch(`${API_BASE}/v1/lobbying/network-graph?year=${year}`, {
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`Failed to fetch network data: ${response.statusText}`);
        }

        networkData = await response.json();
        // API returns {success:true, data: {graph: {nodes, links}, metadata: {...}}}
        const apiData = networkData.data || networkData;
        const graphData = apiData.graph || apiData;

        // Normalize to {nodes, links} at top level for the rest of the code
        networkData = {
            nodes: graphData.nodes || [],
            links: graphData.links || []
        };

        console.log('Network data loaded:', networkData.nodes.length, 'nodes,', networkData.links.length, 'links');

        // Update stats
        updateTotalStats(networkData);

        // Initial render
        applyFilters();

        document.getElementById('loading').style.display = 'none';

    } catch (error) {
        console.error('Error loading network:', error);
        document.getElementById('loading').innerHTML = `
            <p style="color: #ff5252;">Error loading network data</p>
            <p style="font-size: 0.85rem; margin-top: 0.5rem;">${error.message}</p>
        `;
    }
}

function updateTotalStats(data) {
    const members = data.nodes?.filter(n => n.type === 'member').length || 0;
    const bills = data.nodes?.filter(n => n.type === 'bill').length || 0;
    const clients = data.nodes?.filter(n => n.type === 'client').length || 0;
    const lobbyists = data.nodes?.filter(n => n.type === 'lobbyist').length || 0;

    document.getElementById('members-count').textContent = members;
    document.getElementById('bills-count').textContent = bills;
    document.getElementById('clients-count').textContent = clients;
    document.getElementById('lobbyists-count').textContent = lobbyists;

    document.getElementById('stat-total-nodes').textContent =
        (data.nodes?.length || 0).toLocaleString();
}

function applyFilters() {
    if (!networkData) return;

    const data = networkData.data || networkData;

    // Get filter values
    const showMembers = document.getElementById('show-members').checked;
    const showBills = document.getElementById('show-bills').checked;
    const showClients = document.getElementById('show-clients').checked;
    const showLobbyists = document.getElementById('show-lobbyists').checked;
    const minStrength = parseInt(document.getElementById('strength-slider').value);
    const searchQuery = document.getElementById('search-input').value.toLowerCase();

    // Filter nodes by type
    let nodes = (data.nodes || []).filter(n => {
        if (n.type === 'member' && !showMembers) return false;
        if (n.type === 'bill' && !showBills) return false;
        if (n.type === 'client' && !showClients) return false;
        if (n.type === 'lobbyist' && !showLobbyists) return false;

        // Search filter
        if (searchQuery) {
            const name = (n.name || n.id || '').toLowerCase();
            if (!name.includes(searchQuery)) return false;
        }

        return true;
    });

    const nodeIds = new Set(nodes.map(n => n.id));

    // Filter links
    let links = (data.links || []).filter(l => {
        const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
        const targetId = typeof l.target === 'object' ? l.target.id : l.target;

        // Only include links where both nodes are visible
        if (!nodeIds.has(sourceId) || !nodeIds.has(targetId)) return false;

        // Strength filter
        const strength = l.strength || l.weight || 0;
        if (strength < minStrength) return false;

        return true;
    });

    // Remove orphan nodes (nodes with no connections)
    const connectedNodeIds = new Set();
    links.forEach(l => {
        const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
        const targetId = typeof l.target === 'object' ? l.target.id : l.target;
        connectedNodeIds.add(sourceId);
        connectedNodeIds.add(targetId);
    });

    nodes = nodes.filter(n => connectedNodeIds.has(n.id));

    filteredData = { nodes, links };

    // Update stats
    document.getElementById('stat-visible-nodes').textContent = nodes.length;
    document.getElementById('stat-visible-links').textContent = links.length;

    renderGraph(filteredData);
}

function renderGraph(data) {
    // Clear existing graph
    g.selectAll('*').remove();

    if (data.nodes.length === 0) {
        showEmptyState();
        return;
    }

    // Clone data to avoid mutation
    const nodes = data.nodes.map(n => ({ ...n }));
    const links = data.links.map(l => ({ ...l }));

    // Get layout parameters
    const chargeStrength = parseInt(document.getElementById('charge-slider').value);
    const linkDistance = parseInt(document.getElementById('distance-slider').value);

    // Create force simulation
    const container = document.getElementById('graph-container');
    const width = container.clientWidth;
    const height = container.clientHeight;

    simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links)
            .id(d => d.id)
            .distance(linkDistance)
            .strength(l => (l.strength || 50) / 100))
        .force('charge', d3.forceManyBody()
            .strength(chargeStrength))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collide', d3.forceCollide()
            .radius(d => getNodeSize(d) + 5)
            .strength(0.7))
        .force('x', d3.forceX(width / 2).strength(0.05))
        .force('y', d3.forceY(height / 2).strength(0.05));

    // Draw links
    const link = g.append('g')
        .attr('class', 'links')
        .selectAll('line')
        .data(links)
        .join('line')
        .attr('class', 'link')
        .attr('stroke', d => getLinkColor(d))
        .attr('stroke-width', d => getLinkWidth(d))
        .attr('stroke-dasharray', d => d.link_type === 'lobbied' ? '5,5' : 'none');

    // Draw nodes
    const node = g.append('g')
        .attr('class', 'nodes')
        .selectAll('g')
        .data(nodes)
        .join('g')
        .attr('class', 'node')
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended))
        .on('click', (event, d) => {
            event.stopPropagation();
            selectNode(d);
        })
        .on('mouseover', (event, d) => {
            highlightConnections(d, true);
            showTooltip(event, d);
        })
        .on('mouseout', (event, d) => {
            highlightConnections(d, false);
            hideTooltip();
        });

    // Draw shapes based on node type
    node.each(function (d) {
        const nodeGroup = d3.select(this);

        if (d.type === 'client') {
            // Square for clients
            nodeGroup.append('rect')
                .attr('width', getNodeSize(d) * 2)
                .attr('height', getNodeSize(d) * 2)
                .attr('x', -getNodeSize(d))
                .attr('y', -getNodeSize(d))
                .attr('fill', COLORS.client)
                .attr('stroke', '#fff')
                .attr('stroke-width', 1.5);
        } else if (d.type === 'lobbyist') {
            // Diamond for lobbyists
            const size = getNodeSize(d);
            nodeGroup.append('path')
                .attr('d', `M 0,${-size} L ${size},0 L 0,${size} L ${-size},0 Z`)
                .attr('fill', COLORS.lobbyist)
                .attr('stroke', '#fff')
                .attr('stroke-width', 1.5);
        } else {
            // Circle for members and bills
            nodeGroup.append('circle')
                .attr('r', getNodeSize(d))
                .attr('fill', getNodeColor(d))
                .attr('stroke', '#fff')
                .attr('stroke-width', 1.5);
        }
    });

    // Add labels
    node.append('text')
        .attr('dy', d => getNodeSize(d) + 12)
        .text(d => getNodeLabel(d))
        .style('opacity', labelsVisible ? 1 : 0);

    // Update positions on tick
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

        node.attr('transform', d => `translate(${d.x},${d.y})`);
    });
}

// View mode determines how nodes are sized
function getNodeSize(d) {
    const viewMode = document.getElementById('view-mode')?.value || 'spend';

    const baseSize = {
        member: 6,
        bill: 7,
        client: 8,
        lobbyist: 7
    }[d.type] || 6;

    let scale = 0;

    switch (viewMode) {
        case 'spend':
            // Size by dollar flow
            scale = Math.sqrt((d.spend || 0) / 10000);
            break;
        case 'connections':
            // Size by number of connections
            scale = (d.connections || 1) * 1.5;
            break;
        case 'bills':
            // Size by bill impact (clients/lobbyists with bill refs larger)
            if (d.type === 'bill') {
                scale = 5 + (d.connections || 1) * 2;
            } else {
                scale = (d.bill_count || d.connections || 1);
            }
            break;
        case 'uniform':
            // All same size
            return baseSize;
    }

    return Math.max(baseSize, Math.min(baseSize + scale, 25));
}

// Sector color mapping
const SECTOR_COLORS = {
    'Defense': '#ef4444',      // Red
    'Healthcare': '#10b981',   // Green
    'Finance': '#3b82f6',      // Blue
    'Energy': '#f59e0b',       // Orange
    'Technology': '#8b5cf6',   // Purple
    'Industrial': '#6b7280',   // Gray
    'Consumer': '#ec4899',     // Pink
    'Government': '#14b8a6',   // Teal
    'Other': '#9ca3af'         // Light gray
};

function getNodeColor(d) {
    const colorMode = document.getElementById('color-mode')?.value || 'type';

    switch (colorMode) {
        case 'type':
            // Color by node type (default)
            if (d.type === 'member') {
                if (d.party === 'Democrat') return '#3b82f6';
                if (d.party === 'Republican') return '#ef4444';
                return '#8b5cf6';
            }
            return COLORS[d.type] || '#9ca3af';

        case 'sector':
            // Color by industry sector
            return SECTOR_COLORS[d.sector] || SECTOR_COLORS['Other'];

        case 'spend':
            // Color by spending level (heat map)
            const spend = d.spend || 0;
            if (spend > 100000) return '#ef4444';  // Red - high spend
            if (spend > 50000) return '#f59e0b';   // Orange
            if (spend > 10000) return '#fbbf24';   // Yellow
            if (spend > 1000) return '#84cc16';    // Light green
            return '#10b981';                       // Green - low spend
    }

    return COLORS[d.type] || '#9ca3af';
}

function getNodeLabel(d) {
    if (d.type === 'member') {
        return d.last_name || d.name || d.id;
    }
    if (d.type === 'bill') {
        return d.bill_id || d.id;
    }
    if (d.type === 'client' || d.type === 'lobbyist') {
        const name = d.name || d.id;
        return name.length > 20 ? name.substring(0, 20) + '...' : name;
    }
    return d.id;
}

function getLinkColor(d) {
    return COLORS.link[d.link_type] || COLORS.link.default;
}

function getLinkWidth(d) {
    const strength = d.strength || d.weight || 10;
    return Math.max(1, Math.min(strength / 20, 5));
}

function highlightConnections(d, highlight) {
    const connectedIds = new Set([d.id]);

    // Find all connected nodes
    g.selectAll('.link')
        .each(function (l) {
            const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
            const targetId = typeof l.target === 'object' ? l.target.id : l.target;

            if (sourceId === d.id) connectedIds.add(targetId);
            if (targetId === d.id) connectedIds.add(sourceId);
        })
        .classed('highlighted', function (l) {
            if (!highlight) return false;
            const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
            const targetId = typeof l.target === 'object' ? l.target.id : l.target;
            return sourceId === d.id || targetId === d.id;
        })
        .style('stroke-opacity', function (l) {
            if (!highlight) return 0.25;
            const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
            const targetId = typeof l.target === 'object' ? l.target.id : l.target;
            return (sourceId === d.id || targetId === d.id) ? 0.9 : 0.05;
        });

    // Highlight connected nodes
    g.selectAll('.node')
        .style('opacity', function (n) {
            if (!highlight) return 1;
            return connectedIds.has(n.id) ? 1 : 0.2;
        });
}

function selectNode(d) {
    selectedNode = d;

    // Show details panel
    document.getElementById('details-placeholder').style.display = 'none';
    const detailsContainer = document.getElementById('node-details');
    detailsContainer.style.display = 'block';

    renderNodeDetails(d, detailsContainer);

    // Highlight selected node
    g.selectAll('.node')
        .select('circle, rect, path')
        .attr('stroke', n => n.id === d.id ? '#000' : '#fff')
        .attr('stroke-width', n => n.id === d.id ? 3 : 1.5);
}

function deselectNode() {
    selectedNode = null;

    // Hide details panel
    document.getElementById('details-placeholder').style.display = 'flex';
    document.getElementById('node-details').style.display = 'none';

    // Reset node highlights
    g.selectAll('.node')
        .select('circle, rect, path')
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5);
}

function renderNodeDetails(d, container) {
    const typeIcons = {
        member: '🏛️',
        bill: '📜',
        client: '🏢',
        lobbyist: '👔'
    };

    let detailsHTML = `
        <div class="node-details">
            <div class="detail-header">
                <div class="detail-icon">${typeIcons[d.type] || '📍'}</div>
                <div class="detail-title">${d.name || d.id}</div>
                <div class="detail-subtitle">${d.type.charAt(0).toUpperCase() + d.type.slice(1)}</div>
            </div>
    `;

    // Type-specific details
    if (d.type === 'member') {
        detailsHTML += renderMemberDetails(d);
    } else if (d.type === 'bill') {
        detailsHTML += renderBillDetails(d);
    } else if (d.type === 'client') {
        detailsHTML += renderClientDetails(d);
    } else if (d.type === 'lobbyist') {
        detailsHTML += renderLobbyistDetails(d);
    }

    // Connections
    detailsHTML += renderConnections(d);

    detailsHTML += '</div>';

    container.innerHTML = detailsHTML;
}

function renderMemberDetails(d) {
    return `
        <div class="detail-stats">
            <div class="detail-stat">
                <div class="value">${d.party || 'N/A'}</div>
                <div class="label">Party</div>
            </div>
            <div class="detail-stat">
                <div class="value">${d.state || 'N/A'}</div>
                <div class="label">State</div>
            </div>
            <div class="detail-stat">
                <div class="value">${d.bills_sponsored || 0}</div>
                <div class="label">Bills Sponsored</div>
            </div>
            <div class="detail-stat">
                <div class="value">${d.connections || 0}</div>
                <div class="label">Connections</div>
            </div>
        </div>
    `;
}

function renderBillDetails(d) {
    return `
        <div class="detail-stats">
            <div class="detail-stat">
                <div class="value">${d.bill_id || 'N/A'}</div>
                <div class="label">Bill ID</div>
            </div>
            <div class="detail-stat">
                <div class="value">${d.sponsor_name || 'N/A'}</div>
                <div class="label">Sponsor</div>
            </div>
            <div class="detail-stat" style="grid-column: span 2;">
                <div class="value">${formatCurrency(d.lobbying_spend || 0)}</div>
                <div class="label">Lobbying Spend</div>
            </div>
        </div>
        ${d.title ? `<p style="font-size: 0.85rem; line-height: 1.5; color: #666; margin-bottom: 1rem;">${d.title}</p>` : ''}
    `;
}

function renderClientDetails(d) {
    const spendAmount = d.spend || d.total_spend || 0;
    const firmsHired = d.registrants_hired || d.connections || 0;

    // Build intelligent summary
    let summary = '';
    if (spendAmount > 100000) {
        summary = `<p style="font-size: 0.85rem; color: #666; margin-top: 0.5rem;">🔥 High-spend lobbying client with significant influence activity.</p>`;
    } else if (spendAmount > 50000) {
        summary = `<p style="font-size: 0.85rem; color: #666; margin-top: 0.5rem;">📊 Active lobbying client engaging multiple firms.</p>`;
    }

    return `
        <div class="detail-stats">
            <div class="detail-stat" style="grid-column: span 2;">
                <div class="value">${formatCurrency(spendAmount)}</div>
                <div class="label">Total Lobbying Spend</div>
            </div>
            <div class="detail-stat">
                <div class="value">${firmsHired}</div>
                <div class="label">Firms Hired</div>
            </div>
            <div class="detail-stat">
                <div class="value">${d.connections || 0}</div>
                <div class="label">Connections</div>
            </div>
        </div>
        ${summary}
    `;
}

function renderLobbyistDetails(d) {
    const spendAmount = d.spend || d.total_revenue || 0;
    const clientCount = d.connections || d.client_count || 0;

    // Build intelligent summary
    let summary = '';
    if (spendAmount > 200000) {
        summary = `<p style="font-size: 0.85rem; color: #666; margin-top: 0.5rem;">🏆 Major lobbying firm with substantial client portfolio.</p>`;
    } else if (clientCount > 5) {
        summary = `<p style="font-size: 0.85rem; color: #666; margin-top: 0.5rem;">📈 Active firm representing multiple clients.</p>`;
    }

    return `
        <div class="detail-stats">
            <div class="detail-stat" style="grid-column: span 2;">
                <div class="value">${formatCurrency(spendAmount)}</div>
                <div class="label">Total Revenue</div>
            </div>
            <div class="detail-stat">
                <div class="value">${clientCount}</div>
                <div class="label">Clients</div>
            </div>
            <div class="detail-stat">
                <div class="value">${d.bill_count || d.connections || 0}</div>
                <div class="label">Bills Lobbied</div>
            </div>
        </div>
        ${summary}
    `;
}

function renderConnections(d) {
    // Find connected nodes
    const connections = [];
    g.selectAll('.link')
        .each(function (l) {
            const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
            const targetId = typeof l.target === 'object' ? l.target.id : l.target;

            if (sourceId === d.id) {
                connections.push({
                    node: l.target,
                    type: l.link_type,
                    strength: l.strength || l.weight || 0
                });
            } else if (targetId === d.id) {
                connections.push({
                    node: l.source,
                    type: l.link_type,
                    strength: l.strength || l.weight || 0
                });
            }
        });

    // Sort by strength
    connections.sort((a, b) => b.strength - a.strength);

    // Take top 10
    const topConnections = connections.slice(0, 10);

    if (topConnections.length === 0) {
        return '<p style="text-align: center; color: #999; padding: 2rem;">No connections</p>';
    }

    let html = '<div class="connections-list"><h5>Top Connections</h5>';

    topConnections.forEach(conn => {
        const node = conn.node;
        const name = node.name || node.id;
        const displayName = name.length > 30 ? name.substring(0, 30) + '...' : name;

        html += `
            <div class="connection-item">
                <span class="name">${displayName}</span>
                <span class="value">${conn.strength}</span>
            </div>
        `;
    });

    html += '</div>';

    return html;
}

function showTooltip(event, d) {
    const tooltip = document.getElementById('tooltip');
    const name = d.name || d.id;

    let content = `<strong>${name}</strong><br>`;
    content += `Type: ${d.type}<br>`;

    if (d.connections) {
        content += `Connections: ${d.connections}<br>`;
    }

    if (d.spend || d.total_spend) {
        content += `Spend: ${formatCurrency(d.spend || d.total_spend || 0)}`;
    }

    tooltip.innerHTML = content;
    tooltip.style.display = 'block';
    tooltip.style.left = (event.pageX + 10) + 'px';
    tooltip.style.top = (event.pageY - 10) + 'px';
}

function hideTooltip() {
    document.getElementById('tooltip').style.display = 'none';
}

function showEmptyState() {
    g.append('text')
        .attr('x', '50%')
        .attr('y', '50%')
        .attr('text-anchor', 'middle')
        .attr('fill', 'rgba(255, 255, 255, 0.5)')
        .attr('font-size', '1.2rem')
        .text('No nodes match the current filters');
}

function formatCurrency(amount) {
    if (!amount) return '$0';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
        notation: 'compact'
    }).format(amount);
}

// Drag functions
function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
}

function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
}

function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
}

// Event listeners
function setupEventListeners() {
    // Node type checkboxes
    ['show-members', 'show-bills', 'show-clients', 'show-lobbyists'].forEach(id => {
        document.getElementById(id)?.addEventListener('change', applyFilters);
    });

    // Filters
    document.getElementById('filter-year')?.addEventListener('change', () => {
        document.getElementById('loading').style.display = 'flex';
        fetchNetworkData();
    });

    const strengthSlider = document.getElementById('strength-slider');
    const strengthValue = document.getElementById('strength-value');
    strengthSlider?.addEventListener('input', (e) => {
        strengthValue.textContent = e.target.value;
        debounce(applyFilters, 300)();
    });

    document.getElementById('search-input')?.addEventListener('input',
        debounce(applyFilters, 300));

    // Layout sliders
    document.getElementById('charge-slider')?.addEventListener('input',
        debounce(applyFilters, 300));
    document.getElementById('distance-slider')?.addEventListener('input',
        debounce(applyFilters, 300));

    // Action buttons
    document.getElementById('reset-btn')?.addEventListener('click', resetView);
    document.getElementById('labels-btn')?.addEventListener('click', toggleLabels);
    document.getElementById('export-btn')?.addEventListener('click', exportToPNG);
}

function resetView() {
    // Reset filters
    document.getElementById('show-members').checked = true;
    document.getElementById('show-bills').checked = true;
    document.getElementById('show-clients').checked = true;
    document.getElementById('show-lobbyists').checked = true;
    document.getElementById('strength-slider').value = 30;
    document.getElementById('strength-value').textContent = '30';
    document.getElementById('search-input').value = '';
    document.getElementById('charge-slider').value = -200;
    document.getElementById('distance-slider').value = 80;

    // Reset zoom
    svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity);

    // Deselect node
    deselectNode();

    // Re-render
    applyFilters();
}

function toggleLabels() {
    labelsVisible = !labelsVisible;
    g.selectAll('.node text')
        .transition()
        .duration(200)
        .style('opacity', labelsVisible ? 1 : 0);
}

function exportToPNG() {
    // Get SVG element
    const svgElement = document.getElementById('graph-svg');
    const svgData = new XMLSerializer().serializeToString(svgElement);

    // Create canvas
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();

    canvas.width = svgElement.clientWidth;
    canvas.height = svgElement.clientHeight;

    img.onload = function () {
        ctx.fillStyle = '#0f1419';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0);

        // Download
        const link = document.createElement('a');
        link.download = `lobbying-network-${new Date().toISOString().split('T')[0]}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
    };

    img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
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
