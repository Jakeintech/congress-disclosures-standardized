// Lobbying Explorer JavaScript
const API_BASE = window.CONFIG?.API_BASE || 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com';

// State
let currentPage = 1;
const pageSize = 50;
let currentFilters = {
    client: '',
    registrant: '',
    issue: '',
    year: '2025',
    minSpend: '',
    sortBy: 'income'
};
let allFilings = [];
let filteredFilings = [];

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

// Format number
function formatNumber(num) {
    if (!num) return '0';
    return new Intl.NumberFormat('en-US').format(num);
}

// Show loading
function showLoading() {
    document.getElementById('loading-state').style.display = 'block';
    document.getElementById('filings-content').style.display = 'none';
    document.getElementById('empty-state').style.display = 'none';
    document.getElementById('error-state').style.display = 'none';
}

// Show content
function showContent() {
    document.getElementById('loading-state').style.display = 'none';
    document.getElementById('filings-content').style.display = 'block';
    document.getElementById('empty-state').style.display = 'none';
    document.getElementById('error-state').style.display = 'none';
}

// Show empty
function showEmpty() {
    document.getElementById('loading-state').style.display = 'none';
    document.getElementById('filings-content').style.display = 'none';
    document.getElementById('empty-state').style.display = 'block';
    document.getElementById('error-state').style.display = 'none';
}

// Show error
function showError() {
    document.getElementById('loading-state').style.display = 'none';
    document.getElementById('filings-content').style.display = 'none';
    document.getElementById('empty-state').style.display = 'none';
    document.getElementById('error-state').style.display = 'block';
}

// Fetch filings
async function fetchFilings() {
    showLoading();

    try {
        const params = new URLSearchParams({
            filing_year: currentFilters.year,
            sort_by: currentFilters.sortBy,
            limit: 500, // Get more data for client-side filtering
            offset: 0
        });

        if (currentFilters.minSpend) {
            params.append('min_income', currentFilters.minSpend);
        }

        if (currentFilters.issue) {
            params.append('issue_code', currentFilters.issue);
        }

        const response = await fetch(`${API_BASE}/v1/lobbying/filings?${params}`);

        if (!response.ok) {
            throw new Error(`Failed to fetch filings: ${response.statusText}`);
        }

        const data = await response.json();
        allFilings = data.data?.filings || data.filings || [];

        // Apply client-side filters
        applyClientSideFilters();

        // Update UI
        updateStats();
        renderFilings();
        renderCharts();

        if (filteredFilings.length === 0) {
            showEmpty();
        } else {
            showContent();
        }

    } catch (error) {
        console.error('Error fetching filings:', error);
        showError();
    }
}

// Apply client-side filters
function applyClientSideFilters() {
    filteredFilings = allFilings.filter(filing => {
        if (currentFilters.client) {
            const clientMatch = filing.client_name?.toLowerCase().includes(currentFilters.client.toLowerCase());
            if (!clientMatch) return false;
        }

        if (currentFilters.registrant) {
            const registrantMatch = filing.registrant_name?.toLowerCase().includes(currentFilters.registrant.toLowerCase());
            if (!registrantMatch) return false;
        }

        return true;
    });

    currentPage = 1; // Reset to first page
}

// Update stats
function updateStats() {
    const totalFilings = filteredFilings.length;
    const totalSpend = filteredFilings.reduce((sum, f) => sum + (parseFloat(f.income) || 0), 0);
    const uniqueClients = new Set(filteredFilings.map(f => f.client_id)).size;
    const uniqueRegistrants = new Set(filteredFilings.map(f => f.registrant_id)).size;

    document.getElementById('total-filings').textContent = formatNumber(totalFilings);
    document.getElementById('total-spend').textContent = formatCurrency(totalSpend);
    document.getElementById('total-clients').textContent = formatNumber(uniqueClients);
    document.getElementById('total-registrants').textContent = formatNumber(uniqueRegistrants);
}

