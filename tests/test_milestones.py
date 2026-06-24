"""Tests for milestone system."""

import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import tempfile
import os

from src.milestones import get_milestone, get_new_milestones, Milestone, FIXED_MILESTONES


class TestGetMilestone(unittest.TestCase):
    """Test get_milestone function."""

    def test_fixed_milestones_exist(self):
        """All fixed milestones should be returned correctly."""
        for m in FIXED_MILESTONES:
            result = get_milestone(m.count)
            self.assertIsNotNone(result)
            self.assertEqual(result.count, m.count)
            self.assertEqual(result.type, m.type)

    def test_non_milestone_returns_none(self):
        """Non-milestone counts should return None."""
        self.assertIsNone(get_milestone(1))
        self.assertIsNone(get_milestone(7))
        self.assertIsNone(get_milestone(11))
        self.assertIsNone(get_milestone(99))
        self.assertIsNone(get_milestone(201))

    def test_dynamic_badge_every_100_above_200(self):
        """Counts > 200 that are multiples of 100 should be badges."""
        for count in [300, 400, 500, 1000]:
            result = get_milestone(count)
            self.assertIsNotNone(result, f"Expected milestone at {count}")
            self.assertEqual(result.type, "badge")
            self.assertEqual(result.count, count)
            self.assertIn(str(count), result.text)

    def test_dynamic_message_every_50_above_200(self):
        """Counts > 200 that are multiples of 50 (not 100) should be messages."""
        for count in [250, 350, 450, 550]:
            result = get_milestone(count)
            self.assertIsNotNone(result, f"Expected milestone at {count}")
            self.assertEqual(result.type, "message")
            self.assertEqual(result.count, count)
            self.assertIn(str(count), result.text)

    def test_dynamic_non_milestone_above_200(self):
        """Counts > 200 that are not multiples of 50 should return None."""
        self.assertIsNone(get_milestone(210))
        self.assertIsNone(get_milestone(275))
        self.assertIsNone(get_milestone(301))

    def test_milestone_5_is_message(self):
        m = get_milestone(5)
        self.assertEqual(m.type, "message")

    def test_milestone_10_is_badge(self):
        m = get_milestone(10)
        self.assertEqual(m.type, "badge")
        self.assertIsNotNone(m.badge_filename)

    def test_milestone_50_is_badge(self):
        m = get_milestone(50)
        self.assertEqual(m.type, "badge")


class TestGetNewMilestones(unittest.TestCase):
    """Test get_new_milestones function."""

    def test_no_milestones_at_zero(self):
        """Zero classes means no milestones."""
        result = get_new_milestones(0, [])
        self.assertEqual(result, [])

    def test_first_milestone_at_5(self):
        """At 5 classes with nothing awarded, should get milestone 5."""
        result = get_new_milestones(5, [])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].count, 5)

    def test_multiple_milestones_at_once(self):
        """If user reaches 20 with nothing awarded, should get 5, 10, 15, 20."""
        result = get_new_milestones(20, [])
        counts = [m.count for m in result]
        self.assertEqual(counts, [5, 10, 15, 20])

    def test_already_awarded_excluded(self):
        """Already awarded milestones should not be returned."""
        result = get_new_milestones(20, [5, 10, 15])
        counts = [m.count for m in result]
        self.assertEqual(counts, [20])

    def test_no_new_milestones(self):
        """If all reached milestones are awarded, return empty."""
        result = get_new_milestones(10, [5, 10])
        self.assertEqual(result, [])

    def test_between_milestones(self):
        """At 8 classes (between 5 and 10), only 5 should be milestone."""
        result = get_new_milestones(8, [])
        counts = [m.count for m in result]
        self.assertEqual(counts, [5])

    def test_dynamic_milestones_above_200(self):
        """At 300, should include all fixed + dynamic milestones."""
        all_fixed = [m.count for m in FIXED_MILESTONES]
        result = get_new_milestones(300, all_fixed)
        counts = [m.count for m in result]
        self.assertIn(250, counts)
        self.assertIn(300, counts)

    def test_sorted_output(self):
        """Results should always be sorted by count."""
        result = get_new_milestones(100, [])
        counts = [m.count for m in result]
        self.assertEqual(counts, sorted(counts))

    def test_large_count_dynamic(self):
        """Test large counts generate correct dynamic milestones."""
        awarded = [m.count for m in FIXED_MILESTONES] + [250, 300, 350, 400]
        result = get_new_milestones(500, awarded)
        counts = [m.count for m in result]
        self.assertIn(450, counts)
        self.assertIn(500, counts)
        self.assertNotIn(400, counts)  # already awarded


