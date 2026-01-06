/**
 * Document Quality Logic (quality.html)
 * Loads and displays document quality metrics.
 * Uses API Gateway endpoints for live data.
 */

// API Gateway URL (from config.js or fallback)
const QUALITY_API_BASE = window.API_GATEWAY_URL || window.CONFIG?.API_GATEWAY_URL || 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com';

let qualityData = [];
let filteredQualityData = [];
const QUALITY_PAGE_SIZE = 50;
let currentQualityPage = 1;

document.addEventListener('DOMContentLoaded', () => {
    initDocumentQuality();
});

async function initDocumentQuality() {
    console.log('Initializing Document Quality...');
    try {
        const response = await fetch(`${QUALITY_API_BASE}/v1/analytics/compliance`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const result = await response.json();
        // API returns { success: true, data: { members: [...], ... } }
        const data = result.data || result;
        qualityData = data.members || [];
        filteredQualityData = [...qualityData];

        updateQualityStats(data);
        setupQualityEventListeners();
        renderQualityTable();

        document.getElementById('quality-loading').classList.add('hidden');
        document.getElementById('quality-data-section').classList.remove('hidden');

    } catch (error) {
        console.error('Error loading document quality data:', error);
        document.getElementById('quality-loading').classList.add('hidden');
        document.getElementById('quality-error').classList.remove('hidden');
    }
}

function updateQualityStats(data) {
    document.getElementById('quality-total-members').textContent = data.total_members || 0;
    document.getElementById('quality-flagged').textContent = data.flagged_members_count || 0;
    document.getElementById('quality-avg-score').textContent = data.average_quality_score ? data.average_quality_score.toFixed(1) : '-';

    const filerNote = document.getElementById('quality-total-filers-note');
    if (filerNote) filerNote.textContent = `${data.total_members || 0} total filers`;

    if (data.generated_at) {
        const date = new Date(data.generated_at);
        document.getElementById('quality-updated').textContent = date.toLocaleDateString();
    }
}

function setupQualityEventListeners() {
    document.getElementById('quality-search').addEventListener('input', filterQualityData);
    document.getElementById('quality-party-filter').addEventListener('change', filterQualityData);
    document.getElementById('quality-category-filter').addEventListener('change', filterQualityData);
    document.getElementById('quality-flagged-filter').addEventListener('change', filterQualityData);

    document.getElementById('quality-prev-page').addEventListener('click', () => {
        if (currentQualityPage > 1) {
            currentQualityPage--;
            renderQualityTable();
        }
    });

    document.getElementById('quality-next-page').addEventListener('click', () => {
        const totalPages = Math.ceil(filteredQualityData.length / QUALITY_PAGE_SIZE);
        if (currentQualityPage < totalPages) {
            currentQualityPage++;
            renderQualityTable();
        }
    });

    document.getElementById('quality-export-csv').addEventListener('click', exportQualityCSV);

    document.querySelectorAll('#quality-data-section th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            sortQualityData(th.dataset.sort);
        });
    });
}

function filterQualityData() {
    const search = document.getElementById('quality-search').value.toLowerCase();
    const party = document.getElementById('quality-party-filter').value;
    const category = document.getElementById('quality-category-filter').value;
    const flagged = document.getElementById('quality-flagged-filter').value;

    filteredQualityData = qualityData.filter(member => {
        if (search) {
            const searchText = `${member.full_name} ${member.party} ${member.state_district}`.toLowerCase();
            if (!searchText.includes(search)) return false;
        }
        if (party && member.party !== party) return false;
        if (category && member.quality_category !== category) return false;
        if (flagged) {
            const isFlagged = flagged === 'true';
            if (member.is_hard_to_process !== isFlagged) return false;
        }
        return true;
    });

    currentQualityPage = 1;
    renderQualityTable();
}

let currentQualitySort = { field: 'image_pdf_pct', direction: 'desc' };

