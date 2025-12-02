// Admin Page - Document Viewer
// IP-based access control and document inspection

const S3_BUCKET = "congress-disclosures-standardized";
const S3_REGION = "us-east-1";
const API_BASE = `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com`;

// Access control
// For now, disable IP allowlist so the page is publicly viewable
const ALLOW_ALL = true;
// Authorized IP addresses (kept for future use if ALLOW_ALL is set to false)
const AUTHORIZED_IPS = [];

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await checkAccess();
});

// Check IP access (bypassed when ALLOW_ALL = true)
async function checkAccess() {
    if (ALLOW_ALL) {
        const accessEl = document.getElementById('access-check');
        const adminEl = document.getElementById('admin-container');
        if (accessEl) accessEl.style.display = 'none';
        if (adminEl) adminEl.style.display = 'flex';
        initializeAdmin();
        return;
    }

    try {
        const response = await fetch('https://api.ipify.org?format=json');
        const data = await response.json();
        const userIP = data.ip;
        const accessEl = document.getElementById('access-check');
        const adminEl = document.getElementById('admin-container');
        const ipEl = document.getElementById('user-ip');
        if (ipEl) ipEl.textContent = userIP;

        const isAuthorized = AUTHORIZED_IPS.includes(userIP);
        if (isAuthorized) {
            if (accessEl) accessEl.style.display = 'none';
            if (adminEl) adminEl.style.display = 'flex';
            initializeAdmin();
        } else {
            if (accessEl) accessEl.style.display = 'flex';
            if (adminEl) adminEl.style.display = 'none';
        }
    } catch (error) {
        console.error('Error checking IP:', error);
        const accessEl = document.getElementById('access-check');
        const adminEl = document.getElementById('admin-container');
        if (accessEl) accessEl.style.display = 'none';
        if (adminEl) adminEl.style.display = 'flex';
        initializeAdmin();
    }
}

// Initialize admin interface
async function initializeAdmin() {
    // Load document list
    await loadDocumentList();
    // Initialize sort and resizer UI
    initSortFromUrl();
    initResizer();
    
    // Check if doc_id is in URL
    const urlParams = new URLSearchParams(window.location.search);
    const docId = urlParams.get('doc_id');
    const year = urlParams.get('year') || '2025';
    const q = urlParams.get('q') || '';
    const ft = urlParams.get('ft') || '';
    const sortParam = urlParams.get('sort') || '';
    const ps = urlParams.get('ps') || '';
    
    if (docId) {
        // When a specific document is deep-linked, do NOT apply list filters from URL.
        // Clear search and filing-type UI to allow free navigation.
        const searchEl = document.getElementById('doc-search');
        const sel = document.getElementById('filing-type-filter');
        if (searchEl) searchEl.value = '';
        if (sel) sel.value = '';
        filterDocuments();

        // Clean up URL: drop q/ft so filters don't remain sticky from shared links
        const parts = [`doc_id=${docId}`, `year=${year}`];
        if (sortParam) parts.push(`sort=${sortParam}`);
        window.history.replaceState({}, '', `?${parts.join('&')}`);

        document.getElementById('doc-search').value = docId;
        loadDocument(docId, year);
    } else {
        // Apply query/filter from URL if present only when not deep-linked to a doc
        if (q) {
            const searchEl = document.getElementById('doc-search');
            if (searchEl) searchEl.value = q;
            filterDocuments();
        }
        if (ps) {
            const sel2 = document.getElementById('processing-filter');
            if (sel2) sel2.value = ps;
            filterDocuments();
        }
        if (ft) {
            const sel = document.getElementById('filing-type-filter');
            if (sel) sel.value = ft;
            filterDocuments();
        }
    }
}

// Document list state
let allDocuments = [];
let filteredDocuments = [];
let bronzeByDocId = new Map();
let silverByDocId = new Map();
let filingTypeOptions = [];
let filingTypeCounts = new Map();
let sortYearAsc = false; // default Year ↓
let currentPdfObjectUrl = null; // revoke between loads
let pdfDoc = null; let pdfPageNum = 1; let pdfScale = 1.25; let pdfRendering = false; let pdfPendingPage = null; let pdfAutoFit = true;

// Human-friendly filing type labels
const FILING_TYPE_LABELS = {
    'A': 'Annual',
    'P': 'PTR (Periodic Transaction Report)',
    'I': 'Initial/New',
    'N': 'New Filer',
    'T': 'Termination',
    'AM': 'Amendment',
    'AMEND': 'Amendment'
};

function labelFilingType(code) {
    if (!code) return '-';
    const key = String(code).trim().toUpperCase();
    return FILING_TYPE_LABELS[key] || key;
}

// Toggle sort order and update UI
function toggleSortYear() {
    sortYearAsc = !sortYearAsc;
    const btn = document.getElementById('sort-year-btn');
    if (btn) btn.textContent = sortYearAsc ? 'Year ↑' : 'Year ↓';
    // persist in URL
    const params = new URLSearchParams(window.location.search);
    params.set('sort', sortYearAsc ? 'year_asc' : 'year_desc');
    window.history.replaceState({}, '', `?${params.toString()}`);
    renderDocumentList();
}