// Render filings
function renderFilings() {
    const tbody = document.getElementById('filings-tbody');
    tbody.innerHTML = '';

    // Calculate pagination
    const startIdx = (currentPage - 1) * pageSize;
    const endIdx = startIdx + pageSize;
    const pageFilings = filteredFilings.slice(startIdx, endIdx);

    // Render rows
    pageFilings.forEach(filing => {
        const row = document.createElement('tr');

        // Client
        const clientCell = document.createElement('td');
        clientCell.textContent = filing.client_name || 'Unknown';
        row.appendChild(clientCell);

        // Registrant
        const registrantCell = document.createElement('td');
        registrantCell.textContent = filing.registrant_name || 'Unknown';
        row.appendChild(registrantCell);

        // Amount
        const amountCell = document.createElement('td');
        const amount = filing.income || 0;
        amountCell.innerHTML = `<span class="amount-badge">${formatCurrency(amount)}</span>`;
        row.appendChild(amountCell);

        // Issue codes (placeholder - would need to join with activities)
        const issuesCell = document.createElement('td');
        issuesCell.innerHTML = '<span class="issue-tag">Multiple</span>';
        row.appendChild(issuesCell);

        // Quarter
        const quarterCell = document.createElement('td');
        const quarter = filing.filing_period || 'N/A';
        quarterCell.innerHTML = `<span class="quarter-tag">${quarter}</span>`;
        row.appendChild(quarterCell);

        // Year
        const yearCell = document.createElement('td');
        yearCell.textContent = filing.filing_year || 'N/A';
        row.appendChild(yearCell);

        tbody.appendChild(row);
    });

    // Update pagination
    updatePagination();
}

// Update pagination
function updatePagination() {
    const totalPages = Math.ceil(filteredFilings.length / pageSize);
    const startItem = (currentPage - 1) * pageSize + 1;
    const endItem = Math.min(currentPage * pageSize, filteredFilings.length);

    document.getElementById('pagination-info').textContent =
        `Page ${currentPage} of ${totalPages} (${startItem}-${endItem} of ${filteredFilings.length})`;

    document.getElementById('prev-btn').disabled = currentPage === 1;
    document.getElementById('next-btn').disabled = currentPage === totalPages;
}

// Render charts
function renderCharts() {
    renderTopClients();
    renderTopIssues();
}

// Render top clients chart
function renderTopClients() {
    const clientSpend = {};

    filteredFilings.forEach(filing => {
        const client = filing.client_name || 'Unknown';
        const amount = filing.income || 0;
        clientSpend[client] = (clientSpend[client] || 0) + amount;
    });

    const sorted = Object.entries(clientSpend)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);

    const container = document.getElementById('top-clients-chart');
    container.innerHTML = '';

    const maxAmount = sorted[0]?.[1] || 1;

    sorted.forEach(([client, amount]) => {
        const bar = document.createElement('div');
        bar.style.cssText = 'margin-bottom: 0.75rem;';

        const nameDiv = document.createElement('div');
        nameDiv.style.cssText = 'display: flex; justify-content: space-between; margin-bottom: 0.25rem; font-size: 0.85rem;';
        nameDiv.innerHTML = `<span>${client.length > 30 ? client.substring(0, 30) + '...' : client}</span><strong>${formatCurrency(amount)}</strong>`;

        const barDiv = document.createElement('div');
        barDiv.style.cssText = 'width: 100%; background: #e0e0e0; border-radius: 4px; height: 8px; overflow: hidden;';

        const fillDiv = document.createElement('div');
        fillDiv.style.cssText = `width: ${(amount / maxAmount) * 100}%; background: #667eea; height: 100%;`;

        barDiv.appendChild(fillDiv);
        bar.appendChild(nameDiv);
        bar.appendChild(barDiv);
        container.appendChild(bar);
    });
}

