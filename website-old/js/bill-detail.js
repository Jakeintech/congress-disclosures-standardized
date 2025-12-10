// Bill Detail Page JavaScript
const API_BASE = window.CONFIG?.API_BASE || 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com';

// State
let billData = null;
let allActions = [];
let fullHistoryLoaded = false;

// Parse URL parameter
function getBillIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get('id');
}

// Validate bill ID format
function validateBillId(billId) {
    if (!billId) return false;
    const regex = /^\d{3}-(hr|s|hjres|sjres|hconres|sconres|hres|sres)-\d+$/i;
    return regex.test(billId);
}

// Format date
function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch (e) {
        return dateStr;
    }
}

// Truncate text
function truncate(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

// Show error
function showError(message) {
    document.getElementById('loading-state').style.display = 'none';
    document.getElementById('error-state').style.display = 'block';
    document.getElementById('error-message').textContent = message;
}

// Show loading
function showLoading() {
    document.getElementById('loading-state').style.display = 'block';
    document.getElementById('error-state').style.display = 'none';
    document.getElementById('main-content').style.display = 'none';
}

// Show main content
function showContent() {
    document.getElementById('loading-state').style.display = 'none';
    document.getElementById('error-state').style.display = 'none';
    document.getElementById('main-content').style.display = 'block';
}

// Fetch bill data
async function fetchBillData(billId) {
    try {
        const response = await fetch(`${API_BASE}/v1/congress/bills/${billId}`);

        if (!response.ok) {
            if (response.status === 404) {
                throw new Error('Bill not found. Please check the bill ID and try again.');
            }
            throw new Error(`Failed to load bill: ${response.statusText}`);
        }

        const data = await response.json();
        return data.data || data;
    } catch (error) {
        throw error;
    }
}

// Render bill header
function renderHeader(bill) {
    document.getElementById('bill-id').textContent = `${bill.congress}-${bill.bill_type}-${bill.bill_number}`.toUpperCase();
    document.getElementById('breadcrumb-bill-id').textContent = `${bill.bill_type?.toUpperCase()} ${bill.bill_number}`;
    document.getElementById('bill-title').textContent = bill.title || 'No title available';

    // Status badge
    const statusBadge = document.getElementById('status-badge');
    const latestAction = bill.latest_action_text || '';
    let statusClass = 'status-active';
    let statusText = 'Active';

    if (latestAction.toLowerCase().includes('passed')) {
        statusClass = 'status-passed';
        statusText = 'Passed';
    } else if (latestAction.toLowerCase().includes('failed') || latestAction.toLowerCase().includes('rejected')) {
        statusClass = 'status-failed';
        statusText = 'Failed';
    }

    statusBadge.className = `status-badge ${statusClass}`;
    statusBadge.textContent = statusText;

    // Congress.gov link
    const congressLink = document.getElementById('congress-link');
    const billTypeFormatted = bill.bill_type.toLowerCase();
    congressLink.href = `https://www.congress.gov/bill/${bill.congress}th-congress/${billTypeFormatted}-bill/${bill.bill_number}`;
}

// Render key metrics
function renderKeyMetrics(bill) {
    const container = document.getElementById('key-metrics');

    const sponsorLink = bill.sponsor_bioguide_id
        ? `<a href="member-profile.html?id=${bill.sponsor_bioguide_id}">${bill.sponsor_first_name || ''} ${bill.sponsor_last_name || ''}</a>`
        : (bill.sponsor_name || 'N/A');

    container.innerHTML = `
        <div class="metric-card">
            <div class="metric-label">Sponsor</div>
            <div class="metric-value">${sponsorLink}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Cosponsors</div>
            <div class="metric-value">${bill.cosponsors_count || 0}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Latest Action</div>
            <div class="metric-value">${formatDate(bill.latest_action_date)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Policy Area</div>
            <div class="metric-value">${bill.policy_area || 'N/A'}</div>
        </div>
    `;
}

// Render industry tags
function renderIndustryTags(bill) {
    const alertContainer = document.getElementById('trade-alert-banner');
    const industryContainer = document.getElementById('industry-tags');
    const tickersContainer = document.getElementById('stock-tickers');

    // Trade alert banner
    const tradeCorrelationsCount = bill.trade_correlations_count || 0;
    if (tradeCorrelationsCount > 0) {
        alertContainer.innerHTML = `
            <div class="trade-alert-banner" onclick="document.getElementById('trades-section').scrollIntoView({behavior: 'smooth'})">
                <strong>⚠️ ${tradeCorrelationsCount} legislator${tradeCorrelationsCount > 1 ? 's' : ''} traded related stocks within 90 days of bill activity</strong>
                <p style="margin: 0.5rem 0 0; font-size: 0.9rem;">Click to view related trades below</p>
            </div>
        `;
    } else {
        alertContainer.innerHTML = '';
    }

    // Industry tags
    const industryTags = bill.industry_tags || bill.top_industry_tags || [];
    if (industryTags.length > 0) {
        const industryIcons = {
            'Defense': '🛡️',
            'Healthcare': '🏥',
            'Finance': '💰',
            'Energy': '⚡',
            'Technology': '💻',
            'Agriculture': '🌾',
            'Transportation': '🚗',
            'Real Estate': '🏠'
        };

        let html = '<div style="margin-bottom: 1rem;">';
        industryTags.forEach(tag => {
            const industry = typeof tag === 'string' ? tag : tag.industry;
            const confidence = typeof tag === 'object' ? tag.confidence_score : null;
            const icon = industryIcons[industry] || '🏭';
            const confidenceText = confidence ? ` <span class="confidence-score">(${(confidence * 100).toFixed(0)}%)</span>` : '';
            html += `<span class="badge industry-badge">${icon} ${industry}${confidenceText}</span>`;
        });
        html += '</div>';
        industryContainer.innerHTML = html;
    } else {
        industryContainer.innerHTML = '<p class="empty-state">No industry tags identified</p>';
    }

    // Stock tickers
    const tickers = bill.tickers || [];
    if (tickers.length > 0) {
        let html = '<div><strong>Mentioned Stocks:</strong> ';
        tickers.forEach(ticker => {
            html += `<a href="https://finance.yahoo.com/quote/${ticker}" target="_blank" class="badge ticker-badge">$${ticker}</a>`;
        });
        html += '</div>';
        tickersContainer.innerHTML = html;
    } else {
        tickersContainer.innerHTML = '';
    }
}

// Render sponsor and cosponsors
function renderSponsors(bill) {
    const sponsorContainer = document.getElementById('sponsor-card');
    const cosponsorsContainer = document.getElementById('cosponsors-summary');

    // Sponsor card
    const partyClass = `party-${bill.sponsor_party || 'I'}`;
    const partyBadge = bill.sponsor_party ? `<span class="party-badge ${partyClass}">${bill.sponsor_party}</span>` : '';
    const stateBadge = bill.sponsor_state ? `<span class="state-badge">${bill.sponsor_state}</span>` : '';
    const sponsorLink = bill.sponsor_bioguide_id
        ? `onclick="window.location.href='member-profile.html?id=${bill.sponsor_bioguide_id}'"`
        : '';

    sponsorContainer.innerHTML = `
        <div class="sponsor-card">
            <div class="sponsor-name" ${sponsorLink}>
                ${bill.sponsor_first_name || ''} ${bill.sponsor_last_name || bill.sponsor_name || 'Unknown'}
            </div>
            <div>
                ${partyBadge}
                ${stateBadge}
            </div>
        </div>
    `;

    // Cosponsors summary
    const cosponsorsCount = bill.cosponsors_count || 0;
    if (cosponsorsCount > 0) {
        cosponsorsContainer.innerHTML = `
            <div class="cosponsors-summary">
                <strong>${cosponsorsCount} Cosponsor${cosponsorsCount > 1 ? 's' : ''}</strong>
                <button class="btn btn-primary" id="view-cosponsors-btn" style="margin-left: 1rem;">
                    View All Cosponsors
                </button>
            </div>
        `;

        // Add event listener for modal
        document.getElementById('view-cosponsors-btn').addEventListener('click', () => {
            loadCosponsors(bill);
        });
    } else {
        cosponsorsContainer.innerHTML = '<p class="empty-state">No cosponsors</p>';
    }
}

// Load and display cosponsors
async function loadCosponsors(bill) {
    const modal = document.getElementById('cosponsors-modal');
    const list = document.getElementById('cosponsor-list');
    const search = document.getElementById('cosponsor-search');

    // Show modal
    modal.classList.add('active');
    list.innerHTML = '<li class="cosponsor-item">Loading cosponsors...</li>';

    try {
        // For now, show message that cosponsors will be loaded from API
        // In production, this would fetch from /v1/congress/bills/{bill_id}/cosponsors
        const billId = `${bill.congress}-${bill.bill_type}-${bill.bill_number}`;

        // Mock data structure - in production, fetch from API
        list.innerHTML = `
            <li class="cosponsor-item">
                <div>
                    <strong>Loading cosponsor data...</strong>
                    <div style="font-size: 0.85rem; color: #666; margin-top: 0.25rem;">
                        API endpoint: /v1/congress/bills/${billId}/cosponsors
                    </div>
                </div>
            </li>
        `;

        // Add search functionality
        search.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            const items = list.querySelectorAll('.cosponsor-item');
            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                item.style.display = text.includes(searchTerm) ? 'flex' : 'none';
            });
        });

    } catch (error) {
        list.innerHTML = `<li class="cosponsor-item">Error loading cosponsors: ${error.message}</li>`;
    }
}

