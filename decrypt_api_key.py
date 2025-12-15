#!/usr/bin/env python3
"""
Decrypt the OpenRouter API key using the password-based encryption.

This script replicates the JavaScript encryption.js decryption logic
to allow Python scripts to use the same encrypted API key.
"""

import argparse
import base64
import hashlib
import sys
from typing import Tuple

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print("ERROR: cryptography library not found")
    print("Install it with: pip install cryptography")
    sys.exit(1)

# The encrypted API key (same as in website/src/encryption.js)
ENCRYPTED_API_KEY = '65887f5d109435ade82c32bf64dabba3:3cfe3c769252ebd9373714781f8b283d:59ddcfc27cc2af723383b9fc78a3b6431118c1471b504776ba3c6c4256f18ddd76d8d6d9d6247baab68051824f9c92502377b3ca0a14546466d837f895df38f2b8f545aeeeb099cf30fc5ca828d02002'


def hex_to_bytes(hex_string: str) -> bytes:
    """Convert hex string to bytes."""
    return bytes.fromhex(hex_string)


def decrypt_api_key(encrypted_data: str, password: str) -> str:
    """
    Decrypt the encrypted API key using PBKDF2 + AES-CBC.
    
    Args:
        encrypted_data: Encrypted data in format "salt:iv:encrypted"
        password: Password to decrypt with
    
    Returns:
        Decrypted API key
    """
    # Parse the encrypted data
    parts = encrypted_data.split(':')
    if len(parts) != 3:
        raise ValueError('Invalid encrypted data format')
    
    salt = hex_to_bytes(parts[0])
    iv = hex_to_bytes(parts[1])
    encrypted = hex_to_bytes(parts[2])
    
    # Derive key using PBKDF2 (matching JavaScript Web Crypto API)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bits
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = kdf.derive(password.encode('utf-8'))
    
    # Decrypt using AES-CBC
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(encrypted) + decryptor.finalize()
    
    # Remove PKCS7 padding
    padding_length = decrypted[-1]
    decrypted = decrypted[:-padding_length]
    
    return decrypted.decode('utf-8')


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Decrypt the OpenRouter API key using a password",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Decrypt and print the API key
  python3 decrypt_api_key.py --password "your-secret-password"
  
  # Decrypt and export to environment
  export OPENROUTER_KEY=$(python3 decrypt_api_key.py --password "your-secret-password")
        """
    )
    parser.add_argument(
        '--password',
        '-p',
        required=True,
        help='Password to decrypt the API key'
    )
    
    args = parser.parse_args()
    
    try:
        api_key = decrypt_api_key(ENCRYPTED_API_KEY, args.password)
        print(api_key)
    except Exception as e:
        print(f"ERROR: Failed to decrypt API key: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
