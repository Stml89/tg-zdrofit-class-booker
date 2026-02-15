"""Encryption/decryption utilities for sensitive data like passwords."""

import os
from cryptography.fernet import Fernet
from config.config import PROJECT_ROOT


class PasswordEncryptor:
    """Handles password encryption and decryption."""
    
    # Key is stored in .env or generated once and saved
    _KEY_FILE = os.path.join(PROJECT_ROOT, '.crypto_key')
    _cipher = None
    
    @classmethod
    def _get_cipher(cls):
        """Get or initialize cipher."""
        if cls._cipher is None:
            key = cls._get_or_create_key()
            cls._cipher = Fernet(key)
        return cls._cipher
    
        
    @classmethod
    def _get_or_create_key(cls) -> bytes:
        """Get encryption key from file or create new one."""
        if os.path.exists(cls._KEY_FILE):
            with open(cls._KEY_FILE, 'rb') as f:
                return f.read()
        
        # Generate new key
        key = Fernet.generate_key()
        
        # Save to file with restricted permissions
        with open(cls._KEY_FILE, 'wb') as f:
            f.write(key)
        os.chmod(cls._KEY_FILE, 0o600)  # Read/write only for owner
        
        return key
    
    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """Encrypt password and return as string."""
        if not plaintext:
            return plaintext
        
        cipher = cls._get_cipher()
        encrypted = cipher.encrypt(plaintext.encode('utf-8'))
        return encrypted.decode('utf-8')
    
    @classmethod
    def decrypt(cls, encrypted_text: str) -> str:
        """Decrypt password."""
        if not encrypted_text:
            return encrypted_text
        
        try:
            cipher = cls._get_cipher()
            decrypted = cipher.decrypt(encrypted_text.encode('utf-8'))
            return decrypted.decode('utf-8')
        except Exception as e:
            # If decryption fails, return as-is (for backwards compatibility with unencrypted passwords)
            # In production, log warning and handle appropriately
            return encrypted_text
