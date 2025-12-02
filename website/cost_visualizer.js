/**
 * Cost Visualizer
 * Fetches and displays AWS cost data from the API.
 */

// Use config if available, otherwise use the deployed API Gateway
const API_BASE_URL = window.API_BASE_URL || 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com';

async function fetchCosts() {
    try {
        const response = await fetch(`${API_BASE_URL}/costs`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Failed to fetch costs:', error);
        const errorEl = document.getElementById('cost-error');
        if (errorEl) {
            errorEl.textContent = `Failed to load cost data: ${error.message}`;
            errorEl.classList.remove('hidden');
        }
        return null;
    }
}

function renderCostTable(data) {
    const tableBody = document.getElementById('cost-table-body');
    if (!tableBody) return;

    tableBody.innerHTML = '';

    if (!data || !data.daily_costs) return;

    // Sort by date descending
    const sortedDays = [...data.daily_costs].sort((a, b) => new Date(b.date) - new Date(a.date));

    sortedDays.forEach(day => {
        const row = document.createElement('tr');

        // Date
        const dateCell = document.createElement('td');
        dateCell.textContent = day.date;
        row.appendChild(dateCell);

        // Total Cost
        const totalCell = document.createElement('td');
        totalCell.textContent = `$${day.total_cost.toFixed(2)}`;
        row.appendChild(totalCell);

        // Services Breakdown
        const servicesCell = document.createElement('td');
        const servicesList = day.services
            .sort((a, b) => b.cost - a.cost)
            .map(s => `${s.service}: $${s.cost.toFixed(2)}`)
            .join(', ');
        servicesCell.textContent = servicesList;
        row.appendChild(servicesCell);

        tableBody.appendChild(row);
    });

    // Update summary
    const totalEl = document.getElementById('total-period-cost');
    if (totalEl) totalEl.textContent = `$${data.total_period_cost.toFixed(2)}`;

    const updatedEl = document.getElementById('last-updated');
    if (updatedEl) updatedEl.textContent = new Date(data.last_updated).toLocaleString();
}

async function initCostVisualizer() {
    const loadingEl = document.getElementById('loading');
    if (loadingEl) loadingEl.classList.remove('hidden');

    const data = await fetchCosts();

    if (loadingEl) loadingEl.classList.add('hidden');

    if (data) {
        renderCostTable(data);
        const contentEl = document.getElementById('cost-content');
        if (contentEl) contentEl.classList.remove('hidden');
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initCostVisualizer);
