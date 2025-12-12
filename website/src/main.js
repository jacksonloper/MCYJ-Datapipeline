// Main application logic
import { initDB, storeQuery, getQueriesForDocument, findExistingQuery } from './indexedDB.js';
import { getApiKey } from './encryption.js';
import { queryDeepSeek } from './apiService.js';

let allAgencies = [];
let filteredAgencies = [];
let currentOpenAgencyId = null;
let currentDocumentData = null; // Store current document for queries
let apiKey = null; // Store decrypted API key

// Filter state
let filters = {
    sirOnly: false,
    violationsFilter: 'all', // 'all', 'with', 'without'
    complianceStatus: 'all' // 'all', 'not_in_compliance', 'in_compliance', 'neither'
};

// Load and display data
async function init() {
    try {
        // Initialize IndexedDB
        await initDB();
        
        // Fetch the agency data
        const response = await fetch('/data/agencies_data.json');
        if (!response.ok) {
            throw new Error(`Failed to load data: ${response.statusText}`);
        }
        
        allAgencies = await response.json();
        filteredAgencies = allAgencies;
        
        hideLoading();
        displayStats();
        displayAgencies(allAgencies);
        setupSearch();
        setupShaLookup();
        setupFilters();
        handleUrlHash();
        handleQueryStringDocument();
        
    } catch (error) {
        console.error('Error loading data:', error);
        showError(`Failed to load data: ${error.message}`);
        hideLoading();
    }
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function showError(message) {
    const errorEl = document.getElementById('error');
    errorEl.textContent = message;
    errorEl.style.display = 'block';
}

function displayStats() {
    const statsEl = document.getElementById('stats');
    
    // Use filtered agencies for stats
    const agencies = filteredAgencies;
    const totalAgencies = agencies.length;
    const totalViolations = agencies.reduce((sum, a) => sum + a.total_violations, 0);
    const totalReports = agencies.reduce((sum, a) => sum + a.total_reports, 0);
    const agenciesWithViolations = agencies.filter(a => a.total_violations > 0).length;
    
    statsEl.innerHTML = `
        <div class="stat-card">
            <div class="stat-number">${totalAgencies}</div>
            <div class="stat-label">Total Agencies</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${totalViolations}</div>
            <div class="stat-label">Total Violations</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${agenciesWithViolations}</div>
            <div class="stat-label">Agencies with Violations</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${totalReports}</div>
            <div class="stat-label">Reports/Inspections</div>
        </div>
    `;
}

function applyFilters() {
    // Start with all agencies
    let agencies = JSON.parse(JSON.stringify(allAgencies)); // Deep clone
    
    // Apply filters to each agency's violations
    agencies = agencies.map(agency => {
        if (!agency.violations || !Array.isArray(agency.violations)) {
            return agency;
        }
        
        let filteredViolations = agency.violations.filter(v => {
            // Filter by SIR only
            if (filters.sirOnly && !v.is_special_investigation) {
                return false;
            }
            
            // Filter by violations
            if (filters.violationsFilter === 'with' && v.num_violations === 0) {
                return false;
            }
            if (filters.violationsFilter === 'without' && v.num_violations > 0) {
                return false;
            }
            
            // Filter by compliance status
            if (filters.complianceStatus === 'not_in_compliance' && !v.has_not_in_compliance) {
                return false;
            }
            if (filters.complianceStatus === 'in_compliance' && !v.has_in_compliance) {
                return false;
            }
            if (filters.complianceStatus === 'neither' && (v.has_not_in_compliance || v.has_in_compliance)) {
                return false;
            }
            
            return true;
        });
        
        // Update agency stats based on filtered violations
        return {
            ...agency,
            violations: filteredViolations,
            total_violations: filteredViolations.reduce((sum, v) => sum + v.num_violations, 0),
            total_reports: filteredViolations.length
        };
    });
    
    // Remove agencies with no reports after filtering
    agencies = agencies.filter(agency => agency.total_reports > 0);
    
    filteredAgencies = agencies;
    displayStats();
    displayAgencies(filteredAgencies);
}

function setupFilters() {
    // SIR only filter
    const sirOnlyCheckbox = document.getElementById('filterSirOnly');
    sirOnlyCheckbox.addEventListener('change', (e) => {
        filters.sirOnly = e.target.checked;
        applyFilters();
    });
    
    // Violations filter
    const violationsRadios = document.querySelectorAll('input[name="violationsFilter"]');
    violationsRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            if (e.target.checked) {
                filters.violationsFilter = e.target.value;
                applyFilters();
            }
        });
    });
    
    // Compliance status filter
    const complianceRadios = document.querySelectorAll('input[name="complianceFilter"]');
    complianceRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            if (e.target.checked) {
                filters.complianceStatus = e.target.value;
                applyFilters();
            }
        });
    });
}

