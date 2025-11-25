// Configuration
const S3_BUCKET = 'congress-disclosures-standardized';
const S3_REGION = 'us-east-1';
const MANIFEST_URL = `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com/manifest.json`;
const SILVER_DOCUMENTS_URL = `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com/silver_documents.json`;
const ITEMS_PER_PAGE = 50;

// State - Bronze Layer
let allFilings = [];
let filteredFilings = [];
let currentPage = 1;
let sortColumn = 'filing_date';
let sortDirection = 'desc';

// State - Silver Layer
let allSilverDocuments = [];
let filteredSilverDocuments = [];
let silverCurrentPage = 1;
let silverSortColumn = 'doc_id';
let silverSortDirection = 'asc';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadData();
    loadSilverData();
    setupEventListeners();
    setupTabs();
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
    // Bronze layer event listeners
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

    // Silver layer event listeners
    setupSilverEventListeners();
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
    // Link directly to official House website (more reliable than storing copies)
    return `https://disclosures-clerk.house.gov/public_disc/financial-pdfs/${filing.year}/${filing.doc_id}.pdf`;
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

// Tab Management
function setupTabs() {
    const tabTriggers = document.querySelectorAll('.tab-trigger');
    const tabContents = document.querySelectorAll('.tab-content');

    tabTriggers.forEach(trigger => {
        trigger.addEventListener('click', () => {
            const targetTab = trigger.dataset.tab;

            // Remove active from all triggers and contents
            tabTriggers.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            // Add active to clicked trigger and corresponding content
            trigger.classList.add('active');
            const targetContent = document.querySelector(`.tab-content[data-tab="${targetTab}"]`);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        });
    });
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

// ============================================================================
// SILVER LAYER FUNCTIONS
// ============================================================================

// Load silver documents data from S3
async function loadSilverData() {
    try {
        showSilverLoading();

        const response = await fetch(SILVER_DOCUMENTS_URL);
        if (!response.ok) {
            throw new Error('Failed to fetch silver documents');
        }

        const data = await response.json();
        allSilverDocuments = data.documents || [];

        updateSilverStats(data.stats || {});
        populateSilverFilters();
        applySilverFilters();
        hideSilverLoading();

    } catch (error) {
        console.error('Error loading silver data:', error);
        showSilverError();
    }
}

// Update silver layer statistics
function updateSilverStats(stats) {
    document.getElementById('silver-total-docs').textContent = stats.total_documents?.toLocaleString() || '0';
    document.getElementById('silver-success').textContent = stats.extraction_stats?.success?.toLocaleString() || '0';
    document.getElementById('silver-pending').textContent = stats.extraction_stats?.pending?.toLocaleString() || '0';
    document.getElementById('silver-total-pages').textContent = stats.total_pages?.toLocaleString() || '0';
}

// Populate silver filter dropdowns
function populateSilverFilters() {
    const years = [...new Set(allSilverDocuments.map(d => d.year))].sort((a, b) => b - a);

    const yearFilter = document.getElementById('silver-year-filter');
    years.forEach(year => {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        yearFilter.appendChild(option);
    });
}

// Setup silver event listeners
function setupSilverEventListeners() {
    // Search
    document.getElementById('silver-search').addEventListener('input', debounce(applySilverFilters, 300));

    // Filters
    document.getElementById('silver-year-filter').addEventListener('change', applySilverFilters);
    document.getElementById('silver-status-filter').addEventListener('change', applySilverFilters);
    document.getElementById('silver-method-filter').addEventListener('change', applySilverFilters);

    // Pagination
    document.getElementById('silver-prev-page').addEventListener('click', () => changeSilverPage(-1));
    document.getElementById('silver-next-page').addEventListener('click', () => changeSilverPage(1));

    // Export
    document.getElementById('silver-export-csv').addEventListener('click', exportSilverToCSV);

    // Sort
    document.querySelectorAll('#silver-data-section th[data-sort]').forEach(th => {
        th.addEventListener('click', () => sortSilverBy(th.dataset.sort));
    });
}

// Apply silver filters
function applySilverFilters() {
    const searchTerm = document.getElementById('silver-search').value.toLowerCase();
    const yearFilter = document.getElementById('silver-year-filter').value;
    const statusFilter = document.getElementById('silver-status-filter').value;
    const methodFilter = document.getElementById('silver-method-filter').value;

    filteredSilverDocuments = allSilverDocuments.filter(doc => {
        const matchesSearch = !searchTerm ||
            doc.doc_id?.toLowerCase().includes(searchTerm);

        const matchesYear = !yearFilter || doc.year == yearFilter;
        const matchesStatus = !statusFilter || doc.extraction_status === statusFilter;
        const matchesMethod = !methodFilter || doc.extraction_method === methodFilter;

        return matchesSearch && matchesYear && matchesStatus && matchesMethod;
    });

    sortSilverDocuments();
    silverCurrentPage = 1;
    renderSilverTable();
    updateSilverPagination();
}

// Sort silver documents
function sortSilverDocuments() {
    filteredSilverDocuments.sort((a, b) => {
        let aVal = a[silverSortColumn];
        let bVal = b[silverSortColumn];

        // Handle nulls
        if (aVal === null || aVal === undefined) return 1;
        if (bVal === null || bVal === undefined) return -1;

        if (aVal < bVal) return silverSortDirection === 'asc' ? -1 : 1;
        if (aVal > bVal) return silverSortDirection === 'asc' ? 1 : -1;
        return 0;
    });
}

// Sort silver by column
function sortSilverBy(column) {
    if (silverSortColumn === column) {
        silverSortDirection = silverSortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        silverSortColumn = column;
        silverSortDirection = 'asc';
    }

    sortSilverDocuments();
    renderSilverTable();
}

// Render silver table
function renderSilverTable() {
    const tbody = document.getElementById('silver-table-body');
    tbody.innerHTML = '';

    const start = (silverCurrentPage - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;
    const pageDocuments = filteredSilverDocuments.slice(start, end);

    pageDocuments.forEach(doc => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><code>${doc.doc_id || '-'}</code></td>
            <td>${doc.year || '-'}</td>
            <td>
                <span class="badge badge-status-${(doc.extraction_status || 'unknown').toLowerCase()}">
                    ${doc.extraction_status || 'Unknown'}
                </span>
            </td>
            <td>${doc.extraction_method || '-'}</td>
            <td>${doc.pages || 0}</td>
            <td>${(doc.char_count || 0).toLocaleString()}</td>
            <td>${formatFileSize(doc.pdf_file_size_bytes)}</td>
            <td>
                <a href="https://disclosures-clerk.house.gov/public_disc/financial-pdfs/${doc.year}/${doc.doc_id}.pdf"
                   target="_blank" rel="noopener" class="btn-link">
                    View PDF
                </a>
            </td>
        `;
        tbody.appendChild(row);
    });

    document.getElementById('silver-showing-count').textContent =
        `Showing ${start + 1}-${Math.min(end, filteredSilverDocuments.length)} of ${filteredSilverDocuments.length.toLocaleString()} documents`;
}

// Update silver pagination
function updateSilverPagination() {
    const totalPages = Math.ceil(filteredSilverDocuments.length / ITEMS_PER_PAGE);

    document.getElementById('silver-prev-page').disabled = silverCurrentPage === 1;
    document.getElementById('silver-next-page').disabled = silverCurrentPage === totalPages;
    document.getElementById('silver-page-info').textContent = `Page ${silverCurrentPage} of ${totalPages}`;
}

// Change silver page
function changeSilverPage(delta) {
    silverCurrentPage += delta;
    renderSilverTable();
    updateSilverPagination();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Export silver to CSV
function exportSilverToCSV() {
    const headers = ['Document ID', 'Year', 'Status', 'Method', 'Pages', 'Characters', 'File Size (bytes)', 'PDF URL'];
    const rows = filteredSilverDocuments.map(d => [
        d.doc_id,
        d.year,
        d.extraction_status,
        d.extraction_method,
        d.pages,
        d.char_count,
        d.pdf_file_size_bytes,
        `https://disclosures-clerk.house.gov/public_disc/financial-pdfs/${d.year}/${d.doc_id}.pdf`
    ]);

    const csv = [headers, ...rows]
        .map(row => row.map(cell => `"${cell || ''}"`).join(','))
        .join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `congress-disclosures-silver-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
}

// Helper function to format file size
function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '-';
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    const mb = kb / 1024;
    return `${mb.toFixed(1)} MB`;
}

function showSilverLoading() {
    document.getElementById('silver-loading').classList.remove('hidden');
    document.getElementById('silver-data-section').classList.add('hidden');
    document.getElementById('silver-error').classList.add('hidden');
}

function hideSilverLoading() {
    document.getElementById('silver-loading').classList.add('hidden');
    document.getElementById('silver-data-section').classList.remove('hidden');
}

function showSilverError() {
    document.getElementById('silver-loading').classList.add('hidden');
    document.getElementById('silver-error').classList.remove('hidden');
}
