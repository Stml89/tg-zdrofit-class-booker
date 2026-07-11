"""Tests for the 'Not Interested' (skipped classes) feature."""

import sys
import os
import unittest
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import Database


class TestSkippedClassesDatabase(unittest.TestCase):
    """Test database operations for skipped classes."""

    def setUp(self):
        """Set up a temporary test database."""
        self.test_db_path = tempfile.mktemp(suffix=".db")
        self.db = Database(db_path=self.test_db_path)

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

    def test_no_skipped_classes_initially(self):
        """A new user should have no skipped classes."""
        self.assertEqual(self.db.get_skipped_class_ids(12345), [])

    def test_add_and_get_skipped_class(self):
        """Adding a skipped class should be retrievable."""
        self.assertTrue(self.db.add_skipped_class(12345, "class_abc"))
        self.assertEqual(self.db.get_skipped_class_ids(12345), ["class_abc"])

    def test_add_multiple_skipped_classes(self):
        """Multiple skipped classes should all be tracked."""
        self.db.add_skipped_class(12345, "class_1")
        self.db.add_skipped_class(12345, "class_2")
        self.db.add_skipped_class(12345, "class_3")
        self.assertCountEqual(
            self.db.get_skipped_class_ids(12345),
            ["class_1", "class_2", "class_3"],
        )

    def test_duplicate_skip_ignored(self):
        """Skipping the same class twice should not create duplicates."""
        self.db.add_skipped_class(12345, "class_1")
        self.db.add_skipped_class(12345, "class_1")
        self.assertEqual(self.db.get_skipped_class_ids(12345), ["class_1"])

    def test_skips_are_per_user(self):
        """Skipped classes should be isolated per user."""
        self.db.add_skipped_class(111, "class_a")
        self.db.add_skipped_class(222, "class_b")
        self.assertEqual(self.db.get_skipped_class_ids(111), ["class_a"])
        self.assertEqual(self.db.get_skipped_class_ids(222), ["class_b"])

    def test_integer_class_id_stored_as_string(self):
        """Integer class IDs should be normalized to strings."""
        self.db.add_skipped_class(12345, 999)
        self.assertEqual(self.db.get_skipped_class_ids(12345), ["999"])


class TestSchedulerSkipsNotifications(unittest.IsolatedAsyncioTestCase):
    """Verify the scheduler does not notify about skipped classes."""

    def setUp(self):
        self.test_db_path = tempfile.mktemp(suffix=".db")
        self.db = Database(db_path=self.test_db_path)
        # Register a user so foreign keys are satisfied
        from src.database.models import User, UserFilter
        self.db.add_user(User(
            telegram_id=999,
            zdrofit_email="user@example.com",
            zdrofit_password="secret",
        ))
        # Register an active filter so the scheduler fetches classes
        self.db.add_filter(UserFilter(
            user_id=999,
            club_id=7,
            club_name="Test Club",
            zone_id="10",
            timetable_id="20",
        ))

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

    async def test_skipped_class_not_notified(self):
        """A class marked as skipped must not trigger a notification, others should."""
        from src.scheduler.class_scheduler import ClassCheckScheduler

        # User skipped class "skip_me"
        self.db.add_skipped_class(999, "skip_me")

        # Two available classes: one skipped, one new
        available_classes = [
            {"id": "skip_me", "title": "Yoga", "start_time": "2099-01-01T10:00:00"},
            {"id": "new_one", "title": "Pilates", "start_time": "2099-01-01T11:00:00"},
        ]

        # Mock API client
        mock_client = MagicMock()
        mock_client.authenticate.return_value = True
        mock_client.get_classes_by_filter.return_value = available_classes
        mock_client.get_user_schedule.return_value = []  # for milestone check

        scheduler = ClassCheckScheduler()
        scheduler.notification_sender = AsyncMock()

        with patch("src.scheduler.class_scheduler.db", self.db), \
             patch("src.scheduler.class_scheduler.ZdrofitAPIClient", return_value=mock_client):
            await scheduler._check_user_classes(999, "user@example.com", "secret")

        # Only the non-skipped class should be notified
        notified_ids = [
            call.args[2] for call in scheduler.notification_sender.send_class_notification.call_args_list
        ]
        self.assertIn("new_one", notified_ids)
        self.assertNotIn("skip_me", notified_ids)
        self.assertEqual(len(notified_ids), 1)

    async def test_skipped_class_not_notified_integer_ids(self):
        """Regression: API returns integer class IDs but skips are stored as strings.

        Ensures the int/str mismatch does not cause skipped classes to be notified.
        """
        from src.scheduler.class_scheduler import ClassCheckScheduler

        # User skipped class 1308455 (stored as string "1308455")
        self.db.add_skipped_class(999, 1308455)

        # API returns integer IDs (as real JSON does)
        available_classes = [
            {"id": 1308455, "title": "Stretching", "start_time": "2099-01-01T08:00:00"},
            {"id": 1308999, "title": "Stretching", "start_time": "2099-01-01T09:00:00"},
        ]

        mock_client = MagicMock()
        mock_client.authenticate.return_value = True
        mock_client.get_classes_by_filter.return_value = available_classes
        mock_client.get_user_schedule.return_value = []

        scheduler = ClassCheckScheduler()
        scheduler.notification_sender = AsyncMock()

        with patch("src.scheduler.class_scheduler.db", self.db), \
             patch("src.scheduler.class_scheduler.ZdrofitAPIClient", return_value=mock_client):
            await scheduler._check_user_classes(999, "user@example.com", "secret")

        notified_ids = [
            call.args[2] for call in scheduler.notification_sender.send_class_notification.call_args_list
        ]
        self.assertIn(1308999, notified_ids)
        self.assertNotIn(1308455, notified_ids)
        self.assertEqual(len(notified_ids), 1)

    async def test_no_filters_no_notifications(self):
        """With no filters configured, the scheduler must not notify at all."""
        from src.scheduler.class_scheduler import ClassCheckScheduler
        from src.database.models import User

        # Fresh user with NO filters
        self.db.add_user(User(
            telegram_id=1000,
            zdrofit_email="nofilter@example.com",
            zdrofit_password="secret",
        ))

        mock_client = MagicMock()
        mock_client.authenticate.return_value = True
        mock_client.get_classes_by_filter.return_value = [
            {"id": 1, "title": "Yoga", "start_time": "2099-01-01T10:00:00"},
        ]
        mock_client.get_available_classes.return_value = [
            {"id": 2, "title": "Pilates", "start_time": "2099-01-01T11:00:00"},
        ]
        mock_client.get_user_schedule.return_value = []

        scheduler = ClassCheckScheduler()
        scheduler.notification_sender = AsyncMock()

        with patch("src.scheduler.class_scheduler.db", self.db), \
             patch("src.scheduler.class_scheduler.ZdrofitAPIClient", return_value=mock_client):
            await scheduler._check_user_classes(1000, "nofilter@example.com", "secret")

        # No notifications and no fallback class fetch
        scheduler.notification_sender.send_class_notification.assert_not_called()
        mock_client.get_available_classes.assert_not_called()
        mock_client.get_classes_by_filter.assert_not_called()


if __name__ == "__main__":
    unittest.main()