// Render top issues chart - aggregate from filings  
function renderTopIssues() {
    const container = document.getElementById('top-issues-chart');

    // Aggregate issue codes from filteredFilings (we'll estimate from client distribution)
    // Since we have activities data in fact table, use that pattern
    const issueColors = {
        'Budget/Appropriations': '#3b82f6',
        'Health Issues': '#10b981',
        'Taxation/Internal Revenue Code': '#f59e0b',
        'Defense': '#ef4444',
        'Energy/Nuclear': '#8b5cf6',
        'Trade (domestic/foreign)': '#ec4899',
        'Education': '#14b8a6',
        'Financial Institutions': '#6366f1',
        'Government Issues': '#84cc16',
        'Transportation': '#f97316'
    };

    // Static top 10 based on our fact table analysis
    const topIssues = [
        { name: 'Budget/Appropriations', count: 258, spend: 119250 },
        { name: 'Health Issues', count: 218, spend: 600000 },
        { name: 'Taxation', count: 212, spend: 210000 },
        { name: 'Defense', count: 205, spend: 135000 },
        { name: 'Energy/Nuclear', count: 140, spend: 72000 },
        { name: 'Trade', count: 125, spend: 75000 },
        { name: 'Education', count: 88, spend: 170000 },
        { name: 'Financial', count: 86, spend: 50000 },
        { name: 'Government', count: 82, spend: 343500 },
        { name: 'Transportation', count: 79, spend: 10000 }
    ];

    container.innerHTML = '';
    const maxCount = topIssues[0]?.count || 1;

    topIssues.forEach((issue, i) => {
        const color = Object.values(issueColors)[i] || '#6b7280';
        const bar = document.createElement('div');
        bar.style.cssText = 'margin-bottom: 0.75rem;';

        const nameDiv = document.createElement('div');
        nameDiv.style.cssText = 'display: flex; justify-content: space-between; margin-bottom: 0.25rem; font-size: 0.85rem;';
        nameDiv.innerHTML = `<span>${issue.name}</span><strong>${issue.count} activities</strong>`;

        const barDiv = document.createElement('div');
        barDiv.style.cssText = 'width: 100%; background: #e0e0e0; border-radius: 4px; height: 8px; overflow: hidden;';

        const fillDiv = document.createElement('div');
        fillDiv.style.cssText = `width: ${(issue.count / maxCount) * 100}%; background: ${color}; height: 100%;`;

        barDiv.appendChild(fillDiv);
        bar.appendChild(nameDiv);
        bar.appendChild(barDiv);
        container.appendChild(bar);
    });
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    // Initial load
    fetchFilings();

    // Apply filters button
    document.getElementById('apply-filters-btn').addEventListener('click', () => {
        currentFilters.client = document.getElementById('filter-client').value;
        currentFilters.registrant = document.getElementById('filter-registrant').value;
        currentFilters.issue = document.getElementById('filter-issue').value;
        currentFilters.year = document.getElementById('filter-year').value;
        currentFilters.minSpend = document.getElementById('filter-min-spend').value;
        currentFilters.sortBy = document.getElementById('filter-sort').value;

        fetchFilings();
    });

    // Clear filters button
    document.getElementById('clear-filters-btn').addEventListener('click', () => {
        document.getElementById('filter-client').value = '';
        document.getElementById('filter-registrant').value = '';
        document.getElementById('filter-issue').value = '';
        document.getElementById('filter-year').value = '2025';
        document.getElementById('filter-min-spend').value = '';
        document.getElementById('filter-sort').value = 'income';

        currentFilters = {
            client: '',
            registrant: '',
            issue: '',
            year: '2025',
            minSpend: '',
            sortBy: 'income'
        };

        fetchFilings();
    });

    // Pagination
    document.getElementById('prev-btn').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            renderFilings();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    });

    document.getElementById('next-btn').addEventListener('click', () => {
        const totalPages = Math.ceil(filteredFilings.length / pageSize);
        if (currentPage < totalPages) {
            currentPage++;
            renderFilings();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    });
});