// Close modal
document.getElementById('modal-close').addEventListener('click', () => {
    document.getElementById('cosponsors-modal').classList.remove('active');
});

// Close modal on background click
document.getElementById('cosponsors-modal').addEventListener('click', (e) => {
    if (e.target.id === 'cosponsors-modal') {
        document.getElementById('cosponsors-modal').classList.remove('active');
    }
});

// Render legislative timeline
function renderTimeline(bill) {
    const container = document.getElementById('timeline');
    const loadHistoryBtn = document.getElementById('load-full-history-btn');

    // Get recent actions (first 10)
    const actions = bill.actions_recent || bill.actions || [];
    allActions = actions;

    if (actions.length === 0) {
        container.innerHTML = '<p class="empty-state">No actions available</p>';
        loadHistoryBtn.style.display = 'none';
        return;
    }

    // Render first 10 actions
    const actionsToShow = actions.slice(0, 10);
    let html = '';

    actionsToShow.forEach(action => {
        const chamber = action.chamber || action.action_code?.charAt(0) === 'H' ? 'House' : 'Senate';
        const chamberClass = chamber === 'House' ? 'chamber-house' : 'chamber-senate';

        html += `
            <div class="timeline-item">
                <div class="timeline-date">
                    <span class="timeline-chamber ${chamberClass}">${chamber}</span>
                    ${formatDate(action.action_date)}
                </div>
                <div class="timeline-text">${action.action_text || action.text || 'No description'}</div>
            </div>
        `;
    });

    container.innerHTML = html;

    // Show load more button if there are more actions
    if (actions.length > 10) {
        loadHistoryBtn.style.display = 'block';
        loadHistoryBtn.onclick = () => loadFullHistory(bill);
    } else {
        loadHistoryBtn.style.display = 'none';
    }
}

