// Keywords page - displays all keywords with counts

// Trie data structure for keyword autocomplete (copied from main.js)
class TrieNode {
    constructor() {
        this.children = new Map();
        this.isEndOfWord = false;
        this.isFullKeyword = false;
        this.fullKeywords = new Set();
        this.count = 0;
    }
}

class Trie {
    constructor() {
        this.root = new TrieNode();
        this.keywordCounts = new Map();
    }

    insert(word, isFullKeyword = false, fullKeywordPhrase = null) {
        let node = this.root;
        word = word.toLowerCase();
        
        for (const char of word) {
            if (!node.children.has(char)) {
                node.children.set(char, new TrieNode());
            }
            node = node.children.get(char);
            
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

// Load and display data
async function init() {
    try {
        // Fetch the agency data
        const response = await fetch('/data/agencies_data.json');
        if (!response.ok) {
            throw new Error(`Failed to load data: ${response.statusText}`);
        }
        
        const allAgencies = await response.json();
        
        // Build keyword trie from all documents
        buildKeywordTrie(allAgencies);
        
        // Render the complete keyword bar chart
        renderKeywordBarChart();
        
        hideLoading();
        
    } catch (error) {
        console.error('Error loading data:', error);
        showError(`Failed to load data: ${error.message}`);
        hideLoading();
    }
}

function buildKeywordTrie(allAgencies) {
    allAgencies.forEach(agency => {
        if (agency.documents && Array.isArray(agency.documents)) {
            agency.documents.forEach(doc => {
                if (doc.sir_violation_level && doc.sir_violation_level.keywords && Array.isArray(doc.sir_violation_level.keywords)) {
                    doc.sir_violation_level.keywords.forEach(keyword => {
                        keywordTrie.insert(keyword, true, keyword);
                        
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
}

function renderKeywordBarChart() {
    const container = document.getElementById('barChartContainer');
    const chartDiv = document.getElementById('keywordBarChart');
    
    if (!container || !chartDiv) return;
    
    // Get all keywords sorted by count
    const allKeywords = keywordTrie.getAllKeywords();
    
    if (allKeywords.length === 0) {
        container.innerHTML = '<div style="color: #666; font-size: 0.9em; font-style: italic; padding: 20px; text-align: center;">No keyword data available</div>';
        chartDiv.style.display = 'block';
        return;
    }
    
    // Find max count for scaling
    const maxCount = Math.max(...allKeywords.map(k => k.count));
    
    // Build bar chart HTML for all keywords
    const barsHtml = allKeywords.map(item => {
        const percentage = maxCount > 0 ? (item.count / maxCount) * 100 : 0;
        return `
            <div class="bar-chart-row">
                <div class="bar-chart-label">${escapeHtml(item.keyword)}</div>
                <div class="bar-chart-bar-container">
                    <div class="bar-chart-bar" style="width: ${percentage}%"></div>
                </div>
                <div class="bar-chart-count">${item.count}</div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = barsHtml;
    chartDiv.style.display = 'block';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function showError(message) {
    const loadingEl = document.getElementById('loading');
    loadingEl.textContent = `Error: ${message}`;
    loadingEl.style.color = '#e74c3c';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize the page
init();
