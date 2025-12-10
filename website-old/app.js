// S3 Configuration
const S3_BUCKET = "congress-disclosures-standardized";
const S3_REGION = "us-east-1";
const API_BASE = `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com/website/api/v1`;

// API Endpoints
const MANIFEST_URL = `${API_BASE}/documents/manifest.json`;
const PTR_TRANSACTIONS_URL = `${API_BASE}/schedules/b/transactions.json`;
// Silver documents API endpoint (falls back to data file if API unavailable)
const SILVER_DOCUMENTS_API_URL = `${API_BASE}/documents/silver/manifest.json`;
const SILVER_DOCUMENTS_FALLBACK_URL = `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com/website/data/silver_documents_v2.json`;
const ITEMS_PER_PAGE = 50;

// State - Bronze Layer
let allFilings = [];
let filteredFilings = [];
let currentPage = 1;
let sortColumn = 'filing_date';
let sortDirection = 'desc';



// State - PTR Transactions
let allPTRTransactions = [];
let filteredPTRTransactions = [];
let ptrCurrentPage = 1;
let ptrSortColumn = 'transaction_date';
let ptrSortDirection = 'desc';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadData();
    loadPTRTransactions();
    setupEventListeners();
    setupTabs();
});

// Load data from S3 (Bronze manifest)
async function loadData() {
    try {
        console.log('Loading Bronze manifest from:', MANIFEST_URL);
        showLoading();

        const response = await fetch(MANIFEST_URL);
        if (!response.ok) {
            // Non-blocking: if manifest doesn't exist, just log and continue
            if (response.status === 403 || response.status === 404) {
                console.warn('Bronze manifest not available (403/404). Continuing without Bronze data.');
                allFilings = [];
                hideLoading();
                return;
            }
            throw new Error(`Failed to fetch manifest: HTTP ${response.status}`);
        }

        const data = await response.json();
        allFilings = data.filings || [];
        console.log('Bronze data loaded:', { total_filings: allFilings.length });

        updateStats(data.stats || {});
        populateFilters();
        applyFilters();
        hideLoading();

    } catch (error) {
        console.error('Error loading Bronze data:', error);
        // Non-blocking: don't show error UI, just log and continue
        allFilings = [];
        hideLoading();
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

    // Calculate Top State
    const stateCounts = {};
    allFilings.forEach(f => {
        if (f.state_district) {
            const state = f.state_district.substring(0, 2);
            stateCounts[state] = (stateCounts[state] || 0) + 1;
        }
    });
    const topState = Object.entries(stateCounts).sort((a, b) => b[1] - a[1])[0];

    // Calculate Top Filer
    const filerCounts = {};
    allFilings.forEach(f => {
        const name = `${f.first_name} ${f.last_name}`;
        filerCounts[name] = (filerCounts[name] || 0) + 1;
    });
    const topFiler = Object.entries(filerCounts).sort((a, b) => b[1] - a[1])[0];

    document.getElementById('bronze-total-filings').textContent = totalFilings.toLocaleString();
    document.getElementById('bronze-total-filers').textContent = uniqueFilers.toLocaleString();
    document.getElementById('bronze-top-state').textContent = topState ? `${topState[0]} (${topState[1]})` : '-';
    document.getElementById('bronze-top-filer').textContent = topFiler ? topFiler[0] : '-';

    // Render Filing Types Chart
    renderFilingTypesChart();
}

function renderFilingTypesChart() {
    const ctx = document.getElementById('bronze-filing-types-chart');
    if (!ctx) return;

    // Calculate counts
    const typeCounts = {
        'Annual': 0,
        'Periodic': 0,
        'New Member': 0,
        'Termination': 0,
        'Other': 0
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

    // Destroy existing chart if any
    if (window.bronzeChart) {
        window.bronzeChart.destroy();
    }

    window.bronzeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(typeCounts),
            datasets: [{
                data: Object.values(typeCounts),
                backgroundColor: [
                    'hsl(217, 91%, 60%)', // Annual - Blue
                    'hsl(48, 96%, 60%)',  // Periodic - Yellow
                    'hsl(142, 76%, 60%)', // New Member - Green
                    'hsl(0, 84%, 60%)',   // Termination - Red
                    'hsl(215, 16%, 60%)'  // Other - Grey
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        boxWidth: 12
                    }
                },
                title: {
                    display: true,
                    text: 'Filing Types Distribution'
                }
            }
        }
    });
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
    // setupSilverEventListeners(); // Removed: Handled by silver_split_view.js

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





