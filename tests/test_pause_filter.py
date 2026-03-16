"""Tests for the filter pause/freeze feature."""

import unittest
import os
import tempfile
from datetime import datetime, timedelta

from src.database.db import Database
from src.database.models import UserFilter, User


class TestFilterPauseModel(unittest.TestCase):
    """Test UserFilter pause model properties."""
    
    def test_is_paused_when_no_pause(self):
        """Filter without paused_until should not be paused."""
        f = UserFilter(id=1, user_id=123, paused_until=None)
        self.assertFalse(f.is_paused)
    
    def test_is_paused_when_future(self):
        """Filter with future paused_until should be paused."""
        f = UserFilter(id=1, user_id=123, paused_until=datetime.now() + timedelta(days=3))
        self.assertTrue(f.is_paused)
    
    def test_is_paused_when_past(self):
        """Filter with past paused_until should not be paused."""
        f = UserFilter(id=1, user_id=123, paused_until=datetime.now() - timedelta(hours=1))
        self.assertFalse(f.is_paused)
    
    def test_is_paused_default(self):
        """Filter created without pause should default to not paused."""
        f = UserFilter(id=1, user_id=123)
        self.assertFalse(f.is_paused)
        self.assertIsNone(f.paused_until)


class TestFilterPauseDatabase(unittest.TestCase):
    """Test database pause/unpause operations."""
    
    def setUp(self):
        """Create temporary database for each test."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db = Database(db_path=self.temp_db.name)
        
        # Create a test user
        user = User(telegram_id=999999, zdrofit_email='test@test.com', zdrofit_password='pass123')
        self.db.add_user(user)
        
        # Create a test filter
        user_filter = UserFilter(
            user_id=999999,
            club_id=75,
            club_name="Zdrofit Lazurowa",
            timetable_id="63",
            timetable_name="Pilates",
            auto_booking=True
        )
        self.db.add_filter(user_filter)
        self.filter_id = self.db.get_all_filters(999999)[0].id
    
    def tearDown(self):
        """Remove temporary database."""
        os.unlink(self.temp_db.name)
    
    def test_pause_filter(self):
        """Test pausing a filter."""
        paused_until = datetime.now() + timedelta(days=7)
        result = self.db.pause_filter(self.filter_id, 999999, paused_until)
        self.assertTrue(result)
        
        # Verify the filter is paused
        filters = self.db.get_all_filters(999999)
        self.assertEqual(len(filters), 1)
        self.assertTrue(filters[0].is_paused)
        self.assertIsNotNone(filters[0].paused_until)
    
    def test_unpause_filter(self):
        """Test unpausing a filter."""
        # First pause it
        paused_until = datetime.now() + timedelta(days=7)
        self.db.pause_filter(self.filter_id, 999999, paused_until)
        
        # Then unpause it
        result = self.db.unpause_filter(self.filter_id, 999999)
        self.assertTrue(result)
        
        # Verify the filter is not paused
        filters = self.db.get_all_filters(999999)
        self.assertEqual(len(filters), 1)
        self.assertFalse(filters[0].is_paused)
        self.assertIsNone(filters[0].paused_until)
    
    def test_pause_preserves_other_fields(self):
        """Test that pausing a filter doesn't change other fields."""
        filters_before = self.db.get_all_filters(999999)
        
        paused_until = datetime.now() + timedelta(days=3)
        self.db.pause_filter(self.filter_id, 999999, paused_until)
        
        filters_after = self.db.get_all_filters(999999)
        
        self.assertEqual(filters_before[0].club_name, filters_after[0].club_name)
        self.assertEqual(filters_before[0].timetable_name, filters_after[0].timetable_name)
        self.assertEqual(filters_before[0].auto_booking, filters_after[0].auto_booking)
    
    def test_get_expired_paused_filters_returns_expired(self):
        """Test that expired paused filters are returned."""
        # Pause with past time (already expired)
        expired_time = datetime.now() - timedelta(hours=1)
        self.db.pause_filter(self.filter_id, 999999, expired_time)
        
        expired = self.db.get_expired_paused_filters()
        self.assertEqual(len(expired), 1)
        self.assertEqual(expired[0].id, self.filter_id)
    
    def test_get_expired_paused_filters_ignores_active(self):
        """Test that actively paused filters are not returned as expired."""
        # Pause with future time (still active)
        future_time = datetime.now() + timedelta(days=7)
        self.db.pause_filter(self.filter_id, 999999, future_time)
        
        expired = self.db.get_expired_paused_filters()
        self.assertEqual(len(expired), 0)
    
    def test_get_expired_paused_filters_ignores_unpaused(self):
        """Test that non-paused filters are not returned."""
        # Don't pause anything
        expired = self.db.get_expired_paused_filters()
        self.assertEqual(len(expired), 0)
    
    def test_pause_wrong_user(self):
        """Test that pausing with wrong user_id doesn't affect the filter."""
        paused_until = datetime.now() + timedelta(days=7)
        self.db.pause_filter(self.filter_id, 111111, paused_until)  # Wrong user
        
        filters = self.db.get_all_filters(999999)
        self.assertFalse(filters[0].is_paused)
    
    def test_pause_durations(self):
        """Test various pause durations."""
        for days in [1, 3, 7, 14, 21]:
            paused_until = datetime.now() + timedelta(days=days)
            self.db.pause_filter(self.filter_id, 999999, paused_until)
            
            filters = self.db.get_all_filters(999999)
            self.assertTrue(filters[0].is_paused)
            
            # Unpause for next iteration
            self.db.unpause_filter(self.filter_id, 999999)
    
    def test_multiple_filters_independent_pause(self):
        """Test that pausing one filter doesn't affect another."""
        # Create second filter
        filter2 = UserFilter(
            user_id=999999,
            club_id=7,
            club_name="Zdrofit Bemowo",
            timetable_id="20",
            timetable_name="Trening Cross",
            auto_booking=False
        )
        self.db.add_filter(filter2)
        all_filters = self.db.get_all_filters(999999)
        filter2_id = all_filters[1].id
        
        # Pause only first filter
        paused_until = datetime.now() + timedelta(days=7)
        self.db.pause_filter(self.filter_id, 999999, paused_until)
        
        # Verify only first is paused
        all_filters = self.db.get_all_filters(999999)
        self.assertTrue(all_filters[0].is_paused)
        self.assertFalse(all_filters[1].is_paused)