function displayAgencies(agencies) {
    const agenciesEl = document.getElementById('agencies');
    const noResultsEl = document.getElementById('noResults');
    
    if (agencies.length === 0) {
        agenciesEl.innerHTML = '';
        noResultsEl.style.display = 'block';
        return;
    }
    
    noResultsEl.style.display = 'none';
    
    agenciesEl.innerHTML = agencies.map(agency => {
        return `
            <div class="agency-card" id="agency-${agency.agencyId}" data-agency-id="${agency.agencyId}">
                <div class="agency-header">
                    <div>
                        <div class="agency-name">
                            ${escapeHtml(agency.AgencyName || 'Unknown Agency')}
                            <button class="copy-link-btn" onclick="copyAgencyLink('${agency.agencyId}', event)" title="Copy link to this agency">
                                🔗
                            </button>
                        </div>
                        <div style="color: #666; font-size: 0.9em; margin-top: 4px;">ID: ${escapeHtml(agency.agencyId)}</div>
                    </div>
                </div>
                
                <div class="agency-stats">
                    <span class="stat-badge violations-badge">
                        ⚠️ ${agency.total_violations} Violations
                    </span>
                    <span class="stat-badge reports-badge">
                        📋 ${agency.total_reports} Reports
                    </span>
                </div>
                
                <div class="agency-details" id="details-${agency.agencyId}">
                    ${renderViolations(agency.violations)}
                </div>
            </div>
        `;
    }).join('');
    
    // Add click handlers to expand/collapse details
    document.querySelectorAll('.agency-card').forEach(card => {
        card.addEventListener('click', (e) => {
            // Don't toggle if clicking on the copy link button
            if (e.target.closest('.copy-link-btn')) {
                return;
            }
            
            const agencyId = card.dataset.agencyId;
            openAgencyCard(agencyId);
        });
    });
}