class TestMilestoneBadgePath(unittest.TestCase):
    """Test badge path resolution."""

    def test_badge_path_for_fixed(self):
        m = get_milestone(10)
        self.assertIsNotNone(m.badge_path)
        self.assertTrue(str(m.badge_path).endswith("badge_010.png"))

    def test_no_badge_path_for_message(self):
        m = get_milestone(5)
        self.assertIsNone(m.badge_path)

    def test_dynamic_badge_path(self):
        m = get_milestone(300)
        self.assertIsNotNone(m.badge_path)
        self.assertTrue(str(m.badge_path).endswith("badge_dynamic.png"))


class TestDatabaseMilestones(unittest.TestCase):
    """Test database milestone operations."""

    def setUp(self):
        """Set up test database."""
        from src.database.db import Database
        self.test_db_path = tempfile.mktemp(suffix=".db")
        self.db = Database(db_path=self.test_db_path)

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

    def test_get_milestones_empty(self):
        """New user should have no milestones."""
        result = self.db.get_user_milestones(12345)
        self.assertEqual(result, [])

    def test_add_and_get_milestone(self):
        """Adding a milestone should be retrievable."""
        self.db.add_user_milestone(12345, 5)
        result = self.db.get_user_milestones(12345)
        self.assertEqual(result, [5])

    def test_add_multiple_milestones(self):
        """Multiple milestones should be tracked."""
        self.db.add_user_milestone(12345, 5)
        self.db.add_user_milestone(12345, 10)
        self.db.add_user_milestone(12345, 15)
        result = self.db.get_user_milestones(12345)
        self.assertCountEqual(result, [5, 10, 15])

    def test_duplicate_milestone_ignored(self):
        """Adding same milestone twice should not duplicate."""
        self.db.add_user_milestone(12345, 10)
        self.db.add_user_milestone(12345, 10)
        result = self.db.get_user_milestones(12345)
        self.assertEqual(result, [10])

    def test_milestones_per_user(self):
        """Milestones are per-user."""
        self.db.add_user_milestone(111, 5)
        self.db.add_user_milestone(222, 10)
        self.assertEqual(self.db.get_user_milestones(111), [5])
        self.assertEqual(self.db.get_user_milestones(222), [10])


class TestNotificationSenderMilestones(unittest.IsolatedAsyncioTestCase):
    """Test milestone notification sending."""

    async def test_send_milestone_message(self):
        """Should send text message for motivation milestones."""
        from src.telegram_bot.notifications import NotificationSender
        bot = AsyncMock()
        sender = NotificationSender(bot=bot)
        await sender.send_milestone_message(123, "Test message")
        bot.send_message.assert_called_once()
        args = bot.send_message.call_args
        self.assertEqual(args.kwargs['chat_id'], 123)
        self.assertEqual(args.kwargs['text'], "Test message")

    async def test_send_milestone_badge_with_image(self):
        """Should send photo when badge file exists."""
        from src.telegram_bot.notifications import NotificationSender
        bot = AsyncMock()
        sender = NotificationSender(bot=bot)

        # Create a temp file to simulate badge
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image data")
            temp_path = f.name

        try:
            await sender.send_milestone_badge(123, "Badge text", temp_path)
            bot.send_photo.assert_called_once()
            args = bot.send_photo.call_args
            self.assertEqual(args.kwargs['chat_id'], 123)
            self.assertEqual(args.kwargs['caption'], "Badge text")
        finally:
            os.unlink(temp_path)

    async def test_send_milestone_badge_fallback_text(self):
        """Should fallback to text when badge file doesn't exist."""
        from src.telegram_bot.notifications import NotificationSender
        bot = AsyncMock()
        sender = NotificationSender(bot=bot)
        await sender.send_milestone_badge(123, "Badge text", "/nonexistent/path.png")
        bot.send_message.assert_called_once()
        bot.send_photo.assert_not_called()


if __name__ == "__main__":
    unittest.main()
