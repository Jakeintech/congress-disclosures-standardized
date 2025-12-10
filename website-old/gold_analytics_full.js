/**
 * Gold Analytics - Full Implementation
 * Handles visualization and data display for Member Stats, Trending Stocks, and Sector Analysis
 */

// ============================================================================
// MEMBER TRADING STATS
// ============================================================================

function initMemberTradingStats(data) {
    const container = document.querySelector('[data-gold-view="member-stats"]');
    if (!container) return;

    const members = data.members || [];
    const totalVolume = data.total_volume || 0;

    // Sort by volume desc
    members.sort((a, b) => b.total_volume - a.total_volume);

    container.innerHTML = `
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">👥 Member Trading Activity</h2>
                <p class="card-description">Top active members by trading volume and frequency</p>
            </div>
            <div class="card-content">
                <!-- Volume Chart -->
                <div class="chart-container mb-8">
                    <h3 class="text-sm font-semibold mb-4">Top 10 Members by Volume</h3>
                    <div class="bar-chart">
                        ${renderVolumeChart(members.slice(0, 10), totalVolume)}
                    </div>
                </div>

                <!-- Data Table -->
                <div class="table-actions">
                    <span class="text-muted">Showing ${members.length} members</span>
                    <button class="btn btn-secondary" onclick="exportMemberStatsCSV()">Export CSV</button>
                </div>
                <div class="table-container">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Member</th>
                                <th>Party</th>
                                <th>State</th>
                                <th>Total Trades</th>
                                <th>Buy Volume</th>
                                <th>Sell Volume</th>
                                <th>Total Volume</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${renderMemberTableRows(members)}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    // Store data globally for export
    window.memberStatsData = members;
}

function renderVolumeChart(members, totalVolume) {
    const maxVol = Math.max(...members.map(m => m.total_volume));

    return members.map(m => `
        <div class="chart-row">
            <div class="chart-label">${m.name}</div>
            <div class="chart-bar-container">
                <div class="chart-bar" style="width: ${(m.total_volume / maxVol) * 100}%">
                    <span class="chart-tooltip">$${formatMoney(m.total_volume)}</span>
                </div>
            </div>
            <div class="chart-value">$${formatMoneyCompact(m.total_volume)}</div>
        </div>
    `).join('');
}

function renderMemberTableRows(members) {
    return members.map(m => `
        <tr>
            <td><strong>${m.name}</strong></td>
            <td><span class="badge badge-${m.party === 'D' ? 'primary' : m.party === 'R' ? 'error' : 'secondary'}">${m.party}</span></td>
            <td>${m.state}</td>
            <td>${m.total_trades}</td>
            <td class="text-success">$${formatMoneyCompact(m.buy_volume)}</td>
            <td class="text-error">$${formatMoneyCompact(m.sell_volume)}</td>
            <td><strong>$${formatMoneyCompact(m.total_volume)}</strong></td>
        </tr>
    `).join('');
}

function exportMemberStatsCSV() {
    if (!window.memberStatsData) return;
    const headers = ['Name', 'Party', 'State', 'Total Trades', 'Buy Volume', 'Sell Volume', 'Total Volume'];
    const rows = window.memberStatsData.map(m => [
        m.name, m.party, m.state, m.total_trades, m.buy_volume, m.sell_volume, m.total_volume
    ]);
    downloadCSV(headers, rows, 'member_trading_stats.csv');
}

// ============================================================================
// TRENDING STOCKS
// ============================================================================

function initTrendingStocks(data) {
    const container = document.querySelector('[data-gold-view="trending"]');
    if (!container) return;

    const stocks = data.stocks || [];
    stocks.sort((a, b) => b.trade_count - a.trade_count);

    container.innerHTML = `
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">📈 Trending Stocks</h2>
                <p class="card-description">Most traded assets by Congress members</p>
            </div>
            <div class="card-content">
                <!-- Data Table -->
                <div class="table-actions">
                    <span class="text-muted">Showing ${stocks.length} assets</span>
                    <button class="btn btn-secondary" onclick="exportTrendingStocksCSV()">Export CSV</button>
                </div>
                <div class="table-container">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Ticker</th>
                                <th>Company/Asset</th>
                                <th>Trade Count</th>
                                <th>Buy/Sell Ratio</th>
                                <th>Total Volume</th>
                                <th>Sentiment</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${renderStockTableRows(stocks)}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    window.trendingStocksData = stocks;
}

function renderStockTableRows(stocks) {
    return stocks.map(s => {
        const buyRatio = s.buy_count / (s.buy_count + s.sell_count) * 100;
        const sentiment = buyRatio > 60 ? 'Bullish' : buyRatio < 40 ? 'Bearish' : 'Neutral';
        const sentimentClass = buyRatio > 60 ? 'success' : buyRatio < 40 ? 'error' : 'warning';

        return `
        <tr>
            <td><code class="font-bold">${s.ticker}</code></td>
            <td>${s.asset_name}</td>
            <td>${s.trade_count}</td>
            <td>
                <div class="flex items-center gap-2">
                    <div class="progress-bar" style="width: 80px;">
                        <div class="bg-success" style="width: ${buyRatio}%"></div>
                        <div class="bg-error" style="width: ${100 - buyRatio}%"></div>
                    </div>
                </div>
            </td>
            <td>$${formatMoneyCompact(s.total_volume)}</td>
            <td><span class="badge badge-${sentimentClass}">${sentiment}</span></td>
        </tr>
    `}).join('');
}

