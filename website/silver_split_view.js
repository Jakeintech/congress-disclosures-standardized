/**
 * Silver Layer Split View Controller
 * Handles the public-facing split view of documents (PDF + Structured Data)
 */

(function () {
    'use strict';

    const S3_BUCKET = "congress-disclosures-standardized";
    const S3_REGION = "us-east-1";
    const API_BASE = `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com`;

    // State
    let allDocuments = [];
    let filteredDocuments = [];
    let currentDocId = null;
    let currentDocData = null; // Store structured data
    let currentDocText = null; // Store extracted text
    let pdfDoc = null;
    let pdfPageNum = 1;
    let pdfScale = 1.0;
    let pdfRendering = false;
    let pdfPendingPage = null;

    // DOM Elements
    const elements = {};

    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSilverSplitView);
    } else {
        initSilverSplitView();
    }

    function initSilverSplitView() {
        // Cache DOM elements
        const ids = [
            'silver-split-view', 'silver-doc-search', 'silver-type-filter', 'silver-year-filter',
            'silver-list-count', 'silver-refresh-btn', 'silver-doc-list',
            'silver-empty-state', 'silver-content-pane', 'silver-pane-left', 'silver-pane-right',
            'silver-resizer', 'silver-pdf-canvas', 'silver-data-content',
            'pdf-prev', 'pdf-next', 'pdf-zoom-in', 'pdf-zoom-out', 'pdf-page-num', 'pdf-page-count', 'pdf-download-link',
            'data-doc-title', 'data-doc-meta', 'audit-view-select'
        ];

        ids.forEach(id => {
            elements[id] = document.getElementById(id);
        });

        // Only proceed if we are on the page with the split view
        if (!elements['silver-split-view']) return;

        // Event Listeners
        elements['silver-doc-search'].addEventListener('input', filterDocuments);
        elements['silver-type-filter'].addEventListener('change', filterDocuments);
        elements['silver-year-filter'].addEventListener('change', filterDocuments);
        elements['silver-refresh-btn'].addEventListener('click', loadSilverDocuments);

        if (elements['audit-view-select']) {
            elements['audit-view-select'].addEventListener('change', renderAuditView);
        }

        // PDF Controls
        elements['pdf-prev'].addEventListener('click', onPrevPage);
        elements['pdf-next'].addEventListener('click', onNextPage);
        elements['pdf-zoom-in'].addEventListener('click', () => { pdfScale += 0.25; renderPage(pdfPageNum); });
        elements['pdf-zoom-out'].addEventListener('click', () => { if (pdfScale > 0.5) { pdfScale -= 0.25; renderPage(pdfPageNum); } });

        // Resizer
        initResizer();

        // Load Data
        loadSilverDocuments();

        console.log('✅ Silver Split View initialized');
    }

    async function loadSilverDocuments() {
        setListLoading(true);
        try {
            const response = await fetch(`${API_BASE}/website/api/v1/documents/manifest.json`);
            if (!response.ok) throw new Error('Failed to load manifest');

            const data = await response.json();
            allDocuments = data.filings || [];

            // Sort by date desc
            allDocuments.sort((a, b) => new Date(b.filing_date) - new Date(a.filing_date));

            populateFilters();
            filterDocuments();
        } catch (error) {
            console.error('Error loading documents:', error);
            elements['silver-doc-list'].innerHTML = `<div class="error-state">Failed to load documents. <br><button class="btn btn-ghost" onclick="loadSilverDocuments()">Retry</button></div>`;
        } finally {
            setListLoading(false);
        }
    }

    function populateFilters() {
        // Years
        const years = [...new Set(allDocuments.map(d => d.year))].sort().reverse();
        const yearSelect = elements['silver-year-filter'];
        yearSelect.innerHTML = '<option value="">Year</option>';
        years.forEach(y => {
            yearSelect.innerHTML += `<option value="${y}">${y}</option>`;
        });

        // Types
        const types = [...new Set(allDocuments.map(d => d.filing_type))].sort();
        const typeSelect = elements['silver-type-filter'];
        typeSelect.innerHTML = '<option value="">All Types</option>';
        types.forEach(t => {
            typeSelect.innerHTML += `<option value="${t}">${getFilingTypeLabel(t)}</option>`;
        });
    }

    function filterDocuments() {
        const search = elements['silver-doc-search'].value.toLowerCase();
        const type = elements['silver-type-filter'].value;
        const year = elements['silver-year-filter'].value;

        filteredDocuments = allDocuments.filter(doc => {
            const matchesSearch = !search ||
                doc.doc_id.toLowerCase().includes(search) ||
                (doc.first_name + ' ' + doc.last_name).toLowerCase().includes(search);
            const matchesType = !type || doc.filing_type === type;
            const matchesYear = !year || String(doc.year) === year;
            return matchesSearch && matchesType && matchesYear;
        });

        renderDocumentList();
    }

    function renderDocumentList() {
        const list = elements['silver-doc-list'];
        elements['silver-list-count'].textContent = `${filteredDocuments.length} documents`;

        if (filteredDocuments.length === 0) {
            list.innerHTML = '<div class="empty-state" style="padding: 1rem; font-size: 0.9rem;">No documents found</div>';
            return;
        }

        list.innerHTML = filteredDocuments.map(doc => `
            <div class="doc-item ${currentDocId === doc.doc_id ? 'active' : ''}" onclick="selectDocument('${doc.doc_id}')">
                <div class="doc-item-header">
                    <span class="doc-member">${doc.first_name} ${doc.last_name}</span>
                    <span class="badge badge-secondary" style="font-size: 0.7rem;">${doc.filing_type}</span>
                </div>
                <div class="doc-meta">
                    <span class="doc-date">${doc.filing_date}</span>
                    <span class="doc-id">${doc.state_district || ''}</span>
                </div>
            </div>
        `).join('');
    }

    window.selectDocument = async function (docId) {
        currentDocId = docId;
        currentDocData = null;
        currentDocText = null;
        if (elements['audit-view-select']) elements['audit-view-select'].value = 'structured';

        renderDocumentList(); // Update active state

        const doc = allDocuments.find(d => d.doc_id === docId);
        if (!doc) return;

        // Show content pane
        elements['silver-empty-state'].classList.add('hidden');
        elements['silver-content-pane'].classList.remove('hidden');

        // Update Header
        elements['data-doc-title'].textContent = `${doc.first_name} ${doc.last_name} - ${getFilingTypeLabel(doc.filing_type)}`;
        elements['data-doc-meta'].textContent = `Filed: ${doc.filing_date} • ID: ${doc.doc_id} • ${doc.state_district}`;

        // Load PDF
        loadPDF(doc);

        // Load Data
        loadData(doc);
    };

    // PDF Handling
    async function loadPDF(doc) {
        // Official URL (Source of Truth)
        let officialUrl = `https://disclosures-clerk.house.gov/public_disc/financial-pdfs/${doc.year}/${doc.doc_id}.pdf`;
        if (doc.filing_type === 'P') {
            officialUrl = `https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/${doc.year}/${doc.doc_id}.pdf`;
        }

        // S3 URL (Internal Cache - Faster/CORS friendly)
        const s3Base = `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com`;
        const s3Url = `${s3Base}/bronze/house/financial/year=${doc.year}/pdfs/${doc.year}/${doc.doc_id}.pdf`;

        // Set download link to official source for "View Original" behavior
        elements['pdf-download-link'].href = officialUrl;

        try {
            const loadingTask = pdfjsLib.getDocument(s3Url);
            pdfDoc = await loadingTask.promise;
            elements['pdf-page-count'].textContent = pdfDoc.numPages;
            pdfPageNum = 1;
            renderPage(pdfPageNum);
        } catch (error) {
            console.error('Error loading PDF from S3:', error);

            // Show error in PDF container with link to official source
            const container = elements['silver-pdf-canvas'].parentElement;
            container.innerHTML = `
                <div class="error-state" style="height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 2rem;">
                    <div style="font-size: 2rem; margin-bottom: 1rem;">⚠️</div>
                    <h3>PDF Not Available</h3>
                    <p>Unable to load the document PDF from our cache.</p>
                    <a href="${officialUrl}" target="_blank" class="btn btn-primary" style="margin-top: 1rem;">Try Official Source</a>
                </div>
            `;
        }
    }

    function renderPage(num) {
        pdfRendering = true;
        pdfDoc.getPage(num).then(function (page) {
            const canvas = elements['silver-pdf-canvas'];
            const ctx = canvas.getContext('2d');
            const viewport = page.getViewport({ scale: pdfScale });

            canvas.height = viewport.height;
            canvas.width = viewport.width;

            const renderContext = {
                canvasContext: ctx,
                viewport: viewport
            };
            const renderTask = page.render(renderContext);

            renderTask.promise.then(function () {
                pdfRendering = false;
                elements['pdf-page-num'].textContent = num;
                if (pdfPendingPage !== null) {
                    renderPage(pdfPendingPage);
                    pdfPendingPage = null;
                }
            });
        });
    }

    function onPrevPage() {
        if (pdfPageNum <= 1) return;
        pdfPageNum--;
        queueRenderPage(pdfPageNum);
    }

    function onNextPage() {
        if (pdfPageNum >= pdfDoc.numPages) return;
        pdfPageNum++;
        queueRenderPage(pdfPageNum);
    }

    function queueRenderPage(num) {
        if (pdfRendering) {
            pdfPendingPage = num;
        } else {
            renderPage(num);
        }
    }

    // Data Handling
    async function loadData(doc) {
        const container = elements['silver-data-content'];
        container.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Loading extracted data...</p></div>';

        // Currently only PTRs (Type P) have structured extraction
        if (doc.filing_type !== 'P') {
            currentDocData = null; // No structured data
            renderAuditView();
            return;
        }

        try {
            // Construct path for structured data
            // silver/house/financial/structured_code/year=YYYY/filing_type=X/doc_id=ID.json
            const path = `silver/house/financial/structured_code/year=${doc.year}/filing_type=${doc.filing_type}/doc_id=${doc.doc_id}.json`;
            const url = `${API_BASE}/${path}`;

            const response = await fetch(url);
            if (!response.ok) {
                if (response.status === 403 || response.status === 404) {
                    currentDocData = null;
                    renderAuditView();
                    return;
                }
                throw new Error('Failed to load data');
            }

            const data = await response.json();
            currentDocData = data;
            renderAuditView();

        } catch (error) {
            console.error('Error loading data:', error);
            container.innerHTML = `<div class="error-state">Failed to load extracted data.</div>`;
        }
    }

    async function renderAuditView() {
        const view = elements['audit-view-select'] ? elements['audit-view-select'].value : 'structured';
        const container = elements['silver-data-content'];
        const doc = allDocuments.find(d => d.doc_id === currentDocId);

        if (view === 'structured') {
            if (currentDocData) {
                renderStructuredData(currentDocData, container);
            } else {
                // Fallback if structured data isn't loaded
                container.innerHTML = `
                    <div class="alert alert-info">
                        <div class="alert-title">Extraction Not Available</div>
                        <div class="alert-description">
                            Structured data extraction is currently only available for <strong>Periodic Transaction Reports (PTR)</strong>.
                            <br><br>
                            This document is a <strong>${getFilingTypeLabel(doc ? doc.filing_type : '')}</strong>.
                        </div>
                    </div>
                `;
            }
        } else if (view === 'raw_json') {
            // Show currentDocData if available, else show the basic doc object
            const dataToShow = currentDocData || doc;
            container.innerHTML = `<div class="json-display"><pre style="font-size: 0.8rem; overflow: auto;">${JSON.stringify(dataToShow, null, 2)}</pre></div>`;
        } else if (view === 'extracted_text') {
            if (!currentDocText) {
                await loadText(currentDocId);
            }
            // Check again after load
            const text = currentDocText || 'No text content available.';
            container.innerHTML = `<div class="text-display" style="white-space: pre-wrap; font-family: monospace; font-size: 0.8rem; padding: 1rem; background: var(--surface-hover); border-radius: 4px; overflow: auto; height: 100%;">${escapeHtml(text)}</div>`;
        }
    }

    async function loadText(docId) {
        const doc = allDocuments.find(d => d.doc_id === docId);
        if (!doc) return;

        const container = elements['silver-data-content'];
        container.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Loading text...</p></div>';

        try {
            const path = `silver/house/financial/text/year=${doc.year}/doc_id=${doc.doc_id}/raw_text.txt.gz`;
            const url = `${API_BASE}/${path}`;
            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to load text');

            const blob = await response.blob();
            const arrayBuffer = await blob.arrayBuffer();

            // Decompress using pako if available, else try simple text decode
            try {
                if (window.pako) {
                    currentDocText = pako.inflate(new Uint8Array(arrayBuffer), { to: 'string' });
                } else {
                    currentDocText = "Error: Pako library not loaded.";
                }
            } catch (e) {
                console.error('Decompression failed', e);
                currentDocText = "Error: Could not decompress text (Invalid GZIP).";
            }
        } catch (e) {
            currentDocText = "Error: Could not load text (404 Not Found or Access Denied).";
        }
    }

    function renderStructuredData(data, container) {
        let html = '';
        const meta = data.extraction_metadata || {};

        // Metadata Section
        html += `
            <div class="data-section">
                <div class="data-section-title">Extraction Metadata</div>
                <div class="metadata-grid">
                    <div><strong>Method:</strong> ${meta.method || meta.extraction_method || 'Unknown'}</div>
                    <div><strong>Confidence:</strong> ${meta.confidence_score ? (meta.confidence_score * 100).toFixed(1) + '%' : 'N/A'}</div>
                    <div><strong>Processed:</strong> ${meta.extraction_timestamp || meta.processed_at || 'N/A'}</div>
                    <div><strong>Text Length:</strong> ${meta.text_length ? meta.text_length.toLocaleString() + ' chars' : 'N/A'}</div>
                    <div><strong>Filing Type:</strong> ${meta.filing_type || data.filing_type || 'N/A'}</div>
                </div>
            </div>
        `;

        // Transactions (if available)
        if (data.transactions && data.transactions.length > 0) {
            html += `
                <div class="data-section">
                    <div class="data-section-title">Transactions (${data.transactions.length})</div>
                    <div class="table-container">
                        <table class="trans-table">
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>Owner</th>
                                    <th>Ticker</th>
                                    <th>Asset</th>
                                    <th>Type</th>
                                    <th>Amount</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.transactions.map(t => `
                                    <tr class="trans-row">
                                        <td>${t.transaction_date || '-'}</td>
                                        <td>${getOwnerLabel(t.owner_code)}</td>
                                        <td><span class="code-inline">${t.ticker || '-'}</span></td>
                                        <td>${t.asset_name || t.asset_description || '-'}</td>
                                        <td class="${getTransTypeClass(t.transaction_type)}">${t.transaction_type || '-'}</td>
                                        <td>${t.amount_range || t.amount || '-'}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        } else {
            html += `
                <div class="data-section">
                    <div class="data-section-title">Transactions</div>
                    <p class="text-muted" style="font-size: 0.9rem; font-style: italic;">No structured transactions found.</p>
                </div>
            `;
        }

        // Raw JSON Toggle - REMOVED (Moved to Audit View Dropdown)

        container.innerHTML = html;
    }

    // Utilities
    function escapeHtml(text) {
        if (!text) return '';
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function setListLoading(isLoading) {
        const list = elements['silver-doc-list'];
        if (isLoading) {
            list.innerHTML = '<div class="loading-state"><div class="spinner" style="width: 20px; height: 20px; border-width: 2px;"></div></div>';
        }
    }

    function getFilingTypeLabel(code) {
        const labels = {
            'P': 'Periodic Transaction',
            'A': 'Annual',
            'T': 'Termination',
            'N': 'New Filer',
            'M': 'Amendment',
            'D': 'Annual (Original)'
        };
        return labels[code] || code;
    }

    function getOwnerLabel(code) {
        if (!code) return '-';
        const labels = {
            'SP': 'Spouse',
            'DC': 'Dependent Child',
            'JT': 'Joint',
            '--': 'Self'
        };
        return labels[code] || code;
    }

    function getTransTypeClass(type) {
        if (!type) return '';
        const t = type.toLowerCase();
        if (t.includes('purchase') || t === 'p') return 'trans-type-purchase';
        if (t.includes('sale') || t === 's') return 'trans-type-sale';
        if (t.includes('exchange') || t === 'e') return 'trans-type-exchange';
        return '';
    }

    function initResizer() {
        const resizer = elements['silver-resizer'];
        const left = elements['silver-pane-left'];
        const right = elements['silver-pane-right'];
        const container = elements['silver-content-pane'];

        if (!resizer || !left || !right || !container) return;

        let dragging = false;

        resizer.addEventListener('mousedown', (e) => {
            dragging = true;
            resizer.classList.add('active');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', (e) => {
            if (!dragging) return;
            const rect = container.getBoundingClientRect();
            let pct = ((e.clientX - rect.left) / rect.width) * 100;
            pct = Math.min(75, Math.max(25, pct)); // Limit between 25% and 75%
            left.style.width = `${pct}%`;
            right.style.width = `${100 - pct}%`;
        });

        document.addEventListener('mouseup', () => {
            if (dragging) {
                dragging = false;
                resizer.classList.remove('active');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                // Resize PDF
                if (pdfDoc) renderPage(pdfPageNum);
            }
        });
    }

})();
