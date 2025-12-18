// Main application logic

let allAgencies = [];
let filteredAgencies = [];
let currentOpenAgencyId = null;

// Filter state
let filters = {
    sirOnly: false,
    keywords: [] // Array of selected keywords
};

// Trie data structure for keyword autocomplete
class TrieNode {
    constructor() {
        this.children = new Map();
        this.isEndOfWord = false;
        this.isFullKeyword = false; // Track if this is an actual full keyword vs just a word fragment
        this.fullKeywords = new Set(); // Store which full keywords contain this word/prefix
        this.count = 0; // Number of documents with this keyword (only for full keywords)
    }
}

class Trie {
    constructor() {
        this.root = new TrieNode();
        this.keywordCounts = new Map(); // Track counts for full keywords
    }

    insert(word, isFullKeyword = false, fullKeywordPhrase = null) {
        let node = this.root;
        word = word.toLowerCase();
        
        for (const char of word) {
            if (!node.children.has(char)) {
                node.children.set(char, new TrieNode());
            }
            node = node.children.get(char);
            
            // Track which full keyword this prefix belongs to
            if (fullKeywordPhrase) {
                node.fullKeywords.add(fullKeywordPhrase.toLowerCase());
            }
        }
        node.isEndOfWord = true;
        if (isFullKeyword) {
            node.isFullKeyword = true;
            const lowerKey = word.toLowerCase();
            this.keywordCounts.set(lowerKey, (this.keywordCounts.get(lowerKey) || 0) + 1);
            node.count = this.keywordCounts.get(lowerKey);
        }
        if (fullKeywordPhrase) {
            node.fullKeywords.add(fullKeywordPhrase.toLowerCase());
        }
    }

    search(prefix) {
        let node = this.root;
        prefix = prefix.toLowerCase();
        
        for (const char of prefix) {
            if (!node.children.has(char)) {
                return [];
            }
            node = node.children.get(char);
        }
        
        const results = new Map(); // Use map to deduplicate
        this._collectKeywords(node, prefix, results);
        return Array.from(results.values()).sort((a, b) => b.count - a.count);
    }

    _collectKeywords(node, prefix, results, maxResults = 10) {
        if (results.size >= maxResults) return;
        
        // If this is a full keyword, add it
        if (node.isEndOfWord && node.isFullKeyword) {
            const lowerPrefix = prefix.toLowerCase();
            if (!results.has(lowerPrefix)) {
                results.set(lowerPrefix, { 
                    keyword: prefix, 
                    count: this.keywordCounts.get(lowerPrefix) || node.count 
                });
            }
        }
        
        // Add all full keywords that contain this word/prefix
        for (const fullKeyword of node.fullKeywords) {
            if (!results.has(fullKeyword)) {
                results.set(fullKeyword, { 
                    keyword: fullKeyword, 
                    count: this.keywordCounts.get(fullKeyword) || 1
                });
            }
        }
        
        // Continue traversing to find more matches
        for (const [char, childNode] of node.children) {
            this._collectKeywords(childNode, prefix + char, results, maxResults);
        }
    }

    getAllKeywords() {
        const results = new Map();
        this._collectAllFullKeywords(this.root, '', results);
        return Array.from(results.values()).sort((a, b) => b.count - a.count);
    }
    
    _collectAllFullKeywords(node, prefix, results) {
        if (node.isEndOfWord && node.isFullKeyword) {
            const lowerPrefix = prefix.toLowerCase();
            if (!results.has(lowerPrefix)) {
                results.set(lowerPrefix, { 
                    keyword: prefix, 
                    count: this.keywordCounts.get(lowerPrefix) || node.count 
                });
            }
        }
        
        for (const [char, childNode] of node.children) {
            this._collectAllFullKeywords(childNode, prefix + char, results);
        }
    }
}

let keywordTrie = new Trie();
let allKeywords = new Set();

