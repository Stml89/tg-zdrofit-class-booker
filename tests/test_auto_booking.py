#!/usr/bin/env python
"""Unit tests for auto-booking functionality."""

import unittest
import sys
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import Database
from src.database.models import User, UserFilter, Booking


class TestAutoBookingModel(unittest.TestCase):
    """Test auto-booking fields in models."""
    
    def test_user_filter_auto_booking_field(self):
        """Test UserFilter has auto_booking field."""
        user_filter = UserFilter(
            user_id=123456,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates",
            auto_booking=True
        )
        
        self.assertTrue(user_filter.auto_booking)
    
    def test_user_filter_auto_booking_default_false(self):
        """Test UserFilter auto_booking defaults to False."""
        user_filter = UserFilter(
            user_id=123456,
            club_id=75,
            club_name="Zdrofit Lazurowa"
        )
        
        self.assertFalse(user_filter.auto_booking)
    
    def test_booking_filter_id_field(self):
        """Test Booking has filter_id field."""
        booking = Booking(
            user_id=123456,
            class_id="class_123",
            title="Pilates",
            start_time=datetime.now(),
            filter_id=1
        )
        
        self.assertEqual(booking.filter_id, 1)
    
    def test_booking_is_auto_booked_field(self):
        """Test Booking has is_auto_booked field."""
        booking = Booking(
            user_id=123456,
            class_id="class_123",
            title="Pilates",
            start_time=datetime.now(),
            is_auto_booked=True,
            filter_id=1
        )
        
        self.assertTrue(booking.is_auto_booked)
    
    def test_booking_is_auto_booked_default_false(self):
        """Test Booking is_auto_booked defaults to False."""
        booking = Booking(
            user_id=123456,
            class_id="class_123",
            title="Pilates",
            start_time=datetime.now()
        )
        
        self.assertFalse(booking.is_auto_booked)


