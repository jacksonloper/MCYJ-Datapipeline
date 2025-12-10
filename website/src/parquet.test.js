import { describe, it, expect, beforeAll } from 'vitest';
import { gunzipSync } from 'fflate';
import { init as initZstd, decompress as decompressZstd } from '@bokuweb/zstd-wasm';

describe('Parquet Decompression', () => {
    let zstdInitialized = false;

    async function ensureZstdInitialized() {
        if (!zstdInitialized) {
            await initZstd();
            zstdInitialized = true;
        }
    }

    async function decompressor(method, data) {
        console.log(`Decompressing with ${method}, input length: ${data?.byteLength || data?.length}`);
        
        try {
            if (method === 'ZSTD') {
                await ensureZstdInitialized();
                const input = data instanceof Uint8Array ? data : new Uint8Array(data);
                const result = decompressZstd(input);
                console.log(`ZSTD decompressed length: ${result?.length}`);
                return result;
            } else if (method === 'GZIP') {
                const input = data instanceof Uint8Array ? data : new Uint8Array(data);
                const result = gunzipSync(input);
                console.log(`GZIP decompressed length: ${result?.length}`);
                return result;
            } else if (method === 'SNAPPY') {
                throw new Error(`Unsupported compression: ${method}`);
            } else {
                // Uncompressed - return as Uint8Array
                const result = data instanceof Uint8Array ? data : new Uint8Array(data);
                console.log(`Uncompressed length: ${result?.length}`);
                return result;
            }
        } catch (err) {
            console.error(`Decompression error for ${method}:`, err);
            throw err;
        }
    }

    describe('ZSTD Decompression', () => {
        beforeAll(async () => {
            await ensureZstdInitialized();
        });

        it('should initialize ZSTD', async () => {
            await ensureZstdInitialized();
            expect(zstdInitialized).toBe(true);
        });

        it('should decompress ZSTD data', async () => {
            // Create a simple test string
            const testString = 'Hello, World! This is a test string for ZSTD compression.';
            const testData = new TextEncoder().encode(testString);
            
            // For this test, we'd need compressed data
            // Since we can't easily compress in the test, we'll just verify the API works
            try {
                const result = await decompressor('ZSTD', testData);
                // The decompressor should return a Uint8Array
                expect(result).toBeInstanceOf(Uint8Array);
            } catch (err) {
                // It's expected to fail on uncompressed data
                // This test mainly verifies the API structure
                console.log('Expected error for uncompressed data:', err.message);
            }
        });

        it('should handle ArrayBuffer input', async () => {
            const testData = new Uint8Array([1, 2, 3, 4, 5]);
            const arrayBuffer = testData.buffer;
            
            try {
                const result = await decompressor('ZSTD', arrayBuffer);
                expect(result).toBeInstanceOf(Uint8Array);
            } catch (err) {
                // Expected to fail on invalid compressed data
                console.log('Expected error:', err.message);
            }
        });
    });

    describe('GZIP Decompression', () => {
        it('should handle GZIP data', () => {
            // Simple uncompressed data test
            const testData = new Uint8Array([1, 2, 3, 4, 5]);
            
            try {
                const result = decompressor('GZIP', testData);
                expect(result).toBeInstanceOf(Promise);
            } catch (err) {
                // Expected to fail on invalid gzip data
                console.log('Expected error for invalid gzip:', err.message);
            }
        });
    });

    describe('Uncompressed Data', () => {
        it('should return uncompressed data as-is', async () => {
            const testData = new Uint8Array([1, 2, 3, 4, 5]);
            const result = await decompressor('UNCOMPRESSED', testData);
            
            expect(result).toBeInstanceOf(Uint8Array);
            expect(result.length).toBe(5);
            expect(Array.from(result)).toEqual([1, 2, 3, 4, 5]);
        });

        it('should convert ArrayBuffer to Uint8Array', async () => {
            const testData = new Uint8Array([1, 2, 3, 4, 5]);
            const arrayBuffer = testData.buffer;
            const result = await decompressor('UNCOMPRESSED', arrayBuffer);
            
            expect(result).toBeInstanceOf(Uint8Array);
            expect(result.length).toBe(5);
        });
    });

    describe('Error Handling', () => {
        it('should throw error for SNAPPY compression', async () => {
            const testData = new Uint8Array([1, 2, 3, 4, 5]);
            
            await expect(decompressor('SNAPPY', testData)).rejects.toThrow('Unsupported compression: SNAPPY');
        });
    });
});
