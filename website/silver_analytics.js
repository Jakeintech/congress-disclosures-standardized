/**
 * Silver Analytics - Dynamic Sidebar & Data Loading
 * Shows all available Silver layer tables as a GUI over the database
 */

(function () {
    'use strict';

    const SILVER_TABLES = [
        {
            id: 'documents',
            name: 'Documents',
            icon: '📄',
            description: 'Extracted document metadata',
            s3Path: 'silver/house/financial/documents/',
        }
    ];

    // Wait for DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSilverAnalytics);
    } else {
        initSilverAnalytics();
    }

    function initSilverAnalytics() {
        const silverTab = document.querySelector('[data-tab="silver-filings"]');
        if (!silverTab) {
            console.warn('Silver tab not found');
            return;
        }

        // Setup sidebar navigation
        setupSilverSidebar();

        // Load data when tab becomes active
        const observer = new MutationObserver(() => {
            if (silverTab.classList.contains('active')) {
                loadSilverTable('filings'); // Load filings by default
            }
        });

        observer.observe(silverTab, { attributes: true, attributeFilter: ['class'] });

        if (silverTab.classList.contains('active')) {
            loadSilverTable('filings');
        }

        console.log('✅ Silver Analytics initialized');
    }

    function setupSilverSidebar() {
        const silverTabContent = document.querySelector('[data-tab="silver-filings"]');
        if (!silverTabContent) return;

        // Create sidebar layout
        const layout = document.createElement('div');
        layout.className = 'silver-analytics-layout';
        layout.innerHTML = `
            <div class="silver-sidebar">
                <h3 class="silver-sidebar-title">Silver Tables</h3>
                <nav class="silver-sidebar-nav">
                    ${SILVER_TABLES.map((table, idx) => `
                        <button class="silver-nav-item ${idx === 0 ? 'active' : ''}" data-silver-table="${table.id}">
                            <span style="font-size: 1.2rem; margin-right: 0.5rem;">${table.icon}</span>
                            <div style="flex: 1; text-align: left;">
                                <div style="font-weight: 600;">${table.name}</div>
                                <div style="font-size: 0.8rem; opacity: 0.7;">${table.description}</div>
                            </div>
                        </button>
                    `).join('')}
                </nav>
            </div>
            <div class="silver-main-content">
                ${SILVER_TABLES.map((table, idx) => `
                    <div class="silver-view ${idx === 0 ? 'active' : ''}" data-silver-table="${table.id}">
                        <div class="card">
                            <div class="card-header">
                                <h2 class="card-title">${table.icon} ${table.name}</h2>
                                <p class="card-description">${table.description}</p>
                            </div>
                            <div class="card-content">
                                <div class="loading-state">
                                    <div class="spinner"></div>
                                    <p>Loading ${table.name.toLowerCase()}...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        // Replace existing content
        const cardContent = silverTabContent.querySelector('.silver-layer-layout');
        if (cardContent) {
            // If the layout already exists (from static HTML), replace it or bind to it.
            // But here we are dynamically creating it as per original design.
            // The static HTML in index.html lines 210-300+ seems to be a hardcoded version.
            // We should probably replace the *entire* content of the tab to be safe and dynamic.
            silverTabContent.innerHTML = '';
            silverTabContent.appendChild(layout);
        } else {
            // Fallback if structure is different
            silverTabContent.innerHTML = '';
            silverTabContent.appendChild(layout);
        }

        // Setup navigation clicks
        const navItems = layout.querySelectorAll('.silver-nav-item');
        navItems.forEach(item => {
            item.addEventListener('click', () => {
                const tableId = item.dataset.silverTable;

                // Update active nav
                navItems.forEach(nav => nav.classList.remove('active'));
                item.classList.add('active');

                // Update active view
                const views = layout.querySelectorAll('.silver-view');
                views.forEach(view => {
                    if (view.dataset.silverTable === tableId) {
                        view.classList.add('active');
                    } else {
                        view.classList.remove('active');
                    }
                });

                // Load data for this table
                loadSilverTable(tableId);
            });
        });
    }

    async function loadSilverTable(tableId) {
        const table = SILVER_TABLES.find(t => t.id === tableId);
        if (!table) return;

        const view = document.querySelector(`.silver-view[data-silver-table="${tableId}"]`);
        if (!view) return;

        console.log(`Loading Silver table: ${tableId}`);

        try {
            // Load data from manifest or S3
            const manifestUrl = `https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/silver_${tableId}.json`;
            const response = await fetch(manifestUrl);

            if (response.ok) {
                const data = await response.json();
                renderSilverTable(view, table, data);
            } else {
                // Fallback: show parquet download links
                renderParquetLinks(view, table);
            }
        } catch (error) {
            console.log(`Manifest not available for ${tableId}, showing parquet links`);
            renderParquetLinks(view, table);
        }
    }

    function renderSilverTable(view, table, data) {
        const cardContent = view.querySelector('.card-content');
        const records = data.records || data.data || data;

        if (table.id === 'documents') {
            renderDocumentsDashboard(cardContent, table, records);
        } else {
            renderDefaultTable(cardContent, table, records);
        }
    }

    function renderDocumentsDashboard(container, table, records) {
        const totalDocs = records.length;
        const successDocs = records.filter(d => d.extraction_status === 'success').length;
        const pendingDocs = records.filter(d => d.extraction_status === 'pending').length;
        const totalPages = records.reduce((sum, d) => sum + (d.pages || 0), 0);
        const uniqueFilers = new Set(records.map(d => d.member_name)).size;

        const successRate = totalDocs > 0 ? ((successDocs / totalDocs) * 100).toFixed(1) + '%' : '0%';
        const avgPages = totalDocs > 0 ? (totalPages / totalDocs).toFixed(1) : '0';

        const html = `
            <div class="dashboard-grid">
                <div class="stats-column">
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value">${totalDocs.toLocaleString()}</div>
                            <div class="stat-label">Total Documents</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${uniqueFilers.toLocaleString()}</div>
                            <div class="stat-label">Unique Filers</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${successRate}</div>
                            <div class="stat-label">Success Rate</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${avgPages}</div>
                            <div class="stat-label">Avg Pages/Doc</div>
                        </div>
                    </div>
                </div>
                <div class="chart-column">
                    <div style="position: relative; height: 200px; width: 100%;">
                        <canvas id="silver-status-chart-${Date.now()}"></canvas>
                    </div>
                </div>
            </div>
            ${renderTableHtml(records)}
            ${renderDownloadSection(table)}
        `;

        container.innerHTML = html;

        // Render Chart
        const canvas = container.querySelector('canvas');
        if (canvas) {
            const statusCounts = { 'Success': 0, 'Pending': 0, 'Failed': 0 };
            records.forEach(d => {
                if (d.extraction_status === 'success') statusCounts['Success']++;
                else if (d.extraction_status === 'pending') statusCounts['Pending']++;
                else statusCounts['Failed']++;
            });

            new Chart(canvas, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(statusCounts),
                    datasets: [{
                        data: Object.values(statusCounts),
                        backgroundColor: ['hsl(142, 76%, 60%)', 'hsl(48, 96%, 60%)', 'hsl(0, 84%, 60%)'],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'right', labels: { boxWidth: 12 } },
                        title: { display: true, text: 'Extraction Status' }
                    }
                }
            });
        }
    }

    function renderDefaultTable(container, table, records) {
        const sampleRecord = Array.isArray(records) && records[0] ? records[0] : {};
        const columns = Object.keys(sampleRecord);

        const html = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">${Array.isArray(records) ? records.length : 0}</div>
                    <div class="stat-label">Total Records</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${columns.length}</div>
                    <div class="stat-label">Columns</div>
                </div>
            </div>
            ${renderTableHtml(records)}
            ${renderDownloadSection(table)}
        `;
        container.innerHTML = html;
    }

    function renderTableHtml(records) {
        const sampleRecord = Array.isArray(records) && records[0] ? records[0] : {};
        const columns = Object.keys(sampleRecord);

        return `
            <div class="table-container" style="margin-top: 2rem;">
                <table class="table">
                    <thead>
                        <tr>
                            ${columns.slice(0, 8).map(col => `<th>${col.replace(/_/g, ' ').toUpperCase()}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${records.slice(0, 100).map(record => `
                            <tr>
                                ${columns.slice(0, 8).map(col => {
            let value = record[col];
            if (typeof value === 'object') value = JSON.stringify(value);
            if (value === null || value === undefined) value = '-';
            if (typeof value === 'string' && value.length > 50) value = value.substring(0, 50) + '...';
            return `<td>${value}</td>`;
        }).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    function renderDownloadSection(table) {
        return `
            <div class="alert alert-info" style="margin-top: 2rem;">
                <div class="alert-title">Download Full Dataset</div>
                <div class="alert-description">
                    <strong>Parquet:</strong> <a href="https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/${table.s3Path}year=2025/part-0000.parquet" download>Download ${table.name}</a><br>
                    <strong>Query with:</strong> <code>pd.read_parquet('${table.id}.parquet')</code> or <code>SELECT * FROM '${table.id}.parquet'</code>
                </div>
            </div>
        `;
    }

    function renderParquetLinks(view, table) {
        const cardContent = view.querySelector('.card-content');

        const html = `
            <div class="alert alert-info">
                <div class="alert-title">Download ${table.name} Dataset</div>
                <div class="alert-description">
                    <p>This table contains ${table.description.toLowerCase()}.</p>
                    <br>
                    <strong>Parquet File:</strong> <a href="https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/${table.s3Path}year=2025/part-0000.parquet" download>Download</a><br>
                    <strong>Query with Pandas:</strong> <code>pd.read_parquet('${table.id}.parquet')</code><br>
                    <strong>Query with DuckDB:</strong> <code>SELECT * FROM '${table.id}.parquet' LIMIT 100</code>
                </div>
            </div>

            <div class="alert alert-warning" style="margin-top: 1rem;">
                <div class="alert-title">Preview Not Available</div>
                <div class="alert-description">
                    To view this data in the browser, generate a manifest file with:
                    <code>python scripts/generate_silver_manifest.py --table ${table.id}</code>
                </div>
            </div>
        `;

        cardContent.innerHTML = html;
    }

    // Export for testing
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = { SILVER_TABLES };
    }
})();