// Sort PTR transactions
function sortPTRTransactions() {
    filteredPTRTransactions.sort((a, b) => {
        let aVal = a[ptrSortColumn];
        let bVal = b[ptrSortColumn];

        // Handle nulls
        if (aVal === null || aVal === undefined) return 1;
        if (bVal === null || bVal === undefined) return -1;

        // Special handling for dates and numbers
        if (ptrSortColumn === 'transaction_date') {
            aVal = new Date(aVal);
            bVal = new Date(bVal);
        } else if (ptrSortColumn === 'amount_range') {
            // Simple heuristic for amount ranges (e.g. "$1,001 - $15,000")
            // Extract first number
            const getMinAmount = (str) => {
                const match = str.match(/\$?([\d,]+)/);
                return match ? parseInt(match[1].replace(/,/g, '')) : 0;
            };
            aVal = getMinAmount(aVal);
            bVal = getMinAmount(bVal);
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
        ptrSortDirection = 'desc'; // Default to desc for transactions
    }

    sortPTRTransactions();
    renderPTRTable();
}

// ============================================================================
// PTR TRANSACTIONS FUNCTIONS
// ============================================================================

// Load PTR transactions data from S3
// Load PTR transactions data from S3
async function loadPTRTransactions() {
    console.log('Starting loadPTRTransactions...');
    try {
        showPTRLoading();

        console.log('Fetching PTR data from:', PTR_TRANSACTIONS_URL);
        const response = await fetch(PTR_TRANSACTIONS_URL);
        console.log('PTR fetch status:', response.status);

        if (!response.ok) {
            throw new Error('Failed to fetch PTR transactions');
        }

        const data = await response.json();
        console.log('PTR data received:', data);

        allPTRTransactions = data.transactions || [];
        console.log('Parsed PTR transactions:', allPTRTransactions.length);

        updatePTRStats(data);
        populatePTRFilters();
        applyPTRFilters();
        hidePTRLoading();
        console.log('PTR loading complete, hidden class removed');

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
    console.log('Applying PTR filters...');
    const searchTerm = (document.getElementById('ptr-search')?.value || '').toLowerCase();
    const typeFilter = document.getElementById('ptr-type-filter')?.value || '';

    console.log('Filters:', { searchTerm, typeFilter });

    filteredPTRTransactions = allPTRTransactions.filter(trans => {
        const matchesSearch = !searchTerm ||
            trans.first_name?.toLowerCase().includes(searchTerm) ||
            trans.last_name?.toLowerCase().includes(searchTerm) ||
            trans.asset_name?.toLowerCase().includes(searchTerm) ||
            trans.state_district?.toLowerCase().includes(searchTerm);

        const matchesType = !typeFilter || trans.transaction_type === typeFilter;
        // Simplified for debug
        return matchesSearch && matchesType;
    });

    console.log('Filtered PTR transactions:', filteredPTRTransactions.length);

    sortPTRTransactions();
    ptrCurrentPage = 1;
    renderPTRTable();
    updatePTRPagination();
}

// Render PTR table
function renderPTRTable() {
    console.log('Rendering PTR table...');
    const tbody = document.getElementById('ptr-table-body');
    if (!tbody) {
        console.error('PTR table body not found!');
        return;
    }

    tbody.innerHTML = '';

    const start = (ptrCurrentPage - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;
    const pageTransactions = filteredPTRTransactions.slice(start, end);

    console.log('Rendering rows:', pageTransactions.length);

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
                <a href="${trans.pdf_url || '#'}"
                   target="_blank" rel="noopener" class="btn-link">
                    View PDF
                </a>
            </td>
        `;
        tbody.appendChild(row);
    });
    console.log('PTR table rendered.');

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


