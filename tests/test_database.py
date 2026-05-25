"""Unit tests for database operations."""

import sys
import os
import unittest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import Database
from src.database.models import User, UserFilter, Booking
from src.api.filter import filter_classes
from src.utils.helpers import (
    parse_datetime, format_datetime_display, 
    is_class_available_soon
)


class TestFiltering(unittest.TestCase):
    """Test class filtering logic."""
    
    def setUp(self):
        """Set up test data."""
        self.classes = [
            {
                "Id": "1",
                "Title": "Yoga",
                "ZoneId": "10",
                "ZoneName": "Zdrofit Bemowo",
                "TrainerId": "185",
                "TrainerName": "Adam",
                "TimetableId": "20",
                "TimetableName": "Tabata",
                "AvailableSpots": 5
            },
            {
                "Id": "2",
                "Title": "Pilates",
                "ZoneId": "63",
                "ZoneName": "Zdrofit Lazurowa",
                "TrainerId": "200",
                "TrainerName": "Jane",
                "TimetableId": "30",
                "TimetableName": "Cardio",
                "AvailableSpots": 3
            }
        ]
    
    def test_filter_by_zone(self):
        """Test filtering by zone."""
        user_filter = UserFilter(zone_id="10")
        filtered = filter_classes(self.classes, user_filter)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["Id"], "1")
    
    def test_filter_by_trainer(self):
        """Test filtering by trainer."""
        user_filter = UserFilter(trainer_id="200")
        filtered = filter_classes(self.classes, user_filter)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["Id"], "2")
    
    def test_filter_by_timetable(self):
        """Test filtering by timetable."""
        user_filter = UserFilter(timetable_id="20")
        filtered = filter_classes(self.classes, user_filter)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["Id"], "1")
    
    def test_filter_multiple_criteria(self):
        """Test filtering by multiple criteria."""
        user_filter = UserFilter(
            zone_id="63",
            trainer_id="200",
            timetable_id="30"
        )
        filtered = filter_classes(self.classes, user_filter)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["Id"], "2")
    
    def test_filter_no_matches(self):
        """Test filtering with no matches."""
        user_filter = UserFilter(zone_id="999")
        filtered = filter_classes(self.classes, user_filter)
        
        self.assertEqual(len(filtered), 0)
    
    def test_filter_with_none_filter(self):
        """Test filtering with no filter set."""
        filtered = filter_classes(self.classes, None)
        
        self.assertEqual(len(filtered), len(self.classes))


class TestHelpers(unittest.TestCase):
    """Test helper functions."""
    
    def test_parse_datetime(self):
        """Test datetime parsing."""
        dt_string = "2026-01-01T14:30:00Z"
        dt = parse_datetime(dt_string)
        
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 1)
    
    def test_format_datetime_display(self):
        """Test datetime formatting for display."""
        dt = datetime(2026, 1, 1, 14, 30)
        formatted = format_datetime_display(dt)
        
        self.assertEqual(formatted, "01.01.2026 14:30")


class TestBookingCancellation(unittest.TestCase):
    """Test booking cancellation operations."""
    
    def setUp(self):
        """Create a temporary database and user for testing."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        self.db = Database(self.db_path)
        
        # Add a test user
        user = User(
            telegram_id=777777,
            zdrofit_email="booking_test@example.com",
            zdrofit_password="password123"
        )
        self.db.add_user(user)
    
    def tearDown(self):
        """Clean up temporary database."""
        try:
            Path(self.db_path).unlink()
        except:
            pass
    
    def test_cancel_booking(self):
        """Test cancelling a booking."""
        booking = Booking(
            user_id=777777,
            class_id="class_cancel_1",
            title="Pilates",
            start_time=datetime.now() + timedelta(days=1)
        )
        
        self.db.add_booking(booking)
        
        # Verify booking was added and is active
        bookings = self.db.get_user_bookings(777777)
        self.assertEqual(len(bookings), 1)
        self.assertIsNone(bookings[0].cancelled_at)
        
        # Cancel the booking
        result = self.db.cancel_booking(777777, "class_cancel_1")
        self.assertTrue(result)
        
        # After cancellation, get_user_bookings should return empty (only active)
        bookings = self.db.get_user_bookings(777777)
        self.assertEqual(len(bookings), 0)
    
    def test_get_active_bookings_excludes_cancelled(self):
        """Test that cancelled bookings are not in active list."""
        # Add 3 bookings
        for i in range(3):
            booking = Booking(
                user_id=777777,
                class_id=f"class_cancel_{i}",
                title=f"Class {i}",
                start_time=datetime.now() + timedelta(days=1)
            )
            self.db.add_booking(booking)
        
        # Verify all 3 are active
        bookings = self.db.get_user_bookings(777777)
        self.assertEqual(len(bookings), 3)
        
        # Cancel one
        self.db.cancel_booking(777777, "class_cancel_0")
        
        # Should have 2 active bookings
        bookings = self.db.get_user_bookings(777777)
        self.assertEqual(len(bookings), 2)
        
        # Verify the cancelled one is gone from active list
        cancelled_ids = [b.class_id for b in bookings]
        self.assertNotIn("class_cancel_0", cancelled_ids)
    
    def test_is_class_booked_after_cancellation(self):
        """Test that cancelled booking is no longer considered booked."""
        booking = Booking(
            user_id=777777,
            class_id="class_check_booked",
            title="Yoga",
            start_time=datetime.now() + timedelta(days=1)
        )
        
        self.db.add_booking(booking)
        
        # Should be booked before cancellation
        is_booked = self.db.is_class_booked(777777, "class_check_booked")
        self.assertTrue(is_booked)
        
        # Cancel the booking
        self.db.cancel_booking(777777, "class_check_booked")
        
        # Cancelled booking should not count as currently booked
        is_booked = self.db.is_class_booked(777777, "class_check_booked")
        self.assertFalse(is_booked)


if __name__ == "__main__":
    unittest.main()
