/**
 * Network Graph Logic (network.html)
 * Handles the D3 Social Network Graph.
 */

document.addEventListener('DOMContentLoaded', () => {
    loadNetworkGraph();
});

async function loadNetworkGraph() {
    try {
        const response = await fetch('https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/website/data/network_graph.json');
        if (response.ok) {
            const data = await response.json();
            initNetworkGraph(data);
        }
    } catch (err) {
        console.log('Network graph not yet available');
    }
}

function initNetworkGraph(data) {
    const container = document.getElementById('network-graph-container');
    if (!container) return;

    const nodes = data.nodes || [];
    const links = data.links || [];

    container.innerHTML = `
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">🕸️ Social Network Analysis</h2>
                <p class="card-description">Connections between Members and Assets based on trading activity</p>
            </div>
            <div class="card-content">
                <div class="graph-container" style="height: 700px; border: 1px solid var(--border-color); border-radius: 8px; position: relative; overflow: hidden; background: #f8f9fa;">
                    <div id="network-graph" style="width: 100%; height: 100%;"></div>
                    
                    <!-- Legends -->
                    <div class="graph-legend" style="position: absolute; top: 10px; right: 10px; background: rgba(255,255,255,0.95); padding: 12px; border-radius: 8px; border: 1px solid var(--border-color); font-size: 0.8rem; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                        <div class="font-bold mb-2">Nodes</div>
                        <div class="flex items-center gap-2 mb-1"><div class="w-3 h-3 rounded-full" style="background: #ef4444;"></div> Republican</div>
                        <div class="flex items-center gap-2 mb-1"><div class="w-3 h-3 rounded-full" style="background: #3b82f6;"></div> Democrat</div>
                        <div class="flex items-center gap-2 mb-1"><div class="w-3 h-3 rounded-full" style="background: #9ca3af;"></div> Other/Unknown</div>
                        <div class="flex items-center gap-2 mb-3"><div class="w-3 h-3 rounded-full" style="background: #10b981;"></div> Asset</div>
                        
                        <div class="font-bold mb-2">Transactions</div>
                        <div class="flex items-center gap-2 mb-1"><div class="w-3 h-1" style="background: #22c55e;"></div> Buy</div>
                        <div class="flex items-center gap-2"><div class="w-3 h-1" style="background: #ef4444;"></div> Sell</div>
                    </div>

                    <!-- Tooltip -->
                    <div id="graph-tooltip" style="position: absolute; display: none; background: rgba(0,0,0,0.8); color: white; padding: 8px 12px; border-radius: 4px; font-size: 0.8rem; pointer-events: none; z-index: 10;"></div>
                </div>

                <div class="table-actions mt-4">
                    <button class="btn btn-secondary" onclick="exportNetworkCSV()">Export CSV</button>
                </div>
            </div>
        </div>
    `;

    window.networkData = { nodes, links };
    renderD3Graph(nodes, links, '#network-graph');
}

function renderD3Graph(nodes, links, selector) {
    const element = document.querySelector(selector);
    const width = element.clientWidth;
    const height = element.clientHeight;

    // Clear previous
    d3.select(selector).selectAll("*").remove();

    const svg = d3.select(selector)
        .append("svg")
        .attr("width", width)
        .attr("height", height)
        .call(d3.zoom().scaleExtent([0.1, 8]).on("zoom", (event) => {
            g.attr("transform", event.transform);
        }))
        .append("g");

    const g = svg.append("g");

    // Simulation setup
    const simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(d => d.id).distance(100))
        .force("charge", d3.forceManyBody().strength(-200))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collide", d3.forceCollide().radius(d => d.radius + 2).iterations(2));

    // Links
    const link = g.append("g")
        .attr("stroke-opacity", 0.6)
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke-width", d => Math.max(1, Math.sqrt(d.value / 50000))) // Scale width
        .attr("stroke", d => {
            const type = (d.type || '').toLowerCase();
            if (type.includes('purchase') || type.includes('buy')) return '#22c55e'; // Green
            if (type.includes('sale') || type.includes('sell')) return '#ef4444'; // Red
            return '#9ca3af'; // Gray
        });

    // Nodes
    const node = g.append("g")
        .attr("stroke", "#fff")
        .attr("stroke-width", 1.5)
        .selectAll("circle")
        .data(nodes)
        .join("circle")
        .attr("r", d => d.radius)
        .attr("fill", d => {
            if (d.group === 'asset') return '#10b981'; // Green for Assets
            // Party colors for Members
            if (d.party === 'Republican') return '#ef4444';
            if (d.party === 'Democrat') return '#3b82f6';
            return '#9ca3af'; // Gray
        })
        .call(drag(simulation));

    // Labels (only for larger nodes to reduce clutter)
    const label = g.append("g")
        .selectAll("text")
        .data(nodes)
        .join("text")
        .attr("dx", 12)
        .attr("dy", ".35em")
        .text(d => d.radius > 5 ? d.id : '')
        .style("font-size", "10px")
        .style("pointer-events", "none")
        .style("fill", "#374151")
        .style("text-shadow", "1px 1px 0 #fff, -1px -1px 0 #fff, 1px -1px 0 #fff, -1px 1px 0 #fff");

    // Tooltip Logic
    const tooltip = d3.select("#graph-tooltip");

    node.on("mouseover", (event, d) => {
        // Highlight logic
        node.style("opacity", 0.1);
        link.style("opacity", 0.05);
        label.style("opacity", 0.1);

        // Select neighbors
        const connectedNodeIds = new Set();
        connectedNodeIds.add(d.id);

        link.filter(l => l.source.id === d.id || l.target.id === d.id)
            .style("opacity", 1)
            .each(l => {
                connectedNodeIds.add(l.source.id);
                connectedNodeIds.add(l.target.id);
            });

        node.filter(n => connectedNodeIds.has(n.id))
            .style("opacity", 1);

        label.filter(n => connectedNodeIds.has(n.id))
            .style("opacity", 1)
            .text(n => n.id); // Show label on hover even if small

        // Tooltip content
        const formatMoney = (val) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: "compact" }).format(val);

        let content = `<strong>${d.id}</strong><br>`;
        if (d.group === 'member') {
            content += `Party: ${d.party || 'Unknown'}<br>`;
        }
        content += `Volume: ${formatMoney(d.value)}`;

        tooltip.style("display", "block")
            .html(content)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 10) + "px");
    })
        .on("mouseout", () => {
            // Reset styles
            node.style("opacity", 1);
            link.style("opacity", 0.6);
            label.style("opacity", 1)
                .text(d => d.radius > 5 ? d.id : ''); // Reset labels

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

function exportNetworkCSV() {
    if (!window.networkData) return;
    const headers = ['Source', 'Target', 'Type', 'Value', 'Count'];
    const rows = window.networkData.links.map(l => [
        l.source.id || l.source,
        l.target.id || l.target,
        l.type,
        l.value,
        l.count || 1
    ]);

    const csv = [headers.join(','), ...rows.map(row => row.map(cell => `"${cell}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'network_graph_edges.csv';
    a.click();
}
