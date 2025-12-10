/**
 * Dashboard Logic (index.html)
 * Handles the Bronze layer statistics and filings table.
 * Uses API Gateway endpoints for live data.
 */

// API Gateway URL (from config.js or fallback)
const DASHBOARD_API_BASE = window.API_GATEWAY_URL || window.CONFIG?.API_GATEWAY_URL || 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com';

let allFilings = [];
let filteredFilings = [];
let currentPage = 1;
let sortColumn = 'filing_date';
let sortDirection = 'desc';

// Items per page - may be defined in config.js or default to 50
const ITEMS_PER_PAGE = window.ITEMS_PER_PAGE || 50;

document.addEventListener('DOMContentLoaded', () => {
    loadDashboardData();
    setupDashboardEventListeners();
});

async function loadDashboardData() {
    try {
        console.log('Loading data from API Gateway...');
        showLoading();

        // Load filings from API
        const filingsResponse = await fetch(`${DASHBOARD_API_BASE}/v1/filings?limit=500`);
        if (!filingsResponse.ok) {
            console.warn('Filings endpoint not available.');
            allFilings = [];
            hideLoading();
            return;
        }

        const filingsResult = await filingsResponse.json();
        // API returns { success: true, data: { filings: [...] } }
        const filingsData = filingsResult.data || filingsResult;
        allFilings = filingsData.filings || [];

        // Load summary stats from API
        try {
            const summaryResponse = await fetch(`${DASHBOARD_API_BASE}/v1/analytics/summary`);
            if (summaryResponse.ok) {
                const summaryResult = await summaryResponse.json();
                const stats = summaryResult.data || summaryResult;
                updateStats({
                    total_filings: stats.filings?.total || allFilings.length,
                    total_members: stats.members?.total || 0,
                    latest_year: stats.filings?.coverage_years?.slice(-1)[0] || new Date().getFullYear(),
                    last_updated: stats.filings?.latest_filing || new Date().toISOString()
                });
            }
        } catch (summaryError) {
            console.warn('Summary stats not available:', summaryError);
        }

        populateFilters();
        applyFilters();
        hideLoading();

    } catch (error) {
        console.error('Error loading Dashboard data:', error);
        allFilings = [];
        hideLoading();
    }
}

function updateStats(stats) {
    setText('total-filings', stats.total_filings?.toLocaleString() || '0');
    setText('total-members', stats.total_members?.toLocaleString() || '0');
    setText('latest-year', stats.latest_year || '-');
    setText('last-updated', stats.last_updated || '-');

    updateBronzeStats();
}

function updateBronzeStats() {
    const totalFilings = allFilings.length;
    const uniqueFilers = new Set(allFilings.map(f => `${f.first_name} ${f.last_name}`)).size;

    // Top State
    const stateCounts = {};
    allFilings.forEach(f => {
        if (f.state_district) {
            const state = f.state_district.substring(0, 2);
            stateCounts[state] = (stateCounts[state] || 0) + 1;
        }
    });
    const topState = Object.entries(stateCounts).sort((a, b) => b[1] - a[1])[0];

    // Top Filer
    const filerCounts = {};
    allFilings.forEach(f => {
        const name = `${f.first_name} ${f.last_name}`;
        filerCounts[name] = (filerCounts[name] || 0) + 1;
    });
    const topFiler = Object.entries(filerCounts).sort((a, b) => b[1] - a[1])[0];

    setText('bronze-total-filings', totalFilings.toLocaleString());
    setText('bronze-total-filers', uniqueFilers.toLocaleString());
    setText('bronze-top-state', topState ? `${topState[0]} (${topState[1]})` : '-');
    setText('bronze-top-filer', topFiler ? topFiler[0] : '-');

    renderFilingTypesChart();
}

function renderFilingTypesChart() {
    const ctx = document.getElementById('bronze-filing-types-chart');
    if (!ctx) return;

    const typeCounts = {
        'Annual': 0, 'Periodic': 0, 'New Member': 0, 'Termination': 0, 'Other': 0
    };

    allFilings.forEach(f => {
        switch (f.filing_type) {
            case 'A': typeCounts['Annual']++; break;
            case 'P': typeCounts['Periodic']++; break;
            case 'N': typeCounts['New Member']++; break;
            case 'T': typeCounts['Termination']++; break;
            default: typeCounts['Other']++;
        }
    });

    if (window.bronzeChart) window.bronzeChart.destroy();

    window.bronzeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(typeCounts),
            datasets: [{
                data: Object.values(typeCounts),
                backgroundColor: [
                    'hsl(217, 91%, 60%)', 'hsl(48, 96%, 60%)', 'hsl(142, 76%, 60%)',
                    'hsl(0, 84%, 60%)', 'hsl(215, 16%, 60%)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { boxWidth: 12 } },
                title: { display: true, text: 'Filing Types Distribution' }
            }
        }
    });
}

function populateFilters() {
    const years = [...new Set(allFilings.map(f => f.year))].sort((a, b) => b - a);
    const states = [...new Set(allFilings.map(f => f.state_district?.substring(0, 2)))].filter(Boolean).sort();

    const yearFilter = document.getElementById('year-filter');
    years.forEach(year => {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        yearFilter.appendChild(option);
    });

    const stateFilter = document.getElementById('state-filter');
    states.forEach(state => {
        const option = document.createElement('option');
        option.value = state;
        option.textContent = state;
        stateFilter.appendChild(option);
    });
}

