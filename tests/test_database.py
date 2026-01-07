"""Unit tests for the zdrofit bot."""

import sys
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import Database
from src.database.models import User, UserFilter, AvailableClass, FilterCatalog
from src.api.filter import filter_classes
from src.utils.helpers import (
    parse_datetime, format_datetime_display, 
    is_class_available_soon, sanitize_class_data
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
    
    def test_is_class_available_soon(self):
        """Test checking if class is available soon."""
        # Class in 24 hours
        future_time = datetime.now() + timedelta(hours=24)
        self.assertTrue(is_class_available_soon(future_time))
        
        # Class in 49 hours (beyond 48 hour window)
        far_future = datetime.now() + timedelta(hours=49)
        self.assertFalse(is_class_available_soon(far_future))
        
        # Class in the past
        past_time = datetime.now() - timedelta(hours=1)
        self.assertFalse(is_class_available_soon(past_time))
    
    def test_sanitize_class_data(self):
        """Test class data sanitization."""
        raw_data = {
            "id": "123",
            "title": "Yoga",
            "gym": "Main Hall",
            "trainer": "John",
            "activity": "yoga",
            "available_spots": "5"
        }
        
        sanitized = sanitize_class_data(raw_data)
        
        self.assertEqual(sanitized["id"], "123")
        self.assertEqual(sanitized["gym_name"], "Main Hall")
        self.assertEqual(sanitized["trainer_name"], "John")
        self.assertEqual(sanitized["available_spots"], 5)


if __name__ == "__main__":
    unittest.main()
