/**
 * S3 Browser Component
 * Reusable file browser for S3 layers (bronze/silver/gold)
 */

class S3Browser {
    constructor(containerEl, layer) {
        this.container = containerEl;
        this.layer = layer;
        this.currentPrefix = '';
        this.apiBaseUrl = window.API_BASE_URL || 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com';
    }

    async init() {
        await this.loadPath('');
    }

    async loadPath(prefix) {
        this.currentPrefix = prefix;
        this.showLoading();

        try {
            const url = `${this.apiBaseUrl}/v1/storage/${this.layer}${prefix ? `?prefix=${encodeURIComponent(prefix)}` : ''}`;
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.render(data);
        } catch (error) {
            this.showError(error.message);
        }
    }

    render(data) {
        const breadcrumbs = this.renderBreadcrumbs(data.prefix);
        const items = this.renderItems(data.folders, data.files);
        const summary = this.renderSummary(data.folders.length, data.files.length);

        this.container.innerHTML = `
            <div class="s3-browser">
                ${breadcrumbs}
                ${summary}
                ${items}
            </div>
        `;

        // Attach event listeners
        this.attachListeners();
    }

    renderBreadcrumbs(prefix) {
        const parts = prefix ? prefix.split('/').filter(p => p) : [];
        let breadcrumbs = `
            <div class="breadcrumbs">
                <a href="#" data-path="" class="breadcrumb-link">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                        <polyline points="9 22 9 12 15 12 15 22"></polyline>
                    </svg>
                    ${this.layer}
                </a>
        `;

        let currentPath = '';
        parts.forEach((part, i) => {
            currentPath += part + '/';
            breadcrumbs += `
                <span class="breadcrumb-separator">/</span>
                <a href="#" data-path="${currentPath}" class="breadcrumb-link">${part}</a>
            `;
        });

        breadcrumbs += '</div>';
        return breadcrumbs;
    }

    renderSummary(folderCount, fileCount) {
        return `
            <div class="browser-summary">
                <span>${folderCount} folders, ${fileCount} files</span>
            </div>
        `;
    }

    renderItems(folders, files) {
        if (folders.length === 0 && files.length === 0) {
            return '<div class="empty-state">No files or folders found</div>';
        }

        let html = '<div class="file-list">';

        // Folders first
        folders.forEach(folder => {
            html += `
                <div class="file-item folder-item" data-path="${folder.path}">
                    <div class="file-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                        </svg>
                    </div>
                    <div class="file-name">${this.escapeHtml(folder.name)}</div>
                    <div class="file-size">-</div>
                    <div class="file-modified">-</div>
                </div>
            `;
        });

        // Then files
        files.forEach(file => {
            const fileExt = file.name.split('.').pop().toLowerCase();
            html += `
                <div class="file-item">
                    <div class="file-icon ${fileExt}">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                        </svg>
                    </div>
                    <div class="file-name">
                        <a href="${file.url}" target="_blank" class="file-link">${this.escapeHtml(file.name)}</a>
                    </div>
                    <div class="file-size">${this.formatBytes(file.size)}</div>
                    <div class="file-modified">${this.formatDate(file.lastModified)}</div>
                </div>
            `;
        });

        html += '</div>';
        return html;
    }

    attachListeners() {
        // Breadcrumb navigation
        this.container.querySelectorAll('.breadcrumb-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const path = e.currentTarget.dataset.path;
                this.loadPath(path);
            });
        });

        // Folder navigation
        this.container.querySelectorAll('.folder-item').forEach(item => {
            item.addEventListener('click', () => {
                const path = item.dataset.path;
                this.loadPath(path);
            });
        });
    }

    showLoading() {
        this.container.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>Loading...</p>
            </div>
        `;
    }

    showError(message) {
        this.container.innerHTML = `
            <div class="error-state">
                <p>Error: ${this.escapeHtml(message)}</p>
                <button onclick="location.reload()">Retry</button>
            </div>
        `;
    }

    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 10) / 10 + ' ' + sizes[i];
    }

    formatDate(isoString) {
        const date = new Date(isoString);
        return date.toLocaleString();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export for use in HTML pages
window.S3Browser = S3Browser;
