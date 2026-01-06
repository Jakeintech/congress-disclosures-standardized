/**
 * Cost Visualizer
 * Fetches and displays AWS cost data from the API.
 */

// Resolve API base from config if available, otherwise use deployed API Gateway URL
const API_BASE_URL = (typeof API_GATEWAY_URL !== 'undefined' && API_GATEWAY_URL)
    ? API_GATEWAY_URL
    : 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com';

async function fetchCosts() {
    try {
        const response = await fetch(`${API_BASE_URL}/v1/costs`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Failed to fetch costs:', error);
        document.getElementById('cost-error').textContent = `Failed to load cost data: ${error.message}`;
        return null;
    }
}

function renderCostTable(data) {
    const tableBody = document.getElementById('cost-table-body');
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
    document.getElementById('total-period-cost').textContent = `$${data.total_period_cost.toFixed(2)}`;
    document.getElementById('last-updated').textContent = new Date(data.last_updated).toLocaleString();
}

async function initCostVisualizer() {
    const data = await fetchCosts();
    if (data) {
        renderCostTable(data);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initCostVisualizer);
