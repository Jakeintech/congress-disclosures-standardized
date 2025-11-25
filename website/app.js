// Configuration
const S3_BUCKET = 'congress-disclosures-standardized';
const S3_REGION = 'us-east-1';
const MANIFEST_URL = `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com/manifest.json`;
const SILVER_DOCUMENTS_URL = `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com/silver_documents.json`;
const PTR_TRANSACTIONS_URL = `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com/ptr_transactions.json`;
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

// State - PTR Transactions
let allPTRTransactions = [];
let filteredPTRTransactions = [];
let ptrCurrentPage = 1;
let ptrSortColumn = 'transaction_date';
let ptrSortDirection = 'desc';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadData();
    loadSilverData();
    loadPTRTransactions();
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

    // Update Bronze tab stats
    updateBronzeStats();
}

// Update Bronze layer stats
function updateBronzeStats() {
    const totalFilings = allFilings.length;
    const uniqueFilers = new Set(allFilings.map(f => `${f.first_name} ${f.last_name}`)).size;
    const ptrFilings = allFilings.filter(f => f.filing_type === 'P').length;
    const latestYear = Math.max(...allFilings.map(f => f.year || 0));

    document.getElementById('bronze-total-filings').textContent = totalFilings.toLocaleString();
    document.getElementById('bronze-total-filers').textContent = uniqueFilers.toLocaleString();
    document.getElementById('bronze-ptrs').textContent = ptrFilings.toLocaleString();
    document.getElementById('bronze-latest-year').textContent = latestYear || '-';
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

    // PTR transactions event listeners
    setupPTREventListeners();
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
        console.log('Loading silver data from:', SILVER_DOCUMENTS_URL);
        showSilverLoading();

        const response = await fetch(SILVER_DOCUMENTS_URL);
        console.log('Silver data response status:', response.status);

        if (!response.ok) {
            throw new Error(`Failed to fetch silver documents: HTTP ${response.status}`);
        }

        const data = await response.json();
        console.log('Silver data loaded:', {
            total_documents: data?.stats?.total_documents,
            extraction_stats: data?.stats?.extraction_stats,
            documents_count: data.documents?.length
        });

        allSilverDocuments = data.documents || [];

        updateSilverStats(data);
        populateSilverFilters();
        applySilverFilters();
        hideSilverLoading();

        console.log('Silver data initialization complete');

    } catch (error) {
        console.error('Error loading silver data:', error);
        console.error('Error stack:', error.stack);
        showSilverError();
    }
}

// Update silver layer statistics
function updateSilverStats(data) {
    try {
        console.log('Updating silver stats with data:', data);

        const stats = data.stats || {};
        const totalDocsNum = stats.total_documents || (allSilverDocuments?.length || 0);
        const totalDocs = totalDocsNum.toLocaleString();
        const successDocs = (stats.extraction_stats?.success || 0).toLocaleString();
        const pendingDocs = (stats.extraction_stats?.pending || 0).toLocaleString();
        const totalPagesNum = stats.total_pages || allSilverDocuments.reduce((sum, doc) => sum + (doc.pages || 0), 0);

        document.getElementById('silver-total-docs').textContent = totalDocs;
        document.getElementById('silver-success').textContent = successDocs;
        document.getElementById('silver-pending').textContent = pendingDocs;
        document.getElementById('silver-total-pages').textContent = totalPagesNum.toLocaleString();

        console.log('Silver stats updated:', { totalDocs, successDocs, pendingDocs, totalPages: totalPagesNum });
    } catch (error) {
        console.error('Error updating silver stats:', error);
        throw error;
    }
}

// Populate silver filter dropdowns
function populateSilverFilters() {
    // Years
    const years = [...new Set(allSilverDocuments.map(d => d.year))].filter(Boolean).sort((a, b) => b - a);
    const yearFilter = document.getElementById('silver-year-filter');
    if (yearFilter) {
        yearFilter.length = 1; // keep 'All Years'
        years.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            yearFilter.appendChild(option);
        });
    }

    // Methods (dynamic)
    const methods = [...new Set(allSilverDocuments.map(d => d.extraction_method))].filter(Boolean).sort();
    const methodFilter = document.getElementById('silver-method-filter');
    if (methodFilter) {
        methodFilter.innerHTML = '';
        const allOpt = document.createElement('option');
        allOpt.value = '';
        allOpt.textContent = 'All Extraction Methods';
        methodFilter.appendChild(allOpt);
        methods.forEach(m => {
            const option = document.createElement('option');
            option.value = m;
            option.textContent = m;
            methodFilter.appendChild(option);
        });
    }
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
        const textUrl = doc.text_s3_key ? `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com/${doc.text_s3_key}` : null;
        const jsonUrl = doc.json_s3_key ? `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com/${doc.json_s3_key}` : null;
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
                <a href="https://disclosures-clerk.house.gov/public_disc/financial-pdfs/${doc.year}/${doc.doc_id}.pdf" target="_blank" rel="noopener" class="btn-link">PDF</a>
                ${textUrl ? ` | <a href="${textUrl}" target="_blank" rel="noopener" class="btn-link">Text</a>` : ''}
                ${jsonUrl ? ` | <a href="${jsonUrl}" target="_blank" rel="noopener" class="btn-link">JSON</a>` : ''}
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

