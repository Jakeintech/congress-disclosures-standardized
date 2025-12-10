/**
 * Silver Layer Sidebar Navigation
 * Handles navigation between different Silver layer views (Documents, PTR Transactions)
 */

let currentSilverView = 'documents';
let silverInitialized = false;

/**
 * Initialize Silver layer sidebar navigation
 */
function initSilverSidebar() {
    if (silverInitialized) return;

    console.log('Initializing Silver sidebar...');

    // Setup sidebar navigation
    const navButtons = document.querySelectorAll('.silver-nav-item');
    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            const view = button.dataset.silverView;
            if (view) {
                switchSilverView(view);
            }
        });
    });

    // Listen for tab activation
    const silverTab = document.querySelector('[data-tab="silver-filings"]');
    if (silverTab) {
        const observer = new MutationObserver(() => {
            if (silverTab.classList.contains('active') && !silverInitialized) {
                silverInitialized = true;
                loadSilverData();
                loadPTRTransactions();
            }
        });

        observer.observe(silverTab, { attributes: true, attributeFilter: ['class'] });

        // Check if already active
        if (silverTab.classList.contains('active')) {
            silverInitialized = true;
            loadSilverData();
            loadPTRTransactions();
        }
    }

    console.log('Silver sidebar initialized');
}

/**
 * Switch between Silver layer views
 */
function switchSilverView(viewName) {
    console.log(`Switching to Silver view: ${viewName}`);

    currentSilverView = viewName;

    // Update sidebar navigation
    document.querySelectorAll('.silver-nav-item').forEach(btn => {
        if (btn.dataset.silverView === viewName) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Show/hide views
    document.querySelectorAll('.silver-view').forEach(view => {
        if (view.dataset.silverView === viewName) {
            view.classList.add('active');
        } else {
            view.classList.remove('active');
        }
    });
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initSilverSidebar();
});
