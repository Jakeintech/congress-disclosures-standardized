/**
 * Gold Analytics - Complete Implementation
 * All gold layer analytics views with real data
 */

// Member Trading Stats
async function initMemberTradingStats(data) {
    console.log('Initializing Member Trading Stats...');

    const view = document.querySelector('[data-gold-view="member-stats"]');
    if (!view) return;

    const html = `
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">📊 Member Trading Statistics</h2>
                <p class="card-description">Comprehensive trading analytics by member</p>
            </div>
            <div class="card-content">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">${data.total_members || 0}</div>
                        <div class="stat-label">Active Traders</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${data.total_trades || 0}</div>
                        <div class="stat-label">Total Trades</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">$${(data.total_volume / 1000000).toFixed(1)}M</div>
                        <div class="stat-label">Total Volume</div>
                    </div>
                </div>

                <div class="table-container" style="margin-top: 2rem;">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Member</th>
                                <th>Party</th>
                                <th>Trades</th>
                                <th>Buys</th>
                                <th>Sells</th>
                                <th>Volume</th>
                                <th>Avg Size</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${(data.members || []).slice(0, 50).map(m => `
                                <tr>
                                    <td>${m.full_name || 'Unknown'}</td>
                                    <td><span class="badge badge-${m.party === 'R' ? 'error' : m.party === 'D' ? 'info' : 'secondary'}">${m.party || '-'}</span></td>
                                    <td>${m.total_trades || 0}</td>
                                    <td>${m.buy_count || 0}</td>
                                    <td>${m.sell_count || 0}</td>
                                    <td>$${((m.total_volume || 0) / 1000).toFixed(0)}K</td>
                                    <td>$${((m.avg_transaction_size || 0) / 1000).toFixed(0)}K</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    view.innerHTML = html;
    console.log(`✅ Member Trading Stats loaded (${data.total_members} members)`);
}

// Trending Stocks
async function initTrendingStocks(data) {
    console.log('Initializing Trending Stocks...');

    const view = document.querySelector('[data-gold-view="trending"]');
    if (!view) return;

    const html = `
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">📈 Trending Stocks</h2>
                <p class="card-description">Most traded stocks by Congress members</p>
            </div>
            <div class="card-content">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">${data.total_stocks || 0}</div>
                        <div class="stat-label">Trending Stocks</div>
                    </div>
                </div>

                <div class="table-container" style="margin-top: 2rem;">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>Ticker</th>
                                <th>Company</th>
                                <th>Trades</th>
                                <th>Buys</th>
                                <th>Sells</th>
                                <th>Sentiment</th>
                                <th>Volume</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${(data.stocks || []).map(s => `
                                <tr>
                                    <td>${s.rank}</td>
                                    <td><strong>${s.ticker}</strong></td>
                                    <td>${s.name}</td>
                                    <td>${s.trade_count}</td>
                                    <td class="text-success">${s.buy_count}</td>
                                    <td class="text-error">${s.sell_count}</td>
                                    <td>
                                        <span class="badge badge-${s.net_sentiment === 'Bullish' ? 'success' : 'error'}">
                                            ${s.net_sentiment}
                                        </span>
                                    </td>
                                    <td>$${((s.total_volume_usd || 0) / 1000000).toFixed(1)}M</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    view.innerHTML = html;
    console.log(`✅ Trending Stocks loaded (${data.total_stocks} stocks)`);
}

// Sector Analysis
async function initSectorAnalysis(data) {
    console.log('Initializing Sector Analysis...');

    const view = document.querySelector('[data-gold-view="sector"]');
    if (!view) return;

    const html = `
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">🏭 Sector Analysis</h2>
                <p class="card-description">Congressional trading by industry sector</p>
            </div>
            <div class="card-content">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">${data.total_sectors || 0}</div>
                        <div class="stat-label">Sectors Tracked</div>
                    </div>
                </div>

                <div class="table-container" style="margin-top: 2rem;">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Sector</th>
                                <th>Total Trades</th>
                                <th>Buys</th>
                                <th>Sells</th>
                                <th>Net Position</th>
                                <th>Total Volume</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${(data.sectors || []).map(s => {
                                const netPosition = s.buy_count - s.sell_count;
                                return `
                                    <tr>
                                        <td><strong>${s.sector}</strong></td>
                                        <td>${s.trade_count}</td>
                                        <td class="text-success">${s.buy_count}</td>
                                        <td class="text-error">${s.sell_count}</td>
                                        <td>
                                            <span class="badge badge-${netPosition > 0 ? 'success' : netPosition < 0 ? 'error' : 'secondary'}">
                                                ${netPosition > 0 ? '+' : ''}${netPosition}
                                            </span>
                                        </td>
                                        <td>$${((s.total_volume || 0) / 1000000).toFixed(1)}M</td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    view.innerHTML = html;
    console.log(`✅ Sector Analysis loaded (${data.total_sectors} sectors)`);
}

// Export functions
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { initMemberTradingStats, initTrendingStocks, initSectorAnalysis };
}
