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
    year: '2024',
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
    scoreDiv.textContent = score;

    const summaryDiv = document.createElement('div');
    summaryDiv.className = 'correlation-summary';

    const memberName = document.createElement('div');
    memberName.className = 'member-name';
    memberName.textContent = corr.member_name || corr.member_bioguide_id || 'Unknown';

    const quickFacts = document.createElement('div');
    quickFacts.className = 'quick-facts';
    quickFacts.innerHTML = `
        <div class="fact-item">
            <span class="fact-label">Stock:</span>
            <span>${corr.ticker || 'N/A'}</span>
        </div>
        <div class="fact-item">
            <span class="fact-label">Bill:</span>
            <span>${corr.bill_id || 'N/A'}</span>
        </div>
        <div class="fact-item">
            <span class="fact-label">Trade:</span>
            <span>${corr.trade_type || 'N/A'} ${corr.trade_amount_display || ''}</span>
        </div>
        <div class="fact-item">
            <span class="fact-label">Lobbying:</span>
            <span>${formatCurrency(corr.lobbying_spend || 0)}</span>
        </div>
    `;

    summaryDiv.appendChild(memberName);
    summaryDiv.appendChild(quickFacts);
    header.appendChild(scoreDiv);
    header.appendChild(summaryDiv);

    // Details (hidden initially)
    const details = document.createElement('div');
    details.className = 'correlation-details';

    // Explanation
    if (corr.explanation_text) {
        const explanation = document.createElement('div');
        explanation.className = 'explanation-text';
        explanation.textContent = corr.explanation_text;
        details.appendChild(explanation);
    }

    // Scoring breakdown
    const scoringBreakdown = document.createElement('div');
    scoringBreakdown.innerHTML = `
        <div class="timeline-title">Scoring Breakdown</div>
        <div class="scoring-breakdown">
            <div class="score-component">
                <div class="component-label">Stock Trade</div>
                <div class="component-value">40 pts</div>
            </div>
            <div class="score-component" style="border-left-color: ${corr.member_role ? '#4caf50' : '#e0e0e0'}">
                <div class="component-label">Bill ${corr.member_role || 'N/A'}</div>
                <div class="component-value">${corr.member_role ? '30' : '0'} pts</div>
            </div>
            <div class="score-component" style="border-left-color: ${corr.lobbying_spend > 0 ? '#ff9800' : '#e0e0e0'}">
                <div class="component-label">Lobbying Activity</div>
                <div class="component-value">${corr.lobbying_spend > 0 ? '20' : '0'} pts</div>
            </div>
            <div class="score-component" style="border-left-color: ${corr.contribution_amount > 0 ? '#f44336' : '#e0e0e0'}">
                <div class="component-label">Contribution</div>
                <div class="component-value">${corr.contribution_amount > 0 ? '10' : '0'} pts</div>
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
        document.getElementById('filter-year').value = '2024';
        scoreSlider.value = 50;
        scoreDisplay.textContent = '50';
        document.getElementById('contributions-only').checked = false;

        currentFilters = {
            member: '',
            ticker: '',
            bill: '',
            year: '2024',
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
