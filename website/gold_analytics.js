/**
 * Gold Analytics - Sidebar Navigation
 * Handles navigation between different gold layer analytics views
 */

(function() {
    'use strict';

    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initGoldAnalytics);
    } else {
        initGoldAnalytics();
    }

    function initGoldAnalytics() {
        const navItems = document.querySelectorAll('.gold-nav-item');
        const views = document.querySelectorAll('.gold-view');

        // Handle sidebar navigation clicks
        navItems.forEach(item => {
            item.addEventListener('click', () => {
                const viewName = item.dataset.goldView;

                // Don't navigate if it's a "Coming Soon" item
                if (item.querySelector('.badge-secondary')) {
                    return;
                }

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

        console.log('✅ Gold Analytics navigation initialized');
    }
})();
