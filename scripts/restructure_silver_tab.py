#!/usr/bin/env python3
"""Restructure Silver tab to include sidebar with Documents and PTR Transactions views."""

import re
from pathlib import Path

def main():
    html_path = Path(__file__).parent.parent / "website" / "index.html"

    print(f"Reading {html_path}...")
    html = html_path.read_text()

    # Find the Silver tab content (starts at "<!-- Silver Tab" and ends before "<!-- PTR")
    silver_start = html.find("<!-- Silver Tab: Normalized Data -->")
    ptr_start = html.find("<!-- PTR Transactions Tab -->")
    gold_start = html.find("<!-- Gold Analytics Tab -->")

    # Extract Silver tab content (without the container divs)
    silver_section = html[silver_start:ptr_start]

    # Extract PTR tab content
    ptr_section = html[ptr_start:gold_start]

    # Extract Documents view content from Silver tab (everything inside card-content)
    docs_content_match = re.search(
        r'<div class="card-content">(.*?)</div>\s*</div>\s*</div>\s*<!-- PTR',
        silver_section,
        re.DOTALL
    )

    if not docs_content_match:
        print("ERROR: Could not find Silver tab content")
        return 1

    docs_content = docs_content_match.group(1)

    # Extract PTR view content from PTR tab
    ptr_content_match = re.search(
        r'<div class="card-content">(.*?)</div>\s*</div>\s*</div>\s*<!-- Gold',
        ptr_section,
        re.DOTALL
    )

    if not ptr_content_match:
        print("ERROR: Could not find PTR tab content")
        return 1

    ptr_content = ptr_content_match.group(1)

    # Create new Silver tab with sidebar
    new_silver_tab = '''<!-- Silver Tab: Data & Analytics -->
                    <div class="tab-content" data-tab="silver-filings">
                        <!-- Silver Layer Sidebar Layout -->
                        <div class="silver-layer-layout">
                            <!-- Sidebar Navigation -->
                            <aside class="silver-sidebar">
                                <h3 class="silver-sidebar-title">Silver Layer</h3>
                                <nav class="silver-sidebar-nav">
                                    <button class="silver-nav-item active" data-silver-view="documents">
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                            <polyline points="14 2 14 8 20 8"></polyline>
                                        </svg>
                                        Documents
                                    </button>
                                    <button class="silver-nav-item" data-silver-view="ptr-transactions">
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <line x1="12" y1="1" x2="12" y2="23"></line>
                                            <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
                                        </svg>
                                        PTR Transactions
                                    </button>
                                </nav>
                            </aside>

                            <!-- Main Content Area -->
                            <div class="silver-main-content">
                                <!-- Documents View -->
                                <div class="silver-view active" data-silver-view="documents">
                                    <div class="card">
                                        <div class="card-header">
                                            <h2 class="card-title">Documents Extraction Status</h2>
                                            <p class="card-description">View extraction status and metadata for all processed documents</p>
                                        </div>
                                        <div class="card-content">''' + docs_content + '''</div>
                                    </div>
                                </div>

                                <!-- PTR Transactions View -->
                                <div class="silver-view" data-silver-view="ptr-transactions">
                                    <div class="card">
                                        <div class="card-header">
                                            <h2 class="card-title">PTR Transactions</h2>
                                            <p class="card-description">Stock and securities transactions by House members</p>
                                        </div>
                                        <div class="card-content">''' + ptr_content + '''</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    '''

    # Replace old Silver and PTR tabs with new Silver tab
    new_html = html[:silver_start] + new_silver_tab + html[gold_start:]

    # Write back
    print(f"Writing updated HTML...")
    html_path.write_text(new_html)

    print("✅ Successfully restructured Silver tab!")
    print("   - Documents view: Silver layer extraction status")
    print("   - PTR Transactions view: Moved from standalone tab")

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