// Initialize sort state from URL
function initSortFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const s = params.get('sort');
    if (s === 'year_asc') sortYearAsc = true;
    const btn = document.getElementById('sort-year-btn');
    if (btn) btn.textContent = sortYearAsc ? 'Year ↑' : 'Year ↓';
}

// Resizable split between panes
function initResizer() {
    const resizer = document.getElementById('resizer');
    const left = document.getElementById('pane-left');
    const right = document.getElementById('pane-right');
    const container = document.getElementById('admin-right-split');
    if (!resizer || !left || !right || !container) return;
    // Restore last size
    const saved = localStorage.getItem('admin_split_left');
    if (saved) {
        const pct = Math.min(75, Math.max(25, parseFloat(saved)));
        left.style.width = pct + '%';
        right.style.width = (100 - pct) + '%';
    }
    let dragging = false;
    function onMouseMove(e) {
        if (!dragging) return;
        const rect = container.getBoundingClientRect();
        let pct = ((e.clientX - rect.left) / rect.width) * 100;
        pct = Math.min(75, Math.max(25, pct));
        left.style.width = pct + '%';
        right.style.width = (100 - pct) + '%';
    }
    function onMouseUp() {
        if (!dragging) return;
        dragging = false;
        const lw = parseFloat(left.style.width) || 50;
        localStorage.setItem('admin_split_left', String(lw));
        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('mouseup', onMouseUp);
        // After resizing, fit PDF width so X-axis stays in view
        pdfAutoFit = true;
        fitPdfToWidth().catch(() => {});
    }
    resizer.addEventListener('mousedown', () => {
        dragging = true;
        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
    });
}

// Load document list: Bronze as base, Silver for enrichment
async function loadDocumentList() {
    try {
        // Load Bronze manifest first
        const bronzeResp = await fetch(`${API_BASE}/website/api/v1/documents/manifest.json`);
        if (!bronzeResp.ok) {
            throw new Error('Failed to load Bronze manifest');
        }
        const bronze = await bronzeResp.json();
        const filings = bronze.filings || [];
        bronzeByDocId = new Map(filings.filter(f => f.doc_id).map(f => [String(f.doc_id), f]));
        allDocuments = filings; // base list includes all docs
        filteredDocuments = [...allDocuments];

        // Build filing type filters
        const counts = new Map();
        for (const f of filings) {
            const code = (f.filing_type || '').toString().trim();
            if (!code) continue;
            counts.set(code, (counts.get(code) || 0) + 1);
        }
        filingTypeCounts = counts;
        filingTypeOptions = Array.from(counts.keys()).sort();
        populateFilingTypeFilter();

        // Load Silver manifest to enrich statuses
        try {
            const silverResp = await fetch(`${API_BASE}/website/api/v1/documents/silver/manifest.json`);
            if (silverResp.ok) {
                const silver = await silverResp.json();
                const docs = silver.documents || [];
                silverByDocId = new Map(docs.filter(d => d.doc_id).map(d => [String(d.doc_id), d]));
            } else {
                console.warn('Silver manifest not available; proceeding with Bronze only');
            }
        } catch (e) {
            console.warn('Error loading Silver manifest:', e);
        }

        renderTopTypeButtons();
        renderDocumentList();
    } catch (error) {
        console.error('Error loading document list:', error);
        document.getElementById('documents-list').innerHTML = `
            <div class="error-message">
                <p>Failed to load documents: ${error.message}</p>
            </div>
        `;
    }
}

