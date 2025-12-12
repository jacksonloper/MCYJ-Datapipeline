// Encryption/Decryption utilities for API key management

/**
 * Decrypt the encrypted API key using the provided password
 * @param {string} combined - The encrypted data in format: salt:iv:encrypted
 * @param {string} password - The password to decrypt with
 * @returns {Promise<string>} The decrypted API key
 */
export async function decrypt(combined, password) {
    const parts = combined.split(':');
    if (parts.length !== 3) {
        throw new Error('Invalid encrypted data format');
    }

    const salt = hexToUint8Array(parts[0]);
    const iv = hexToUint8Array(parts[1]);
    const encrypted = hexToUint8Array(parts[2]);

    // Derive key using PBKDF2
    const passwordBuffer = new TextEncoder().encode(password);
    const importedKey = await crypto.subtle.importKey(
        'raw',
        passwordBuffer,
        'PBKDF2',
        false,
        ['deriveBits', 'deriveKey']
    );

    const key = await crypto.subtle.deriveKey(
        {
            name: 'PBKDF2',
            salt: salt,
            iterations: 100000,
            hash: 'SHA-256'
        },
        importedKey,
        { name: 'AES-CBC', length: 256 },
        false,
        ['decrypt']
    );

    // Decrypt the data
    const decrypted = await crypto.subtle.decrypt(
        {
            name: 'AES-CBC',
            iv: iv
        },
        key,
        encrypted
    );

    return new TextDecoder().decode(decrypted);
}

/**
 * Convert hex string to Uint8Array
 */
function hexToUint8Array(hexString) {
    const bytes = new Uint8Array(hexString.length / 2);
    for (let i = 0; i < hexString.length; i += 2) {
        bytes[i / 2] = parseInt(hexString.substr(i, 2), 16);
    }
    return bytes;
}

// The encrypted API key data (public, encryption makes it safe)
const ENCRYPTED_API_KEY = '65887f5d109435ade82c32bf64dabba3:3cfe3c769252ebd9373714781f8b283d:59ddcfc27cc2af723383b9fc78a3b6431118c1471b504776ba3c6c4256f18ddd76d8d6d9d6247baab68051824f9c92502377b3ca0a14546466d837f895df38f2b8f545aeeeb099cf30fc5ca828d02002';

/**
 * Get the decrypted API key using the user's secret password
 * @param {string} secretPass - The user's secret password
 * @returns {Promise<string>} The decrypted API key
 */
export async function getApiKey(secretPass) {
    return await decrypt(ENCRYPTED_API_KEY, secretPass);
}
