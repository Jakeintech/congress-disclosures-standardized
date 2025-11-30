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
                <div class="graph-container" style="height: 600px; border: 1px solid var(--border-color); border-radius: 8px; position: relative; overflow: hidden;">
                    <div id="network-graph" style="width: 100%; height: 100%;"></div>
                    <div class="graph-legend" style="position: absolute; top: 10px; right: 10px; background: rgba(255,255,255,0.9); padding: 10px; border-radius: 4px; border: 1px solid var(--border-color); font-size: 0.8rem;">
                        <div class="flex items-center gap-2 mb-1"><div class="w-3 h-3 rounded-full bg-blue-500"></div> Member</div>
                        <div class="flex items-center gap-2"><div class="w-3 h-3 rounded-full bg-green-500"></div> Asset</div>
                    </div>
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
        .call(d3.zoom().on("zoom", (event) => {
            g.attr("transform", event.transform);
        }))
        .append("g");

    const g = svg.append("g");

    const simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(d => d.id).distance(100))
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collide", d3.forceCollide().radius(d => d.radius + 5));

    const link = g.append("g")
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.6)
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke-width", d => Math.sqrt(d.value / 100000)); // Scale width by volume

    const node = g.append("g")
        .attr("stroke", "#fff")
        .attr("stroke-width", 1.5)
        .selectAll("circle")
        .data(nodes)
        .join("circle")
        .attr("r", d => d.radius)
        .attr("fill", d => d.group === 'member' ? '#3b82f6' : '#10b981')
        .call(drag(simulation));

    node.append("title")
        .text(d => d.id);

    const label = g.append("g")
        .selectAll("text")
        .data(nodes)
        .join("text")
        .attr("dx", 12)
        .attr("dy", ".35em")
        .text(d => d.id)
        .style("font-size", "10px")
        .style("pointer-events", "none")
        .style("fill", "var(--text-primary)");

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
    const headers = ['Source', 'Target', 'Type', 'Value'];
    const rows = window.networkData.links.map(l => [
        l.source.id || l.source,
        l.target.id || l.target,
        l.type,
        l.value
    ]);

    const csv = [headers.join(','), ...rows.map(row => row.map(cell => `"${cell}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'network_graph_edges.csv';
    a.click();
}