// Filter documents
function filterDocuments() {
    const rawSearch = document.getElementById('doc-search').value;
    const searchTerm = rawSearch.toLowerCase();
    const typeFilter = (document.getElementById('filing-type-filter')?.value || '').trim();
    const procFilter = (document.getElementById('processing-filter')?.value || '').trim();
    const hint = document.getElementById('search-hint');
    const typeSelect = document.getElementById('filing-type-filter');
    const docIdMode = isDocIdSearch(rawSearch);
    
    if (!searchTerm) {
        filteredDocuments = [...allDocuments];
    } else {
        filteredDocuments = allDocuments.filter(doc => {
            const docId = String(doc.doc_id || '').toLowerCase();
            const bronzeRec = bronzeByDocId.get(String(doc.doc_id)) || {};
            const memberCombined = `${bronzeRec.first_name || ''} ${bronzeRec.last_name || ''}`.trim();
            const memberFromSilver = silverByDocId.get(String(doc.doc_id))?.member_name || '';
            const memberName = (doc.member_name || memberFromSilver || memberCombined).toLowerCase();
            const year = String(doc.year || bronzeRec.year || '').toLowerCase();
            const rawFilingType = (doc.filing_type || bronzeRec.filing_type || '');
            const filingType = rawFilingType.toLowerCase();
            const filingLabel = labelFilingType(rawFilingType).toLowerCase();
            
            return docId.includes(searchTerm) ||
                   memberName.includes(searchTerm) ||
                   year.includes(searchTerm) ||
                   filingType.includes(searchTerm) ||
                   filingLabel.includes(searchTerm);
        });
    }
    
    // Apply filing-type dropdown filter unless the search is a doc-id query
    if (!docIdMode && typeFilter) {
        filteredDocuments = filteredDocuments.filter(doc => {
            const ft = doc.filing_type || bronzeByDocId.get(String(doc.doc_id))?.filing_type || '';
            return String(ft) === typeFilter;
        });
    }
    // Apply processing state filter
    if (!docIdMode && procFilter) {
        filteredDocuments = filteredDocuments.filter(doc => getProcessingState(doc) === procFilter);
    }

    // Update UI state for filter
    if (typeSelect) typeSelect.disabled = docIdMode;
    if (hint) {
        hint.textContent = docIdMode
            ? 'Searching by Document ID. Filing type filter is disabled.'
            : 'Tip: Filter by filing type or search by member/label.';
    }
    // Persist q/ft/ps in URL (without reloading)
    const params = new URLSearchParams(window.location.search);
    if (rawSearch) params.set('q', rawSearch); else params.delete('q');
    const effFt = (!docIdMode ? typeFilter : '');
    if (effFt) params.set('ft', effFt); else params.delete('ft');
    const effPs = (!docIdMode ? procFilter : '');
    if (effPs) params.set('ps', effPs); else params.delete('ps');
    const docIdExisting = params.get('doc_id');
    const yearExisting = params.get('year');
    const base = [];
    if (docIdExisting) base.push(`doc_id=${docIdExisting}`);
    if (yearExisting) base.push(`year=${yearExisting}`);
    const queryStr = params.toString();
    const newUrl = queryStr ? `?${queryStr}` : window.location.pathname;
    window.history.replaceState({}, '', newUrl);
    
    renderDocumentList();
    updateProcessingCounts();
}

// Render document list
function renderDocumentList() {
    const listContainer = document.getElementById('documents-list');
    
    if (filteredDocuments.length === 0) {
        listContainer.innerHTML = '<div class="loading"><p>No documents found</p></div>';
        return;
    }
    
    // Sort by year (toggle asc/desc). Fallback to doc_id desc.
    const sorted = [...filteredDocuments].sort((a, b) => {
        const ay = parseInt(a.year || bronzeByDocId.get(String(a.doc_id))?.year) || 0;
        const by = parseInt(b.year || bronzeByDocId.get(String(b.doc_id))?.year) || 0;
        if (ay !== by) return sortYearAsc ? (ay - by) : (by - ay);
        const aId = parseInt(a.doc_id) || 0;
        const bId = parseInt(b.doc_id) || 0;
        return bId - aId;
    });
    
    listContainer.innerHTML = sorted.map(doc => {
        const isActive = document.querySelector('.document-item.active')?.dataset.docId === String(doc.doc_id);
        const silverRec = silverByDocId.get(String(doc.doc_id));
        const statusBadge = silverRec ? (
            silverRec.extraction_status === 'success' ? '<span style="color: green;">✓</span>' :
            silverRec.extraction_status === 'pending' ? '<span style="color: orange;">⏳</span>' :
            '<span style="color: red;">✗</span>'
        ) : '<span style="color: #64748b;">•</span>';
        const bronzeRec2 = bronzeByDocId.get(String(doc.doc_id)) || {};
        const filingTypeCode = doc.filing_type || bronzeRec2.filing_type || '';
        const filingType = filingTypeCode ? labelFilingType(filingTypeCode) : '-';
        const displayName = (doc.member_name || silverRec?.member_name || `${bronzeRec2.first_name || ''} ${bronzeRec2.last_name || ''}`).trim() || 'Unknown';
        const displayYear = doc.year || bronzeRec2.year || '-';

        return `
            <div class="document-item ${isActive ? 'active' : ''}" 
                 data-doc-id="${doc.doc_id}" 
                 data-year="${displayYear}"
                 onclick="selectDocument('${doc.doc_id}', '${displayYear}')">
                <div class="document-item-code">${statusBadge} ${doc.doc_id}</div>
                <div class="document-item-meta">
                    ${escapeHtml(displayName)} |
                    <span class="badge type" title="Code: ${escapeHtml(filingTypeCode || '-')}" aria-label="Filing type ${escapeHtml(filingType)}">${escapeHtml(filingType)}</span>
                    | ${displayYear}
                </div>
            </div>
        `;
    }).join('');
}

// Populate filing type dropdown
function populateFilingTypeFilter() {
    const select = document.getElementById('filing-type-filter');
    if (!select) return;
    // Reset options (keep first "All" item)
    select.innerHTML = '<option value="">All filing types</option>';
    // Sort by count desc, then by label
    const sorted = [...filingTypeOptions].sort((a, b) => {
        const ca = filingTypeCounts.get(a) || 0;
        const cb = filingTypeCounts.get(b) || 0;
        if (cb !== ca) return cb - ca;
        return labelFilingType(a).localeCompare(labelFilingType(b));
    });
    sorted.forEach(code => {
        const count = filingTypeCounts.get(code) || 0;
        const opt = document.createElement('option');
        opt.value = code;
        opt.textContent = `${labelFilingType(code)} (${count.toLocaleString()})`;
        select.appendChild(opt);
    });
    renderTopTypeButtons();
    updateProcessingCounts();
}

