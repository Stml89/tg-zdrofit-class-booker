#!/usr/bin/env python
"""Test password encryption/decryption."""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.crypto import PasswordEncryptor


def test_encryption_decryption():
    """Test encryption/decryption functionality."""
    test_password = "MySecurePassword123!"
    print(f"Original password: {test_password}")

    # Encrypt
    encrypted = PasswordEncryptor.encrypt(test_password)
    print(f"Encrypted: {encrypted}")

    # Decrypt
    decrypted = PasswordEncryptor.decrypt(encrypted)
    print(f"Decrypted: {decrypted}")

    # Verify
    assert decrypted == test_password, f"Decryption failed! Expected {test_password}, got {decrypted}"
    print("[PASS] Encryption/decryption works correctly!")
    return True


def test_empty_password():
    """Test handling empty password."""
    empty_encrypted = PasswordEncryptor.encrypt("")
    empty_decrypted = PasswordEncryptor.decrypt(empty_encrypted)
    assert empty_decrypted == "", f"Empty password handling failed!"
    print("[PASS] Empty password handling works!")
    return True


if __name__ == "__main__":
    print("\n[INFO] Testing Encryption/Decryption")
    print("=" * 60)
    
    try:
        test_encryption_decryption()
        test_empty_password()
        print("\n[PASS] All crypto tests passed!")
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
