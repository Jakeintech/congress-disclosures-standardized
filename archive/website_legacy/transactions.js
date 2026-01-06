/**
 * Transactions Logic (transactions.html)
 * Handles PTR (Periodic Transaction Report) data.
 * Uses API Gateway endpoints for live data.
 */

// API Gateway URL (from config.js or fallback)
const TRANSACTIONS_API_BASE = window.API_GATEWAY_URL || window.CONFIG?.API_GATEWAY_URL || 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com';

let allPTRTransactions = [];
let filteredPTRTransactions = [];
let ptrCurrentPage = 1;
let ptrSortColumn = 'transaction_date';
let ptrSortDirection = 'desc';

// Items per page - may be defined in config.js or default to 50
const ITEMS_PER_PAGE = window.ITEMS_PER_PAGE || 50;

document.addEventListener('DOMContentLoaded', () => {
    loadPTRTransactions();
    setupPTREventListeners();
});

async function loadPTRTransactions() {
    try {
        showPTRLoading();
        console.log('Fetching PTR data from API Gateway...');

        const response = await fetch(`${TRANSACTIONS_API_BASE}/v1/trades?limit=1000`);
        if (!response.ok) throw new Error('Failed to fetch PTR transactions');

        const result = await response.json();
        // API returns { success: true, data: [...] } OR { success: true, data: { trades: [...] } }
        const data = result.data || result;
        if (Array.isArray(data)) {
            allPTRTransactions = data;
        } else {
            allPTRTransactions = data.trades || data.transactions || [];
        }

        // Transform API response to expected format
        allPTRTransactions = allPTRTransactions.map(t => ({
            transaction_date: t.transaction_date,
            first_name: t.first_name || '',
            last_name: t.last_name || '',
            state_district: t.state || '',
            asset_name: t.ticker || t.asset_name || '',
            transaction_type: t.transaction_type || '',
            amount_range: t.amount || t.amount_range || '',
            owner_code: t.owner || '',
            pdf_url: t.pdf_url || '',
            extraction_confidence: t.confidence || 1.0
        }));

        updatePTRStats({
            total_transactions: allPTRTransactions.length,
            total_ptrs: new Set(allPTRTransactions.map(t => t.first_name + t.last_name)).size,
            latest_date: allPTRTransactions.length > 0 ?
                allPTRTransactions.reduce((max, t) => t.transaction_date > max ? t.transaction_date : max, '') : null
        });
        populatePTRFilters();
        applyPTRFilters();
        hidePTRLoading();

    } catch (error) {
        console.error('Error loading PTR transactions:', error);
        showPTRError();
    }
}

function updatePTRStats(data) {
    setText('ptr-total-trans', data.total_transactions?.toLocaleString() || '0');
    setText('ptr-total-ptrs', data.total_ptrs?.toLocaleString() || '0');
    setText('ptr-latest-date', data.latest_date ? formatDate(data.latest_date) : '-');

    const avgConf = allPTRTransactions.reduce((sum, t) => sum + (t.extraction_confidence || 0), 0) / allPTRTransactions.length;
    setText('ptr-avg-confidence', avgConf ? `${(avgConf * 100).toFixed(1)}%` : '-');
}

function populatePTRFilters() {
    const types = [...new Set(allPTRTransactions.map(t => t.transaction_type))].filter(Boolean).sort();
    const typeFilter = document.getElementById('ptr-type-filter');
    types.forEach(type => {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = type;
        typeFilter.appendChild(option);
    });

    const amounts = [...new Set(allPTRTransactions.map(t => t.amount_range))].filter(Boolean);
    const amountFilter = document.getElementById('ptr-amount-filter');
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

    const owners = [...new Set(allPTRTransactions.map(t => t.owner_code))].filter(Boolean).sort();
    const ownerFilter = document.getElementById('ptr-owner-filter');
    owners.forEach(owner => {
        const option = document.createElement('option');
        option.value = owner;
        option.textContent = getOwnerName(owner);
        ownerFilter.appendChild(option);
    });
}