// Render top filing type chips (buttons)
function renderTopTypeButtons(limit = 5) {
    const container = document.getElementById('top-type-buttons');
    if (!container || filingTypeCounts.size === 0) return;
    const sorted = [...filingTypeCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, limit);
    const current = (document.getElementById('filing-type-filter')?.value || '').trim();
    container.innerHTML = sorted.map(([code, count]) => {
        const label = labelFilingType(code);
        const active = current === code ? 'active' : '';
        return `<button class=\"btn-chip ${active}\" onclick=\"applyTypeChip('${code}')\" title=\"${count.toLocaleString()} filings\">${label}</button>`;
    }).join('');
}

function applyTypeChip(code) {
    const sel = document.getElementById('filing-type-filter');
    if (sel) sel.value = code;
    filterDocuments();
    renderTopTypeButtons();
}

// Processing state chips (Completed/Processing/Failed/Not processed)
function renderProcessingButtons() {
    const container = document.getElementById('top-processing-buttons');
    if (!container) return;
    const counts = computeProcessingCounts();
    const current = (document.getElementById('processing-filter')?.value || '').trim();
    const items = [
        { code: 'success', label: 'Completed', count: counts.success || 0 },
        { code: 'pending', label: 'Processing', count: counts.pending || 0 },
        { code: 'failed', label: 'Failed', count: counts.failed || 0 },
        { code: 'none', label: 'Not processed', count: counts.none || 0 },
    ];
    container.innerHTML = items.map(it => {
        const active = current === it.code ? 'active' : '';
        return `<button class="btn-chip ${active}" onclick="applyProcessingChip('${it.code}')" title="${it.count.toLocaleString()} documents">${it.label} (${it.count.toLocaleString()})</button>`;
    }).join('');
}

function applyProcessingChip(code) {
    const sel = document.getElementById('processing-filter');
    if (sel) sel.value = code;
    filterDocuments();
    renderProcessingButtons();
}

function onProcessingChange() {
    filterDocuments();
    updateProcessingCounts();
}

function getProcessingState(doc) {
    const silverRec = silverByDocId.get(String(doc.doc_id));
    if (!silverRec) return 'none';
    const st = String(silverRec.extraction_status || '').toLowerCase();
    if (st === 'success') return 'success';
    if (st === 'pending') return 'pending';
    if (st === 'failed') return 'failed';
    return 'none';
}

function computeProcessingCounts() {
    const counts = { success: 0, pending: 0, failed: 0, none: 0 };
    for (const doc of allDocuments) {
        counts[getProcessingState(doc)]++;
    }
    return counts;
}

function updateProcessingCounts() {
    const el = document.getElementById('processing-counts');
    if (!el) return;
    const c = computeProcessingCounts();
    el.innerHTML = `Completed (${(c.success||0).toLocaleString()}) • Processing (${(c.pending||0).toLocaleString()}) • Failed (${(c.failed||0).toLocaleString()}) • Not processed (${(c.none||0).toLocaleString()})`;
}

// Called by select onchange in HTML
function onFilingTypeChange() {
    filterDocuments();
    renderTopTypeButtons();
}

// Reset search + filter
function resetFilters() {
    const searchEl = document.getElementById('doc-search');
    const typeSelect = document.getElementById('filing-type-filter');
    if (searchEl) searchEl.value = '';
    if (typeSelect) typeSelect.value = '';
    filterDocuments();
    renderTopTypeButtons();
}

// Detect if search term is document-id style (digits or YYYY/ID)
function isDocIdSearch(term) {
    if (!term) return false;
    const t = String(term).trim();
    return /^\d{5,}$/.test(t) || /^\d{4}\/\d+$/.test(t);
}

// Select document
function selectDocument(docId, year) {
    // Update active state
    document.querySelectorAll('.document-item').forEach(item => {
        item.classList.remove('active');
    });
    const selectedItem = document.querySelector(`[data-doc-id="${docId}"]`);
    if (selectedItem) {
        selectedItem.classList.add('active');
    }
    
    // Show split view and hide empty state
    document.getElementById('admin-right-empty').classList.add('hidden');
    document.getElementById('admin-right-split').classList.add('active');
    
    // Load document
    loadDocument(docId, year);
    
    // Update URL
    window.history.pushState({}, '', `?doc_id=${docId}&year=${year}`);
}

// Toggle sidebar (document list)
function toggleSidebar() {
    const sidebar = document.getElementById('admin-left');
    const toggleBtn = document.querySelector('.toggle-sidebar');
    
    sidebar.classList.toggle('collapsed');
    toggleBtn.classList.toggle('collapsed');
}

// Handle search key press (removed - now uses filterDocuments on keyup)

