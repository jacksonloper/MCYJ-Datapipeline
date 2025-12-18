// Shared Trie data structure for keyword autocomplete

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
        
        const results = new Map();
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

export { Trie, TrieNode };