// Load and display data
async function init() {
    try {
        // Fetch the agency data
        const response = await fetch('/data/agencies_data.json');
        if (!response.ok) {
            throw new Error(`Failed to load data: ${response.statusText}`);
        }
        
        allAgencies = await response.json();
        filteredAgencies = allAgencies;
        
        // Build keyword trie from all documents
        buildKeywordTrie();

        hideLoading();
        displayStats();
        displayAgencies(allAgencies);
        setupSearch();
        setupFilters();
        setupKeywordFilter();
        handleUrlHash();
        handleQueryStringDocument();
        handleQueryStringKeyword();
        
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
    const statsEl = document.getElementById('filterStats');
    if (!statsEl) return;

    // Use filtered agencies for stats
    const agencies = filteredAgencies;
    const totalAgencies = agencies.length;
    const totalReports = agencies.reduce((sum, a) => sum + a.total_reports, 0);

    // Check if filters are active
    const hasFilters = filters.sirOnly || filters.keywords.length > 0;
    const allTotalAgencies = allAgencies.length;
    const allTotalReports = allAgencies.reduce((sum, a) => sum + a.total_reports, 0);

    if (hasFilters) {
        statsEl.textContent = `Showing ${totalAgencies} agencies with ${totalReports} documents (filtered from ${allTotalAgencies} agencies, ${allTotalReports} documents)`;
    } else {
        statsEl.textContent = `${totalAgencies} agencies · ${totalReports} documents`;
    }
}

function applyFilters() {
    // Start with all agencies
    let agencies = JSON.parse(JSON.stringify(allAgencies)); // Deep clone
    
    // Apply filters to each agency's documents
    agencies = agencies.map(agency => {
        if (!agency.documents || !Array.isArray(agency.documents)) {
            return agency;
        }
        
        let filteredDocuments = agency.documents.filter(d => {
            // Filter by SIR only
            if (filters.sirOnly && !d.is_special_investigation) {
                return false;
            }
            
            // Filter by keywords (OR logic - match ANY keyword)
            if (filters.keywords && filters.keywords.length > 0) {
                const docKeywords = d.sir_violation_level?.keywords || [];
                const docKeywordsLower = docKeywords.map(k => k.toLowerCase());
                const hasAnyKeyword = filters.keywords.some(filterKw => 
                    docKeywordsLower.includes(filterKw.toLowerCase())
                );
                if (!hasAnyKeyword) {
                    return false;
                }
            }
            
            return true;
        });
        
        // Update agency stats based on filtered documents
        return {
            ...agency,
            documents: filteredDocuments,
            total_reports: filteredDocuments.length
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
}

function buildKeywordTrie() {
    // Collect all keywords from all documents
    // Split each keyword by whitespace to allow partial word matching
    allAgencies.forEach(agency => {
        if (agency.documents && Array.isArray(agency.documents)) {
            agency.documents.forEach(doc => {
                if (doc.sir_violation_level && doc.sir_violation_level.keywords && Array.isArray(doc.sir_violation_level.keywords)) {
                    doc.sir_violation_level.keywords.forEach(keyword => {
                        // Insert the full keyword phrase and mark it as a full keyword
                        keywordTrie.insert(keyword, true, keyword);
                        allKeywords.add(keyword.toLowerCase());
                        
                        // Also insert individual words from the keyword for search purposes
                        // These link back to the full keyword so typing "inj" can find "serious injury"
                        const words = keyword.trim().split(/\s+/);
                        words.forEach(word => {
                            if (word.length > 0) {
                                keywordTrie.insert(word, false, keyword);
                            }
                        });
                    });
                }
            });
        }
    });
    console.log(`Built keyword trie with ${allKeywords.size} unique keywords`);
}

function setupKeywordFilter() {
    const keywordInput = document.getElementById('keywordFilterInput');
    const keywordSuggestions = document.getElementById('keywordSuggestions');
    const selectedKeywordsContainer = document.getElementById('selectedKeywords');
    
    if (!keywordInput) return; // Element not added yet
    
    // Handle input for autocomplete
    keywordInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        
        if (query.length < 2) {
            keywordSuggestions.style.display = 'none';
            return;
        }
        
        const suggestions = keywordTrie.search(query);
        
        if (suggestions.length === 0) {
            keywordSuggestions.style.display = 'none';
            return;
        }
        
        keywordSuggestions.innerHTML = suggestions.map(s => `
            <div class="keyword-suggestion" data-keyword="${escapeHtml(s.keyword)}">
                <span>${escapeHtml(s.keyword)}</span>
                <span style="color: #666; font-size: 0.85em;">(${s.count})</span>
            </div>
        `).join('');
        keywordSuggestions.style.display = 'block';
        
        // Add click handlers to suggestions
        keywordSuggestions.querySelectorAll('.keyword-suggestion').forEach(div => {
            div.addEventListener('click', () => {
                const keyword = div.dataset.keyword;
                addKeywordFilter(keyword);
                keywordInput.value = '';
                keywordSuggestions.style.display = 'none';
            });
        });
    });
    
    // Hide suggestions when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('#keywordFilterInput') && !e.target.closest('#keywordSuggestions')) {
            keywordSuggestions.style.display = 'none';
        }
    });
    
    // Allow pressing Enter to add the first suggestion
    keywordInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const firstSuggestion = keywordSuggestions.querySelector('.keyword-suggestion');
            if (firstSuggestion) {
                const keyword = firstSuggestion.dataset.keyword;
                addKeywordFilter(keyword);
                keywordInput.value = '';
                keywordSuggestions.style.display = 'none';
            }
        }
    });
}