// Load full action history
async function loadFullHistory(bill) {
    const container = document.getElementById('timeline');
    const loadHistoryBtn = document.getElementById('load-full-history-btn');

    loadHistoryBtn.textContent = 'Loading...';
    loadHistoryBtn.disabled = true;

    try {
        const billId = `${bill.congress}-${bill.bill_type}-${bill.bill_number}`;

        // In production, fetch from /v1/congress/bills/{bill_id}/actions
        // For now, show all actions from the bill data
        let html = '';

        allActions.forEach(action => {
            const chamber = action.chamber || (action.action_code?.charAt(0) === 'H' ? 'House' : 'Senate');
            const chamberClass = chamber === 'House' ? 'chamber-house' : 'chamber-senate';

            html += `
                <div class="timeline-item">
                    <div class="timeline-date">
                        <span class="timeline-chamber ${chamberClass}">${chamber}</span>
                        ${formatDate(action.action_date)}
                    </div>
                    <div class="timeline-text">${action.action_text || action.text || 'No description'}</div>
                </div>
            `;
        });

        container.innerHTML = html;

        loadHistoryBtn.textContent = `Showing ${allActions.length} actions`;
        loadHistoryBtn.disabled = true;
        fullHistoryLoaded = true;

    } catch (error) {
        loadHistoryBtn.textContent = 'Error loading history';
        console.error('Error loading full history:', error);
    }
}