function renderViolations(violations) {
    if (!violations || violations.length === 0) {
        return `
            <div class="violations-list">
                <div class="section-title">Violations & Reports</div>
                <p style="color: #666;">No reports available.</p>
            </div>
        `;
    }
    
    // Sort by date (most recent first)
    const sortedViolations = [...violations].sort((a, b) => {
        return new Date(b.date_processed) - new Date(a.date_processed);
    });
    
    const violationItems = sortedViolations.map(v => {
        const hasViolations = v.num_violations > 0;
        const violationClass = hasViolations ? 'has-violations' : '';
        
        // Use document title if available, otherwise fall back to agency name
        const displayTitle = v.document_title || v.agency_name || 'Untitled Document';
        
        return `
            <div class="violation-item ${violationClass}">
                <div style="font-weight: 600; margin-bottom: 4px;">
                    ${escapeHtml(displayTitle)}
                    ${v.sha256 ? `
                        <button class="copy-link-btn" onclick="copyDocumentLink('${v.sha256}', event)" title="Copy link to this document">
                            🔗
                        </button>
                    ` : ''}
                </div>
                <div class="date">${escapeHtml(v.date || 'Date not specified')}</div>
                ${hasViolations ? `
                    <div class="violations-text">
                        ${v.num_violations} violation${v.num_violations > 1 ? 's' : ''}: 
                        ${escapeHtml(v.violations_list)}
                    </div>
                ` : `
                    <div style="color: #27ae60;">✓ No violations found</div>
                `}
                ${v.sha256 ? `
                    <div style="margin-top: 8px;">
                        <button class="view-document-btn" onclick="viewDocument('${v.sha256}', event)">
                            📄 View Full Document
                        </button>
                        <div id="query-count-${v.sha256}" style="margin-top: 8px; font-size: 0.85em; color: #666; font-style: italic;">
                            <span class="query-count-placeholder" data-sha="${v.sha256}">Loading query history...</span>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
    
    // After rendering, load query counts for each document using microtask
    queueMicrotask(() => {
        sortedViolations.forEach(v => {
            if (v.sha256) {
                loadQueryCount(v.sha256);
            }
        });
    });
    
    return `
        <div class="violations-list">
            <div class="section-title">Violations & Reports (${violations.length})</div>
            ${violationItems}
        </div>
    `;
}

async function viewDocument(sha256, event) {
    if (event) {
        event.stopPropagation();
    }
    
    try {
        const response = await fetch(`/documents/${sha256}.json`);
        if (!response.ok) {
            throw new Error(`Failed to load document: ${response.statusText}`);
        }
        
        const docData = await response.json();
        
        // Find document metadata from agencies data
        let docMetadata = null;
        for (const agency of allAgencies) {
            if (agency.violations && Array.isArray(agency.violations)) {
                const violation = agency.violations.find(v => v.sha256 === sha256);
                if (violation) {
                    docMetadata = {
                        title: violation.document_title || violation.agency_name || 'Untitled Document',
                        num_violations: violation.num_violations || 0,
                        violations_list: violation.violations_list || ''
                    };
                    break;
                }
            }
        }
        
        showDocumentModal(docData, docMetadata);
    } catch (error) {
        console.error('Error loading document:', error);
        alert(`Failed to load document: ${error.message}`);
    }
}

function highlightText(text, highlightRanges) {
    // highlightRanges is an array of {start, end, className} objects
    if (!highlightRanges || highlightRanges.length === 0) {
        return escapeHtml(text);
    }
    
    // Sort ranges by start position
    const sortedRanges = [...highlightRanges].sort((a, b) => a.start - b.start);
    
    let result = '';
    let lastIndex = 0;
    
    for (const range of sortedRanges) {
        // Add text before highlight
        if (range.start > lastIndex) {
            result += escapeHtml(text.substring(lastIndex, range.start));
        }
        
        // Add highlighted text
        const highlightedText = escapeHtml(text.substring(range.start, range.end));
        result += `<mark class="${range.className}">${highlightedText}</mark>`;
        
        lastIndex = range.end;
    }
    
    // Add remaining text
    if (lastIndex < text.length) {
        result += escapeHtml(text.substring(lastIndex));
    }
    
    return result;
}

function findTextPositions(text, pattern, flags = 'gi') {
    const positions = [];
    const regex = new RegExp(pattern, flags);
    let match;
    
    while ((match = regex.exec(text)) !== null) {
        positions.push({
            start: match.index,
            end: match.index + match[0].length
        });
    }
    
    return positions;
}

function showDocumentModal(docData, docMetadata) {
    const modal = document.getElementById('documentModal') || createDocumentModal();
    const modalContent = modal.querySelector('.modal-document-content');
    
    // Store current document data for queries
    currentDocumentData = docData;
    
    // Validate document data
    if (!docData.pages || !Array.isArray(docData.pages)) {
        console.error('Invalid document data: pages array missing or invalid');
        return;
    }
    
    // Get highlighting metadata
    const highlighting = docData.highlighting || {};
    
    // Format the document pages with highlighting
    const totalPages = docData.pages.length;
    const pagesHtml = docData.pages.map((page, pageIndex) => {
        let pageContent = page;
        const highlightRanges = [];
        
        // Highlight compliance phrases
        if (highlighting.not_in_compliance_pages && highlighting.not_in_compliance_pages.includes(pageIndex)) {
            const positions = findTextPositions(page, 'is\\s+not\\s+in\\s+compliance', 'gi');
            positions.forEach(pos => {
                highlightRanges.push({
                    ...pos,
                    className: 'highlight-not-in-compliance'
                });
            });
        }
        
        if (highlighting.in_compliance_pages && highlighting.in_compliance_pages.includes(pageIndex)) {
            const positions = findTextPositions(page, '(?<!not\\s)is\\s+in\\s+compliance', 'gi');
            positions.forEach(pos => {
                highlightRanges.push({
                    ...pos,
                    className: 'highlight-in-compliance'
                });
            });
        }
        
        // Highlight rules and violation statuses
        if (highlighting.violations_detailed && Array.isArray(highlighting.violations_detailed)) {
            for (const vDetail of highlighting.violations_detailed) {
                if (vDetail.rule_page === pageIndex) {
                    // Highlight the rule reference
                    const rulePattern = vDetail.rule.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                    const positions = findTextPositions(page, rulePattern, 'gi');
                    positions.forEach(pos => {
                        highlightRanges.push({
                            ...pos,
                            className: 'highlight-rule'
                        });
                    });
                }
                
                if (vDetail.status_page === pageIndex) {
                    // Highlight violation established/not established
                    const statusPattern = vDetail.violation_status === 'established' 
                        ? '(?:Repeat\\s+)?Violation\\s+Established' 
                        : 'Violation\\s+Not\\s+Established';
                    const positions = findTextPositions(page, statusPattern, 'gi');
                    positions.forEach(pos => {
                        highlightRanges.push({
                            ...pos,
                            className: vDetail.violation_status === 'established' 
                                ? 'highlight-violation-established' 
                                : 'highlight-violation-not-established'
                        });
                    });
                }
            }
        }
        
        // Apply highlighting
        const highlightedContent = highlightRanges.length > 0 
            ? highlightText(page, highlightRanges)
            : escapeHtml(page);
        
        return `
            <div class="document-page">
                <div class="page-number">Page ${pageIndex + 1} of ${totalPages}</div>
                <pre class="page-text">${highlightedContent}</pre>
            </div>
        `;
    }).join('');
    
    modalContent.innerHTML = `
        <div class="document-header">
            <h2>Document Details</h2>
            <button class="close-modal" onclick="closeDocumentModal()">✕</button>
        </div>
        <div class="document-info">
            ${docMetadata ? `
                <div><strong>Title:</strong> ${escapeHtml(docMetadata.title)}</div>
                ${docMetadata.num_violations > 0 ? `
                    <div style="word-break: break-word; overflow-wrap: break-word;"><strong>Violations Found:</strong> ${escapeHtml(docMetadata.violations_list)}</div>
                ` : `
                    <div style="color: #27ae60;"><strong>Violations:</strong> ✓ No violations found</div>
                `}
            ` : ''}
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <strong style="flex-shrink: 0;">SHA256:</strong>
                <span style="overflow-x: auto; white-space: nowrap; font-family: monospace; font-size: 0.9em; flex: 1; min-width: 0;">${escapeHtml(docData.sha256)}</span>
                <div style="display: flex; gap: 8px; flex-shrink: 0;">
                    <button class="copy-link-btn" onclick="copySHA('${docData.sha256}', event)" title="Copy SHA256">
                        📋
                    </button>
                    <button class="copy-link-btn" onclick="copyDocumentLink('${docData.sha256}', event)" title="Copy link to this document">
                        🔗
                    </button>
                </div>
            </div>
            <div><strong>Date Processed:</strong> ${escapeHtml(docData.dateprocessed)}</div>
            <div><strong>Total Pages:</strong> ${totalPages}</div>
        </div>
        
        <!-- AI Query Section -->
        <div id="aiQuerySection" style="padding: 20px; background: #f8f9fa; border-bottom: 1px solid #ecf0f1;">
            <div style="margin-bottom: 15px;">
                <h3 style="margin: 0 0 10px 0; color: #2c3e50; font-size: 1.1em;">🤖 Ask AI About This Document</h3>
                <p style="margin: 0; color: #666; font-size: 0.9em;">Query DeepSeek v3.2 about this document. Responses are saved in your browser.</p>
            </div>
            
            <div id="apiKeyPrompt" style="margin-bottom: 15px;">
                <div style="display: flex; gap: 10px; align-items: flex-start;">
                    <input 
                        type="password" 
                        id="secretPassInput" 
                        placeholder="Enter secret password to unlock AI queries..."
                        style="flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px;"
                    />
                    <button 
                        id="unlockApiBtn"
                        onclick="unlockApiKey()"
                        style="padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; white-space: nowrap;"
                    >
                        🔓 Unlock
                    </button>
                </div>
                <div id="apiKeyError" style="color: #e74c3c; font-size: 0.9em; margin-top: 8px; display: none;"></div>
            </div>
            
            <div id="queryInterface" style="display: none;">
                <div style="margin-bottom: 15px;">
                    <textarea 
                        id="aiQueryInput" 
                        placeholder="Ask a question about this document..."
                        style="width: 100%; min-height: 80px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; resize: vertical; font-family: inherit;"
                    ></textarea>
                </div>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <button 
                        id="submitQueryBtn"
                        onclick="submitAiQuery()"
                        style="padding: 10px 20px; background: #27ae60; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;"
                    >
                        🚀 Submit Query
                    </button>
                    <div id="querySpinner" style="display: none;">
                        <span style="font-size: 24px; animation: spin 1s linear infinite; display: inline-block;">⏳</span>
                        <span style="margin-left: 10px; color: #666;">Processing...</span>
                    </div>
                    <div id="queryStatus" style="color: #666; font-size: 0.9em;"></div>
                </div>
            </div>
            
            <!-- Query History -->
            <div id="queryHistory" style="margin-top: 20px; display: none;">
                <h4 style="margin: 0 0 10px 0; color: #2c3e50; font-size: 1em;">Query History</h4>
                <div id="queryHistoryList"></div>
            </div>
        </div>
        
        <div class="document-pages">
            ${pagesHtml}
        </div>
    `;
    
    modal.style.display = 'flex';
    
    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden';
    
    // Load and display query history
    loadQueryHistory(docData.sha256);
    
    // Check if API key is already unlocked
    if (apiKey) {
        showQueryInterface();
    }
}

function createDocumentModal() {
    const modal = document.createElement('div');
    modal.id = 'documentModal';
    modal.className = 'modal';
    modal.innerHTML = '<div class="modal-document-content"></div>';
    document.body.appendChild(modal);
    
    // Close modal when clicking outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeDocumentModal();
        }
    });
    
    return modal;
}

