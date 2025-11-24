// Configuration
const S3_BUCKET = 'congress-disclosures-standardized';
const S3_REGION = 'us-east-1';
const MANIFEST_URL = `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com/manifest.json`;
const ITEMS_PER_PAGE = 50;

// State
let allFilings = [];
let filteredFilings = [];
let currentPage = 1;
let sortColumn = 'filing_date';
let sortDirection = 'desc';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadData();
    setupEventListeners();
});

// Load data from S3
async function loadData() {
    try {
        showLoading();

        const response = await fetch(MANIFEST_URL);
        if (!response.ok) {
            throw new Error('Failed to fetch manifest');
        }

        const data = await response.json();
        allFilings = data.filings || [];

        updateStats(data.stats || {});
        populateFilters();
        applyFilters();
        hideLoading();

    } catch (error) {
        console.error('Error loading data:', error);
        showError();
    }
}

// Update header statistics
function updateStats(stats) {
    document.getElementById('total-filings').textContent = stats.total_filings?.toLocaleString() || '0';
    document.getElementById('total-members').textContent = stats.total_members?.toLocaleString() || '0';
    document.getElementById('latest-year').textContent = stats.latest_year || '-';
    document.getElementById('last-updated').textContent = stats.last_updated || '-';
}

// Populate filter dropdowns
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

// Setup event listeners
function setupEventListeners() {
    // Search
    document.getElementById('search').addEventListener('input', debounce(applyFilters, 300));

    // Filters
    document.getElementById('year-filter').addEventListener('change', applyFilters);
    document.getElementById('state-filter').addEventListener('change', applyFilters);
    document.getElementById('type-filter').addEventListener('change', applyFilters);

    // Pagination
    document.getElementById('prev-page').addEventListener('click', () => changePage(-1));
    document.getElementById('next-page').addEventListener('click', () => changePage(1));

    // Export
    document.getElementById('export-csv').addEventListener('click', exportToCSV);

    // Sort
    document.querySelectorAll('th[data-sort]').forEach(th => {
        th.addEventListener('click', () => sortBy(th.dataset.sort));
    });
}

// Apply filters
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

// Sort filings
function sortFilings() {
    filteredFilings.sort((a, b) => {
        let aVal = a[sortColumn];
        let bVal = b[sortColumn];

        // Handle nulls
        if (aVal === null || aVal === undefined) return 1;
        if (bVal === null || bVal === undefined) return -1;

        // Convert to comparable values
        if (sortColumn === 'filing_date') {
            aVal = new Date(aVal);
            bVal = new Date(bVal);
        }

        if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
        return 0;
    });
}

// Sort by column
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

// Render table
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
            <td>
                <strong>${formatName(filing)}</strong>
            </td>
            <td>${filing.state_district || '-'}</td>
            <td>
                <span class="badge badge-type-${(filing.filing_type || 'a').toLowerCase()}">
                    ${getFilingTypeName(filing.filing_type)}
                </span>
            </td>
            <td><code>${filing.doc_id || '-'}</code></td>
            <td>
                <a href="${getPDFUrl(filing)}" target="_blank" rel="noopener" class="btn-link">
                    View PDF
                </a>
            </td>
        `;
        tbody.appendChild(row);
    });

    document.getElementById('showing-count').textContent =
        `Showing ${start + 1}-${Math.min(end, filteredFilings.length)} of ${filteredFilings.length.toLocaleString()} filings`;
}

// Update pagination
function updatePagination() {
    const totalPages = Math.ceil(filteredFilings.length / ITEMS_PER_PAGE);

    document.getElementById('prev-page').disabled = currentPage === 1;
    document.getElementById('next-page').disabled = currentPage === totalPages;
    document.getElementById('page-info').textContent = `Page ${currentPage} of ${totalPages}`;
}

// Change page
function changePage(delta) {
    currentPage += delta;
    renderTable();
    updatePagination();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Export to CSV
function exportToCSV() {
    const headers = ['Year', 'Filing Date', 'First Name', 'Last Name', 'State/District', 'Filing Type', 'Document ID', 'PDF URL'];
    const rows = filteredFilings.map(f => [
        f.year,
        f.filing_date,
        f.first_name,
        f.last_name,
        f.state_district,
        f.filing_type,
        f.doc_id,
        getPDFUrl(f)
    ]);

    const csv = [headers, ...rows]
        .map(row => row.map(cell => `"${cell || ''}"`).join(','))
        .join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `congress-disclosures-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
}

// Helper functions
function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
        return new Date(dateStr).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    } catch {
        return dateStr;
    }
}

function formatName(filing) {
    const parts = [filing.prefix, filing.first_name, filing.last_name, filing.suffix]
        .filter(Boolean);
    return parts.join(' ') || 'Unknown';
}

function getFilingTypeName(type) {
    const types = {
        'A': 'Annual',
        'N': 'New Member',
        'T': 'Termination',
        'P': 'Periodic'
    };
    return types[type] || type || 'Unknown';
}

function getPDFUrl(filing) {
    return `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com/bronze/house/financial/year=${filing.year}/pdfs/${filing.year}/${filing.doc_id}.pdf`;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
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

function showError() {
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('error').classList.remove('hidden');
}
