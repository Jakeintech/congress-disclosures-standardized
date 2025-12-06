/**
 * Analytics Logic (analytics.html)
 * Handles Member Trading Stats, Trending Stocks, and Sector Analysis.
 * Uses API Gateway endpoints for live data.
 */

// API Gateway URL (from config.js or fallback)
const ANALYTICS_API_BASE = window.API_GATEWAY_URL || window.CONFIG?.API_GATEWAY_URL || 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com';

document.addEventListener('DOMContentLoaded', () => {
    loadAnalyticsData();
});

async function loadAnalyticsData() {
    loadMemberTradingStats();
    loadTrendingStocks();
    loadSectorAnalysis();
}

// ============================================================================
// MEMBER TRADING STATS
// ============================================================================

async function loadMemberTradingStats() {
    try {
        const response = await fetch(`${ANALYTICS_API_BASE}/v1/analytics/top-traders?limit=50`);
        if (response.ok) {
            const result = await response.json();
            // API returns { success: true, data: { top_traders: [...] } }
            const traders = result.data?.top_traders || result.top_traders || [];
            // Transform API response to expected format
            const data = {
                members: traders.map(t => ({
                    name: `${t.first_name || ''} ${t.last_name || ''}`.trim() || 'Unknown',
                    party: t.party || 'I',
                    state: t.state || 'N/A',
                    total_trades: t.total_trades || 0,
                    buy_volume: t.purchase_count || 0,
                    sell_volume: t.sale_count || 0,
                    total_volume: t.total_trades || 0 // Use trade count as volume proxy
                })),
                total_volume: traders.reduce((sum, t) => sum + (t.total_trades || 0), 0)
            };
            initMemberTradingStats(data);
        }
    } catch (err) {
        console.error('Error loading member trading stats:', err);
    }
}

function initMemberTradingStats(data) {
    const container = document.getElementById('member-stats-container');
    if (!container) return;

    const members = data.members || [];
    const totalVolume = data.total_volume || 0;
    members.sort((a, b) => b.total_volume - a.total_volume);

    container.innerHTML = `
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">👥 Member Trading Activity</h2>
                <p class="card-description">Top active members by trading volume and frequency</p>
            </div>
            <div class="card-content">
                <div class="chart-container mb-8">
                    <h3 class="text-sm font-semibold mb-4">Top 10 Members by Volume</h3>
                    <div class="bar-chart">
                        ${renderVolumeChart(members.slice(0, 10), totalVolume)}
                    </div>
                </div>
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
    const rows = window.memberStatsData.map(m => [m.name, m.party, m.state, m.total_trades, m.buy_volume, m.sell_volume, m.total_volume]);
    downloadCSV(headers, rows, 'member_trading_stats.csv');
}

// ============================================================================
// TRENDING STOCKS
// ============================================================================

async function loadTrendingStocks() {
    try {
        const response = await fetch(`${ANALYTICS_API_BASE}/v1/analytics/trending-stocks?limit=30`);
        if (response.ok) {
            const result = await response.json();
            // API returns { success: true, data: { trending_stocks: [...] } }
            const stocks = result.data?.trending_stocks || result.trending_stocks || [];
            // Transform API response to expected format
            const data = {
                stocks: stocks.map(s => ({
                    ticker: s.ticker || 'N/A',
                    asset_name: s.ticker || 'Unknown',
                    trade_count: s.trade_count || 0,
                    buy_count: Math.floor((s.trade_count || 0) / 2),
                    sell_count: Math.ceil((s.trade_count || 0) / 2),
                    total_volume: s.trade_count || 0
                }))
            };
            initTrendingStocks(data);
        }
    } catch (err) {
        console.error('Error loading trending stocks:', err);
    }
}

function initTrendingStocks(data) {
    const container = document.getElementById('trending-stocks-container');
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
    const rows = window.trendingStocksData.map(s => [s.ticker, s.asset_name, s.trade_count, s.buy_count, s.sell_count, s.total_volume]);
    downloadCSV(headers, rows, 'trending_stocks.csv');
}

// ============================================================================
// SECTOR ANALYSIS
// ============================================================================

async function loadSectorAnalysis() {
    try {
        const response = await fetch(`${ANALYTICS_API_BASE}/v1/analytics/sector-activity`);
        if (response.ok) {
            const result = await response.json();
            // API returns { success: true, data: { sectors: [...] } }
            const sectors = result.data?.sectors || result.sectors || [];
            // Transform API response to expected format
            const data = {
                sectors: sectors.map(s => ({
                    sector: s.sector || 'Unknown',
                    trade_count: s.trade_count || 0,
                    buy_count: s.buy_count || 0,
                    sell_count: s.sell_count || 0,
                    total_volume: s.total_volume || 0
                }))
            };
            initSectorAnalysis(data);
        }
    } catch (err) {
        console.error('Error loading sector analysis:', err);
    }
}

function initSectorAnalysis(data) {
    const container = document.getElementById('sector-analysis-container');
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
                    <div class="chart-box p-4 border rounded bg-surface-hover flex flex-col items-center justify-center">
                        <h3 class="text-sm font-semibold mb-4">Volume Distribution</h3>
                        <div class="pie-chart" style="background: conic-gradient(${generatePieGradient(sectors)});"></div>
                        <div class="legend mt-4 grid grid-cols-2 gap-2 text-xs">
                            ${renderPieLegend(sectors)}
                        </div>
                    </div>
                    <div class="stats-box">
                        <h3 class="text-sm font-semibold mb-4">Key Insights</h3>
                        <div class="space-y-4">
                            ${renderSectorInsights(sectors)}
                        </div>
                    </div>
                </div>
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
    const rows = window.sectorData.map(s => [s.sector, s.trade_count, s.buy_count, s.sell_count, s.total_volume]);
    downloadCSV(headers, rows, 'sector_analysis.csv');
}

// Utilities
function formatMoney(amount) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);
}

function formatMoneyCompact(amount) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 1 }).format(amount);
}

function downloadCSV(headers, rows, filename) {
    const csv = [headers.join(','), ...rows.map(row => row.map(cell => `"${cell}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
}