function closeDocumentModal() {
    const modal = document.getElementById('documentModal');
    if (modal) {
        modal.style.display = 'none';
        
        // Re-enable body scroll when modal is closed
        document.body.style.overflow = '';
    }
}

// Make viewDocument available globally
window.viewDocument = viewDocument;
window.closeDocumentModal = closeDocumentModal;

function openAgencyCard(agencyId) {
    // If this card is already open, do nothing
    if (currentOpenAgencyId === agencyId) {
        return;
    }
    
    // Close currently open card if different from the one being opened
    if (currentOpenAgencyId && currentOpenAgencyId !== agencyId) {
        const currentDetails = document.getElementById(`details-${currentOpenAgencyId}`);
        if (currentDetails) {
            currentDetails.classList.remove('visible');
        }
    }
    
    // Open the selected card
    const details = document.getElementById(`details-${agencyId}`);
    if (details) {
        details.classList.add('visible');
        currentOpenAgencyId = agencyId;
        
        // Update URL hash without triggering scroll
        history.replaceState(null, null, `#${agencyId}`);
        
        // Scroll to the card - position top of card at top of viewport
        const card = document.getElementById(`agency-${agencyId}`);
        if (card) {
            card.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
}

function handleUrlHash() {
    const hash = window.location.hash.slice(1); // Remove the '#'
    if (hash) {
        // Check if the agency card exists before trying to open it
        const card = document.getElementById(`agency-${hash}`);
        if (card) {
            openAgencyCard(hash);
        } else {
            // If DOM is not ready, wait a bit and try again
            setTimeout(() => {
                const retryCard = document.getElementById(`agency-${hash}`);
                if (retryCard) {
                    openAgencyCard(hash);
                }
            }, 100);
        }
    }
}

async function handleQueryStringDocument() {
    // Parse query string for sha parameter
    const urlParams = new URLSearchParams(window.location.search);
    const sha = urlParams.get('sha');
    
    if (!sha) {
        return;
    }
    
    try {
        // Find the agency that contains this document
        let foundAgency = null;
        
        for (const agency of allAgencies) {
            if (agency.violations && Array.isArray(agency.violations)) {
                const violation = agency.violations.find(v => v.sha256 === sha);
                if (violation) {
                    foundAgency = agency;
                    break;
                }
            }
        }
        
        // If we found the agency, open it and scroll to it
        if (foundAgency) {
            openAgencyCard(foundAgency.agencyId);
        }
        
        // Open the document modal (this will handle errors if document doesn't exist)
        await viewDocument(sha);
    } catch (error) {
        console.error('Error handling query string document:', error);
        showError(`Failed to load document with SHA: ${sha}. ${error.message}`);
    }
}

function copyAgencyLink(agencyId, event) {
    if (event) {
        event.stopPropagation();
    }
    
    const url = `${window.location.origin}${window.location.pathname}#${agencyId}`;
    
    // Copy to clipboard
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(() => {
            // Show feedback
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = '✓';
            setTimeout(() => {
                btn.textContent = originalText;
            }, 1000);
        }).catch(err => {
            console.error('Failed to copy link:', err);
            alert('Failed to copy link to clipboard');
        });
    } else {
        // Fallback for browsers without Clipboard API
        // Create a temporary textarea element
        const textarea = document.createElement('textarea');
        textarea.value = url;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            // Show feedback
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = '✓';
            setTimeout(() => {
                btn.textContent = originalText;
            }, 1000);
        } catch (err) {
            console.error('Failed to copy link:', err);
            alert('Failed to copy link to clipboard');
        } finally {
            document.body.removeChild(textarea);
        }
    }
}