// Render committees
function renderCommittees(bill) {
    const container = document.getElementById('committees-list');
    const committees = bill.committees || [];

    if (committees.length === 0) {
        container.innerHTML = '<li class="empty-state">No committee assignments</li>';
        return;
    }

    let html = '';
    committees.forEach(committee => {
        const name = committee.committee_name || committee.name || 'Unknown Committee';
        const date = formatDate(committee.referral_date || committee.date);
        html += `
            <li class="committee-item">
                <span class="committee-name">${name}</span>
                <span class="committee-date">${date}</span>
            </li>
        `;
    });

    container.innerHTML = html;
}

// Render related trades
function renderTrades(bill) {
    const container = document.getElementById('trades-container');
    const trades = bill.trade_correlations || [];

    if (trades.length === 0) {
        container.innerHTML = '<p class="empty-state">No related trades detected</p>';
        return;
    }

    // Sort by correlation score (descending)
    trades.sort((a, b) => (b.correlation_score || 0) - (a.correlation_score || 0));

    let html = `
        <table class="trades-table" id="trades-table">
            <thead>
                <tr>
                    <th onclick="sortTrades('member')">Member</th>
                    <th onclick="sortTrades('ticker')">Ticker</th>
                    <th onclick="sortTrades('date')">Trade Date</th>
                    <th onclick="sortTrades('type')">Type</th>
                    <th onclick="sortTrades('amount')">Amount</th>
                    <th onclick="sortTrades('days')">Days from Bill</th>
                    <th onclick="sortTrades('score')">Score ↓</th>
                    <th onclick="sortTrades('role')">Role</th>
                    <th>Committee</th>
                </tr>
            </thead>
            <tbody>
    `;

    trades.forEach(trade => {
        const memberName = trade.member_name || `${trade.member_first_name || ''} ${trade.member_last_name || ''}`.trim() || 'Unknown';
        const memberLink = trade.member_bioguide_id
            ? `<a href="member-profile.html?id=${trade.member_bioguide_id}">${memberName}</a>`
            : memberName;

        const score = trade.correlation_score || 0;
        let scoreClass = 'score-low';
        if (score >= 70) scoreClass = 'score-high';
        else if (score >= 40) scoreClass = 'score-moderate';

        const tradeType = trade.trade_type || trade.type || '';
        const tradeClass = tradeType.toLowerCase() === 'purchase' ? 'trade-type-purchase' : 'trade-type-sale';

        const committeeOverlap = trade.committee_overlap || false;
        const committeeBadge = committeeOverlap ? '<span class="committee-badge" title="Member serves on committee reviewing this bill">🏛️</span>' : '-';

        html += `
            <tr>
                <td>${memberLink}</td>
                <td><strong>${trade.ticker || 'N/A'}</strong></td>
                <td>${formatDate(trade.trade_date)}</td>
                <td class="${tradeClass}">${tradeType || 'N/A'}</td>
                <td>${trade.amount_range || trade.amount || 'N/A'}</td>
                <td>${trade.days_offset || trade.days_from_action || 'N/A'}</td>
                <td><span class="correlation-score ${scoreClass}">${score}</span></td>
                <td>${trade.role_type || trade.role || 'N/A'}</td>
                <td>${committeeBadge}</td>
            </tr>
        `;
    });

    html += '</tbody></table>';

    // Add tooltip for correlation score
    html += `
        <div style="margin-top: 1rem; padding: 1rem; background: #f9f9f9; border-radius: 8px; font-size: 0.85rem;">
            <strong>Correlation Score Explanation:</strong>
            <ul style="margin: 0.5rem 0 0 1.5rem; line-height: 1.8;">
                <li><strong>Time Proximity:</strong> 0-50 points (closer to bill activity = higher score)</li>
                <li><strong>Industry/Ticker Match:</strong> 0-30 points (direct ticker mention = 30, industry match = 20)</li>
                <li><strong>Role Weight:</strong> 0-10 points (sponsor = 10, cosponsor = 5)</li>
                <li><strong>Committee Overlap:</strong> 0-10 points (member on bill committee = 10)</li>
            </ul>
            <p style="margin: 0.5rem 0 0;"><strong>Score Ranges:</strong>
                <span class="correlation-score score-high">70-100 = High</span>
                <span class="correlation-score score-moderate">40-69 = Moderate</span>
                <span class="correlation-score score-low">0-39 = Low</span>
            </p>
        </div>
    `;

    container.innerHTML = html;
}

