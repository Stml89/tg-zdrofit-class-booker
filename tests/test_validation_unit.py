#!/usr/bin/env python
"""Unit tests for input validation."""

import unittest
import sys
import os
import re

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class EmailValidator:
    """Email validation helper."""
    
    @staticmethod
    def validate(email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email)) and len(email) <= 254


class PasswordValidator:
    """Password validation helper."""
    
    @staticmethod
    def validate(password: str) -> bool:
        """Validate password (1-200 chars)."""
        return 1 <= len(password) <= 200


class TestEmailValidation(unittest.TestCase):
    """Test email validation."""
    
    def test_valid_email_simple(self):
        """Test simple valid email."""
        self.assertTrue(EmailValidator.validate("user@example.com"))
    
    def test_valid_email_with_plus(self):
        """Test valid email with plus addressing."""
        self.assertTrue(EmailValidator.validate("user+tag@example.com"))
    
    def test_valid_email_with_subdomain(self):
        """Test valid email with subdomain."""
        self.assertTrue(EmailValidator.validate("user@mail.example.co.uk"))
    
    def test_valid_email_with_numbers(self):
        """Test valid email with numbers."""
        self.assertTrue(EmailValidator.validate("user123@example456.com"))
    
    def test_valid_email_with_dot(self):
        """Test valid email with dot in local part."""
        self.assertTrue(EmailValidator.validate("user.name@example.com"))
    
    def test_invalid_email_missing_at(self):
        """Test invalid email without @ sign."""
        self.assertFalse(EmailValidator.validate("userexample.com"))
    
    def test_invalid_email_missing_domain(self):
        """Test invalid email missing domain."""
        self.assertFalse(EmailValidator.validate("user@"))
    
    def test_invalid_email_missing_local(self):
        """Test invalid email missing local part."""
        self.assertFalse(EmailValidator.validate("@example.com"))
    
    def test_invalid_email_short_tld(self):
        """Test invalid email with too short TLD."""
        self.assertFalse(EmailValidator.validate("user@domain.c"))
    
    def test_invalid_email_too_long(self):
        """Test invalid email exceeding length limit."""
        long_email = "a" * 250 + "@example.com"
        self.assertFalse(EmailValidator.validate(long_email))
    
    def test_valid_email_max_length(self):
        """Test valid email at maximum allowed length."""
        # Create email exactly 254 characters
        local_part = "a" * (254 - len("@example.com"))
        email = local_part + "@example.com"
        self.assertEqual(len(email), 254)
        self.assertTrue(EmailValidator.validate(email))
    
    def test_invalid_email_with_spaces(self):
        """Test invalid email with spaces."""
        self.assertFalse(EmailValidator.validate("user name@example.com"))
    
    def test_invalid_email_with_special_chars(self):
        """Test invalid email with invalid special characters."""
        self.assertFalse(EmailValidator.validate("user#name@example.com"))


class TestPasswordValidation(unittest.TestCase):
    """Test password validation."""
    
    def test_valid_password_simple(self):
        """Test simple valid password."""
        self.assertTrue(PasswordValidator.validate("password123"))
    
    def test_valid_password_with_special_chars(self):
        """Test password with special characters."""
        self.assertTrue(PasswordValidator.validate("P@ssw0rd!"))
    
    def test_valid_password_single_char(self):
        """Test password with single character (minimum)."""
        self.assertTrue(PasswordValidator.validate("a"))
    
    def test_valid_password_max_length(self):
        """Test password at maximum length (200 chars)."""
        password = "x" * 200
        self.assertEqual(len(password), 200)
        self.assertTrue(PasswordValidator.validate(password))
    
    def test_valid_password_with_unicode(self):
        """Test password with unicode characters."""
        self.assertTrue(PasswordValidator.validate("пароль123"))
    
    def test_invalid_password_empty(self):
        """Test empty password."""
        self.assertFalse(PasswordValidator.validate(""))
    
    def test_invalid_password_too_long(self):
        """Test password exceeding maximum length."""
        password = "x" * 201
        self.assertFalse(PasswordValidator.validate(password))
    
    def test_valid_password_with_spaces(self):
        """Test password with spaces."""
        self.assertTrue(PasswordValidator.validate("pass word 123"))
    
    def test_valid_password_complex(self):
        """Test complex password with mixed character types."""
        self.assertTrue(PasswordValidator.validate("MyP@ssw0rd!#2026"))


class TestValidationCombined(unittest.TestCase):
    """Test combined validation scenarios."""
    
    def test_valid_credentials(self):
        """Test valid email and password pair."""
        email = "user@example.com"
        password = "SecurePassword123!"
        
        self.assertTrue(EmailValidator.validate(email))
        self.assertTrue(PasswordValidator.validate(password))
    
    def test_invalid_email_valid_password(self):
        """Test invalid email with valid password."""
        email = "invalid@"
        password = "ValidPassword123"
        
        self.assertFalse(EmailValidator.validate(email))
        self.assertTrue(PasswordValidator.validate(password))
    
    def test_valid_email_invalid_password(self):
        """Test valid email with invalid password."""
        email = "user@example.com"
        password = ""
        
        self.assertTrue(EmailValidator.validate(email))
        self.assertFalse(PasswordValidator.validate(password))
    
    def test_invalid_email_invalid_password(self):
        """Test invalid email and password."""
        email = "notanemail"
        password = "x" * 300
        
        self.assertFalse(EmailValidator.validate(email))
        self.assertFalse(PasswordValidator.validate(password))


if __name__ == "__main__":
    unittest.main()