function setupPTREventListeners() {
    document.getElementById('ptr-search').addEventListener('input', debounce(applyPTRFilters, 300));
    document.getElementById('ptr-type-filter').addEventListener('change', applyPTRFilters);
    document.getElementById('ptr-amount-filter').addEventListener('change', applyPTRFilters);
    document.getElementById('ptr-owner-filter').addEventListener('change', applyPTRFilters);
    document.getElementById('ptr-prev-page').addEventListener('click', () => changePTRPage(-1));
    document.getElementById('ptr-next-page').addEventListener('click', () => changePTRPage(1));
    document.getElementById('ptr-export-csv').addEventListener('click', exportPTRCSV);

    document.querySelectorAll('th[data-sort]').forEach(th => {
        th.addEventListener('click', () => sortPTRBy(th.dataset.sort));
    });
}

function applyPTRFilters() {
    const searchTerm = document.getElementById('ptr-search').value.toLowerCase();
    const typeFilter = document.getElementById('ptr-type-filter').value;
    const amountFilter = document.getElementById('ptr-amount-filter').value;
    const ownerFilter = document.getElementById('ptr-owner-filter').value;

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

function sortPTRTransactions() {
    filteredPTRTransactions.sort((a, b) => {
        let aVal = a[ptrSortColumn];
        let bVal = b[ptrSortColumn];

        if (aVal === null || aVal === undefined) return 1;
        if (bVal === null || bVal === undefined) return -1;

        if (ptrSortColumn === 'transaction_date') {
            aVal = new Date(aVal);
            bVal = new Date(bVal);
        } else if (ptrSortColumn === 'amount_range') {
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

function sortPTRBy(column) {
    if (ptrSortColumn === column) {
        ptrSortDirection = ptrSortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        ptrSortColumn = column;
        ptrSortDirection = 'desc';
    }
    sortPTRTransactions();
    renderPTRTable();
}

function renderPTRTable() {
    const tbody = document.getElementById('ptr-table-body');
    tbody.innerHTML = '';

    const start = (ptrCurrentPage - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;
    const pageTransactions = filteredPTRTransactions.slice(start, end);

    pageTransactions.forEach(trans => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${formatDate(trans.transaction_date)}</td>
            <td><strong>${trans.first_name} ${trans.last_name}</strong></td>
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
                <a href="${trans.pdf_url || '#'}" target="_blank" rel="noopener" class="btn-link">View PDF</a>
            </td>
        `;
        tbody.appendChild(row);
    });

    setText('ptr-showing-count', `Showing ${start + 1}-${Math.min(end, filteredPTRTransactions.length)} of ${filteredPTRTransactions.length.toLocaleString()} transactions`);
}

function updatePTRPagination() {
    const totalPages = Math.ceil(filteredPTRTransactions.length / ITEMS_PER_PAGE);
    document.getElementById('ptr-prev-page').disabled = ptrCurrentPage === 1;
    document.getElementById('ptr-next-page').disabled = ptrCurrentPage === totalPages || totalPages === 0;
    setText('ptr-page-info', `Page ${ptrCurrentPage} of ${totalPages || 1}`);
}

function changePTRPage(delta) {
    ptrCurrentPage += delta;
    renderPTRTable();
    updatePTRPagination();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function exportPTRCSV() {
    const headers = ['Date', 'First Name', 'Last Name', 'State', 'Asset', 'Type', 'Amount', 'Owner', 'PDF URL'];
    const rows = filteredPTRTransactions.map(t => [
        t.transaction_date, t.first_name, t.last_name, t.state_district, t.asset_name, t.transaction_type, t.amount_range, t.owner_code, t.pdf_url
    ]);

    const csv = [headers, ...rows].map(row => row.map(cell => `"${cell || ''}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ptr-transactions-${new Date().toISOString().split('T')[0]}.csv`;
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

function getTransactionTypeClass(type) {
    if (!type) return 'unknown';
    const lower = type.toLowerCase();
    if (lower.includes('purchase')) return 'p';
    if (lower.includes('sale')) return 'a';
    return 'unknown';
}

function getOwnerName(code) {
    const codes = { 'SP': 'Spouse', 'DC': 'Dependent Child', 'JT': 'Joint' };
    return codes[code] || code || 'Filer';
}

function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

function showPTRLoading() {
    document.getElementById('ptr-loading').classList.remove('hidden');
    document.getElementById('ptr-data-section').classList.add('hidden');
    document.getElementById('ptr-error').classList.add('hidden');
}

function hidePTRLoading() {
    document.getElementById('ptr-loading').classList.add('hidden');
    document.getElementById('ptr-data-section').classList.remove('hidden');
}

function showPTRError() {
    document.getElementById('ptr-loading').classList.add('hidden');
    document.getElementById('ptr-error').classList.remove('hidden');
}