// Sort trades table
let currentSortColumn = 'score';
let currentSortDirection = 'desc';

function sortTrades(column) {
    const trades = billData.trade_correlations || [];
    if (trades.length === 0) return;

    // Toggle direction if same column
    if (currentSortColumn === column) {
        currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        currentSortColumn = column;
        currentSortDirection = column === 'score' ? 'desc' : 'asc';
    }

    // Sort
    trades.sort((a, b) => {
        let valA, valB;

        switch (column) {
            case 'member':
                valA = a.member_name || '';
                valB = b.member_name || '';
                break;
            case 'ticker':
                valA = a.ticker || '';
                valB = b.ticker || '';
                break;
            case 'date':
                valA = new Date(a.trade_date || 0);
                valB = new Date(b.trade_date || 0);
                break;
            case 'type':
                valA = a.trade_type || '';
                valB = b.trade_type || '';
                break;
            case 'amount':
                valA = a.amount_range || '';
                valB = b.amount_range || '';
                break;
            case 'days':
                valA = parseInt(a.days_offset || 0);
                valB = parseInt(b.days_offset || 0);
                break;
            case 'score':
                valA = a.correlation_score || 0;
                valB = b.correlation_score || 0;
                break;
            case 'role':
                valA = a.role_type || '';
                valB = b.role_type || '';
                break;
            default:
                return 0;
        }

        if (valA < valB) return currentSortDirection === 'asc' ? -1 : 1;
        if (valA > valB) return currentSortDirection === 'asc' ? 1 : -1;
        return 0;
    });

    billData.trade_correlations = trades;
    renderTrades(billData);
}

