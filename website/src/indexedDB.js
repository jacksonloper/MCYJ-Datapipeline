// IndexedDB module for storing and retrieving AI queries

const DB_NAME = 'MCYJ_Queries';
const DB_VERSION = 1;
const STORE_NAME = 'queries';

let db = null;

/**
 * Initialize the IndexedDB database
 */
export async function initDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            db = request.result;
            resolve(db);
        };

        request.onupgradeneeded = (event) => {
            const database = event.target.result;
            
            // Create object store if it doesn't exist
            if (!database.objectStoreNames.contains(STORE_NAME)) {
                const objectStore = database.createObjectStore(STORE_NAME, { 
                    keyPath: 'id',
                    autoIncrement: true 
                });
                
                // Create indexes
                objectStore.createIndex('sha256', 'sha256', { unique: false });
                objectStore.createIndex('queryHash', 'queryHash', { unique: false });
                objectStore.createIndex('timestamp', 'timestamp', { unique: false });
            }
        };
    });
}

/**
 * Generate a simple hash for a query string
 */
function hashQuery(query) {
    let hash = 0;
    for (let i = 0; i < query.length; i++) {
        const char = query.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32bit integer
    }
    return hash.toString(36);
}

/**
 * Store a query result in IndexedDB
 */
export async function storeQuery(sha256, query, response, inputTokens, outputTokens, durationMs, cost = null) {
    if (!db) {
        await initDB();
    }

    return new Promise((resolve, reject) => {
        const transaction = db.transaction([STORE_NAME], 'readwrite');
        const objectStore = transaction.objectStore(STORE_NAME);

        const queryData = {
            sha256,
            query,
            queryHash: hashQuery(query),
            response,
            inputTokens,
            outputTokens,
            cost,
            durationMs,
            timestamp: Date.now()
        };

        const request = objectStore.add(queryData);
        
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

/**
 * Get all queries for a specific document (by SHA256)
 */
export async function getQueriesForDocument(sha256) {
    if (!db) {
        await initDB();
    }

    return new Promise((resolve, reject) => {
        const transaction = db.transaction([STORE_NAME], 'readonly');
        const objectStore = transaction.objectStore(STORE_NAME);
        const index = objectStore.index('sha256');
        const request = index.getAll(sha256);

        request.onsuccess = () => {
            // Sort by timestamp descending (most recent first)
            const results = request.result.sort((a, b) => b.timestamp - a.timestamp);
            resolve(results);
        };
        request.onerror = () => reject(request.error);
    });
}

/**
 * Check if a query already exists for a document
 */
export async function findExistingQuery(sha256, query) {
    if (!db) {
        await initDB();
    }

    return new Promise((resolve, reject) => {
        const transaction = db.transaction([STORE_NAME], 'readonly');
        const objectStore = transaction.objectStore(STORE_NAME);
        const index = objectStore.index('sha256');
        const request = index.getAll(sha256);

        request.onsuccess = () => {
            const results = request.result;
            // Find exact match by query content
            const match = results.find(r => r.query === query);
            resolve(match || null);
        };
        request.onerror = () => reject(request.error);
    });
}

/**
 * Delete a query by ID
 */
export async function deleteQuery(queryId) {
    if (!db) {
        await initDB();
    }

    return new Promise((resolve, reject) => {
        const transaction = db.transaction([STORE_NAME], 'readwrite');
        const objectStore = transaction.objectStore(STORE_NAME);
        const request = objectStore.delete(queryId);

        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
    });
}