class TestSchedulerPauseSkip(unittest.TestCase):
    """Test that the scheduler skips paused filters."""
    
    def test_paused_filter_is_skipped(self):
        """Paused filter should be skipped in processing."""
        paused_filter = UserFilter(
            id=1, user_id=123, club_id=7,
            paused_until=datetime.now() + timedelta(days=3)
        )
        active_filter = UserFilter(
            id=2, user_id=123, club_id=75,
            paused_until=None
        )
        
        # Simulate scheduler logic
        filters_to_process = [f for f in [paused_filter, active_filter] if not f.is_paused]
        
        self.assertEqual(len(filters_to_process), 1)
        self.assertEqual(filters_to_process[0].id, 2)
    
    def test_expired_pause_not_skipped(self):
        """Filter with expired pause should not be skipped."""
        expired_filter = UserFilter(
            id=1, user_id=123, club_id=7,
            paused_until=datetime.now() - timedelta(hours=1)
        )
        
        filters_to_process = [f for f in [expired_filter] if not f.is_paused]
        
        self.assertEqual(len(filters_to_process), 1)
    
    def test_all_paused_results_empty(self):
        """When all filters are paused, none should be processed."""
        filters = [
            UserFilter(id=1, user_id=123, club_id=7, paused_until=datetime.now() + timedelta(days=1)),
            UserFilter(id=2, user_id=123, club_id=75, paused_until=datetime.now() + timedelta(days=5)),
        ]
        
        filters_to_process = [f for f in filters if not f.is_paused]
        self.assertEqual(len(filters_to_process), 0)


if __name__ == '__main__':
    unittest.main()