function exportTrendingStocksCSV() {
    if (!window.trendingStocksData) return;
    const headers = ['Ticker', 'Asset Name', 'Trade Count', 'Buy Count', 'Sell Count', 'Total Volume'];
    const rows = window.trendingStocksData.map(s => [
        s.ticker, s.asset_name, s.trade_count, s.buy_count, s.sell_count, s.total_volume
    ]);
    downloadCSV(headers, rows, 'trending_stocks.csv');
}

// ============================================================================
// SECTOR ANALYSIS
// ============================================================================

function initSectorAnalysis(data) {
    const container = document.querySelector('[data-gold-view="sector"]');
    if (!container) return;

    const sectors = data.sectors || [];
    sectors.sort((a, b) => b.total_volume - a.total_volume);

    container.innerHTML = `
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">🏢 Sector Analysis</h2>
                <p class="card-description">Investment distribution across industries</p>
            </div>
            <div class="card-content">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
                    <!-- Pie Chart Placeholder -->
                    <div class="chart-box p-4 border rounded bg-surface-hover flex flex-col items-center justify-center">
                        <h3 class="text-sm font-semibold mb-4">Volume Distribution</h3>
                        <div class="pie-chart" style="background: conic-gradient(${generatePieGradient(sectors)});"></div>
                        <div class="legend mt-4 grid grid-cols-2 gap-2 text-xs">
                            ${renderPieLegend(sectors)}
                        </div>
                    </div>
                    
                    <!-- Summary Stats -->
                    <div class="stats-box">
                        <h3 class="text-sm font-semibold mb-4">Key Insights</h3>
                        <div class="space-y-4">
                            ${renderSectorInsights(sectors)}
                        </div>
                    </div>
                </div>

                <!-- Data Table -->
                <div class="table-actions">
                    <button class="btn btn-secondary" onclick="exportSectorCSV()">Export CSV</button>
                </div>
                <div class="table-container">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Sector</th>
                                <th>Trade Count</th>
                                <th>Buy Volume</th>
                                <th>Sell Volume</th>
                                <th>Total Volume</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${renderSectorTableRows(sectors)}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    window.sectorData = sectors;
}

function generatePieGradient(sectors) {
    let currentDeg = 0;
    const total = sectors.reduce((sum, s) => sum + s.total_volume, 0);
    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#6366f1'];

    return sectors.map((s, i) => {
        const deg = (s.total_volume / total) * 360;
        const start = currentDeg;
        currentDeg += deg;
        return `${colors[i % colors.length]} ${start}deg ${currentDeg}deg`;
    }).join(', ');
}

function renderPieLegend(sectors) {
    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#6366f1'];
    return sectors.map((s, i) => `
        <div class="flex items-center gap-2">
            <div class="w-3 h-3 rounded-full" style="background: ${colors[i % colors.length]}"></div>
            <span>${s.sector}</span>
        </div>
    `).join('');
}

function renderSectorInsights(sectors) {
    const topSector = sectors[0];
    return `
        <div class="stat-row">
            <span class="text-muted">Top Sector</span>
            <span class="font-bold">${topSector.sector}</span>
        </div>
        <div class="stat-row">
            <span class="text-muted">Volume</span>
            <span class="font-bold">$${formatMoneyCompact(topSector.total_volume)}</span>
        </div>
    `;
}

function renderSectorTableRows(sectors) {
    return sectors.map(s => `
        <tr>
            <td><strong>${s.sector}</strong></td>
            <td>${s.trade_count}</td>
            <td>${s.buy_count}</td>
            <td>${s.sell_count}</td>
            <td>$${formatMoneyCompact(s.total_volume)}</td>
        </tr>
    `).join('');
}

function exportSectorCSV() {
    if (!window.sectorData) return;
    const headers = ['Sector', 'Trade Count', 'Buy Count', 'Sell Count', 'Total Volume'];
    const rows = window.sectorData.map(s => [
        s.sector, s.trade_count, s.buy_count, s.sell_count, s.total_volume
    ]);
    downloadCSV(headers, rows, 'sector_analysis.csv');
}

// ============================================================================
// NETWORK GRAPH
// ============================================================================

function initNetworkGraph(data) {
    const container = document.querySelector('[data-gold-view="network"]');
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

                <!-- Data Table -->
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
    downloadCSV(headers, rows, 'network_graph_edges.csv');
}

// ============================================================================
// UTILITIES
// ============================================================================

function formatMoney(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 0
    }).format(amount);
}

function formatMoneyCompact(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        notation: 'compact',
        maximumFractionDigits: 1
    }).format(amount);
}

function downloadCSV(headers, rows, filename) {
    const csv = [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
}