function addKeywordFilter(keyword) {
    const keywordLower = keyword.toLowerCase();
    
    // Check if keyword is already selected
    if (filters.keywords.includes(keywordLower)) {
        return;
    }
    
    filters.keywords.push(keywordLower);
    renderSelectedKeywords();
    applyFilters();
}

function removeKeywordFilter(keyword) {
    filters.keywords = filters.keywords.filter(k => k !== keyword.toLowerCase());
    renderSelectedKeywords();
    applyFilters();
}

function renderSelectedKeywords() {
    const container = document.getElementById('selectedKeywords');

    if (!container) return;

    if (filters.keywords.length === 0) {
        container.innerHTML = '<div style="color: #666; font-size: 0.9em; font-style: italic;">No keywords selected</div>';
    } else {
        container.innerHTML = filters.keywords.map(keyword => `
            <span class="selected-keyword-badge">
                ${escapeHtml(keyword)}
                <button class="remove-keyword-btn" onclick="window.removeKeywordFilter('${escapeHtml(keyword)}')" title="Remove keyword">✕</button>
            </span>
        `).join('');
    }
}

// Export functions to window for inline onclick handlers
window.removeKeywordFilter = removeKeywordFilter;

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
                    <span class="stat-badge reports-badge">
                        📋 ${agency.total_reports} Reports
                    </span>
                </div>
                
                <div class="agency-details" id="details-${agency.agencyId}">
                    ${renderDocuments(agency.documents)}
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