// ============================================================================
// PTR TRANSACTIONS FUNCTIONS
// ============================================================================

// Load PTR transactions data from S3
async function loadPTRTransactions() {
    try {
        showPTRLoading();

        const response = await fetch(PTR_TRANSACTIONS_URL);
        if (!response.ok) {
            throw new Error('Failed to fetch PTR transactions');
        }

        const data = await response.json();
        allPTRTransactions = data.transactions || [];

        updatePTRStats(data);
        populatePTRFilters();
        applyPTRFilters();
        hidePTRLoading();

    } catch (error) {
        console.error('Error loading PTR transactions:', error);
        showPTRError();
    }
}

// Update PTR statistics
function updatePTRStats(data) {
    document.getElementById('ptr-total-trans').textContent = data.total_transactions?.toLocaleString() || '0';
    document.getElementById('ptr-total-ptrs').textContent = data.total_ptrs?.toLocaleString() || '0';
    document.getElementById('ptr-latest-date').textContent = data.latest_date ? formatDate(data.latest_date) : '-';

    // Calculate average confidence
    const avgConf = allPTRTransactions.reduce((sum, t) => sum + (t.extraction_confidence || 0), 0) / allPTRTransactions.length;
    document.getElementById('ptr-avg-confidence').textContent = avgConf ? `${(avgConf * 100).toFixed(1)}%` : '-';
}

// Populate PTR filter dropdowns
function populatePTRFilters() {
    // Transaction types
    const types = [...new Set(allPTRTransactions.map(t => t.transaction_type))].filter(Boolean).sort();
    const typeFilter = document.getElementById('ptr-type-filter');
    types.forEach(type => {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = type;
        typeFilter.appendChild(option);
    });

    // Amount ranges
    const amounts = [...new Set(allPTRTransactions.map(t => t.amount_range))].filter(Boolean);
    const amountFilter = document.getElementById('ptr-amount-filter');
    // Sort by numeric value
    const sortedAmounts = amounts.sort((a, b) => {
        const aNum = parseInt(a.replace(/[^0-9]/g, ''));
        const bNum = parseInt(b.replace(/[^0-9]/g, ''));
        return aNum - bNum;
    });
    sortedAmounts.forEach(amount => {
        const option = document.createElement('option');
        option.value = amount;
        option.textContent = amount;
        amountFilter.appendChild(option);
    });

    // Owner codes
    const owners = [...new Set(allPTRTransactions.map(t => t.owner_code))].filter(Boolean).sort();
    const ownerFilter = document.getElementById('ptr-owner-filter');
    owners.forEach(owner => {
        const option = document.createElement('option');
        option.value = owner;
        option.textContent = getOwnerName(owner);
        ownerFilter.appendChild(option);
    });
}

// Setup PTR event listeners
function setupPTREventListeners() {
    // Search
    const searchEl = document.getElementById('ptr-search');
    if (searchEl) {
        searchEl.addEventListener('input', debounce(applyPTRFilters, 300));
    }

    // Filters
    const typeFilter = document.getElementById('ptr-type-filter');
    if (typeFilter) typeFilter.addEventListener('change', applyPTRFilters);

    const amountFilter = document.getElementById('ptr-amount-filter');
    if (amountFilter) amountFilter.addEventListener('change', applyPTRFilters);

    const ownerFilter = document.getElementById('ptr-owner-filter');
    if (ownerFilter) ownerFilter.addEventListener('change', applyPTRFilters);

    // Pagination
    const prevBtn = document.getElementById('ptr-prev-page');
    if (prevBtn) prevBtn.addEventListener('click', () => changePTRPage(-1));

    const nextBtn = document.getElementById('ptr-next-page');
    if (nextBtn) nextBtn.addEventListener('click', () => changePTRPage(1));

    // Sort
    document.querySelectorAll('#ptr-data-section th[data-sort]').forEach(th => {
        th.addEventListener('click', () => sortPTRBy(th.dataset.sort));
    });
}

// Apply PTR filters
function applyPTRFilters() {
    const searchTerm = (document.getElementById('ptr-search')?.value || '').toLowerCase();
    const typeFilter = document.getElementById('ptr-type-filter')?.value || '';
    const amountFilter = document.getElementById('ptr-amount-filter')?.value || '';
    const ownerFilter = document.getElementById('ptr-owner-filter')?.value || '';

    filteredPTRTransactions = allPTRTransactions.filter(trans => {
        const matchesSearch = !searchTerm ||
            trans.first_name?.toLowerCase().includes(searchTerm) ||
            trans.last_name?.toLowerCase().includes(searchTerm) ||
            trans.asset_name?.toLowerCase().includes(searchTerm) ||
            trans.state_district?.toLowerCase().includes(searchTerm);

        const matchesType = !typeFilter || trans.transaction_type === typeFilter;
        const matchesAmount = !amountFilter || trans.amount_range === amountFilter;
        const matchesOwner = !ownerFilter || trans.owner_code === ownerFilter;

        return matchesSearch && matchesType && matchesAmount && matchesOwner;
    });

    sortPTRTransactions();
    ptrCurrentPage = 1;
    renderPTRTable();
    updatePTRPagination();
}