function copyDocumentLink(sha256, event) {
    if (event) {
        event.stopPropagation();
    }
    
    const url = `${window.location.origin}${window.location.pathname}?sha=${sha256}`;
    
    // Helper function to show feedback on button
    const showCopyFeedback = (btn) => {
        const originalText = btn.textContent;
        btn.textContent = '✓';
        setTimeout(() => {
            btn.textContent = originalText;
        }, 1500);
    };
    
    // Copy to clipboard
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(() => {
            showCopyFeedback(event.target);
        }).catch(err => {
            console.error('Failed to copy link:', err);
            alert('Failed to copy link to clipboard');
        });
    } else {
        // Fallback for browsers without Clipboard API
        const textarea = document.createElement('textarea');
        textarea.value = url;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            showCopyFeedback(event.target);
        } catch (err) {
            console.error('Failed to copy link:', err);
            alert('Failed to copy link to clipboard');
        } finally {
            document.body.removeChild(textarea);
        }
    }
}

function copySHA(sha256, event) {
    if (event) {
        event.stopPropagation();
    }
    
    // Helper function to show feedback on button
    const showCopyFeedback = (btn) => {
        const originalText = btn.textContent;
        btn.textContent = '✓';
        setTimeout(() => {
            btn.textContent = originalText;
        }, 1500);
    };
    
    // Copy to clipboard
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(sha256).then(() => {
            showCopyFeedback(event.target);
        }).catch(err => {
            console.error('Failed to copy SHA:', err);
            alert('Failed to copy SHA to clipboard');
        });
    } else {
        // Fallback for browsers without Clipboard API
        const textarea = document.createElement('textarea');
        textarea.value = sha256;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            showCopyFeedback(event.target);
        } catch (err) {
            console.error('Failed to copy SHA:', err);
            alert('Failed to copy SHA to clipboard');
        } finally {
            document.body.removeChild(textarea);
        }
    }
}

