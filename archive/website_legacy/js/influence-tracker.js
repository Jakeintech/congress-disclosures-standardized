// Influence Tracker JavaScript - STAR FEATURE
const API_BASE = window.CONFIG?.API_BASE || 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com';

// State
let allCorrelations = [];
let displayedCount = 0;
const loadIncrement = 20;
let currentFilters = {
    member: '',
    ticker: '',
    bill: '',
    year: '2025',
    minScore: 50,
    contributionsOnly: false
};

// Format currency
function formatCurrency(amount) {
    if (!amount) return '$0';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
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

// Get score class
function getScoreClass(score) {
    if (score === 100) return 'score-100';
    if (score >= 80) return 'score-80';
    if (score >= 60) return 'score-60';
    if (score >= 40) return 'score-40';
    return 'score-low';
}

// Show/hide states
function showLoading() {
    document.getElementById('loading-state').style.display = 'block';
    document.getElementById('empty-state').style.display = 'none';
    document.getElementById('error-state').style.display = 'none';
    document.getElementById('correlations-container').style.display = 'none';
}

function showCorrelations() {
    document.getElementById('loading-state').style.display = 'none';
    document.getElementById('empty-state').style.display = 'none';
    document.getElementById('error-state').style.display = 'none';
    document.getElementById('correlations-container').style.display = 'block';
}

function showEmpty() {
    document.getElementById('loading-state').style.display = 'none';
    document.getElementById('empty-state').style.display = 'block';
    document.getElementById('error-state').style.display = 'none';
    document.getElementById('correlations-container').style.display = 'none';
}

function showError() {
    document.getElementById('loading-state').style.display = 'none';
    document.getElementById('empty-state').style.display = 'none';
    document.getElementById('error-state').style.display = 'block';
    document.getElementById('correlations-container').style.display = 'none';
}

// Fetch correlations
async function fetchCorrelations() {
    showLoading();

    try {
        const params = new URLSearchParams({
            year: currentFilters.year,
            min_score: currentFilters.minScore,
            limit: 200 // Get batch
        });

        if (currentFilters.member) params.append('member_bioguide', currentFilters.member);
        if (currentFilters.ticker) params.append('ticker', currentFilters.ticker.toUpperCase());
        if (currentFilters.bill) params.append('bill_id', currentFilters.bill.toLowerCase());

        const response = await fetch(`${API_BASE}/v1/correlations/triple?${params}`);

        if (!response.ok) {
            throw new Error(`Failed to fetch correlations: ${response.statusText}`);
        }

        const data = await response.json();
        allCorrelations = data.data?.correlations || data.correlations || [];

        // Apply contributions filter
        if (currentFilters.contributionsOnly) {
            allCorrelations = allCorrelations.filter(c => c.contribution_amount > 0);
        }

        // Reset display
        displayedCount = 0;

        if (allCorrelations.length === 0) {
            showEmpty();
        } else {
            showCorrelations();
            renderCorrelations();
        }

    } catch (error) {
        console.error('Error fetching correlations:', error);
        showError();
    }
}

// Render correlations
function renderCorrelations() {
    const container = document.getElementById('correlations-list');

    // Show next batch
    const endIdx = Math.min(displayedCount + loadIncrement, allCorrelations.length);
    const batch = allCorrelations.slice(displayedCount, endIdx);

    batch.forEach(corr => {
        const card = createCorrelationCard(corr);
        container.appendChild(card);
    });

    displayedCount = endIdx;

    // Update count
    document.getElementById('correlation-count').textContent = allCorrelations.length;

    // Show/hide load more
    const loadMoreBtn = document.getElementById('load-more-btn');
    if (displayedCount >= allCorrelations.length) {
        loadMoreBtn.style.display = 'none';
    } else {
        loadMoreBtn.style.display = 'block';
        loadMoreBtn.textContent = `Load More (${allCorrelations.length - displayedCount} remaining)`;
    }
}

// Issue code descriptions
const ISSUE_DESCRIPTIONS = {
    'BUD': 'Budget & Appropriations - Federal spending and budget allocation',
    'DEF': 'Defense - Military, national security, and defense contracts',
    'ENG': 'Energy - Oil, gas, nuclear, and renewable energy policy',
    'HCR': 'Health - Healthcare, pharmaceuticals, and medical policy',
    'TAX': 'Taxation - Tax policy, credits, and revenue',
    'TRA': 'Transportation - Infrastructure, aviation, and transit',
    'FIN': 'Finance - Banking, securities, and financial regulation',
    'TRD': 'Trade - Import/export, tariffs, and trade agreements',
    'ENV': 'Environment - EPA regulations, climate, pollution',
    'AGR': 'Agriculture - Farm policy, food safety, subsidies',
    'EDU': 'Education - Schools, higher ed, student loans',
    'AER': 'Aerospace - Aviation, space, and satellite policy',
    'SCI': 'Science - Research funding, technology R&D',
    'TEC': 'Technology - Tech regulation, AI, cybersecurity'
};

// Stock impact mapping by issue code
const STOCK_IMPACTS = {
    'DEF': { tickers: ['LMT', 'RTX', 'NOC', 'GD', 'BA'], sentiment: 'BULLISH', reason: 'Defense contractors typically benefit from defense legislation' },
    'AER': { tickers: ['BA', 'LMT', 'RTX', 'GE', 'HWM'], sentiment: 'BULLISH', reason: 'Aerospace firms benefit from aviation/space policy' },
    'HCR': { tickers: ['UNH', 'JNJ', 'PFE', 'CVS', 'ABBV'], sentiment: 'MIXED', reason: 'Healthcare legislation can be positive or negative depending on provisions' },
    'PHA': { tickers: ['PFE', 'MRK', 'ABBV', 'LLY', 'AMGN'], sentiment: 'MIXED', reason: 'Drug pricing/regulation can have varied effects' },
    'ENG': { tickers: ['XOM', 'CVX', 'COP', 'SLB', 'EOG'], sentiment: 'BULLISH', reason: 'Energy companies usually lobby for favorable treatment' },
    'ENV': { tickers: ['NEE', 'ENPH', 'FSLR', 'PLUG'], sentiment: 'BULLISH', reason: 'Clean energy firms benefit from green policies' },
    'TAX': { tickers: ['JPM', 'BAC', 'GS', 'MS', 'C'], sentiment: 'MIXED', reason: 'Tax policy effects vary by provision' },
    'FIN': { tickers: ['JPM', 'BAC', 'GS', 'BLK', 'SCHW'], sentiment: 'MIXED', reason: 'Financial regulation can help or hurt depending on details' },
    'TEC': { tickers: ['AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA'], sentiment: 'MIXED', reason: 'Tech regulation impact varies by company/sector' },
    'CPT': { tickers: ['NVDA', 'AMD', 'INTC', 'AVGO', 'QCOM'], sentiment: 'BULLISH', reason: 'CHIPS Act and semiconductor policy is supportive' },
    'TRA': { tickers: ['UPS', 'FDX', 'DAL', 'UAL', 'CSX'], sentiment: 'MIXED', reason: 'Infrastructure bills can be positive; regulations vary' },
    'AGR': { tickers: ['ADM', 'BG', 'TSN', 'CAG', 'DE'], sentiment: 'BULLISH', reason: 'Farm subsidies typically benefit ag companies' },
    'EDU': { tickers: ['LOPE', 'CHGG', 'UDMY', 'COUR'], sentiment: 'MIXED', reason: 'Education policy can benefit or restrict for-profit education' },
    'SCI': { tickers: ['TMO', 'DHR', 'A', 'IQV'], sentiment: 'BULLISH', reason: 'Research funding benefits life sciences companies' },
    'INS': { tickers: ['BRK.B', 'UNH', 'PGR', 'MET', 'AIG'], sentiment: 'MIXED', reason: 'Insurance regulation effects vary' },
    'TEL': { tickers: ['T', 'VZ', 'TMUS', 'CMCSA'], sentiment: 'MIXED', reason: 'Telecom regulation can be positive or restrictive' },
};

// Get stock impacts for a set of issue codes
function getStockImpactsForIssues(issueCodes, clientCount) {
    const impacts = [];
    const seenTickers = new Set();

    for (const code of issueCodes) {
        const mapping = STOCK_IMPACTS[code];
        if (!mapping) continue;

        // Add top tickers (limit to avoid clutter)
        for (const ticker of mapping.tickers.slice(0, 3)) {
            if (seenTickers.has(ticker)) continue;
            seenTickers.add(ticker);

            // Adjust confidence based on client count
            const confidence = clientCount >= 3 ? 'HIGH' : clientCount >= 2 ? 'MEDIUM' : 'LOW';

            impacts.push({
                ticker,
                sentiment: mapping.sentiment,
                confidence,
                issueCode: code
            });
        }
    }

    // Limit total tickers shown
    return impacts.slice(0, 8);
}

// Generate Congress.gov URL from bill ID
function getCongressUrl(billId) {
    // Parse bill ID like "118-s-4921" or "118-hr-123"
    const match = billId?.match(/(\d+)-(hr|s|hjres|sjres|hres|sres)-(\d+)/i);
    if (match) {
        const [, congress, type, number] = match;
        const typeMap = { 'hr': 'house-bill', 's': 'senate-bill', 'hjres': 'house-joint-resolution', 'sjres': 'senate-joint-resolution' };
        const urlType = typeMap[type.toLowerCase()] || type;
        return `https://www.congress.gov/bill/${congress}th-congress/${urlType}/${number}`;
    }
    return null;
}

// Generate intelligent summary
function generateLobbyingSummary(corr) {
    const clientCount = corr.client_count || 0;
    const registrantCount = corr.registrant_count || 0;
    const filingCount = corr.filing_count || 0;
    const issues = (corr.top_issue_codes || '').split('|').filter(i => i);

    let summary = '';

    if (clientCount >= 3) {
        summary += `🔥 <strong>High interest bill</strong> - ${clientCount} different organizations are paying lobbyists to influence this legislation. `;
    } else if (clientCount >= 2) {
        summary += `📊 <strong>Active lobbying target</strong> - Multiple clients are engaged on this bill. `;
    } else {
        summary += `📋 <strong>Targeted lobbying</strong> - Specific interest group activity on this bill. `;
    }

    if (registrantCount > 1) {
        summary += `${registrantCount} lobbying firms are working on behalf of clients. `;
    }

    if (filingCount > 1) {
        summary += `Activity spans ${filingCount} quarterly disclosures. `;
    }

    // Generate stock impact section based on issue codes
    const stockImpacts = getStockImpactsForIssues(issues, clientCount);
    if (stockImpacts.length > 0) {
        summary += `<br><br><strong>📈 Potential Stock Impact:</strong><br>`;
        summary += `<div style="display:flex; flex-wrap:wrap; gap:0.5rem; margin-top:0.5rem;">`;
        stockImpacts.forEach(impact => {
            const bgColor = impact.sentiment === 'BULLISH' ? '#e8f5e9' :
                impact.sentiment === 'BEARISH' ? '#ffebee' : '#fff3e0';
            const textColor = impact.sentiment === 'BULLISH' ? '#2e7d32' :
                impact.sentiment === 'BEARISH' ? '#c62828' : '#e65100';
            const icon = impact.sentiment === 'BULLISH' ? '📈' :
                impact.sentiment === 'BEARISH' ? '📉' : '↔️';
            summary += `<span style="background:${bgColor}; color:${textColor}; padding:0.25rem 0.5rem; border-radius:4px; font-size:0.75rem; font-weight:bold;">${icon} ${impact.ticker}</span>`;
        });
        summary += `</div>`;
    }

    if (issues.includes('DEF') || issues.includes('AER')) {
        summary += `<br><br>⚠️ <em>Defense/Aerospace contractors may benefit from this legislation.</em>`;
    } else if (issues.includes('HCR') || issues.includes('PHA')) {
        summary += `<br><br>💊 <em>Healthcare/pharmaceutical industry interests are involved.</em>`;
    } else if (issues.includes('ENG') || issues.includes('ENV')) {
        summary += `<br><br>⚡ <em>Energy sector stakeholders are actively lobbying.</em>`;
    }

    return summary;
}

// Create correlation card
function createCorrelationCard(corr) {
    const card = document.createElement('div');
    card.className = 'correlation-card';

    const score = corr.correlation_score || 0;
    const scoreClass = getScoreClass(score);

    // Header
    const header = document.createElement('div');
    header.className = 'correlation-header';

    const scoreDiv = document.createElement('div');
    scoreDiv.className = `correlation-score ${scoreClass}`;
    scoreDiv.textContent = Math.round(score);

    const summaryDiv = document.createElement('div');
    summaryDiv.className = 'correlation-summary';

    // Bill ID with link to Congress.gov
    const billName = document.createElement('div');
    billName.className = 'member-name';
    const congressUrl = getCongressUrl(corr.bill_id);
    if (congressUrl) {
        billName.innerHTML = `<a href="${congressUrl}" target="_blank" style="color:inherit;text-decoration:underline;">${corr.raw_reference || corr.bill_id}</a> <span style="font-size:0.7rem;">↗</span>`;
    } else {
        billName.textContent = corr.raw_reference || corr.bill_id || 'Unknown Bill';
    }

    // Parse client names (pipe-separated)
    const clients = (corr.client_names || '').split('|').filter(c => c).slice(0, 3);
    const registrants = (corr.registrant_names || '').split('|').filter(r => r).slice(0, 2);
    const issues = (corr.top_issue_codes || '').split('|').filter(i => i);

    const quickFacts = document.createElement('div');
    quickFacts.className = 'quick-facts';
    quickFacts.innerHTML = `
        <div class="fact-item">
            <span class="fact-label">Clients:</span>
            <span>${corr.client_count || 0} ${clients.length > 0 ? `(${clients[0].substring(0, 20)}${clients.length > 1 ? '...' : ''})` : ''}</span>
        </div>
        <div class="fact-item">
            <span class="fact-label">Lobbyists:</span>
            <span>${corr.registrant_count || 0} firms</span>
        </div>
        <div class="fact-item">
            <span class="fact-label">Filings:</span>
            <span>${corr.filing_count || 0}</span>
        </div>
        <div class="fact-item">
            <span class="fact-label">Lobbying:</span>
            <span>${formatCurrency(corr.lobbying_amount || 0)}</span>
        </div>
    `;

    summaryDiv.appendChild(billName);
    summaryDiv.appendChild(quickFacts);
    header.appendChild(scoreDiv);
    header.appendChild(summaryDiv);

    // Details (hidden initially)
    const details = document.createElement('div');
    details.className = 'correlation-details';

    // What This Means section - intelligent summary
    const summarySection = document.createElement('div');
    summarySection.innerHTML = `
        <div class="timeline-title">💡 What This Means</div>
        <div style="background:#f8f9fa; padding:1rem; border-radius:8px; margin-bottom:1rem; line-height:1.6; font-size:0.9rem;">
            ${generateLobbyingSummary(corr)}
        </div>
    `;
    details.appendChild(summarySection);

    // Lobbying clients section
    if (clients.length > 0) {
        const clientsSection = document.createElement('div');
        clientsSection.innerHTML = `
            <div class="timeline-title">🏢 Lobbying Clients</div>
            <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem;">
                ${clients.map(c => `<span style="background:#e8f5e9; color:#2e7d32; padding:0.25rem 0.5rem; border-radius:4px; font-size:0.8rem;">${c.substring(0, 30)}</span>`).join('')}
            </div>
        `;
        details.appendChild(clientsSection);
    }

    // Lobbying firms section
    if (registrants.length > 0) {
        const firmsSection = document.createElement('div');
        firmsSection.innerHTML = `
            <div class="timeline-title">👔 Lobbying Firms</div>
            <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem;">
                ${registrants.map(r => `<span style="background:#e3f2fd; color:#1565c0; padding:0.25rem 0.5rem; border-radius:4px; font-size:0.8rem;">${r.substring(0, 30)}</span>`).join('')}
            </div>
        `;
        details.appendChild(firmsSection);
    }

    // Issue codes section
    if (issues.length > 0) {
        const issuesSection = document.createElement('div');
        issuesSection.innerHTML = `
            <div class="timeline-title">📋 Issue Codes</div>
            <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem;">
                ${issues.map(i => `<span style="background:#fff3e0; color:#e65100; padding:0.25rem 0.5rem; border-radius:4px; font-size:0.8rem;">${i}</span>`).join('')}
            </div>
        `;
        details.appendChild(issuesSection);
    }

    // Scoring breakdown
    const scoringBreakdown = document.createElement('div');
    scoringBreakdown.innerHTML = `
        <div class="timeline-title">Influence Score Breakdown</div>
        <div class="scoring-breakdown">
            <div class="score-component" style="border-left-color: ${(corr.client_count || 0) > 2 ? '#4caf50' : '#e0e0e0'}">
                <div class="component-label">Multi-client Interest</div>
                <div class="component-value">${Math.min(30, (corr.client_count || 0) * 10)} pts</div>
            </div>
            <div class="score-component" style="border-left-color: ${(corr.filing_count || 0) > 1 ? '#2196f3' : '#e0e0e0'}">
                <div class="component-label">Filing Activity</div>
                <div class="component-value">${Math.min(25, (corr.filing_count || 0) * 5)} pts</div>
            </div>
            <div class="score-component" style="border-left-color: ${(corr.lobbying_amount || 0) > 0 ? '#ff9800' : '#e0e0e0'}">
                <div class="component-label">Lobbying Spend</div>
                <div class="component-value">${Math.min(25, Math.floor((corr.lobbying_amount || 0) / 10000))} pts</div>
            </div>
            <div class="score-component" style="border-left-color: ${(corr.registrant_count || 0) > 1 ? '#9c27b0' : '#e0e0e0'}">
                <div class="component-label">Firm Diversity</div>
                <div class="component-value">${Math.min(20, (corr.registrant_count || 0) * 10)} pts</div>
            </div>
        </div>
    `;
    details.appendChild(scoringBreakdown);

    // Timeline visualization
    if (corr.trade_date && corr.bill_action_date) {
        const timeline = createTimeline(corr);
        details.appendChild(timeline);
    }

    card.appendChild(header);
    card.appendChild(details);

    // Click to expand
    card.addEventListener('click', () => {
        card.classList.toggle('expanded');
        details.classList.toggle('visible');
    });

    return card;
}

// Create timeline
function createTimeline(corr) {
    const timelineDiv = document.createElement('div');
    timelineDiv.className = 'timeline-viz';

    const title = document.createElement('div');
    title.className = 'timeline-title';
    title.textContent = 'Event Timeline';

    const track = document.createElement('div');
    track.className = 'timeline-track';

    // Parse dates
    const dates = [];
    if (corr.trade_date) dates.push({ type: 'Trade', date: new Date(corr.trade_date) });
    if (corr.bill_action_date) dates.push({ type: 'Bill Action', date: new Date(corr.bill_action_date) });

    dates.sort((a, b) => a.date - b.date);

    if (dates.length >= 2) {
        const minDate = dates[0].date;
        const maxDate = dates[dates.length - 1].date;
        const range = maxDate - minDate || 1;

        dates.forEach(event => {
            const position = ((event.date - minDate) / range) * 100;

            const eventDiv = document.createElement('div');
            eventDiv.className = 'timeline-event';
            eventDiv.style.left = `${position}%`;

            const label = document.createElement('div');
            label.className = 'timeline-label';
            label.style.left = `${position}%`;
            label.textContent = `${event.type}: ${formatDate(event.date)}`;

            track.appendChild(eventDiv);
            track.appendChild(label);
        });
    }

    timelineDiv.appendChild(title);
    timelineDiv.appendChild(track);

    return timelineDiv;
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    // Score slider
    const scoreSlider = document.getElementById('score-slider');
    const scoreDisplay = document.getElementById('score-display');

    scoreSlider.addEventListener('input', (e) => {
        scoreDisplay.textContent = e.target.value;
    });

    // Apply filters
    document.getElementById('apply-btn').addEventListener('click', () => {
        currentFilters.member = document.getElementById('filter-member').value;
        currentFilters.ticker = document.getElementById('filter-ticker').value;
        currentFilters.bill = document.getElementById('filter-bill').value;
        currentFilters.year = document.getElementById('filter-year').value;
        currentFilters.minScore = parseInt(scoreSlider.value);
        currentFilters.contributionsOnly = document.getElementById('contributions-only').checked;

        // Clear existing
        document.getElementById('correlations-list').innerHTML = '';

        fetchCorrelations();
    });

    // Clear filters
    document.getElementById('clear-btn').addEventListener('click', () => {
        document.getElementById('filter-member').value = '';
        document.getElementById('filter-ticker').value = '';
        document.getElementById('filter-bill').value = '';
        document.getElementById('filter-year').value = '2025';
        scoreSlider.value = 50;
        scoreDisplay.textContent = '50';
        document.getElementById('contributions-only').checked = false;

        currentFilters = {
            member: '',
            ticker: '',
            bill: '',
            year: '2025',
            minScore: 50,
            contributionsOnly: false
        };

        document.getElementById('correlations-list').innerHTML = '';
        fetchCorrelations();
    });

    // Load more
    document.getElementById('load-more-btn').addEventListener('click', () => {
        renderCorrelations();
    });

    // Initial load
    fetchCorrelations();
});
