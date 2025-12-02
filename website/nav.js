/**
 * Shared Navigation Component
 * Injects the navigation header into pages and highlights the active link.
 */

document.addEventListener('DOMContentLoaded', () => {
    injectNavigation();
});

function injectNavigation() {
    const navContainer = document.getElementById('nav-container');
    if (!navContainer) return;

    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const inSubdir = window.location.pathname.includes('/api-docs/');
    const base = inSubdir ? '../' : '';

    const navHTML = `
    <header class="header">
        <div class="header-content">
            <div class="header-left">
                <h1>Congress Financial Disclosures</h1>
                <p class="subtitle">Standardized access to U.S. House financial disclosure reports</p>
            </div>
            <div class="header-right">
                <nav class="main-nav">
                    <a href="${base}index.html" class="nav-link ${isActive(currentPage, 'index.html')}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="3" width="7" height="7"></rect>
                            <rect x="14" y="3" width="7" height="7"></rect>
                            <rect x="14" y="14" width="7" height="7"></rect>
                            <rect x="3" y="14" width="7" height="7"></rect>
                        </svg>
                        Dashboard
                    </a>
                    <a href="${base}documents.html" class="nav-link ${isActive(currentPage, 'documents.html')}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                        </svg>
                        Documents
                    </a>
                    <a href="${base}transactions.html" class="nav-link ${isActive(currentPage, 'transactions.html')}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                        </svg>
                        Transactions
                    </a>
                    <a href="${base}analytics.html" class="nav-link ${isActive(currentPage, 'analytics.html')}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
                            <path d="M2 17l10 5 10-5M2 12l10 5 10-5"></path>
                        </svg>
                        Analytics
                    </a>
                    <a href="${base}network.html" class="nav-link ${isActive(currentPage, 'network.html')}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="2" y1="12" x2="22" y2="12"></line>
                            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                        </svg>
                        Network
                    </a>
                    <a href="${base}quality.html" class="nav-link ${isActive(currentPage, 'quality.html')}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
                        </svg>
                        Quality
                    </a>
                    <a href="${base}downloads.html" class="nav-link ${isActive(currentPage, 'downloads.html')}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        Downloads
                    </a>
                    <a href="${base}api-docs/index.html" class="nav-link ${isActive(currentPage, 'api-docs')}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M16 18l2-2 4 4-4 4-2-2m-9-3h12a3 3 0 003-3V8a3 3 0 00-3-3H4a3 3 0 00-3 3v6a3 3 0 003 3z"></path>
                            <path d="M7 8v8m5-8v8"></path>
                        </svg>
                        API Docs
                    </a>
                </nav>
            </div>
        </div>
    </header>
    `;

    navContainer.innerHTML = navHTML;
}

function isActive(currentPage, linkPage) {
    if (currentPage === linkPage) return 'active';
    if (currentPage === '' && linkPage === 'index.html') return 'active';
    // Handle api-docs directory
    if (linkPage === 'api-docs' && (currentPage.includes('api-docs') || window.location.pathname.includes('api-docs'))) return 'active';
    return '';
}
