# Conditions for "Invalid password. Please try again." Error

## Overview

The error message "Invalid password. Please try again." is displayed in the web application when the API key decryption process fails. This document explains all the conditions under which this error occurs.

## Error Location

The error is triggered in the `unlockApiKey()` function in `/website/src/main.js` at line 965:

```javascript
catch (error) {
    console.error('Failed to unlock API key:', error);
    apiKeyError.textContent = 'Invalid password. Please try again.';
    apiKeyError.style.display = 'block';
}
```

## Conditions That Trigger This Error

### 1. **Incorrect Password**

**Most Common Cause**

When the user enters a password that doesn't match the one used to encrypt the API key, the AES-CBC decryption will fail.

**What "Incorrect" Means:**

An "incorrect" password means any password that differs from the one originally used to encrypt the API key. There is no way to verify a password is correct *before* attempting decryption - the system only knows the password is wrong when decryption fails.

**How the System Detects an Incorrect Password:**

1. User enters a password (correct or incorrect)
2. System uses PBKDF2 to derive an AES-256 key from that password
3. System attempts to decrypt the encrypted API key using the derived key
4. **If password is correct:** Decryption succeeds, returns valid API key string
5. **If password is incorrect:** Decryption fails with an error (the decrypted data is garbage, causing `TextDecoder().decode()` to fail at line 52 in `encryption.js`, or `crypto.subtle.decrypt()` itself throws an error)

The error is detected when the decryption process throws an exception. AES-CBC doesn't have built-in authentication, so the only way to know the password was wrong is when decryption produces invalid data.

**Technical Details:**
- The password is used with PBKDF2 (100,000 iterations, SHA-256) to derive an AES-256 key
- Each different password produces a completely different derived key
- If the derived key doesn't match the original encryption key, decryption produces garbage data
- The `crypto.subtle.decrypt()` call at lines 43-50 in `encryption.js` or the `TextDecoder().decode()` at line 52 will throw an error
- This is the intended behavior for password verification

**User Experience:**
- Password is case-sensitive
- Any character difference (even a single character) will cause this error
- Leading or trailing spaces are trimmed automatically by the code (line 940 in main.js)

### 2. **Invalid Encrypted Data Format**

When the `ENCRYPTED_API_KEY` constant doesn't have exactly 3 colon-separated parts (salt:iv:encrypted), the decryption fails.

**Technical Details:**
- Checked at lines 10-12 in `encryption.js`
- Expected format: `salt:iv:encrypted` where each part is hex-encoded
- If `parts.length !== 3`, throws: `Error('Invalid encrypted data format')`

**When This Occurs:**
- Corrupted `ENCRYPTED_API_KEY` constant in the code
- Manual editing of the encrypted key string
- Data corruption during code deployment

### 3. **Invalid Hex Encoding**

When any part of the encrypted data (salt, IV, or encrypted data) contains invalid hexadecimal characters.

**Technical Details:**
- The `hexToUint8Array()` function at lines 58-64 in `encryption.js` converts hex strings to byte arrays
- The hex parsing logic at lines 60-62 uses `parseInt(hexString.substring(i, i + 2), 16)` which returns `NaN` for invalid hex
- This results in corrupted byte arrays that cause decryption to fail

**When This Occurs:**
- Non-hexadecimal characters in the encrypted data
- Odd-length hex strings (must be even-length for proper byte conversion)
- String encoding issues during deployment

### 4. **Crypto API Not Available**

When the Web Crypto API is not available in the browser environment.

**Technical Details:**
- Requires `crypto.subtle` API support
- If not available, calls to `crypto.subtle.importKey()`, `crypto.subtle.deriveKey()`, or `crypto.subtle.decrypt()` will fail

**When This Occurs:**
- Non-HTTPS context (Web Crypto API requires secure context)
- Very old browsers that don't support Web Crypto API
- Disabled crypto features in browser settings

### 5. **Network/Runtime Errors**

Any unexpected JavaScript runtime errors during the decryption process.

**Technical Details:**
- Memory errors
- Browser tab crashes
- Unexpected JavaScript exceptions

## Error Handling Flow

```
User clicks "Unlock" button
    ↓
unlockApiKey() called
    ↓
getApiKey(secretPass) called
    ↓
decrypt(ENCRYPTED_API_KEY, secretPass) called
    ↓
Try to:
  1. Parse encrypted data format (3 parts)
  2. Convert hex strings to byte arrays
  3. Import password as raw key
  4. Derive AES key using PBKDF2
  5. Decrypt using AES-CBC
  6. Decode result as UTF-8 string
    ↓
If ANY step fails → throw error
    ↓
Caught by unlockApiKey() catch block
    ↓
Display: "Invalid password. Please try again."
```

## What the Error Does NOT Indicate

This error message is **generic** and does not distinguish between:
- Wrong password (most common)
- Invalid encrypted data format
- Hex encoding issues
- Crypto API unavailability
- Other technical errors

**All errors are presented to the user as "Invalid password"** for security reasons (to avoid leaking information about the system state).

## Debugging

To determine the actual cause of the error:

1. **Check browser console** - The actual error is logged: `console.error('Failed to unlock API key:', error)`
2. **Verify HTTPS** - Ensure the site is served over HTTPS
3. **Browser compatibility** - Test in a modern browser with Web Crypto API support
4. **Password verification** - Confirm the password is correct and case-sensitive
5. **Code integrity** - Verify the `ENCRYPTED_API_KEY` constant hasn't been corrupted

## Resolution Steps

### For Users:
1. Verify you're using the correct password
2. Check for case sensitivity
3. Ensure you're on HTTPS
4. Try a modern browser (Chrome, Firefox, Safari, Edge)
5. Check browser console for technical details

### For Developers:
1. Verify `ENCRYPTED_API_KEY` format is correct (3 colon-separated hex parts)
2. Ensure all hex strings are valid and even-length
3. Test encryption/decryption in isolated environment
4. Add more specific error messages during development (remove before production)
5. Verify deployment process doesn't corrupt the encrypted key string

## Related Files

- `/website/src/main.js` - UI and error display (line 965)
- `/website/src/encryption.js` - Decryption logic (lines 9-76)
- `/website/AI_QUERY_FEATURE.md` - User-facing documentation (lines 125-128)