// Load document
async function loadDocument(docId = null, year = null) {
    const searchInput = document.getElementById('doc-search');
    const inputValue = docId || searchInput.value.trim();
    
    if (!inputValue) {
        alert('Please enter a Document ID');
        return;
    }
    
    // Extract year if provided (format: "10063228" or "2025/10063228")
    let actualDocId = inputValue;
    let actualYear = year || '2025';
    
    if (inputValue.includes('/')) {
        const parts = inputValue.split('/');
        actualYear = parts[0];
        actualDocId = parts[1];
    }
    
    // Show loading
    document.getElementById('document-data').innerHTML = '<div class="loading"><p>Loading document data...</p></div>';
    // In split view layout there is no placeholder element; ensure we don't access null
    // The split view is activated in selectDocument(), so we only need to update the iframe src below
    
    try {
        // Load document data directly from Silver layer (with robust fallbacks)
        const structuredCandidates = [
            `${API_BASE}/silver/house/financial/structured/year=${actualYear}/doc_id=${actualDocId}.json`,
            `${API_BASE}/silver/house/financial/structured/year=${actualYear}/doc_id=${actualDocId}/structured.json`,
        ];
        const metadataCandidates = [
            `${API_BASE}/silver/house/financial/documents/year=${actualYear}/${actualDocId}/metadata.json`,
        ];
        const textCandidates = [
            `${API_BASE}/silver/house/financial/documents/year=${actualYear}/${actualDocId}/text.txt`,
            // Compressed text (optional): `${API_BASE}/silver/house/financial/text/extraction_method=pypdf/year=${actualYear}/doc_id=${actualDocId}/raw_text.txt.gz`,
        ];
        const pdfUrl = `https://disclosures-clerk.house.gov/public_disc/financial-pdfs/${actualYear}/${actualDocId}.pdf`;
        // Candidate Bronze PDF locations (try in order)
        const bronzePdfCandidates = [
            `${API_BASE}/bronze/house/financial/year=${actualYear}/pdfs/${actualYear}/${actualDocId}.pdf`,
            `${API_BASE}/bronze/house/financial/disclosures/year=${actualYear}/doc_id=${actualDocId}/${actualDocId}.pdf`,
            `${API_BASE}/bronze/house/financial/ptr-pdfs/${actualYear}/${actualDocId}.pdf`,
        ];
        const bronzePdfUrl = await resolveBronzePdfUrl(bronzePdfCandidates);
        
        // Load structured JSON data with fallback
        let jsonData = null; let jsonUrl = structuredCandidates[0];
        for (const url of structuredCandidates) {
            try {
                const resp = await fetch(url);
                if (resp.ok) { jsonData = await resp.json(); jsonUrl = url; break; }
            } catch (e) { /* continue */ }
        }
        
        // Load metadata with fallback
        let metadata = null; let metadataUrl = metadataCandidates[0];
        for (const url of metadataCandidates) {
            try {
                const resp = await fetch(url);
                if (resp.ok) { metadata = await resp.json(); metadataUrl = url; break; }
            } catch (e) { /* continue */ }
        }
        
        // Load text (optional, best-effort)
        let extractedText = null; let textUrl = textCandidates[0];
        for (const url of textCandidates) {
            try {
                const resp = await fetch(url);
                if (resp.ok) { extractedText = await resp.text(); textUrl = url; break; }
            } catch (e) { /* continue */ }
        }
        
        // Display PDF inline by fetching bytes and using a Blob URL.
        // This avoids Content-Disposition=attachment triggering a download prompt.
        const srcLabel = document.getElementById('pdf-source-label');
        try {
            await renderPdfWithPdfjs(bronzePdfUrl);
            if (srcLabel) srcLabel.textContent = 'Source: Bronze (PDF.js)';
        } catch (e) {
            console.warn('PDF.js render failed, trying Blob inline:', e);
            try {
                await renderPdfInline(bronzePdfUrl);
                if (srcLabel) srcLabel.textContent = 'Source: Bronze (inline)';
            } catch (e2) {
                console.warn('Inline PDF render failed, falling back to direct URL:', e2);
                const iframe = document.getElementById('pdf-viewer');
                if (iframe) iframe.src = bronzePdfUrl;
                if (srcLabel) srcLabel.textContent = 'Source: Bronze';
            }
        }
        
        // Compute pipeline progress
        const pipeline = {
            silverRecord: silverByDocId.has(String(actualDocId)) ? (silverByDocId.get(String(actualDocId)).extraction_status || 'present') : null,
            bronzePdf: await urlExists(bronzePdfUrl),
            metadata: !!metadata,
            text: !!extractedText,
            structuredJson: !!jsonData,
        };

        // Display all data
        displayDocumentData({
            docId: actualDocId,
            year: actualYear,
            jsonData,
            metadata,
            extractedText,
            pdfUrl,
            bronzePdfUrl,
            jsonUrl,
            metadataUrl,
            textUrl,
            pipeline
        });
        
        // Update URL
        window.history.pushState({}, '', `?doc_id=${actualDocId}&year=${actualYear}`);
        
    } catch (error) {
        console.error('Error loading document:', error);
        document.getElementById('document-data').innerHTML = `
            <div class="error-message">
                <h3>Error Loading Document</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

// Display all document data
function displayDocumentData(data) {
    const { docId, year, jsonData, metadata, extractedText, pdfUrl, bronzePdfUrl, jsonUrl, metadataUrl, textUrl, pipeline } = data;
    // Resolve effective filing type and member name using Silver/BRONZE fallbacks
    const bronzeRec = bronzeByDocId.get(String(docId)) || {};
    const silverRec = silverByDocId.get(String(docId)) || {};
    const effectiveTypeCode = (jsonData?.filing_type) || (metadata?.filing_type) || bronzeRec.filing_type || silverRec.filing_type || '';
    const effectiveTypeLabel = effectiveTypeCode ? labelFilingType(effectiveTypeCode) : '-';
    const effectiveMemberName = (metadata?.member_name) || (jsonData?.member_name) || (silverRec.member_name) || `${bronzeRec.first_name || ''} ${bronzeRec.last_name || ''}`.trim() || '-';
    const effectiveYear = year || bronzeRec.year || '-';
    
    let html = '';
    
    // Basic Info Section
    html += `
        <div class="document-info">
            <div class="info-section">
                <h3>📋 Document Information</h3>
                <div class="info-grid">
                    <div class="info-item">
                        <strong>Document ID</strong>
                        <span>${docId}</span>
                    </div>
                    <div class="info-item">
                        <strong>Year</strong>
                        <span>${effectiveYear}</span>
                    </div>
                    <div class="info-item">
                        <strong>Filing Type</strong>
                        <span>${effectiveTypeLabel}</span>
                    </div>
                    <div class="info-item">
                        <strong>Member Name</strong>
                        <span>${escapeHtml(effectiveMemberName)}</span>
                    </div>
                </div>
            </div>
    `;

    // Pipeline Progress
    if (pipeline) {
        const step = (label, ok, extra = '') => `
            <div class="checkbox-item">
                <span class="${ok ? 'checkbox-on' : 'checkbox-off'}">${ok ? '✅' : '⬜'}</span>
                <span>${escapeHtml(label)}${extra ? ` — ${escapeHtml(extra)}` : ''}</span>
            </div>
        `;
        const silverStatus = pipeline.silverRecord ? String(pipeline.silverRecord) : null;
        const silverOk = !!silverStatus && silverStatus !== 'failed';
        html += `
            <div class="info-section">
                <h3>🛠️ Pipeline Progress</h3>
                <div class="checkbox-grid">
                    ${step('Bronze PDF downloaded', !!pipeline.bronzePdf)}
                    ${step('Silver record', !!pipeline.silverRecord, silverStatus || '')}
                    ${step('Metadata JSON', !!pipeline.metadata)}
                    ${step('Extracted text', !!pipeline.text)}
                    ${step('Structured JSON', !!pipeline.structuredJson)}
                </div>
            </div>
        `;
    }
    
    // Structured Fields (filled vs empty)
    if (jsonData) {
        const dh = jsonData.document_header || {};
        const checkboxes = jsonData.checkboxes || {};

        const fields = [
            { key: 'filing_id', label: 'Filing ID' },
            { key: 'filer_name', label: 'Filer Name' },
            { key: 'status', label: 'Status' },
            { key: 'state_district', label: 'State/District' },
            { key: 'filing_type', label: 'Filing Type' },
            { key: 'filing_year', label: 'Filing Year' },
            { key: 'filing_date', label: 'Filing Date' },
        ];

        html += `
            <div class="info-section">
                <h3>✅ Filled Fields Overview</h3>
                <div class="field-grid">
                    ${fields.map(f => renderFieldItem(f.label, safeVal(dh[f.key]))).join('')}
                </div>
            </div>
        `;

        // Checkboxes section
        const checkboxKeys = Object.keys(checkboxes || {});
        html += `
            <div class="info-section">
                <h3>☑️ Checkboxes</h3>
                ${checkboxKeys.length === 0 ? '<div class="schedule-empty">No checkboxes found</div>' : `
                    <div class="checkbox-grid">
                        ${checkboxKeys.map(k => renderCheckboxItem(k, !!checkboxes[k])).join('')}
                    </div>
                `}
            </div>
        `;

        // Schedules summary
        const schedules = jsonData.schedules || {};
        const scheduleKeys = Object.keys(schedules);
        if (scheduleKeys.length > 0) {
            html += `
                <div class="info-section">
                    <h3>🗂️ Schedules Summary</h3>
                    <table class="schedules-table">
                        <thead>
                            <tr><th>Schedule</th><th>Type</th><th>Entries</th><th>Tables</th><th>Status</th></tr>
                        </thead>
                        <tbody>
                            ${scheduleKeys.map(sk => {
                                const s = schedules[sk] || {};
                                const entries = (s.data || []).length;
                                const tables = (s.tables || []).length;
                                const has = entries > 0 || tables > 0;
                                return `
                                    <tr>
                                        <td>${escapeHtml(sk)}</td>
                                        <td>${escapeHtml(s.type || '-')}</td>
                                        <td>${entries}</td>
                                        <td>${tables}</td>
                                        <td>${has ? '<span class="schedule-has">Has data</span>' : '<span class="schedule-empty">Empty</span>'}</td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }
    }

    // Extraction Metadata
    if (metadata) {
        html += `
            <div class="info-section">
                <h3>⚙️ Extraction Metadata</h3>
                <div class="info-grid">
                    <div class="info-item">
                        <strong>Status</strong>
                        <span>${metadata.extraction_status || '-'}</span>
                    </div>
                    <div class="info-item">
                        <strong>Method</strong>
                        <span>${metadata.extraction_method || '-'}</span>
                    </div>
                    <div class="info-item">
                        <strong>Pages</strong>
                        <span>${metadata.pages || '-'}</span>
                    </div>
                    <div class="info-item">
                        <strong>Character Count</strong>
                        <span>${metadata.char_count ? parseInt(metadata.char_count).toLocaleString() : '-'}</span>
                    </div>
                    <div class="info-item">
                        <strong>Has Embedded Text</strong>
                        <span>${metadata.has_embedded_text || '-'}</span>
                    </div>
                    <div class="info-item">
                        <strong>Extraction Version</strong>
                        <span>${metadata.extraction_version || '-'}</span>
                    </div>
                    <div class="info-item">
                        <strong>Extracted At</strong>
                        <span>${metadata.extraction_timestamp ? new Date(metadata.extraction_timestamp).toLocaleString(undefined, {
                            year: 'numeric',
                            month: '2-digit',
                            day: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                            timeZoneName: 'short'
                        }) : '-'}</span>
                    </div>
                    <div class="info-item">
                        <strong>Processing Time</strong>
                        <span>${metadata.processing_time_ms ? `${metadata.processing_time_ms}ms` : '-'}</span>
                    </div>
                </div>
            </div>
        `;
    }
    
        // Storage Locations
        html += `
            <div class="info-section">
                <h3>📦 Storage Locations</h3>
                <div class="s3-links">
                    <a href="${pdfUrl}" target="_blank" class="s3-link">
                        <span>📄</span>
                        <span><strong>Original PDF:</strong> House Clerk Website</span>
                    </a>
                    <a href="${bronzePdfUrl}" target="_blank" class="s3-link">
                        <span>📄</span>
                        <span><strong>Bronze PDF:</strong> ${bronzePdfUrl}</span>
                    </a>
                    <a href="${jsonUrl}" target="_blank" class="s3-link">
                        <span>📊</span>
                        <span><strong>Structured JSON:</strong> ${jsonUrl}</span>
                    </a>
                    <a href="${metadataUrl}" target="_blank" class="s3-link">
                        <span>📋</span>
                        <span><strong>Metadata JSON:</strong> ${metadataUrl}</span>
                    </a>
                    <div class="s3-link" role="button" tabindex="0" onclick="scrollToSection('extracted-text-section')">
                        <span>📝</span>
                        <span><strong>Extracted Text:</strong> View below</span>
                    </div>
                </div>
            </div>
        `;
    
    // JSON Data
    if (jsonData) {
        html += `
            <div class="info-section">
                <h3>📊 Structured JSON Data</h3>
                <div class="json-viewer">${JSON.stringify(jsonData, null, 2)}</div>
            </div>
        `;
    }
    
    // Extracted Text
    if (extractedText) {
        html += `
            <div class="info-section" id="extracted-text-section">
                <h3>📝 Extracted Text</h3>
                <div class="text-viewer">${escapeHtml(extractedText.substring(0, 50000))}${extractedText.length > 50000 ? '\n\n... (truncated)' : ''}</div>
            </div>
        `;
    }
    
    // Error Information
    if (metadata?.extraction_error) {
        html += `
            <div class="info-section">
                <h3>⚠️ Extraction Error</h3>
                <div class="error-message">${escapeHtml(metadata.extraction_error)}</div>
            </div>
        `;
    }
    
    html += '</div>';
    
    document.getElementById('document-data').innerHTML = html;
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Smooth-scroll to a section within the right pane
function scrollToSection(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Lightweight URL existence check (HEAD; fallback to range GET)
async function urlExists(url) {
    try {
        const head = await fetch(url, { method: 'HEAD' });
        if (head.ok) return true;
    } catch (_) {}
    try {
        const get = await fetch(url, { method: 'GET', headers: { 'Range': 'bytes=0-0' } });
        return get.ok;
    } catch (_) {
        return false;
    }
}

// Resolve the first existing Bronze PDF URL from candidates
async function resolveBronzePdfUrl(candidates) {
    for (const url of candidates) {
        try {
            if (await urlExists(url)) return url;
        } catch (_) {}
    }
    // Fallback to first candidate even if HEAD blocked; iframe may still render
    return candidates[0];
}

// Fetch a PDF and render it inline via a Blob URL
async function renderPdfInline(url) {
    // Revoke previous URL if any
    try { if (currentPdfObjectUrl) URL.revokeObjectURL(currentPdfObjectUrl); } catch (_) {}
    const resp = await fetch(url, { method: 'GET', mode: 'cors' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const buf = await resp.arrayBuffer();
    const blob = new Blob([buf], { type: 'application/pdf' });
    const objUrl = URL.createObjectURL(blob);
    currentPdfObjectUrl = objUrl;
    document.getElementById('pdf-viewer').src = objUrl;
}

// Render PDF using PDF.js into the canvas
async function renderPdfWithPdfjs(url) {
    if (!window['pdfjsLib']) throw new Error('pdfjsLib not loaded');
    // Reset state
    pdfDoc = null; pdfPageNum = 1; pdfScale = 1.25; pdfRendering = false; pdfPendingPage = null;
    // Prefer URL directly; S3 allows CORS GET
    const loadingTask = pdfjsLib.getDocument({ url });
    pdfDoc = await loadingTask.promise;
    document.getElementById('pdf-page-count').textContent = pdfDoc.numPages;
    await fitPdfToWidth();
}

async function renderPdfPage(num) {
    pdfRendering = true;
    const page = await pdfDoc.getPage(num);
    const viewport = page.getViewport({ scale: pdfScale });
    const canvas = document.getElementById('pdf-canvas');
    const ctx = canvas.getContext('2d');
    
    // High-DPI rendering for crisper text/images
    const MAX_OUTPUT_SCALE = 2; // cap to avoid huge memory on 4k/retina
    const dpr = (window.devicePixelRatio || 1);
    const outputScale = Math.min(dpr, MAX_OUTPUT_SCALE);

    // Set canvas pixel buffer size scaled by outputScale,
    // while CSS size matches logical viewport for layout.
    const pixelWidth = Math.max(1, Math.floor(viewport.width * outputScale));
    const pixelHeight = Math.max(1, Math.floor(viewport.height * outputScale));
    canvas.width = pixelWidth;
    canvas.height = pixelHeight;
    canvas.style.width = `${Math.floor(viewport.width)}px`;
    canvas.style.height = `${Math.floor(viewport.height)}px`;

    const transform = outputScale !== 1 ? [outputScale, 0, 0, outputScale, 0, 0] : null;
    const renderContext = { canvasContext: ctx, viewport, transform };
    await page.render(renderContext).promise;
    pdfRendering = false;
    document.getElementById('pdf-page-num').textContent = num;
    if (pdfPendingPage !== null) {
        const n = pdfPendingPage; pdfPendingPage = null; renderPdfPage(n);
    }
}

function queueRenderPage(num) {
    if (pdfRendering) {
        pdfPendingPage = num;
    } else {
        renderPdfPage(num);
    }
}

// Toolbar controls
function pdfPrevPage() { if (!pdfDoc) return; if (pdfPageNum <= 1) return; pdfPageNum--; if (pdfAutoFit) { fitPdfToWidth(); } else { queueRenderPage(pdfPageNum); } }
function pdfNextPage() { if (!pdfDoc) return; if (pdfPageNum >= pdfDoc.numPages) return; pdfPageNum++; if (pdfAutoFit) { fitPdfToWidth(); } else { queueRenderPage(pdfPageNum); } }
function pdfZoomIn() { if (!pdfDoc) return; pdfAutoFit = false; pdfScale = Math.min(pdfScale + 0.1, 3); queueRenderPage(pdfPageNum); }
function pdfZoomOut() { if (!pdfDoc) return; pdfAutoFit = false; pdfScale = Math.max(pdfScale - 0.1, 0.5); queueRenderPage(pdfPageNum); }

// Fit-to-width utility
async function fitPdfToWidth() {
    if (!pdfDoc) return;
    const page = await pdfDoc.getPage(pdfPageNum);
    const unscaled = page.getViewport({ scale: 1 });
    const container = document.getElementById('pdf-canvas-container');
    if (!container) return;
    const padding = 32; // approximate margins in container
    const targetWidth = Math.max(100, (container.clientWidth || 0) - padding);
    const newScale = Math.max(0.25, Math.min(5, targetWidth / unscaled.width));
    pdfScale = newScale;
    queueRenderPage(pdfPageNum);
}

// React to container resizes (e.g., window resize)
(() => {
    const container = document.getElementById('pdf-canvas-container');
    if (!container || !window.ResizeObserver) return;
    const ro = new ResizeObserver(() => { if (pdfAutoFit) fitPdfToWidth().catch(() => {}); });
    ro.observe(container);
})();

// Helpers for structured fields
function isFilled(value) {
    if (value === null || value === undefined) return false;
    if (typeof value === 'string') return value.trim().length > 0;
    if (Array.isArray(value)) return value.length > 0;
    if (typeof value === 'object') return Object.keys(value).length > 0;
    // numbers/booleans
    return true;
}

function safeVal(value) {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string') return value.trim();
    if (typeof value === 'number' || typeof value === 'boolean') return String(value);
    try { return JSON.stringify(value); } catch { return String(value); }
}

function renderFieldItem(label, value) {
    const filled = isFilled(value);
    const display = filled ? escapeHtml(String(value)) : '-';
    return `
        <div class="field-item ${filled ? 'filled' : 'empty'}">
            <span class="field-label">${escapeHtml(label)}</span>
            <span class="field-value">${display}</span>
        </div>
    `;
}

function renderCheckboxItem(key, checked) {
    return `
        <div class="checkbox-item">
            <span class="${checked ? 'checkbox-on' : 'checkbox-off'}">${checked ? '✅' : '⬜'}</span>
            <span>${escapeHtml(key)}</span>
        </div>
    `;
}