// Export trades to CSV
function exportTradesToCSV() {
    const trades = billData?.trade_correlations || [];
    if (trades.length === 0) {
        alert('No trades to export');
        return;
    }

    // CSV header
    let csv = 'Member,Ticker,Trade Date,Trade Type,Amount Range,Days from Bill,Correlation Score,Role,Committee Overlap\n';

    // CSV rows
    trades.forEach(trade => {
        const memberName = trade.member_name || `${trade.member_first_name || ''} ${trade.member_last_name || ''}`.trim();
        csv += `"${memberName}",`;
        csv += `"${trade.ticker || ''}",`;
        csv += `"${formatDate(trade.trade_date)}",`;
        csv += `"${trade.trade_type || ''}",`;
        csv += `"${trade.amount_range || ''}",`;
        csv += `"${trade.days_offset || ''}",`;
        csv += `"${trade.correlation_score || ''}",`;
        csv += `"${trade.role_type || ''}",`;
        csv += `"${trade.committee_overlap ? 'Yes' : 'No'}"\n`;
    });

    // Download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `bill-${billData.bill_id}-trades.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// Share link
function shareLink() {
    const url = window.location.href;
    navigator.clipboard.writeText(url).then(() => {
        const btn = document.getElementById('share-btn');
        const originalText = btn.textContent;
        btn.textContent = '✓ Copied!';
        setTimeout(() => {
            btn.textContent = originalText;
        }, 2000);
    }).catch(err => {
        alert('Failed to copy link: ' + err);
    });
}

// Fetch and render lobbying activity
async function fetchAndRenderLobbyingActivity(billId) {
    const loadingEl = document.getElementById('lobbying-loading');
    const contentEl = document.getElementById('lobbying-content');
    const emptyEl = document.getElementById('lobbying-empty');
    const errorEl = document.getElementById('lobbying-error');

    try {
        // Fetch lobbying activity from API
        const response = await fetch(`${API_BASE}/v1/lobbying/bills/${billId}/lobbying-activity`);

        if (!response.ok) {
            if (response.status === 404) {
                // No lobbying activity found
                loadingEl.style.display = 'none';
                emptyEl.style.display = 'block';
                return;
            }
            throw new Error(`Failed to fetch lobbying data: ${response.statusText}`);
        }

        const data = await response.json();
        const lobbyingData = data.data || data;

        // Hide loading
        loadingEl.style.display = 'none';

        // Check if there's any lobbying activity
        if (!lobbyingData.lobbying_activity || lobbyingData.lobbying_activity.length === 0) {
            emptyEl.style.display = 'block';
            return;
        }

        // Show content
        contentEl.style.display = 'block';

        // Render summary badge
        const summaryEl = document.getElementById('lobbying-summary');
        const totalSpend = lobbyingData.total_lobbying_spend || 0;
        const clientCount = lobbyingData.client_count || 0;

        summaryEl.innerHTML = `
            💰 <strong>$${totalSpend.toLocaleString()}</strong> in lobbying activity from
            <strong>${clientCount}</strong> ${clientCount === 1 ? 'organization' : 'organizations'}
        `;

        // Render lobbying activities table
        const tableBody = document.getElementById('lobbying-table-body');
        tableBody.innerHTML = '';

        lobbyingData.lobbying_activity.forEach(activity => {
            const row = document.createElement('tr');

            // Client
            const clientCell = document.createElement('td');
            clientCell.textContent = activity.client || 'Unknown';
            row.appendChild(clientCell);

            // Registrant (firm)
            const registrantCell = document.createElement('td');
            registrantCell.textContent = activity.registrant || 'Unknown';
            row.appendChild(registrantCell);

            // Issue codes
            const issuesCell = document.createElement('td');
            const issueCodes = activity.issue_codes || [];
            if (issueCodes.length > 0) {
                issueCodes.slice(0, 3).forEach(code => {
                    const badge = document.createElement('span');
                    badge.className = 'issue-badge';
                    badge.textContent = code;
                    issuesCell.appendChild(badge);
                });
                if (issueCodes.length > 3) {
                    const moreBadge = document.createElement('span');
                    moreBadge.className = 'issue-badge';
                    moreBadge.textContent = `+${issueCodes.length - 3} more`;
                    issuesCell.appendChild(moreBadge);
                }
            } else {
                issuesCell.textContent = 'N/A';
            }
            row.appendChild(issuesCell);

            // Quarters
            const quartersCell = document.createElement('td');
            const quarters = activity.quarters || [];
            if (quarters.length > 0) {
                quarters.forEach(quarter => {
                    const badge = document.createElement('span');
                    badge.className = 'quarter-badge';
                    badge.textContent = quarter;
                    quartersCell.appendChild(badge);
                });
            } else {
                quartersCell.textContent = 'N/A';
            }
            row.appendChild(quartersCell);

            tableBody.appendChild(row);
        });

        // Render timeline (simple text-based for now)
        const timelineChart = document.getElementById('lobbying-timeline-chart');
        const firstDate = lobbyingData.first_lobbying_date || 'N/A';
        const lastDate = lobbyingData.last_lobbying_date || 'N/A';

        timelineChart.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>First Activity:</strong> ${formatDate(firstDate)}
                </div>
                <div style="color: #999;">━━━━━━━━━━━━━━</div>
                <div>
                    <strong>Latest Activity:</strong> ${formatDate(lastDate)}
                </div>
            </div>
        `;

    } catch (error) {
        console.error('Error fetching lobbying data:', error);
        loadingEl.style.display = 'none';
        errorEl.style.display = 'block';
    }
}

// Print page
function printPage() {
    window.print();
}

// Initialize page
async function init() {
    const billId = getBillIdFromUrl();

    if (!validateBillId(billId)) {
        showError('Invalid bill ID format. Expected format: XXX-hr-YYYY (e.g., 118-hr-1234)');
        return;
    }

    showLoading();

    try {
        billData = await fetchBillData(billId);

        // Render all sections
        renderHeader(billData);
        renderKeyMetrics(billData);
        renderIndustryTags(billData);
        renderSponsors(billData);
        renderTimeline(billData);
        renderCommittees(billData);
        renderTrades(billData);

        // Fetch and render lobbying activity (async, non-blocking)
        fetchAndRenderLobbyingActivity(billId);

        // Set up action buttons
        document.getElementById('share-btn').addEventListener('click', shareLink);
        document.getElementById('export-csv-btn').addEventListener('click', exportTradesToCSV);
        document.getElementById('print-btn').addEventListener('click', printPage);

        showContent();

    } catch (error) {
        console.error('Error loading bill:', error);
        showError(error.message || 'Failed to load bill details. Please try again later.');
    }
}

// Run on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