// Make functions available globally
window.copyAgencyLink = copyAgencyLink;
window.copyDocumentLink = copyDocumentLink;
window.copySHA = copySHA;

// Listen for hash changes
window.addEventListener('hashchange', handleUrlHash);


function setupSearch() {
    const searchInput = document.getElementById('searchInput');
    
    searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase().trim();
        
        // Apply filters first, then search
        applyFilters();
        
        if (searchTerm) {
            filteredAgencies = filteredAgencies.filter(agency => {
                return (
                    agency.AgencyName?.toLowerCase().includes(searchTerm) ||
                    agency.agencyId?.toLowerCase().includes(searchTerm)
                );
            });
        }
        
        displayStats();
        displayAgencies(filteredAgencies);
    });
}

function setupShaLookup() {
    const shaInput = document.getElementById('shaLookupInput');
    const shaBtn = document.getElementById('shaLookupBtn');
    
    const performLookup = () => {
        const sha = shaInput.value.trim();
        if (sha) {
            // Update URL with SHA query parameter
            const newUrl = `${window.location.pathname}?sha=${encodeURIComponent(sha)}`;
            window.location.href = newUrl;
        }
    };
    
    shaBtn.addEventListener('click', performLookup);
    
    shaInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performLookup();
        }
    });
}

