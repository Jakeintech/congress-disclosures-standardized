/**
 * Gold Analytics - Sidebar Navigation & Data Loading
 * Handles navigation between different gold layer analytics views
 */

(function () {
    'use strict';

    let initialized = false;

    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initGoldAnalytics);
    } else {
        initGoldAnalytics();
    }

    function initGoldAnalytics() {
        // Listen for gold-analytics tab becoming active
        const goldTab = document.querySelector('[data-tab="gold-analytics"]');
        if (!goldTab) {
            console.warn('Gold Analytics tab not found');
            return;
        }

        // Observe tab changes
        const observer = new MutationObserver(() => {
            if (goldTab.classList.contains('active') && !initialized) {
                initialized = true;
                loadGoldData();
            }
        });

        observer.observe(goldTab, { attributes: true, attributeFilter: ['class'] });

        // Check if already active
        if (goldTab.classList.contains('active')) {
            initialized = true;
            loadGoldData();
        }

        // Setup sidebar navigation
        setupSidebarNavigation();

        console.log('✅ Gold Analytics initialized');
    }

    function setupSidebarNavigation() {
        const navItems = document.querySelectorAll('.gold-nav-item');
        const views = document.querySelectorAll('.gold-view');

        navItems.forEach(item => {
            item.addEventListener('click', () => {
                const viewName = item.dataset.goldView;

                // Update active nav item
                navItems.forEach(nav => nav.classList.remove('active'));
                item.classList.add('active');

                // Show corresponding view
                views.forEach(view => {
                    if (view.dataset.goldView === viewName) {
                        view.classList.add('active');
                    } else {
                        view.classList.remove('active');
                    }
                });
            });
        });
    }

    async function loadGoldData() {
        console.log('Loading gold analytics data...');

        // Initialize Document Quality (already has data)
        if (typeof initDocumentQualityTab === 'function') {
            await initDocumentQualityTab();
        }

        // Load other views
        loadMemberTradingStats();
        loadTrendingStocks();
        loadSectorAnalysis();
        loadNetworkGraph();
    }

    async function loadMemberTradingStats() {
        try {
            const response = await fetch('https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/website/data/member_trading_stats.json');
            if (response.ok) {
                const data = await response.json();
                if (typeof initMemberTradingStats === 'function') {
                    initMemberTradingStats(data);
                }
            }
        } catch (err) {
            console.log('Member trading stats not yet available');
        }
    }

    async function loadTrendingStocks() {
        try {
            const response = await fetch('https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/website/data/trending_stocks.json');
            if (response.ok) {
                const data = await response.json();
                if (typeof initTrendingStocks === 'function') {
                    initTrendingStocks(data);
                }
            }
        } catch (err) {
            console.log('Trending stocks not yet available');
        }
    }

    async function loadSectorAnalysis() {
        try {
            const response = await fetch('https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/website/data/sector_analysis.json');
            if (response.ok) {
                const data = await response.json();
                if (typeof initSectorAnalysis === 'function') {
                    initSectorAnalysis(data);
                }
            }
        }
        } catch (err) {
        console.log('Sector analysis not yet available');
    }
}

    async function loadNetworkGraph() {
    try {
        const response = await fetch('https://congress-disclosures-standardized.s3.us-east-1.amazonaws.com/website/data/network_graph.json');
        if (response.ok) {
            const data = await response.json();
            if (typeof initNetworkGraph === 'function') {
                initNetworkGraph(data);
            }
        }
    } catch (err) {
        console.log('Network graph not yet available');
    }
}
}) ();
