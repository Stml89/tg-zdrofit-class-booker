#!/usr/bin/env python
"""Unit tests for weekday filtering functionality."""

import unittest
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.zdrofit_client import ZdrofitAPIClient


class TestWeekdayFiltering(unittest.TestCase):
    """Test weekday filtering logic in ZdrofitAPIClient."""
    
    def setUp(self):
        """Set up test client and sample classes."""
        self.client = ZdrofitAPIClient("test@example.com", "password")
        
        # Create sample classes for different days
        # Monday class
        monday = datetime(2026, 1, 19, 6, 0)  # Monday, January 19, 2026 at 06:00
        # Tuesday class
        tuesday = datetime(2026, 1, 20, 6, 15)  # Tuesday, January 20, 2026 at 06:15
        # Wednesday class
        wednesday = datetime(2026, 1, 21, 6, 0)  # Wednesday, January 21, 2026 at 06:00
        # Thursday class
        thursday = datetime(2026, 1, 22, 6, 15)  # Thursday, January 22, 2026 at 06:15
        # Friday class
        friday = datetime(2026, 1, 23, 6, 0)  # Friday, January 23, 2026 at 06:00
        # Saturday class
        saturday = datetime(2026, 1, 24, 10, 0)  # Saturday, January 24, 2026 at 10:00
        # Sunday class
        sunday = datetime(2026, 1, 25, 10, 0)  # Sunday, January 25, 2026 at 10:00
        
        self.classes = [
            {
                "id": "1",
                "title": "Monday Class",
                "start_time": monday.isoformat() + "Z",
                "trainer_name": "ANDRZEJ KOWALSKI"
            },
            {
                "id": "2",
                "title": "Tuesday Class",
                "start_time": tuesday.isoformat() + "Z",
                "trainer_name": "ANDRZEJ KOWALSKI"
            },
            {
                "id": "3",
                "title": "Wednesday Class",
                "start_time": wednesday.isoformat() + "Z",
                "trainer_name": "ANDRZEJ KOWALSKI"
            },
            {
                "id": "4",
                "title": "Thursday Class",
                "start_time": thursday.isoformat() + "Z",
                "trainer_name": "ANDRZEJ KOWALSKI"
            },
            {
                "id": "5",
                "title": "Friday Class",
                "start_time": friday.isoformat() + "Z",
                "trainer_name": "ANDRZEJ KOWALSKI"
            },
            {
                "id": "6",
                "title": "Saturday Class",
                "start_time": saturday.isoformat() + "Z",
                "trainer_name": "ADAM TEST"
            },
            {
                "id": "7",
                "title": "Sunday Class",
                "start_time": sunday.isoformat() + "Z",
                "trainer_name": "ADAM TEST"
            }
        ]
    
    def test_filter_single_weekday_tuesday(self):
        """Test filtering for only Tuesday (weekday 2)."""
        weekdays = "2"  # Tuesday only
        filtered = self.client._filter_by_weekdays(self.classes, weekdays)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["id"], "2")
        self.assertEqual(filtered[0]["title"], "Tuesday Class")
    
    def test_filter_weekdays_monday_to_friday(self):
        """Test filtering for Monday-Friday (weekdays 1-5)."""
        weekdays = "1,2,3,4,5"  # Monday to Friday
        filtered = self.client._filter_by_weekdays(self.classes, weekdays)
        
        self.assertEqual(len(filtered), 5)
        ids = [c["id"] for c in filtered]
        self.assertIn("1", ids)  # Monday
        self.assertIn("2", ids)  # Tuesday
        self.assertIn("3", ids)  # Wednesday
        self.assertIn("4", ids)  # Thursday
        self.assertIn("5", ids)  # Friday
        self.assertNotIn("6", ids)  # Saturday should be excluded
        self.assertNotIn("7", ids)  # Sunday should be excluded
    
    def test_filter_weekend_only(self):
        """Test filtering for weekend only (Saturday, Sunday)."""
        weekdays = "6,7"  # Saturday, Sunday
        filtered = self.client._filter_by_weekdays(self.classes, weekdays)
        
        self.assertEqual(len(filtered), 2)
        ids = [c["id"] for c in filtered]
        self.assertIn("6", ids)  # Saturday
        self.assertIn("7", ids)  # Sunday
    
    def test_filter_specific_days_tuesday_thursday(self):
        """Test filtering for Tuesday and Thursday only."""
        weekdays = "2,4"  # Tuesday, Thursday
        filtered = self.client._filter_by_weekdays(self.classes, weekdays)
        
        self.assertEqual(len(filtered), 2)
        ids = [c["id"] for c in filtered]
        self.assertIn("2", ids)  # Tuesday
        self.assertIn("4", ids)  # Thursday
        self.assertNotIn("1", ids)  # Monday excluded
        self.assertNotIn("3", ids)  # Wednesday excluded
        self.assertNotIn("5", ids)  # Friday excluded
    
    def test_filter_no_weekdays_returns_all(self):
        """Test that empty weekdays filter returns all classes."""
        weekdays = ""
        filtered = self.client._filter_by_weekdays(self.classes, weekdays)
        
        self.assertEqual(len(filtered), 7)
    
    def test_filter_none_weekdays_returns_all(self):
        """Test that None weekdays filter returns all classes."""
        weekdays = None
        filtered = self.client._filter_by_weekdays(self.classes, weekdays)
        
        self.assertEqual(len(filtered), 7)
    
    def test_filter_invalid_class_no_start_time(self):
        """Test that classes without start_time are excluded."""
        classes_with_invalid = self.classes + [
            {
                "id": "8",
                "title": "No Time Class",
                "start_time": None,
                "trainer_name": "TEST"
            }
        ]
        
        weekdays = "1,2,3,4,5"
        filtered = self.client._filter_by_weekdays(classes_with_invalid, weekdays)
        
        # Should only get Monday-Friday classes, invalid one excluded
        self.assertEqual(len(filtered), 5)
        ids = [c["id"] for c in filtered]
        self.assertNotIn("8", ids)
    
    def test_real_world_bug_scenario(self):
        """
        Test the real-world bug scenario:
        Filter set for Tuesday 06:00-07:00, should NOT match Thursday 06:15.
        """
        # User's filter: Tuesday only
        weekdays = "2"  # Tuesday
        
        # Apply weekday filter
        filtered = self.client._filter_by_weekdays(self.classes, weekdays)
        
        # Should ONLY have Tuesday class
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["id"], "2")
        self.assertEqual(filtered[0]["title"], "Tuesday Class")
        
        # Thursday class should NOT be in results
        thursday_ids = [c["id"] for c in filtered if c["id"] == "4"]
        self.assertEqual(len(thursday_ids), 0, "Thursday class should be excluded when filtering for Tuesday only")


if __name__ == "__main__":
    unittest.main()
