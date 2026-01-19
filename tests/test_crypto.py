#!/usr/bin/env python
"""Unit tests for password encryption/decryption."""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.crypto import PasswordEncryptor


class TestPasswordEncryption(unittest.TestCase):
    """Test password encryption and decryption."""
    
    def test_encryption_decryption_basic(self):
        """Test basic encryption/decryption functionality."""
        original_password = "MySecurePassword123!"
        
        # Encrypt
        encrypted = PasswordEncryptor.encrypt(original_password)
        self.assertIsNotNone(encrypted)
        self.assertNotEqual(encrypted, original_password)
        
        # Decrypt
        decrypted = PasswordEncryptor.decrypt(encrypted)
        self.assertEqual(decrypted, original_password)
    
    def test_encryption_decryption_empty_password(self):
        """Test encryption/decryption of empty password."""
        original_password = ""
        
        encrypted = PasswordEncryptor.encrypt(original_password)
        decrypted = PasswordEncryptor.decrypt(encrypted)
        self.assertEqual(decrypted, original_password)
    
    def test_encryption_decryption_with_spaces(self):
        """Test encryption/decryption with spaces."""
        original_password = "Pass word with spaces 123"
        
        encrypted = PasswordEncryptor.encrypt(original_password)
        decrypted = PasswordEncryptor.decrypt(encrypted)
        self.assertEqual(decrypted, original_password)
    
    def test_encryption_decryption_special_chars(self):
        """Test encryption/decryption with special characters."""
        original_password = "P@ssw0rd!#$%^&*()"
        
        encrypted = PasswordEncryptor.encrypt(original_password)
        decrypted = PasswordEncryptor.decrypt(encrypted)
        self.assertEqual(decrypted, original_password)
    
    def test_encryption_decryption_unicode(self):
        """Test encryption/decryption with unicode characters."""
        original_password = "пароль123密碼"
        
        encrypted = PasswordEncryptor.encrypt(original_password)
        decrypted = PasswordEncryptor.decrypt(encrypted)
        self.assertEqual(decrypted, original_password)
    
    def test_encryption_produces_different_output(self):
        """Test that encrypted password is different from original."""
        original_password = "TestPassword123"
        
        encrypted = PasswordEncryptor.encrypt(original_password)
        self.assertNotEqual(encrypted, original_password)
    
    def test_encryption_consistency(self):
        """Test that same password always encrypts/decrypts correctly."""
        original_password = "ConsistentPassword"
        
        # Encrypt and decrypt multiple times
        for _ in range(5):
            encrypted = PasswordEncryptor.encrypt(original_password)
            decrypted = PasswordEncryptor.decrypt(encrypted)
            self.assertEqual(decrypted, original_password)
    
    def test_encryption_long_password(self):
        """Test encryption/decryption of long password."""
        original_password = "x" * 200  # Maximum allowed length
        
        encrypted = PasswordEncryptor.encrypt(original_password)
        decrypted = PasswordEncryptor.decrypt(encrypted)
        self.assertEqual(decrypted, original_password)
    
    def test_encryption_single_char_password(self):
        """Test encryption/decryption of single character password."""
        original_password = "a"
        
        encrypted = PasswordEncryptor.encrypt(original_password)
        decrypted = PasswordEncryptor.decrypt(encrypted)
        self.assertEqual(decrypted, original_password)
    
    def test_encryption_newline_in_password(self):
        """Test encryption/decryption with newlines."""
        original_password = "Line1\nLine2\nLine3"
        
        encrypted = PasswordEncryptor.encrypt(original_password)
        decrypted = PasswordEncryptor.decrypt(encrypted)
        self.assertEqual(decrypted, original_password)


if __name__ == "__main__":
    unittest.main()
