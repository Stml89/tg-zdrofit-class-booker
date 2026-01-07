#!/usr/bin/env python
"""Unit tests for database models."""

import unittest
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.models import User, UserFilter, AvailableClass


class TestUserModel(unittest.TestCase):
    """Test User model."""
    
    def test_user_creation(self):
        """Test creating a user."""
        user = User(
            telegram_id=123456,
            zdrofit_email="test@example.com",
            zdrofit_password="password123"
        )
        
        self.assertEqual(user.telegram_id, 123456)
        self.assertEqual(user.zdrofit_email, "test@example.com")
        self.assertEqual(user.zdrofit_password, "password123")
        self.assertIsNotNone(user.created_at)
    
    def test_user_password_encryption(self):
        """Test user password encryption."""
        user = User(
            telegram_id=123456,
            zdrofit_email="test@example.com",
            zdrofit_password="password123"
        )
        
        original_password = user.zdrofit_password
        user.encrypt_password()
        
        # Password should be encrypted now
        self.assertNotEqual(user.zdrofit_password, original_password)
        self.assertTrue(user._password_encrypted)
        
        # Should be able to decrypt
        decrypted = user.get_decrypted_password()
        self.assertEqual(decrypted, original_password)


class TestUserFilter(unittest.TestCase):
    """Test UserFilter model."""
    
    def test_filter_creation(self):
        """Test creating a filter with all fields."""
        user_filter = UserFilter(
            user_id=123456,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            zone_id="167",
            zone_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Full Body Workout",
            category_id="9",
            category_name="Wzmacniające",
            trainer_id="1276",
            trainer_name="Tomasz Kostro",
            time_from="07:00",
            time_to="20:00",
            weekdays="1,2,3,4,5"
        )
        
        self.assertEqual(user_filter.user_id, 123456)
        self.assertEqual(user_filter.club_id, 75)
        self.assertEqual(user_filter.time_from, "07:00")
        self.assertEqual(user_filter.time_to, "20:00")
        self.assertEqual(user_filter.weekdays, "1,2,3,4,5")
        self.assertIsNotNone(user_filter.created_at)
    
    def test_filter_optional_fields(self):
        """Test filter with optional fields."""
        user_filter = UserFilter(
            user_id=123456,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Full Body Workout"
            # trainer_id and other optional fields are None
        )
        
        self.assertIsNone(user_filter.trainer_id)
        self.assertIsNone(user_filter.time_from)
        self.assertIsNone(user_filter.weekdays)


class TestAvailableClass(unittest.TestCase):
    """Test AvailableClass model."""
    
    def test_available_class_creation(self):
        """Test creating an available class."""
        start_time = datetime.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=1)
        
        available_class = AvailableClass(
            user_id=123456,
            class_id="1091041",
            title="Trening Cross",
            gym_name="Zdrofit Bemowo Dywizjonu 303",
            trainer_name="MARCIN URBAN",
            activity_type="Trening Cross",
            start_time=start_time,
            end_time=end_time,
            available_spots=5
        )
        
        self.assertEqual(available_class.user_id, 123456)
        self.assertEqual(available_class.class_id, "1091041")
        self.assertEqual(available_class.title, "Trening Cross")
        self.assertEqual(available_class.available_spots, 5)
        self.assertIsNotNone(available_class.created_at)


if __name__ == "__main__":
    unittest.main()
