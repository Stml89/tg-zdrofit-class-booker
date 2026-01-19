#!/usr/bin/env python
"""Unit tests for database models."""

import unittest
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.models import User, UserFilter, Booking


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
    
    def test_filter_auto_booking_enabled(self):
        """Test filter with auto_booking enabled."""
        user_filter = UserFilter(
            user_id=123456,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates",
            auto_booking=True
        )
        
        self.assertTrue(user_filter.auto_booking)
    
    def test_filter_auto_booking_default_disabled(self):
        """Test that auto_booking defaults to False."""
        user_filter = UserFilter(
            user_id=123456,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Yoga"
        )
        
        self.assertFalse(user_filter.auto_booking)


class TestBooking(unittest.TestCase):
    """Test Booking model."""
    
    def test_booking_creation(self):
        """Test creating a basic booking."""
        start_time = datetime.now() + timedelta(days=1)
        
        booking = Booking(
            user_id=123456,
            class_id="1091041",
            title="Trening Cross",
            start_time=start_time
        )
        
        self.assertEqual(booking.user_id, 123456)
        self.assertEqual(booking.class_id, "1091041")
        self.assertEqual(booking.title, "Trening Cross")
        self.assertEqual(booking.start_time, start_time)
        self.assertIsNotNone(booking.created_at)
    
    def test_booking_with_auto_booking_fields(self):
        """Test booking with auto-booking fields."""
        start_time = datetime.now() + timedelta(days=1)
        
        booking = Booking(
            user_id=123456,
            class_id="1091041",
            title="Trening Cross",
            start_time=start_time,
            filter_id=1,
            is_auto_booked=True
        )
        
        self.assertEqual(booking.filter_id, 1)
        self.assertTrue(booking.is_auto_booked)
    
    def test_booking_auto_booked_default_false(self):
        """Test that is_auto_booked defaults to False."""
        booking = Booking(
            user_id=123456,
            class_id="1091041",
            title="Trening Cross",
            start_time=datetime.now()
        )
        
        self.assertFalse(booking.is_auto_booked)
        self.assertIsNone(booking.filter_id)
    
    def test_booking_manual_booking(self):
        """Test manual booking (without auto-booking fields)."""
        booking = Booking(
            user_id=123456,
            class_id="1091041",
            title="Yoga",
            start_time=datetime.now(),
            is_auto_booked=False
        )
        
        self.assertFalse(booking.is_auto_booked)
        self.assertIsNone(booking.filter_id)
    
    def test_booking_cancellation(self):
        """Test booking with cancellation info."""
        start_time = datetime.now() + timedelta(days=1)
        cancel_time = datetime.now()
        
        booking = Booking(
            user_id=123456,
            class_id="1091041",
            title="Pilates",
            start_time=start_time,
            cancelled_at=cancel_time,
            filter_id=1,
            is_auto_booked=True
        )
        
        self.assertIsNotNone(booking.cancelled_at)
        self.assertEqual(booking.cancelled_at, cancel_time)
        self.assertTrue(booking.is_auto_booked)


if __name__ == "__main__":
    unittest.main()