function setupDashboardEventListeners() {
    document.getElementById('search').addEventListener('input', debounce(applyFilters, 300));
    document.getElementById('year-filter').addEventListener('change', applyFilters);
    document.getElementById('state-filter').addEventListener('change', applyFilters);
    document.getElementById('type-filter').addEventListener('change', applyFilters);
    document.getElementById('prev-page').addEventListener('click', () => changePage(-1));
    document.getElementById('next-page').addEventListener('click', () => changePage(1));
    document.getElementById('export-csv').addEventListener('click', exportToCSV);

    document.querySelectorAll('th[data-sort]').forEach(th => {
        th.addEventListener('click', () => sortBy(th.dataset.sort));
    });
}

function applyFilters() {
    const searchTerm = document.getElementById('search').value.toLowerCase();
    const yearFilter = document.getElementById('year-filter').value;
    const stateFilter = document.getElementById('state-filter').value;
    const typeFilter = document.getElementById('type-filter').value;

    filteredFilings = allFilings.filter(filing => {
        const matchesSearch = !searchTerm ||
            filing.first_name?.toLowerCase().includes(searchTerm) ||
            filing.last_name?.toLowerCase().includes(searchTerm) ||
            filing.state_district?.toLowerCase().includes(searchTerm) ||
            filing.doc_id?.toLowerCase().includes(searchTerm);

        const matchesYear = !yearFilter || filing.year == yearFilter;
        const matchesState = !stateFilter || filing.state_district?.startsWith(stateFilter);
        const matchesType = !typeFilter || filing.filing_type === typeFilter;

        return matchesSearch && matchesYear && matchesState && matchesType;
    });

    sortFilings();
    currentPage = 1;
    renderTable();
    updatePagination();
}

function sortFilings() {
    filteredFilings.sort((a, b) => {
        let aVal = a[sortColumn];
        let bVal = b[sortColumn];

        if (aVal === null || aVal === undefined) return 1;
        if (bVal === null || bVal === undefined) return -1;

        if (sortColumn === 'filing_date') {
            aVal = new Date(aVal);
            bVal = new Date(bVal);
        }

        if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
        return 0;
    });
}

function sortBy(column) {
    if (sortColumn === column) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortColumn = column;
        sortDirection = 'desc';
    }
    sortFilings();
    renderTable();
}

function renderTable() {
    const tbody = document.getElementById('table-body');
    tbody.innerHTML = '';

    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;
    const pageFilings = filteredFilings.slice(start, end);

    pageFilings.forEach(filing => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${filing.year || '-'}</td>
            <td>${formatDate(filing.filing_date)}</td>
            <td><strong>${formatName(filing)}</strong></td>
            <td>${filing.state_district || '-'}</td>
            <td>
                <span class="badge badge-type-${(filing.filing_type || 'a').toLowerCase()}">
                    ${getFilingTypeName(filing.filing_type)}
                </span>
            </td>
            <td><code>${filing.doc_id || '-'}</code></td>
            <td>
                <a href="${getPDFUrl(filing)}" target="_blank" rel="noopener" class="btn-link">View PDF</a>
            </td>
        `;
        tbody.appendChild(row);
    });

    setText('showing-count', `Showing ${start + 1}-${Math.min(end, filteredFilings.length)} of ${filteredFilings.length.toLocaleString()} filings`);
}

function updatePagination() {
    const totalPages = Math.ceil(filteredFilings.length / ITEMS_PER_PAGE);
    document.getElementById('prev-page').disabled = currentPage === 1;
    document.getElementById('next-page').disabled = currentPage === totalPages || totalPages === 0;
    setText('page-info', `Page ${currentPage} of ${totalPages || 1}`);
}

function changePage(delta) {
    currentPage += delta;
    renderTable();
    updatePagination();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function exportToCSV() {
    const headers = ['Year', 'Filing Date', 'First Name', 'Last Name', 'State/District', 'Filing Type', 'Document ID', 'PDF URL'];
    const rows = filteredFilings.map(f => [
        f.year, f.filing_date, f.first_name, f.last_name, f.state_district, f.filing_type, f.doc_id, getPDFUrl(f)
    ]);

    const csv = [headers, ...rows].map(row => row.map(cell => `"${cell || ''}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `congress-disclosures-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
}

// Utilities
function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
        return new Date(dateStr).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch { return dateStr; }
}

function formatName(filing) {
    return [filing.prefix, filing.first_name, filing.last_name, filing.suffix].filter(Boolean).join(' ') || 'Unknown';
}

function getFilingTypeName(type) {
    const types = { 'A': 'Annual', 'N': 'New Member', 'T': 'Termination', 'P': 'Periodic' };
    return types[type] || type || 'Unknown';
}

function getPDFUrl(filing) {
    return `https://disclosures-clerk.house.gov/public_disc/financial-pdfs/${filing.year}/${filing.doc_id}.pdf`;
}

function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

function showLoading() {
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('data-section').classList.add('hidden');
    document.getElementById('error').classList.add('hidden');
}

function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('data-section').classList.remove('hidden');
}