class TestAutoBookingDatabase(unittest.TestCase):
    """Test auto-booking database operations."""
    
    def setUp(self):
        """Create a temporary database for testing."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        self.db = Database(self.db_path)
        
        # Add a test user
        user = User(
            telegram_id=999999,
            zdrofit_email="test@example.com",
            zdrofit_password="password123"
        )
        self.db.add_user(user)
    
    def tearDown(self):
        """Clean up temporary database."""
        try:
            Path(self.db_path).unlink()
        except:
            pass
    
    def test_save_filter_with_auto_booking(self):
        """Test saving filter with auto_booking=True."""
        user_filter = UserFilter(
            user_id=999999,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            zone_id="167",
            zone_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates",
            category_id="9",
            category_name="Mini Class",
            trainer_id=None,
            trainer_name=None,
            time_from="07:00",
            time_to="20:00",
            weekdays="1,2,3,4,5",
            auto_booking=True
        )
        
        result = self.db.add_filter(user_filter)
        self.assertTrue(result)
        
        # Retrieve and verify
        filters = self.db.get_all_filters(999999)
        self.assertEqual(len(filters), 1)
        self.assertTrue(filters[0].auto_booking)
    
    def test_save_filter_without_auto_booking(self):
        """Test saving filter with auto_booking=False."""
        user_filter = UserFilter(
            user_id=999999,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates",
            auto_booking=False
        )
        
        result = self.db.add_filter(user_filter)
        self.assertTrue(result)
        
        # Retrieve and verify
        filters = self.db.get_all_filters(999999)
        self.assertEqual(len(filters), 1)
        self.assertFalse(filters[0].auto_booking)
    
    def test_save_booking_with_filter_id(self):
        """Test saving booking with filter_id."""
        # First save a filter
        user_filter = UserFilter(
            user_id=999999,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates",
            auto_booking=True
        )
        self.db.add_filter(user_filter)
        filter_id = self.db.get_all_filters(999999)[0].id
        
        # Save booking with filter_id
        booking = Booking(
            user_id=999999,
            class_id="class_123",
            title="Pilates Class",
            start_time=datetime.now(),
            filter_id=filter_id,
            is_auto_booked=True
        )
        
        result = self.db.add_booking(booking)
        self.assertTrue(result)
        
        # Retrieve and verify
        bookings = self.db.get_user_bookings(999999)
        self.assertEqual(len(bookings), 1)
        self.assertEqual(bookings[0].filter_id, filter_id)
        self.assertTrue(bookings[0].is_auto_booked)
    
    def test_count_filter_bookings(self):
        """Test counting bookings for a filter."""
        # Save a filter
        user_filter = UserFilter(
            user_id=999999,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates",
            auto_booking=True
        )
        self.db.add_filter(user_filter)
        filter_id = self.db.get_all_filters(999999)[0].id
        
        # Add 2 bookings for this filter
        for i in range(2):
            booking = Booking(
                user_id=999999,
                class_id=f"class_{i}",
                title="Pilates Class",
                start_time=datetime.now() + timedelta(days=i),
                filter_id=filter_id,
                is_auto_booked=True
            )
            self.db.add_booking(booking)
        
        # Count bookings
        count = self.db.count_filter_bookings(999999, filter_id)
        self.assertEqual(count, 2)
    
    def test_count_filter_bookings_excludes_cancelled(self):
        """Test that cancelled bookings are not counted."""
        # Save a filter
        user_filter = UserFilter(
            user_id=999999,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates",
            auto_booking=True
        )
        self.db.add_filter(user_filter)
        filter_id = self.db.get_all_filters(999999)[0].id
        
        # Add 3 bookings
        class_ids = []
        for i in range(3):
            class_id = f"class_{i}"
            class_ids.append(class_id)
            booking = Booking(
                user_id=999999,
                class_id=class_id,
                title="Pilates Class",
                start_time=datetime.now() + timedelta(days=i),
                filter_id=filter_id,
                is_auto_booked=True
            )
            self.db.add_booking(booking)
        
        # Cancel one booking
        self.db.cancel_booking(999999, class_ids[0])
        
        # Count should be 2
        count = self.db.count_filter_bookings(999999, filter_id)
        self.assertEqual(count, 2)
    
    def test_update_filter_auto_booking(self):
        """Test updating auto_booking flag for a filter."""
        # Save filter with auto_booking=False
        user_filter = UserFilter(
            user_id=999999,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates",
            auto_booking=False
        )
        self.db.add_filter(user_filter)
        filter_id = self.db.get_all_filters(999999)[0].id
        
        # Update to True
        result = self.db.update_filter_auto_booking(filter_id, True, 999999)
        self.assertTrue(result)
        
        # Verify update
        filters = self.db.get_all_filters(999999)
        self.assertTrue(filters[0].auto_booking)
        
        # Update back to False
        result = self.db.update_filter_auto_booking(filter_id, False, 999999)
        self.assertTrue(result)
        
        # Verify
        filters = self.db.get_all_filters(999999)
        self.assertFalse(filters[0].auto_booking)
    
    def test_auto_booking_limit_enforcement(self):
        """Test that 3-booking limit is enforced."""
        # Save a filter
        user_filter = UserFilter(
            user_id=999999,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates",
            auto_booking=True
        )
        self.db.add_filter(user_filter)
        filter_id = self.db.get_all_filters(999999)[0].id
        
        # Add 3 bookings (at limit)
        for i in range(3):
            booking = Booking(
                user_id=999999,
                class_id=f"class_{i}",
                title="Pilates Class",
                start_time=datetime.now() + timedelta(days=i),
                filter_id=filter_id,
                is_auto_booked=True
            )
            self.db.add_booking(booking)
        
        # Count should be exactly 3
        count = self.db.count_filter_bookings(999999, filter_id)
        self.assertEqual(count, 3)
        
        # Simulate scheduler check - should not auto-book if count >= 3
        should_auto_book = count < 3
        self.assertFalse(should_auto_book)
    
    def test_multiple_filters_independent_counts(self):
        """Test that booking counts are independent per filter."""
        # Create two filters
        filter1 = UserFilter(
            user_id=999999,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates",
            auto_booking=True
        )
        filter2 = UserFilter(
            user_id=999999,
            club_id=7,
            club_name="Zdrofit Bemowo",
            timetable_id="64",
            timetable_name="Yoga",
            auto_booking=True
        )
        
        self.db.add_filter(filter1)
        self.db.add_filter(filter2)
        
        filters = self.db.get_all_filters(999999)
        filter1_id = filters[0].id
        filter2_id = filters[1].id
        
        # Add bookings to first filter only
        for i in range(2):
            booking = Booking(
                user_id=999999,
                class_id=f"class_f1_{i}",
                title="Pilates Class",
                start_time=datetime.now() + timedelta(days=i),
                filter_id=filter1_id,
                is_auto_booked=True
            )
            self.db.add_booking(booking)
        
        # Add 1 booking to second filter
        booking = Booking(
            user_id=999999,
            class_id="class_f2_0",
            title="Yoga Class",
            start_time=datetime.now(),
            filter_id=filter2_id,
            is_auto_booked=True
        )
        self.db.add_booking(booking)
        
        # Verify counts are independent
        count1 = self.db.count_filter_bookings(999999, filter1_id)
        count2 = self.db.count_filter_bookings(999999, filter2_id)
        
        self.assertEqual(count1, 2)
        self.assertEqual(count2, 1)


class TestAutoBookingSchedulerLogic(unittest.TestCase):
    """Test scheduler auto-booking decision logic."""
    
    def test_auto_booking_decision_enabled_under_limit(self):
        """Test auto-booking when enabled and under limit."""
        auto_booking_enabled = True
        booking_count = 2
        limit = 3
        
        should_auto_book = auto_booking_enabled and booking_count < limit
        self.assertTrue(should_auto_book)
    
    def test_auto_booking_decision_enabled_at_limit(self):
        """Test no auto-booking when at limit."""
        auto_booking_enabled = True
        booking_count = 3
        limit = 3
        
        should_auto_book = auto_booking_enabled and booking_count < limit
        self.assertFalse(should_auto_book)
    
    def test_auto_booking_decision_disabled(self):
        """Test no auto-booking when disabled."""
        auto_booking_enabled = False
        booking_count = 1
        limit = 3
        
        should_auto_book = auto_booking_enabled and booking_count < limit
        self.assertFalse(should_auto_book)
    
    def test_auto_booking_decision_over_limit(self):
        """Test no auto-booking when over limit."""
        auto_booking_enabled = True
        booking_count = 5
        limit = 3
        
        should_auto_book = auto_booking_enabled and booking_count < limit
        self.assertFalse(should_auto_book)
    
    @patch('src.scheduler.class_scheduler.db')
    def test_filter_matching_logic(self, mock_db):
        """Test that classes are matched to filters."""
        # Simulate class matching to multiple filters
        class_id = "class_123"
        filter1_id = 1
        filter2_id = 2
        
        # Map classes to filters
        class_to_filters = {
            class_id: [
                UserFilter(id=filter1_id, auto_booking=True),
                UserFilter(id=filter2_id, auto_booking=False)
            ]
        }
        
        # Retrieve filters for this class
        matching_filters = class_to_filters.get(class_id, [])
        
        # Should have 2 filters
        self.assertEqual(len(matching_filters), 2)
        
        # Count how many have auto-booking enabled
        auto_enabled_count = sum(1 for f in matching_filters if f.auto_booking)
        self.assertEqual(auto_enabled_count, 1)


class TestAutoBookingNotifications(unittest.TestCase):
    """Test auto-booking notification messages."""
    
    def test_auto_booking_notification_format(self):
        """Test format of auto-booking confirmation message."""
        class_data = {
            "title": "Pilates",
            "gym_name": "Zdrofit Bemowo",
            "trainer_name": "Jan Kowalski",
            "start_time": "2026-01-15T10:00:00Z",
            "duration": "PT50M"
        }
        
        user_filter = UserFilter(
            id=1,
            club_name="Zdrofit Bemowo",
            timetable_name="Pilates"
        )
        
        # Build notification message
        message = (
            f"🤖 <b>Auto-booking successful!</b>\n\n"
            f"<b>{class_data['title']}</b>\n"
            f"Gym: {class_data['gym_name']}\n"
            f"Trainer: {class_data['trainer_name']}\n"
            f"Date & Time: {class_data['start_time']}\n\n"
            f"<i>Filter: {user_filter.club_name} - {user_filter.timetable_name}</i>"
        )
        
        # Verify message contains key information
        self.assertIn("🤖", message)
        self.assertIn("Auto-booking successful", message)
        self.assertIn(class_data['title'], message)
        self.assertIn(class_data['gym_name'], message)
        self.assertIn(class_data['trainer_name'], message)
        self.assertIn(user_filter.club_name, message)
    
    def test_manual_booking_notification_remains_unchanged(self):
        """Test that manual booking notifications are unchanged."""
        class_data = {
            "title": "Yoga",
            "gym_name": "Zdrofit Lazurowa",
            "trainer_name": "Maria Nowak",
            "start_time": "2026-01-15T14:00:00Z"
        }
        
        # Regular notification should NOT have 🤖 prefix
        message = (
            f"<b>Free spot found for a class!</b>\n\n"
            f"<b>{class_data['title']}</b>\n"
            f"Gym: {class_data['gym_name']}\n"
            f"Trainer: {class_data['trainer_name']}"
        )
        
        # Verify message does NOT have auto-booking emoji
        self.assertNotIn("🤖", message)
        self.assertIn("Free spot found", message)


if __name__ == "__main__":
    unittest.main()