function sortQualityData(field) {
    if (currentQualitySort.field === field) {
        currentQualitySort.direction = currentQualitySort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentQualitySort.field = field;
        currentQualitySort.direction = 'desc';
    }

    filteredQualityData.sort((a, b) => {
        let aVal = a[field];
        let bVal = b[field];

        if (aVal == null) aVal = '';
        if (bVal == null) bVal = '';

        if (typeof aVal === 'number') {
            return currentQualitySort.direction === 'asc' ? aVal - bVal : bVal - aVal;
        }

        aVal = String(aVal).toLowerCase();
        bVal = String(bVal).toLowerCase();

        if (currentQualitySort.direction === 'asc') {
            return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
        } else {
            return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
        }
    });

    renderQualityTable();
}

function renderQualityTable() {
    const tbody = document.getElementById('quality-table-body');
    tbody.innerHTML = '';

    const startIdx = (currentQualityPage - 1) * QUALITY_PAGE_SIZE;
    const endIdx = Math.min(startIdx + QUALITY_PAGE_SIZE, filteredQualityData.length);
    const pageData = filteredQualityData.slice(startIdx, endIdx);

    pageData.forEach(member => {
        const row = document.createElement('tr');
        if (member.is_hard_to_process) row.classList.add('flagged-row');

        const categoryClass = {
            'Excellent': 'badge-success', 'Good': 'badge-info', 'Fair': 'badge-warning', 'Poor': 'badge-danger'
        }[member.quality_category] || '';

        row.innerHTML = `
            <td><strong>${escapeHtml(member.full_name || 'Unknown')}</strong></td>
            <td><span class="badge ${getPartyBadgeClass(member.party)}">${member.party || '-'}</span></td>
            <td>${escapeHtml(member.state_district || '-')}</td>
            <td>${member.total_filings || 0}</td>
            <td><strong style="color: ${member.image_pdf_pct > 30 ? '#dc2626' : '#059669'}">${member.image_pdf_pct}%</strong></td>
            <td>${(member.avg_confidence_score * 100).toFixed(1)}%</td>
            <td><strong>${member.quality_score}</strong></td>
            <td><span class="badge ${categoryClass}">${member.quality_category}</span></td>
            <td>
                ${member.is_hard_to_process ? '<span class="badge badge-danger">⚠️ Flagged</span>' : '<span class="badge badge-success">✓ OK</span>'}
            </td>
        `;
        tbody.appendChild(row);
    });

    document.getElementById('quality-showing-count').textContent = `Showing ${startIdx + 1}-${endIdx} of ${filteredQualityData.length} members`;

    const totalPages = Math.ceil(filteredQualityData.length / QUALITY_PAGE_SIZE);
    document.getElementById('quality-page-info').textContent = `Page ${currentQualityPage} of ${totalPages}`;
    document.getElementById('quality-prev-page').disabled = currentQualityPage === 1;
    document.getElementById('quality-next-page').disabled = currentQualityPage === totalPages;
}

function getPartyBadgeClass(party) {
    switch (party) {
        case 'D': return 'badge-primary';
        case 'R': return 'badge-danger';
        case 'I': return 'badge-warning';
        default: return '';
    }
}

function exportQualityCSV() {
    const headers = ['Member', 'Party', 'State/District', 'Total Filings', 'Text PDF Count', 'Image PDF Count', 'Image PDF %', 'Avg Confidence', 'Quality Score', 'Quality Category', 'Flagged', 'Days Since Last Filing'];
    const rows = filteredQualityData.map(m => [
        m.full_name, m.party, m.state_district, m.total_filings, m.text_pdf_count, m.image_pdf_count, m.image_pdf_pct, m.avg_confidence_score, m.quality_score, m.quality_category, m.is_hard_to_process ? 'Yes' : 'No', m.days_since_last_filing
    ]);

    const csv = [headers.join(','), ...rows.map(row => row.map(cell => `"${cell}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `congress_document_quality_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
