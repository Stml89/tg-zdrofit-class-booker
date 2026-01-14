#!/usr/bin/env python
"""Unit tests for filter functionality with multiple filters support."""

import unittest
import sys
import os
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import Database
from src.database.models import User, UserFilter, Booking


class TestMultipleFilters(unittest.TestCase):
    """Test multiple filter creation and management."""
    
    def setUp(self):
        """Create a temporary database for testing."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        self.db = Database(self.db_path)
        
        # Add a test user
        user = User(
            telegram_id=888888,
            zdrofit_email="filter_test@example.com",
            zdrofit_password="password123"
        )
        self.db.add_user(user)
    
    def tearDown(self):
        """Clean up temporary database."""
        try:
            Path(self.db_path).unlink()
        except:
            pass
    
    def test_create_multiple_filters(self):
        """Test creating multiple filters for same user."""
        # Create 3 filters
        for i in range(3):
            user_filter = UserFilter(
                user_id=888888,
                club_id=75,
                club_name="Zdrofit Lazurowa",
                zone_id="167",
                zone_name="Zdrofit Lazurowa",
                timetable_id=f"63{i}",
                timetable_name=f"Class {i}",
                category_id="9",
                category_name="Mini Class"
            )
            result = self.db.add_filter(user_filter)
            self.assertTrue(result)
        
        # Retrieve all filters
        filters = self.db.get_all_filters(888888)
        self.assertEqual(len(filters), 3)
    
    def test_filter_limit_max_3(self):
        """Test that user cannot create more than 3 filters."""
        # Create 3 filters
        for i in range(3):
            user_filter = UserFilter(
                user_id=888888,
                club_id=75,
                club_name="Zdrofit Lazurowa",
                timetable_id=f"class_{i}",
                timetable_name=f"Class {i}"
            )
            result = self.db.add_filter(user_filter)
            self.assertTrue(result)
        
        # Try to create 4th filter
        user_filter_4 = UserFilter(
            user_id=888888,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="class_4",
            timetable_name="Class 4"
        )
        result = self.db.add_filter(user_filter_4)
        self.assertFalse(result)
        
        # Still should have only 3
        filters = self.db.get_all_filters(888888)
        self.assertEqual(len(filters), 3)
    
    def test_get_specific_filter_by_id(self):
        """Test retrieving a specific filter by ID."""
        # Create a filter
        user_filter = UserFilter(
            user_id=888888,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates"
        )
        self.db.add_filter(user_filter)
        
        # Get all and find ID
        filters = self.db.get_all_filters(888888)
        filter_id = filters[0].id
        
        self.assertIsNotNone(filter_id)
    
    def test_delete_specific_filter_by_id(self):
        """Test deleting a specific filter by ID."""
        # Create 2 filters
        for i in range(2):
            user_filter = UserFilter(
                user_id=888888,
                club_id=75,
                club_name="Zdrofit Lazurowa",
                timetable_id=f"63{i}",
                timetable_name=f"Class {i}"
            )
            self.db.add_filter(user_filter)
        
        filters = self.db.get_all_filters(888888)
        first_filter_id = filters[0].id
        
        # Delete first filter
        result = self.db.delete_filter_by_id(first_filter_id, 888888)
        self.assertTrue(result)
        
        # Should have 1 left
        remaining = self.db.get_all_filters(888888)
        self.assertEqual(len(remaining), 1)
        self.assertNotEqual(remaining[0].id, first_filter_id)
    
    def test_filter_with_optional_fields(self):
        """Test creating filters with minimal and full field sets."""
        # Minimal filter
        minimal_filter = UserFilter(
            user_id=888888,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates"
        )
        self.db.add_filter(minimal_filter)
        
        # Full filter
        full_filter = UserFilter(
            user_id=888888,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            zone_id="167",
            zone_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates",
            category_id="9",
            category_name="Mini Class",
            trainer_id="185",
            trainer_name="Adam",
            time_from="07:00",
            time_to="20:00",
            weekdays="1,2,3,4,5"
        )
        self.db.add_filter(full_filter)
        
        filters = self.db.get_all_filters(888888)
        self.assertEqual(len(filters), 2)
        self.assertIsNone(filters[0].trainer_id)
        self.assertIsNotNone(filters[1].trainer_id)
    
    def test_filter_with_auto_booking_enabled(self):
        """Test filter with auto-booking enabled."""
        user_filter = UserFilter(
            user_id=888888,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates",
            auto_booking=True
        )
        self.db.add_filter(user_filter)
        
        filters = self.db.get_all_filters(888888)
        self.assertTrue(filters[0].auto_booking)
    
    def test_auto_booking_flag_toggle(self):
        """Test toggling auto-booking flag for a filter."""
        # Create filter with auto_booking disabled
        user_filter = UserFilter(
            user_id=888888,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates",
            auto_booking=False
        )
        self.db.add_filter(user_filter)
        filter_id = self.db.get_all_filters(888888)[0].id
        
        # Enable auto-booking
        self.db.update_filter_auto_booking(filter_id, True, 888888)
        filters = self.db.get_all_filters(888888)
        self.assertTrue(filters[0].auto_booking)
        
        # Disable auto-booking
        self.db.update_filter_auto_booking(filter_id, False, 888888)
        filters = self.db.get_all_filters(888888)
        self.assertFalse(filters[0].auto_booking)
    
    def test_filter_with_weekdays(self):
        """Test filter with specific weekdays."""
        # Monday to Friday
        user_filter = UserFilter(
            user_id=888888,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates",
            weekdays="1,2,3,4,5"  # Mon-Fri
        )
        self.db.add_filter(user_filter)
        
        filters = self.db.get_all_filters(888888)
        self.assertEqual(filters[0].weekdays, "1,2,3,4,5")
    
    def test_filter_with_time_range(self):
        """Test filter with time range."""
        user_filter = UserFilter(
            user_id=888888,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates",
            time_from="07:00",
            time_to="20:00"
        )
        self.db.add_filter(user_filter)
        
        filters = self.db.get_all_filters(888888)
        self.assertEqual(filters[0].time_from, "07:00")
        self.assertEqual(filters[0].time_to, "20:00")


if __name__ == "__main__":
    unittest.main()