function checkShaQueryParam() {
    const urlParams = new URLSearchParams(window.location.search);
    const sha = urlParams.get('sha');
    
    if (sha) {
        // Automatically view the document for this SHA
        viewDocument(sha, null);
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Load and display query count for a document in the agency card
 */
async function loadQueryCount(sha256) {
    try {
        const queries = await getQueriesForDocument(sha256);
        const placeholder = document.querySelector(`.query-count-placeholder[data-sha="${sha256}"]`);
        
        if (placeholder) {
            if (queries.length === 0) {
                placeholder.textContent = '🤖 No AI queries yet';
            } else {
                placeholder.innerHTML = `🤖 ${queries.length} AI ${queries.length === 1 ? 'query' : 'queries'} saved`;
                placeholder.style.color = '#3498db';
                placeholder.style.fontWeight = '500';
            }
        }
    } catch (error) {
        console.error('Error loading query count:', error);
        const placeholder = document.querySelector(`.query-count-placeholder[data-sha="${sha256}"]`);
        if (placeholder) {
            placeholder.textContent = '';
        }
    }
}

/**
 * Unlock API key with user's secret password
 */
async function unlockApiKey() {
    const secretPassInput = document.getElementById('secretPassInput');
    const apiKeyError = document.getElementById('apiKeyError');
    const unlockBtn = document.getElementById('unlockApiBtn');
    
    const secretPass = secretPassInput.value.trim();
    
    if (!secretPass) {
        apiKeyError.textContent = 'Please enter the secret password';
        apiKeyError.style.display = 'block';
        return;
    }
    
    // Disable button and show loading
    unlockBtn.disabled = true;
    unlockBtn.textContent = '🔄 Unlocking...';
    apiKeyError.style.display = 'none';
    
    try {
        // Try to decrypt the API key
        apiKey = await getApiKey(secretPass);
        
        // Success - show query interface
        showQueryInterface();
        
        // Clear the password input
        secretPassInput.value = '';
        
    } catch (error) {
        console.error('Failed to unlock API key:', error);
        apiKeyError.textContent = 'Invalid password. Please try again.';
        apiKeyError.style.display = 'block';
        
        // Re-enable button
        unlockBtn.disabled = false;
        unlockBtn.textContent = '🔓 Unlock';
    }
}

/**
 * Show the query interface after successful API key unlock
 */
function showQueryInterface() {
    const apiKeyPrompt = document.getElementById('apiKeyPrompt');
    const queryInterface = document.getElementById('queryInterface');
    
    if (apiKeyPrompt) {
        apiKeyPrompt.style.display = 'none';
    }
    if (queryInterface) {
        queryInterface.style.display = 'block';
    }
}

/**
 * Submit an AI query about the current document
 */
async function submitAiQuery() {
    const queryInput = document.getElementById('aiQueryInput');
    const submitBtn = document.getElementById('submitQueryBtn');
    const spinner = document.getElementById('querySpinner');
    const statusDiv = document.getElementById('queryStatus');
    
    if (!currentDocumentData) {
        statusDiv.innerHTML = '<div style="color: #e74c3c; padding: 10px; background: #fee; border-radius: 4px; margin-top: 10px;">Document not available</div>';
        return;
    }
    
    if (!apiKey) {
        statusDiv.innerHTML = '<div style="color: #e74c3c; padding: 10px; background: #fee; border-radius: 4px; margin-top: 10px;">Please unlock API access first</div>';
        return;
    }
    
    const query = queryInput.value.trim();
    
    if (!query) {
        statusDiv.innerHTML = '<div style="color: #e74c3c; padding: 10px; background: #fee; border-radius: 4px; margin-top: 10px;">Please enter a query</div>';
        setTimeout(() => statusDiv.innerHTML = '', 3000);
        return;
    }
    
    // Check if this exact query already exists
    try {
        const existingQuery = await findExistingQuery(currentDocumentData.sha256, query);
        if (existingQuery) {
            // Show the existing result
            displayQueryResult(existingQuery);
            statusDiv.textContent = 'Loaded from cache';
            setTimeout(() => {
                statusDiv.textContent = '';
            }, 3000);
            return;
        }
    } catch (error) {
        console.error('Error checking for existing query:', error);
    }
    
    // Disable input and button
    queryInput.disabled = true;
    submitBtn.disabled = true;
    spinner.style.display = 'flex';
    spinner.style.alignItems = 'center';
    statusDiv.textContent = '';
    
    try {
        // Concatenate all pages
        const documentText = currentDocumentData.pages.join('\n\n');
        
        // Submit query to API
        const result = await queryDeepSeek(apiKey, query, documentText);
        
        // Store the result in IndexedDB
        await storeQuery(
            currentDocumentData.sha256,
            query,
            result.response,
            result.inputTokens,
            result.outputTokens,
            result.durationMs,
            result.cost
        );
        
        // Display the result
        displayQueryResult({
            query,
            response: result.response,
            inputTokens: result.inputTokens,
            outputTokens: result.outputTokens,
            durationMs: result.durationMs,
            cost: result.cost,
            timestamp: Date.now()
        });
        
        // Clear input and reload history
        queryInput.value = '';
        await loadQueryHistory(currentDocumentData.sha256);
        
        statusDiv.textContent = 'Query completed successfully!';
        statusDiv.style.color = '#27ae60';
        setTimeout(() => {
            statusDiv.textContent = '';
        }, 3000);
        
    } catch (error) {
        console.error('Error submitting query:', error);
        statusDiv.innerHTML = `<div style="color: #e74c3c; padding: 10px; background: #fee; border-radius: 4px; margin-top: 10px;">Error: ${escapeHtml(error.message)}</div>`;
    } finally {
        // Re-enable input and button
        queryInput.disabled = false;
        submitBtn.disabled = false;
        spinner.style.display = 'none';
    }
}

/**
 * Display a query result in a modal or section
 */
function displayQueryResult(queryData) {
    // Create a result display element
    const resultHtml = `
        <div style="background: white; padding: 20px; border: 2px solid #3498db; border-radius: 8px; margin-top: 15px;">
            <div style="margin-bottom: 15px;">
                <strong style="color: #2c3e50;">Query:</strong>
                <div style="background: #f8f9fa; padding: 10px; margin-top: 5px; border-radius: 4px; white-space: pre-wrap;">${escapeHtml(queryData.query)}</div>
            </div>
            <div style="margin-bottom: 15px;">
                <strong style="color: #2c3e50;">Response:</strong>
                <div style="background: #e8f4f8; padding: 15px; margin-top: 5px; border-radius: 4px; white-space: pre-wrap; line-height: 1.6;">${escapeHtml(queryData.response)}</div>
            </div>
            <div style="display: flex; gap: 20px; flex-wrap: wrap; font-size: 0.85em; color: #666;">
                <span>📊 Input tokens: ${queryData.inputTokens}</span>
                <span>📊 Output tokens: ${queryData.outputTokens}</span>
                <span>⏱️ Duration: ${(queryData.durationMs / 1000).toFixed(2)}s</span>
                ${queryData.cost ? `<span>💰 Cost: $${queryData.cost.toFixed(4)}</span>` : ''}
                <span>🕐 ${new Date(queryData.timestamp).toLocaleString()}</span>
            </div>
        </div>
    `;
    
    // Find the query history section and prepend the result
    const historyList = document.getElementById('queryHistoryList');
    if (historyList) {
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = resultHtml;
        historyList.insertBefore(tempDiv.firstElementChild, historyList.firstChild);
        
        // Show history section
        const historySection = document.getElementById('queryHistory');
        if (historySection) {
            historySection.style.display = 'block';
        }
    }
}

/**
 * Load and display query history for a document
 */
async function loadQueryHistory(sha256) {
    const historySection = document.getElementById('queryHistory');
    const historyList = document.getElementById('queryHistoryList');
    
    if (!historySection || !historyList) {
        return;
    }
    
    try {
        const queries = await getQueriesForDocument(sha256);
        
        if (queries.length === 0) {
            historySection.style.display = 'none';
            return;
        }
        
        // Display queries
        historyList.innerHTML = queries.map(q => `
            <div style="background: white; padding: 15px; border: 1px solid #ddd; border-radius: 6px; margin-bottom: 10px;">
                <div style="margin-bottom: 10px;">
                    <strong style="color: #2c3e50;">Query:</strong>
                    <div style="background: #f8f9fa; padding: 8px; margin-top: 5px; border-radius: 4px; font-size: 0.9em; white-space: pre-wrap;">${escapeHtml(q.query)}</div>
                </div>
                <div style="margin-bottom: 10px;">
                    <strong style="color: #2c3e50;">Response:</strong>
                    <div style="background: #e8f4f8; padding: 10px; margin-top: 5px; border-radius: 4px; font-size: 0.9em; white-space: pre-wrap; line-height: 1.5;">${escapeHtml(q.response)}</div>
                </div>
                <div style="display: flex; gap: 15px; flex-wrap: wrap; font-size: 0.8em; color: #666;">
                    <span>📊 ${q.inputTokens} in / ${q.outputTokens} out</span>
                    <span>⏱️ ${(q.durationMs / 1000).toFixed(2)}s</span>
                    ${q.cost ? `<span>💰 $${q.cost.toFixed(4)}</span>` : ''}
                    <span>🕐 ${new Date(q.timestamp).toLocaleString()}</span>
                </div>
            </div>
        `).join('');
        
        historySection.style.display = 'block';
        
    } catch (error) {
        console.error('Error loading query history:', error);
    }
}

// Make AI query functions available globally
window.unlockApiKey = unlockApiKey;
window.submitAiQuery = submitAiQuery;

// Initialize the application
init();