// Sort PTR transactions
function sortPTRTransactions() {
    filteredPTRTransactions.sort((a, b) => {
        let aVal = a[ptrSortColumn];
        let bVal = b[ptrSortColumn];

        // Handle nulls
        if (aVal === null || aVal === undefined) return 1;
        if (bVal === null || bVal === undefined) return -1;

        // Convert dates
        if (ptrSortColumn === 'transaction_date' || ptrSortColumn === 'filing_date') {
            aVal = new Date(aVal);
            bVal = new Date(bVal);
        }

        // Convert amounts
        if (ptrSortColumn === 'amount_low') {
            aVal = parseFloat(aVal) || 0;
            bVal = parseFloat(bVal) || 0;
        }

        if (aVal < bVal) return ptrSortDirection === 'asc' ? -1 : 1;
        if (aVal > bVal) return ptrSortDirection === 'asc' ? 1 : -1;
        return 0;
    });
}

// Sort PTR by column
function sortPTRBy(column) {
    if (ptrSortColumn === column) {
        ptrSortDirection = ptrSortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        ptrSortColumn = column;
        ptrSortDirection = column === 'transaction_date' ? 'desc' : 'asc';
    }

    sortPTRTransactions();
    renderPTRTable();
}

// Render PTR table
function renderPTRTable() {
    const tbody = document.getElementById('ptr-table-body');
    if (!tbody) return;

    tbody.innerHTML = '';

    const start = (ptrCurrentPage - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;
    const pageTransactions = filteredPTRTransactions.slice(start, end);

    pageTransactions.forEach(trans => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${formatDate(trans.transaction_date)}</td>
            <td>
                <strong>${trans.first_name} ${trans.last_name}</strong>
            </td>
            <td>${trans.state_district || '-'}</td>
            <td>${trans.asset_name || '-'}</td>
            <td>
                <span class="badge badge-${getTransactionTypeClass(trans.transaction_type)}">
                    ${trans.transaction_type || '-'}
                </span>
            </td>
            <td>${trans.amount_range || '-'}</td>
            <td>${getOwnerName(trans.owner_code)}</td>
            <td>
                <a href="${trans.pdf_url || getPDFUrl({ year: trans.year, doc_id: trans.doc_id })}"
                   target="_blank" rel="noopener" class="btn-link">
                    View PDF
                </a>
            </td>
        `;
        tbody.appendChild(row);
    });

    const showingEl = document.getElementById('ptr-showing-count');
    if (showingEl) {
        showingEl.textContent =
            `Showing ${start + 1}-${Math.min(end, filteredPTRTransactions.length)} of ${filteredPTRTransactions.length.toLocaleString()} transactions`;
    }
}

// Update PTR pagination
function updatePTRPagination() {
    const totalPages = Math.ceil(filteredPTRTransactions.length / ITEMS_PER_PAGE);

    const prevBtn = document.getElementById('ptr-prev-page');
    const nextBtn = document.getElementById('ptr-next-page');
    const pageInfo = document.getElementById('ptr-page-info');

    if (prevBtn) prevBtn.disabled = ptrCurrentPage === 1;
    if (nextBtn) nextBtn.disabled = ptrCurrentPage === totalPages || totalPages === 0;
    if (pageInfo) pageInfo.textContent = `Page ${ptrCurrentPage} of ${totalPages || 1}`;
}

// Change PTR page
function changePTRPage(delta) {
    ptrCurrentPage += delta;
    renderPTRTable();
    updatePTRPagination();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Helper: Get transaction type CSS class
function getTransactionTypeClass(type) {
    if (!type) return 'unknown';
    const lower = type.toLowerCase();
    if (lower.includes('purchase')) return 'p';
    if (lower.includes('sale')) return 'a';
    return 'unknown';
}

// Helper: Get owner name
function getOwnerName(code) {
    const codes = {
        'SP': 'Spouse',
        'DC': 'Dependent Child',
        'JT': 'Joint',
    };
    return codes[code] || code || 'Filer';
}

function showPTRLoading() {
    const loading = document.getElementById('ptr-loading');
    const dataSection = document.getElementById('ptr-data-section');
    const error = document.getElementById('ptr-error');

    if (loading) loading.classList.remove('hidden');
    if (dataSection) dataSection.classList.add('hidden');
    if (error) error.classList.add('hidden');
}

function hidePTRLoading() {
    const loading = document.getElementById('ptr-loading');
    const dataSection = document.getElementById('ptr-data-section');

    if (loading) loading.classList.add('hidden');
    if (dataSection) dataSection.classList.remove('hidden');
}

function showPTRError() {
    const loading = document.getElementById('ptr-loading');
    const error = document.getElementById('ptr-error');

    if (loading) loading.classList.add('hidden');
    if (error) error.classList.remove('hidden');
}
