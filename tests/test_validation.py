#!/usr/bin/env python
"""Test input validation."""

import sys
import os
import re

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email)) and len(email) <= 254


def validate_password(password: str) -> bool:
    """Validate password."""
    return 1 <= len(password) <= 200


def test_email_validation():
    """Test email validation."""
    test_emails = [
        ("valid@example.com", True),
        ("user.name+tag@example.co.uk", True),
        ("invalid@", False),
        ("@example.com", False),
        ("no-at-sign.com", False),
        ("valid@domain.c", False),  # Too short TLD
        ("a" * 250 + "@example.com", False),  # Too long
    ]

    print("[INFO] Testing email validation:")
    all_passed = True
    for email, expected in test_emails:
        result = validate_email(email)
        status = "[PASS]" if result == expected else "[FAIL]"
        if result != expected:
            all_passed = False
        print(f"{status} {email}: {result} (expected {expected})")
    
    return all_passed


def test_password_validation():
    """Test password validation."""
    test_passwords = [
        ("password123", True),
        ("P@ssw0rd!", True),
        ("", False),  # Too short
        ("x" * 201, False),  # Too long
        ("a", True),  # Minimum valid
        ("x" * 200, True),  # Maximum valid
    ]

    print("\n[INFO] Testing password validation:")
    all_passed = True
    for password, expected in test_passwords:
        result = validate_password(password)
        display = password if len(password) <= 20 else password[:20] + "..."
        status = "[PASS]" if result == expected else "[FAIL]"
        if result != expected:
            all_passed = False
        print(f"{status} {display}: {result} (expected {expected})")
    
    return all_passed


if __name__ == "__main__":
    print("\n[INFO] Input Validation Tests")
    print("=" * 60)
    
    try:
        email_ok = test_email_validation()
        password_ok = test_password_validation()
        
        if email_ok and password_ok:
            print("\n[PASS] All validation tests passed!")
            sys.exit(0)
        else:
            print("\n[FAIL] Some validation tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