function renderDocuments(documents) {
    if (!documents || documents.length === 0) {
        return `
            <div class="documents-list">
                <div class="section-title">Documents & Reports</div>
                <p style="color: #666;">No reports available.</p>
            </div>
        `;
    }
    
    // Sort by date (most recent first)
    const sortedDocuments = [...documents].sort((a, b) => {
        return new Date(b.date_processed) - new Date(a.date_processed);
    });
    
    const documentItems = sortedDocuments.map(d => {
        // Use document title if available, otherwise fall back to agency name
        const displayTitle = d.document_title || d.agency_name || 'Untitled Document';
        const isSir = d.is_special_investigation;
        const hasSummary = d.sir_summary && d.sir_summary.summary;
        const hasViolationLevel = d.sir_violation_level && d.sir_violation_level.level;
        
        // Determine violation level badge
        let violationLevelBadge = '';
        if (hasViolationLevel) {
            const level = d.sir_violation_level.level.toLowerCase();
            let levelColor = '#95a5a6';
            let levelEmoji = '⚪';
            
            if (level === 'low') {
                levelColor = '#f39c12';
                levelEmoji = '🟡';
            } else if (level === 'moderate') {
                levelColor = '#e67e22';
                levelEmoji = '🟠';
            } else if (level === 'severe') {
                levelColor = '#e74c3c';
                levelEmoji = '🔴';
            }
            
            violationLevelBadge = `<span style="color: ${levelColor}; font-size: 0.85em; margin-left: 6px;">${levelEmoji} ${level.charAt(0).toUpperCase() + level.slice(1)}</span>`;
        }
        
        return `
            <div class="document-item ${isSir ? 'is-sir' : ''}">
                <div style="font-weight: 600; margin-bottom: 4px;">
                    ${escapeHtml(displayTitle)}
                    ${isSir ? ' <span style="color: #e74c3c; font-size: 0.85em;">🔍 SIR</span>' : ''}
                    ${d.sha256 ? `
                        <button class="copy-link-btn" onclick="copyDocumentLink('${d.sha256}', event)" title="Copy link to this document">
                            🔗
                        </button>
                    ` : ''}
                </div>
                <div class="date">${escapeHtml(d.date || 'Date not specified')}</div>
                ${hasSummary ? `
                    <div style="margin-top: 10px; padding: 10px; background: #fff9e6; border-left: 3px solid #f39c12; border-radius: 4px;">
                        <div style="font-weight: 600; color: #e67e22; margin-bottom: 6px; font-size: 0.9em;">
                            📋 Summary (AI-generated by DeepSeek v3.2)
                            ${d.sir_summary.violation === 'y' ? `<span style="color: #e74c3c; margin-left: 6px;">⚠️ Violation Substantiated${violationLevelBadge}</span>` : ''}
                            ${d.sir_summary.violation === 'n' ? '<span style="color: #27ae60; margin-left: 6px;">✓ No Violation</span>' : ''}
                        </div>
                        <div style="font-size: 0.9em; line-height: 1.5; color: #555;">${escapeHtml(d.sir_summary.summary)}</div>
                        ${hasViolationLevel && d.sir_violation_level.keywords && d.sir_violation_level.keywords.length > 0 ? `
                            <div style="margin-top: 8px; display: flex; flex-wrap: wrap; gap: 4px;">
                                <span style="font-size: 0.8em; color: #666; margin-right: 4px;">🏷️</span>
                                ${d.sir_violation_level.keywords.slice(0, 5).map(kw => 
                                    `<span style="background: #e8f4f8; color: #2980b9; padding: 2px 8px; border-radius: 10px; font-size: 0.75em; border: 1px solid #3498db;">${escapeHtml(kw)}</span>`
                                ).join('')}
                                ${d.sir_violation_level.keywords.length > 5 ? `<span style="font-size: 0.75em; color: #666;">+${d.sir_violation_level.keywords.length - 5} more</span>` : ''}
                            </div>
                        ` : ''}
                    </div>
                ` : ''}
                ${d.sha256 ? `
                    <div style="margin-top: 8px;">
                        <button class="view-document-btn" onclick="viewDocument('${d.sha256}', event)">
                            📄 View Full Document
                        </button>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');

    return `
        <div class="documents-list">
            <div class="section-title">Documents & Reports (${documents.length})</div>
            ${documentItems}
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
            if (agency.documents && Array.isArray(agency.documents)) {
                const document = agency.documents.find(d => d.sha256 === sha256);
                if (document) {
                    docMetadata = {
                        title: document.document_title || document.agency_name || 'Untitled Document',
                        is_special_investigation: document.is_special_investigation || false
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

    // Validate document data
    if (!docData.pages || !Array.isArray(docData.pages)) {
        console.error('Invalid document data: pages array missing or invalid');
        return;
    }
    
    // Format the document pages
    const totalPages = docData.pages.length;
    const pagesHtml = docData.pages.map((page, pageIndex) => {
        const pageContent = escapeHtml(page);
        
        return `
            <div class="document-page">
                <div class="page-number">Page ${pageIndex + 1} of ${totalPages}</div>
                <pre class="page-text">${pageContent}</pre>
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
                ${docMetadata.is_special_investigation ? `
                    <div style="color: #e74c3c;"><strong>Type:</strong> 🔍 Special Investigation Report</div>
                ` : ''}
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
        
        ${docData.sir_summary && docData.sir_summary.summary ? `
            <!-- SIR Summary Section -->
            <div style="padding: 20px; background: #fffbf0; border-bottom: 2px solid #f39c12;">
                <div style="margin-bottom: 15px;">
                    <h3 style="margin: 0 0 10px 0; color: #e67e22; font-size: 1.1em;">
                        📋 Special Investigation Report Summary (AI-generated by DeepSeek v3.2)
                        ${docData.sir_summary.violation === 'y' ? `<span style="color: #e74c3c; margin-left: 8px; font-size: 0.9em;">⚠️ Violation Substantiated</span>` : ''}
                        ${docData.sir_summary.violation === 'n' ? '<span style="color: #27ae60; margin-left: 8px; font-size: 0.9em;">✓ No Violation</span>' : ''}
                        ${docData.sir_violation_level && docData.sir_violation_level.level ? (() => {
                            const level = docData.sir_violation_level.level.toLowerCase();
                            let levelColor = '#95a5a6';
                            let levelEmoji = '⚪';
                            
                            if (level === 'low') {
                                levelColor = '#f39c12';
                                levelEmoji = '🟡';
                            } else if (level === 'moderate') {
                                levelColor = '#e67e22';
                                levelEmoji = '🟠';
                            } else if (level === 'severe') {
                                levelColor = '#e74c3c';
                                levelEmoji = '🔴';
                            }
                            
                            return `<span style="color: ${levelColor}; margin-left: 8px; font-size: 0.9em;">${levelEmoji} ${level.charAt(0).toUpperCase() + level.slice(1)} Severity</span>`;
                        })() : ''}
                    </h3>
                </div>
                <div style="background: white; padding: 15px; border-radius: 6px; border-left: 4px solid #f39c12; line-height: 1.6; color: #333;">
                    <div style="margin-bottom: ${docData.sir_violation_level && (docData.sir_violation_level.justification || (docData.sir_violation_level.keywords && docData.sir_violation_level.keywords.length > 0)) ? '15px' : '0'};">
                        <strong style="color: #2c3e50;">Summary:</strong>
                        <div style="margin-top: 8px;">${escapeHtml(docData.sir_summary.summary)}</div>
                    </div>
                    ${docData.sir_violation_level && docData.sir_violation_level.keywords && docData.sir_violation_level.keywords.length > 0 ? `
                        <div style="padding-top: 15px; border-top: 1px solid #ecf0f1; margin-bottom: ${docData.sir_violation_level.justification ? '15px' : '0'};">
                            <strong style="color: #2c3e50;">Keywords:</strong>
                            <div style="margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px;">
                                ${docData.sir_violation_level.keywords.map(kw => 
                                    `<span style="background: #e8f4f8; color: #2980b9; padding: 4px 10px; border-radius: 12px; font-size: 0.85em; border: 1px solid #3498db;">${escapeHtml(kw)}</span>`
                                ).join('')}
                            </div>
                        </div>
                    ` : ''}
                    ${docData.sir_violation_level && docData.sir_violation_level.justification ? `
                        <div style="padding-top: 15px; border-top: 1px solid #ecf0f1;">
                            <strong style="color: #2c3e50;">Severity Justification:</strong>
                            <div style="margin-top: 8px;">${escapeHtml(docData.sir_violation_level.justification)}</div>
                        </div>
                    ` : ''}
                </div>
            </div>
        ` : ''}
        
        <div class="document-pages">
            ${pagesHtml}
        </div>
    `;
    
    modal.style.display = 'flex';

    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden';
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

function handleQueryStringKeyword() {
    // Parse query string for keyword parameter
    const urlParams = new URLSearchParams(window.location.search);
    const keyword = urlParams.get('keyword');

    if (!keyword) {
        return;
    }

    // Add the keyword to filters
    addKeywordFilter(keyword);
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

    // Setup Document ID lookup
    const docIdInput = document.getElementById('docIdInput');
    const docIdBtn = document.getElementById('docIdBtn');

    if (docIdInput && docIdBtn) {
        const performLookup = () => {
            const docId = docIdInput.value.trim();
            if (docId) {
                // Update URL with SHA query parameter
                const newUrl = `${window.location.pathname}?sha=${encodeURIComponent(docId)}`;
                window.location.href = newUrl;
            }
        };

        docIdBtn.addEventListener('click', performLookup);

        docIdInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performLookup();
            }
        });
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize the application
init();
